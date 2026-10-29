"""Aggregate scoreboard metrics from joined prediction/score logs.

Inputs: joined DataFrame from load_logs (contracts columns + score columns).
Outputs: plain metric dicts for the Streamlit scoreboard.
Time allowed to know: scored rows only (actuals after release); unscored rows ignored.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ModelScorecard:
    """One model's scored performance summary."""

    model_name: str
    n: int
    rmse: float | None
    mae: float | None
    rmse_ratio_vs_reference: float | None
    coverage_80: float | None
    coverage_95: float | None
    direction_accuracy: float | None

    def as_display(self) -> dict[str, str]:
        """Human-readable strings for the UI (no file paths)."""
        return {
            "Model": self.model_name,
            "Sample size": str(self.n),
            "RMSE": _fmt(self.rmse),
            "RMSE / AR(1)": _fmt(self.rmse_ratio_vs_reference),
            "80% coverage": _pct(self.coverage_80),
            "95% coverage": _pct(self.coverage_95),
            "Direction accuracy": _pct(self.direction_accuracy),
        }


@dataclass(frozen=True)
class HeadlineNowcast:
    """Latest production nowcast beside the comparison baseline."""

    target_ref_month: pd.Timestamp
    predicted_at: pd.Timestamp
    production_model: str
    production_point: float
    production_lower_80: float
    production_upper_80: float
    production_lower_95: float
    production_upper_95: float
    baseline_model: str
    baseline_point: float | None
    baseline_lower_80: float | None
    baseline_upper_80: float | None
    scored: bool


def _fmt(v: float | None, digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "—"
    return f"{v:.{digits}f}"


def _pct(v: float | None) -> str:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "—"
    return f"{100.0 * v:.0f}%"


def _scored_subset(joined: pd.DataFrame, model_name: str) -> pd.DataFrame:
    if joined.empty:
        return joined
    mask = (joined["model_name"] == model_name) & joined["actual"].notna()
    return joined.loc[mask].copy()


def _rmse(errors_sq: pd.Series) -> float | None:
    if errors_sq.empty:
        return None
    return float(np.sqrt(np.mean(errors_sq.to_numpy(dtype=float))))


def _mean_bool(series: pd.Series) -> float | None:
    clean = series.dropna()
    if clean.empty:
        return None
    return float(clean.astype(bool).mean())


def build_scorecard(
    joined: pd.DataFrame,
    model_name: str,
    *,
    reference_model: str = "ar1",
    reference_rmse: float | None = None,
) -> ModelScorecard:
    """Compute scoreboard metrics for one model.

    Inputs: joined logs; model_name; optional precomputed reference RMSE.
    Outputs: ModelScorecard.
    Time allowed to know: scored prediction rows only.
    """
    sub = _scored_subset(joined, model_name)
    n = int(len(sub))
    if n == 0:
        return ModelScorecard(
            model_name=model_name,
            n=0,
            rmse=None,
            mae=None,
            rmse_ratio_vs_reference=None,
            coverage_80=None,
            coverage_95=None,
            direction_accuracy=None,
        )
    rmse = _rmse(sub["squared_error"])
    mae = float(sub["abs_error"].mean()) if sub["abs_error"].notna().any() else None
    if reference_rmse is None:
        if reference_model == model_name:
            reference_rmse = rmse
        else:
            ref_sub = _scored_subset(joined, reference_model)
            reference_rmse = _rmse(ref_sub["squared_error"]) if not ref_sub.empty else None
    ratio = None
    if rmse is not None and reference_rmse is not None and reference_rmse > 0:
        ratio = rmse / reference_rmse
    return ModelScorecard(
        model_name=model_name,
        n=n,
        rmse=rmse,
        mae=mae,
        rmse_ratio_vs_reference=ratio,
        coverage_80=_mean_bool(sub["actual_in_80"]),
        coverage_95=_mean_bool(sub["actual_in_95"]),
        direction_accuracy=_mean_bool(sub["direction_correct"]),
    )


def build_scoreboard(
    joined: pd.DataFrame,
    *,
    production_model: str = "ar1",
    baseline_model: str = "last_value",
    reference_model: str = "ar1",
) -> list[ModelScorecard]:
    """Scoreboard rows: production first, then baseline if distinct.

    Inputs: joined logs and model name roles from dashboard meta.
    Outputs: ordered list of ModelScorecard.
    Time allowed to know: scored rows only.
    """
    ref = build_scorecard(joined, reference_model, reference_model=reference_model)
    cards = [
        build_scorecard(
            joined,
            production_model,
            reference_model=reference_model,
            reference_rmse=ref.rmse,
        )
    ]
    if baseline_model != production_model:
        cards.append(
            build_scorecard(
                joined,
                baseline_model,
                reference_model=reference_model,
                reference_rmse=ref.rmse,
            )
        )
    return cards


def latest_headline(
    predictions: pd.DataFrame,
    scores: pd.DataFrame,
    *,
    production_model: str,
    baseline_model: str,
) -> HeadlineNowcast | None:
    """Pick the latest production prediction and matching baseline.

    Inputs: prediction/score frames; production and baseline model names.
    Outputs: HeadlineNowcast or None if no production rows.
    Time allowed to know: prediction log as written; does not require actuals.
    """
    if predictions.empty:
        return None
    prod = predictions.loc[predictions["model_name"] == production_model]
    if prod.empty:
        return None
    latest_month = prod["target_ref_month"].max()
    row = prod.loc[prod["target_ref_month"] == latest_month].sort_values("predicted_at").iloc[-1]
    base = predictions.loc[
        (predictions["model_name"] == baseline_model)
        & (predictions["target_ref_month"] == latest_month)
    ]
    base_row = base.sort_values("predicted_at").iloc[-1] if not base.empty else None
    scored_ids = set(scores["prediction_id"].tolist()) if not scores.empty else set()
    return HeadlineNowcast(
        target_ref_month=pd.Timestamp(row["target_ref_month"]),
        predicted_at=pd.Timestamp(row["predicted_at"]),
        production_model=production_model,
        production_point=float(row["point"]),
        production_lower_80=float(row["lower_80"]),
        production_upper_80=float(row["upper_80"]),
        production_lower_95=float(row["lower_95"]),
        production_upper_95=float(row["upper_95"]),
        baseline_model=baseline_model,
        baseline_point=None if base_row is None else float(base_row["point"]),
        baseline_lower_80=None if base_row is None else float(base_row["lower_80"]),
        baseline_upper_80=None if base_row is None else float(base_row["upper_80"]),
        scored=row["prediction_id"] in scored_ids,
    )


def scorecards_as_records(cards: list[ModelScorecard]) -> list[dict]:
    """Serialize scorecards for tests / non-Streamlit callers."""
    return [asdict(c) for c in cards]
