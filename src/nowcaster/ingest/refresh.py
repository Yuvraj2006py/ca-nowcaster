"""Refresh all registry series into the raw store.

Inputs: series_registry.yaml entries; live or cached StatCan/Valet responses.
Outputs: RawObservation vintages written with retrieved_at; structured log lines.
Time allowed to know: StatCan releaseTime when present; for Valet (no releaseTime),
release_timestamp is stamped as America/Toronto 16:30 on the observation date
(documented Valet FX publish window) — Quality may refine lags later.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from nowcaster.contracts import RawObservation, SeriesDefinition
from nowcaster.ingest.boc_valet import BocValetClient
from nowcaster.ingest.http import RateLimitedSession
from nowcaster.ingest.registry import load_registry
from nowcaster.ingest.statcan import StatCanClient, product_id_from_table_id
from nowcaster.ingest.store import RawStore, parse_ref_period

logger = logging.getLogger(__name__)

TORONTO = ZoneInfo("America/Toronto")
DEFAULT_BULK_START = "2000-01-01T00:00"
DEFAULT_LATEST_N = 360


@dataclass(frozen=True)
class SeriesRefreshResult:
    series_id: str
    source: str
    fetched: int
    inserted: int
    skipped_duplicates: int


@dataclass(frozen=True)
class RefreshSummary:
    results: list[SeriesRefreshResult]
    store_path: str
    total_rows_after: int

    @property
    def total_fetched(self) -> int:
        return sum(r.fetched for r in self.results)

    @property
    def total_inserted(self) -> int:
        return sum(r.inserted for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.skipped_duplicates for r in self.results)


def configure_logging(level: str | None = None) -> None:
    """Configure root logging for CLI runs."""
    resolved = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )


def refresh_all(
    *,
    registry_path: Path | str | None = None,
    store_path: Path | str | None = None,
    latest_n: int = DEFAULT_LATEST_N,
    bulk_start: str = DEFAULT_BULK_START,
    session: RateLimitedSession | None = None,
) -> RefreshSummary:
    """Pull every registry series and append new vintages to the raw store.

    Inputs: registry path, store path, optional latest_n / bulk_start for StatCan.
    Outputs: RefreshSummary with per-series insert stats.
    Time allowed to know: API release stamps; retrieved_at = UTC now at fetch time.
    """
    series_list = load_registry(registry_path)
    if not series_list:
        raise RuntimeError(
            "series_registry.yaml has no verified series; refusing to refresh an empty registry"
        )

    http = session or RateLimitedSession()
    statcan = StatCanClient(session=http)
    valet = BocValetClient(session=http)
    store = RawStore(store_path)

    results: list[SeriesRefreshResult] = []
    try:
        for definition in series_list:
            logger.info(
                "Refreshing %s (%s / %s)",
                definition.series_id,
                definition.source,
                definition.name,
            )
            retrieved_at = datetime.now(UTC)
            if definition.source == "statcan":
                observations = _fetch_statcan(
                    statcan,
                    definition,
                    latest_n=latest_n,
                    bulk_start=bulk_start,
                    retrieved_at=retrieved_at,
                )
            elif definition.source == "boc_valet":
                observations = _fetch_valet(
                    valet, definition, latest_n=latest_n, retrieved_at=retrieved_at
                )
            else:
                raise RuntimeError(f"Unsupported source: {definition.source}")

            insert_result = store.insert_observations(observations)
            result = SeriesRefreshResult(
                series_id=definition.series_id,
                source=definition.source,
                fetched=len(observations),
                inserted=insert_result.inserted,
                skipped_duplicates=insert_result.skipped_duplicates,
            )
            results.append(result)
            logger.info(
                "  %s: fetched=%s inserted=%s skipped_duplicates=%s",
                definition.series_id,
                result.fetched,
                result.inserted,
                result.skipped_duplicates,
            )
        total = store.count_rows()
    finally:
        store.close()

    summary = RefreshSummary(
        results=results, store_path=str(store.path), total_rows_after=total
    )
    logger.info(
        "Refresh complete: series=%s fetched=%s inserted=%s skipped=%s store_rows=%s path=%s",
        len(results),
        summary.total_fetched,
        summary.total_inserted,
        summary.total_skipped,
        summary.total_rows_after,
        summary.store_path,
    )
    return summary


def _fetch_statcan(
    client: StatCanClient,
    definition: SeriesDefinition,
    *,
    latest_n: int,
    bulk_start: str,
    retrieved_at: datetime,
) -> list[RawObservation]:
    assert definition.table_id and definition.vector_id
    product_id = product_id_from_table_id(definition.table_id)
    # Confirm cube still resolves (metadata check each refresh).
    meta = client.get_cube_metadata(product_id)
    logger.info(
        "  StatCan cube %s title=%r releaseTime=%s",
        product_id,
        meta.get("cubeTitleEn"),
        meta.get("releaseTime"),
    )

    vector_id = int(str(definition.vector_id).lstrip("vV"))
    end_release = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M")
    try:
        bulk = client.get_bulk_range([vector_id], bulk_start, end_release)
        points = bulk.get(vector_id, [])
    except Exception as exc:  # noqa: BLE001 — fall back to latest-N
        logger.warning(
            "  Bulk range failed for %s (%s); falling back to latest N=%s",
            definition.series_id,
            exc,
            latest_n,
        )
        points = client.get_latest_n_periods(vector_id, latest_n=latest_n)

    if not points:
        points = client.get_latest_n_periods(vector_id, latest_n=latest_n)

    return [
        _statcan_point_to_observation(definition.series_id, point, retrieved_at)
        for point in points
        if point.get("value") is not None
    ]


def _statcan_point_to_observation(
    series_id: str, point: dict, retrieved_at: datetime
) -> RawObservation:
    ref = parse_ref_period(str(point["refPer"]))
    release_raw = point.get("releaseTime")
    if not release_raw:
        raise RuntimeError(f"StatCan point missing releaseTime: {point}")
    release_ts = _parse_statcan_release(str(release_raw))
    return RawObservation(
        series_id=series_id,
        ref_period=ref,
        value=float(point["value"]),
        release_timestamp=release_ts,
        retrieved_at=retrieved_at,
    )


def _parse_statcan_release(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    # WDS often returns 'YYYY-MM-DDTHH:MM' without seconds/offset — treat as Toronto local.
    if len(text) == 16 and "T" in text:
        dt = datetime.strptime(text, "%Y-%m-%dT%H:%M")
        return dt.replace(tzinfo=TORONTO).astimezone(UTC)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TORONTO)
    return dt.astimezone(UTC)


def _fetch_valet(
    client: BocValetClient,
    definition: SeriesDefinition,
    *,
    latest_n: int,
    retrieved_at: datetime,
) -> list[RawObservation]:
    assert definition.valet_series
    name = definition.valet_series
    detail, observations = client.get_observations(name, recent=max(latest_n, 24))
    logger.info(
        "  Valet series %s label=%r frequency=%s",
        name,
        detail.get("label"),
        (detail.get("metadata") or {}).get("frequency") or detail.get("dateFormat"),
    )
    rows: list[RawObservation] = []
    for obs in observations:
        try:
            date_str, value = BocValetClient.parse_observation_value(obs, name)
        except Exception as exc:  # noqa: BLE001 — skip empty/partial cells
            logger.debug("  Skipping Valet obs %s: %s", obs, exc)
            continue
        ref = parse_ref_period(date_str)
        release_ts = _valet_release_timestamp(ref)
        rows.append(
            RawObservation(
                series_id=definition.series_id,
                ref_period=ref,
                value=value,
                release_timestamp=release_ts,
                retrieved_at=retrieved_at,
            )
        )
    return rows


def _valet_release_timestamp(ref_period: date) -> datetime:
    """Stamp Valet release time when the API omits one.

    Inputs: observation reference date.
    Outputs: America/Toronto 16:30 on that date, as UTC.
    Time allowed to know: uses observation date only; 16:30 ET matches Valet's
    documented FX publish window. Conservative relative to inventing earlier times.
    """
    local = datetime.combine(ref_period, time(16, 30), tzinfo=TORONTO)
    return local.astimezone(UTC)


def run_double_refresh(
    *,
    registry_path: Path | str | None = None,
    store_path: Path | str | None = None,
) -> tuple[RefreshSummary, RefreshSummary]:
    """Run refresh twice; second pass should insert 0 new rows if vintages match.

    Inputs/outputs/time: same as refresh_all.
    """
    first = refresh_all(registry_path=registry_path, store_path=store_path)
    second = refresh_all(registry_path=registry_path, store_path=store_path)
    if second.total_inserted != 0:
        logger.error(
            "Second refresh inserted %s rows; expected 0 (duplicate prevention failed)",
            second.total_inserted,
        )
    else:
        logger.info("Second refresh inserted 0 rows (no duplicates).")
    return first, second
