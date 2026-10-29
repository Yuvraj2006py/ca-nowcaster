"""Typical publication lags for pseudo-real-time history (approximations).

These lags are quality-owned defaults used ONLY when measured release_timestamp
values are missing. They are not StatCan/BoC API fields. Prefer measured
release times from the raw store whenever ingest provides them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_LAGS_PATH = Path(__file__).resolve().parent / "typical_lags.yaml"


@dataclass(frozen=True)
class TypicalLag:
    """Provisional publication lag for one series_id.

    Inputs: quality-owned typical_lags.yaml entry.
    Outputs: lag metadata for pseudo-real-time imputation.
    Time allowed to know: registry metadata only; no observation values.
    """

    series_id: str
    lag_days_after_ref_period_end: int
    notes: str
    approximate: bool = True


def load_typical_lags(path: Path | None = None) -> dict[str, TypicalLag]:
    """Load typical publication lags keyed by series_id.

    Inputs: optional path; default is package typical_lags.yaml.
    Outputs: mapping series_id -> TypicalLag.
    Time allowed to know: lag config only.
    """
    lag_path = path or _DEFAULT_LAGS_PATH
    data = yaml.safe_load(lag_path.read_text(encoding="utf-8"))

    entries: list[dict[str, Any]] = list(data.get("lags") or [])
    out: dict[str, TypicalLag] = {}
    for row in entries:
        lag = TypicalLag(
            series_id=str(row["series_id"]),
            lag_days_after_ref_period_end=int(row["lag_days_after_ref_period_end"]),
            notes=str(row.get("notes") or ""),
            approximate=bool(row.get("approximate", True)),
        )
        out[lag.series_id] = lag
    return out


def lag_days_map(path: Path | None = None) -> dict[str, int]:
    """Convenience map series_id -> lag days for apply_publication_lags.

    Inputs: optional path to typical_lags.yaml.
    Outputs: dict of integer day lags.
    Time allowed to know: lag config only.
    """
    return {sid: lag.lag_days_after_ref_period_end for sid, lag in load_typical_lags(path).items()}
