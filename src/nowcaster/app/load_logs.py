"""Load prediction and score logs for the dashboard.

Inputs: on-disk CSV/Parquet logs written by the live pipeline (or bundled fixtures).
Outputs: typed DataFrames aligned to contracts.PREDICTION_LOG_COLUMNS / SCORE_COLUMNS.
Time allowed to know: whatever was public when each row was logged; this module
never calls external APIs and never invents observations.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from nowcaster.contracts import PREDICTION_LOG_COLUMNS, SCORE_COLUMNS

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
_DEFAULT_PRED = Path("data/logs/predictions.csv")
_DEFAULT_SCORE = Path("data/logs/scores.csv")
_DEFAULT_META = Path("data/logs/dashboard_meta.json")

BOOL_PRED_COLS = ("direction_beat_prev",)
BOOL_SCORE_COLS = ("actual_in_80", "actual_in_95", "direction_correct")


@dataclass(frozen=True)
class DashboardBundle:
    """Everything the Streamlit page needs from disk.

    Inputs: resolved prediction/score frames plus meta flags.
    Outputs: immutable bundle for UI rendering.
    Time allowed to know: log contents only (no live fetches).
    """

    predictions: pd.DataFrame
    scores: pd.DataFrame
    joined: pd.DataFrame
    meta: dict
    source: str  # "live" | "fixture"
    production_model: str
    baseline_model: str


def fixture_dir() -> Path:
    """Return the bundled sample-log directory (never shown to end users)."""
    return _FIXTURE_DIR


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    return Path(raw) if raw else default


def _read_table(path: Path) -> pd.DataFrame:
    """Read a CSV or Parquet log file.

    Inputs: path ending in .csv / .parquet / .pq.
    Outputs: DataFrame (may be empty).
    Time allowed to know: file contents only.
    """
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported log format: {suffix}")


def _coerce_predictions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(PREDICTION_LOG_COLUMNS))
    out = df.copy()
    for col in PREDICTION_LOG_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    out = out.loc[:, list(PREDICTION_LOG_COLUMNS)]
    out["target_ref_month"] = pd.to_datetime(out["target_ref_month"]).dt.normalize()
    out["predicted_at"] = pd.to_datetime(out["predicted_at"], utc=False)
    for c in ("point", "lower_80", "upper_80", "lower_95", "upper_95"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    for c in BOOL_PRED_COLS:
        out[c] = _to_nullable_bool(out[c])
    return out.sort_values(["target_ref_month", "model_name", "predicted_at"]).reset_index(
        drop=True
    )


def _coerce_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(SCORE_COLUMNS))
    out = df.copy()
    for col in SCORE_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    out = out.loc[:, list(SCORE_COLUMNS)]
    out["scored_at"] = pd.to_datetime(out["scored_at"], utc=False)
    for c in ("actual", "error", "abs_error", "squared_error"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    for c in BOOL_SCORE_COLS:
        out[c] = _to_nullable_bool(out[c])
    return out.reset_index(drop=True)


def _to_nullable_bool(series: pd.Series) -> pd.Series:
    def one(v: object) -> bool | pd.NA:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return pd.NA
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in {"", "nan", "none", "<na>"}:
            return pd.NA
        if s in {"1", "true", "t", "yes"}:
            return True
        if s in {"0", "false", "f", "no"}:
            return False
        return pd.NA

    return series.map(one).astype("boolean")


def _join(predictions: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty:
        return predictions.copy()
    if scores.empty:
        out = predictions.copy()
        for c in SCORE_COLUMNS:
            if c == "prediction_id":
                continue
            out[c] = pd.NA
        return out
    return predictions.merge(scores, on="prediction_id", how="left")


def _load_meta(path: Path | None, *, using_fixture: bool) -> dict:
    defaults = {
        "production_model": os.environ.get("NOWCASTER_PRODUCTION_MODEL", "ar1"),
        "baseline_model": os.environ.get("NOWCASTER_BASELINE_MODEL", "last_value"),
        "reference_baseline": "ar1",
        "honest_verdict": (
            "Phase 3 evaluation found no candidate model beats the AR(1) baseline "
            "on headline RMSE with statistical support. Production nowcast uses AR(1) "
            "until a candidate clearly wins."
        ),
        "using_sample_logs": using_fixture,
    }
    candidates = []
    if path is not None:
        candidates.append(path)
    if using_fixture:
        candidates.append(_FIXTURE_DIR / "dashboard_meta.json")
    for cand in candidates:
        if cand.exists():
            raw = json.loads(cand.read_text(encoding="utf-8"))
            merged = {**defaults, **raw}
            merged["using_sample_logs"] = using_fixture
            return merged
    return defaults


def live_logs_available(
    pred_path: Path | None = None,
    score_path: Path | None = None,
) -> bool:
    """True when live prediction log exists and has at least one row.

    Inputs: optional overrides for prediction/score paths.
    Outputs: bool.
    Time allowed to know: file presence/size only.
    """
    pred = pred_path or _env_path("NOWCASTER_PREDICTION_LOG", _DEFAULT_PRED)
    df = _read_table(pred)
    return not df.empty


def load_dashboard_bundle(
    *,
    pred_path: Path | None = None,
    score_path: Path | None = None,
    meta_path: Path | None = None,
    prefer_fixture: bool = False,
) -> DashboardBundle:
    """Load prediction + score logs, falling back to bundled fixtures.

    Inputs: optional path overrides; prefer_fixture forces sample logs.
    Outputs: DashboardBundle (never empty predictions when fixtures ship).
    Time allowed to know: stored logs only — no StatCan/BoC/network calls.
    """
    pred = pred_path or _env_path("NOWCASTER_PREDICTION_LOG", _DEFAULT_PRED)
    score = score_path or _env_path("NOWCASTER_SCORE_LOG", _DEFAULT_SCORE)
    meta_p = meta_path or _env_path("NOWCASTER_DASHBOARD_META", _DEFAULT_META)

    use_fixture = prefer_fixture or not live_logs_available(pred, score)
    source = "fixture" if use_fixture else "live"
    if use_fixture:
        pred = _FIXTURE_DIR / "predictions.csv"
        score = _FIXTURE_DIR / "scores.csv"
        meta_p = _FIXTURE_DIR / "dashboard_meta.json"

    predictions = _coerce_predictions(_read_table(pred))
    scores = _coerce_scores(_read_table(score))
    meta = _load_meta(meta_p, using_fixture=use_fixture)
    production = str(meta.get("production_model", "ar1"))
    baseline = str(meta.get("baseline_model", "last_value"))
    joined = _join(predictions, scores)
    return DashboardBundle(
        predictions=predictions,
        scores=scores,
        joined=joined,
        meta=meta,
        source=source,
        production_model=production,
        baseline_model=baseline,
    )
