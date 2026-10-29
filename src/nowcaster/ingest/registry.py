"""Load and validate series_registry.yaml into SeriesDefinition objects.

Inputs: path to series_registry.yaml.
Outputs: list of SeriesDefinition (contracts).
Time allowed to know: registry metadata only (verified_at notes); no observation values.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from nowcaster.contracts import SeriesDefinition

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "series_registry.yaml"

ALLOWED_SOURCES = {"statcan", "boc_valet"}
ALLOWED_ROLES = {"primary_target", "secondary_target", "indicator"}


class RegistryError(ValueError):
    """Invalid registry contents."""


def load_registry(path: Path | str | None = None) -> list[SeriesDefinition]:
    """Parse series_registry.yaml into SeriesDefinition rows.

    Inputs: optional filesystem path (defaults to repo-root series_registry.yaml).
    Outputs: list of SeriesDefinition; empty list if series: [].
    Time allowed to know: verified_at timestamps recorded in the YAML only.
    """
    registry_path = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    if not isinstance(raw, dict) or "series" not in raw:
        raise RegistryError(f"{registry_path} must contain a top-level 'series' key")
    series = raw["series"]
    if series is None:
        return []
    if not isinstance(series, list):
        raise RegistryError("'series' must be a list")

    out: list[SeriesDefinition] = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(series):
        if not isinstance(item, dict):
            raise RegistryError(f"series[{idx}] must be a mapping")
        definition = _parse_entry(item, idx=idx)
        if definition.series_id in seen_ids:
            raise RegistryError(f"Duplicate series_id: {definition.series_id}")
        seen_ids.add(definition.series_id)
        out.append(definition)
    return out


def _parse_entry(item: dict[str, Any], *, idx: int) -> SeriesDefinition:
    required = [
        "series_id",
        "source",
        "name",
        "frequency",
        "unit",
        "verification_notes",
        "target_role",
    ]
    for key in required:
        if key not in item or item[key] in (None, ""):
            raise RegistryError(f"series[{idx}] missing required field '{key}'")

    source = str(item["source"])
    if source not in ALLOWED_SOURCES:
        raise RegistryError(f"series[{idx}] invalid source: {source}")

    role = str(item["target_role"])
    if role not in ALLOWED_ROLES:
        raise RegistryError(f"series[{idx}] invalid target_role: {role}")

    table_id = item.get("table_id")
    vector_id = item.get("vector_id")
    valet_series = item.get("valet_series")

    if source == "statcan":
        if not table_id or not vector_id:
            raise RegistryError(
                f"series[{idx}] statcan entries require table_id and vector_id"
            )
        if valet_series not in (None, ""):
            raise RegistryError(f"series[{idx}] statcan entry must have valet_series: null")
        valet_series = None
    else:
        if not valet_series:
            raise RegistryError(f"series[{idx}] boc_valet entries require valet_series")
        if table_id not in (None, "") or vector_id not in (None, ""):
            raise RegistryError(
                f"series[{idx}] boc_valet entry must have table_id/vector_id null"
            )
        table_id = None
        vector_id = None

    verified_at = _parse_verified_at(item.get("verified_at"), idx=idx)

    return SeriesDefinition(
        series_id=str(item["series_id"]),
        source=source,
        table_id=str(table_id) if table_id is not None else None,
        vector_id=str(vector_id) if vector_id is not None else None,
        valet_series=str(valet_series) if valet_series is not None else None,
        name=str(item["name"]),
        frequency=str(item["frequency"]),
        unit=str(item["unit"]),
        verified_at=verified_at,
        verification_notes=str(item["verification_notes"]),
        target_role=role,
    )


def _parse_verified_at(value: Any, *, idx: int) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise RegistryError(f"series[{idx}] verified_at must be an ISO-8601 string")
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise RegistryError(f"series[{idx}] invalid verified_at: {value}") from exc
