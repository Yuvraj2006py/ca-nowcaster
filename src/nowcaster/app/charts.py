"""Chart helpers for predictions vs actuals with interval bands.

Inputs: joined prediction+score rows for one model.
Outputs: Altair chart (or None when insufficient data).
Time allowed to know: logged predictions and post-release actuals only.
"""

from __future__ import annotations

import altair as alt
import pandas as pd


def history_frame(joined: pd.DataFrame, model_name: str) -> pd.DataFrame:
    """Filter and shape rows for the history chart.

    Inputs: joined logs; model_name to plot.
    Outputs: DataFrame with month, point, intervals, actual (nullable).
    Time allowed to know: stored log rows for that model only.
    """
    if joined.empty:
        return pd.DataFrame()
    sub = joined.loc[joined["model_name"] == model_name].copy()
    if sub.empty:
        return sub
    sub = sub.sort_values("target_ref_month")
    # One row per month: keep latest prediction.
    sub = sub.drop_duplicates(subset=["target_ref_month"], keep="last")
    return sub.reset_index(drop=True)


def predictions_vs_actuals_chart(joined: pd.DataFrame, model_name: str) -> alt.Chart | None:
    """Build an Altair chart: point forecast, shaded 80/95 bands, actuals.

    Inputs: joined logs; production model_name.
    Outputs: Altair layered chart, or None if nothing to plot.
    Time allowed to know: prediction log + scored actuals.
    """
    hist = history_frame(joined, model_name)
    if hist.empty:
        return None

    base = alt.Chart(hist).encode(
        x=alt.X(
            "target_ref_month:T",
            title="Reference month",
            axis=alt.Axis(format="%b %Y", labelAngle=-35),
        )
    )

    band_95 = base.mark_area(opacity=0.15, color="#4C6A7A").encode(
        y=alt.Y("lower_95:Q", title="MoM GDP growth (pp)"),
        y2="upper_95:Q",
    )
    band_80 = base.mark_area(opacity=0.28, color="#4C6A7A").encode(
        y="lower_80:Q",
        y2="upper_80:Q",
    )
    pred_line = base.mark_line(color="#1F3A4A", strokeWidth=2.2).encode(
        y="point:Q",
        tooltip=[
            alt.Tooltip("target_ref_month:T", title="Month", format="%Y-%m"),
            alt.Tooltip("point:Q", title="Nowcast", format=".3f"),
            alt.Tooltip("lower_80:Q", title="80% low", format=".3f"),
            alt.Tooltip("upper_80:Q", title="80% high", format=".3f"),
            alt.Tooltip("actual:Q", title="Actual", format=".3f"),
        ],
    )
    pred_pts = base.mark_circle(size=45, color="#1F3A4A").encode(y="point:Q")
    layers: list[alt.Chart] = [band_95, band_80, pred_line, pred_pts]

    scored = hist.loc[hist["actual"].notna()]
    if not scored.empty:
        scored_base = alt.Chart(scored).encode(x=alt.X("target_ref_month:T"))
        actuals = scored_base.mark_line(
            color="#C45C26",
            strokeWidth=2,
            strokeDash=[5, 3],
        ).encode(y="actual:Q")
        actual_pts = scored_base.mark_point(color="#C45C26", filled=True, size=55).encode(
            y="actual:Q"
        )
        layers.extend([actuals, actual_pts])

    return (
        alt.layer(*layers)
        .properties(height=320)
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_view(strokeWidth=0)
    )
