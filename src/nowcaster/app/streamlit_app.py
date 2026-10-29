"""ca-nowcaster public dashboard (Streamlit).

Reads ONLY stored prediction/score logs (or bundled fixtures). No live API calls.
No free-text user input. Does not display filesystem paths.
"""

from __future__ import annotations

import streamlit as st

from nowcaster.app.charts import predictions_vs_actuals_chart
from nowcaster.app.copy_text import HOW_IT_WORKS, LIMITS, month_label
from nowcaster.app.load_logs import load_dashboard_bundle
from nowcaster.app.scoreboard import build_scoreboard, latest_headline


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 920px; }
        h1 { font-size: 1.65rem !important; letter-spacing: -0.02em; }
        .nc-kicker { color: #5A6A72; font-size: 0.85rem; margin-bottom: 0.15rem; }
        .nc-point { font-size: 2.4rem; font-weight: 700; line-height: 1.1; color: #1F3A4A; }
        .nc-range { color: #3D5560; font-size: 0.95rem; margin-top: 0.25rem; }
        .nc-card {
            background: linear-gradient(160deg, #F4F7F8 0%, #E8EEF1 100%);
            border: 1px solid #D2DCE2;
            border-radius: 10px;
            padding: 1rem 1.1rem;
            height: 100%;
        }
        .nc-label {
          font-size: 0.78rem; text-transform: uppercase;
          letter-spacing: 0.04em; color: #5A6A72;
        }
        .nc-note { font-size: 0.9rem; color: #3D5560; }
        div[data-testid="stMetricValue"] { font-size: 1.35rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fmt_pp(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f} pp"


def render() -> None:
    """Render the recruiter-friendly dashboard page.

    Inputs: none (loads logs via load_dashboard_bundle).
    Outputs: Streamlit UI side effects only.
    Time allowed to know: stored logs / fixtures; never live APIs.
    """
    st.set_page_config(
        page_title="ca-nowcaster",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    _inject_style()

    bundle = load_dashboard_bundle()
    headline = latest_headline(
        bundle.predictions,
        bundle.scores,
        production_model=bundle.production_model,
        baseline_model=bundle.baseline_model,
    )
    cards = build_scoreboard(
        bundle.joined,
        production_model=bundle.production_model,
        baseline_model=bundle.baseline_model,
        reference_model=str(bundle.meta.get("reference_baseline", "ar1")),
    )

    st.title("Canada GDP nowcast")
    st.caption(
        "Month-over-month real GDP growth at basic prices — estimated before the "
        "official Statistics Canada release, then scored when the number lands."
    )

    if bundle.source == "fixture" or bundle.meta.get("using_sample_logs"):
        st.info(
            "Showing **sample logs** so the page is reviewable. "
            "Live predictions will appear here once the scheduled pipeline writes them."
        )

    st.warning(
        str(
            bundle.meta.get(
                "honest_verdict",
                "Phase 3 evaluation found no candidate model beats the AR(1) baseline. "
                "Production nowcast uses AR(1).",
            )
        )
    )

    # --- Headline ---
    st.subheader("This month")
    if headline is None:
        st.write("No nowcast logged yet.")
    else:
        status = "awaiting official release" if not headline.scored else "already scored"
        st.markdown(
            f"<div class='nc-kicker'>{month_label(headline.target_ref_month)}"
            f" · logged · {status}</div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"""
                <div class="nc-card">
                  <div class="nc-label">Nowcast · {headline.production_model}</div>
                  <div class="nc-point">{_fmt_pp(headline.production_point)}</div>
                  <div class="nc-range">80%: {_fmt_pp(headline.production_lower_80)}
                    to {_fmt_pp(headline.production_upper_80)}</div>
                  <div class="nc-range">95%: {_fmt_pp(headline.production_lower_95)}
                    to {_fmt_pp(headline.production_upper_95)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            bl = headline.baseline_model
            st.markdown(
                f"""
                <div class="nc-card">
                  <div class="nc-label">Baseline · {bl}</div>
                  <div class="nc-point">{_fmt_pp(headline.baseline_point)}</div>
                  <div class="nc-range">80%: {_fmt_pp(headline.baseline_lower_80)}
                    to {_fmt_pp(headline.baseline_upper_80)}</div>
                  <div class="nc-note">Simple comparison forecast — not the production pick
                    when they differ.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --- Chart ---
    st.subheader("Past predictions vs actuals")
    chart = predictions_vs_actuals_chart(bundle.joined, bundle.production_model)
    if chart is None:
        st.write("No history to chart yet.")
    else:
        st.altair_chart(chart, use_container_width=True)
        st.caption(
            f"Teal line = {bundle.production_model} nowcast · shaded bands = 80%/95% ranges · "
            "orange dashed = official actual after release."
        )

    # --- Scoreboard ---
    st.subheader("Scoreboard")
    st.caption(
        "RMSE / AR(1) below 1 means better than the reference baseline. "
        "Coverage should land near 80% / 95% if intervals are well calibrated."
    )
    if not cards or all(c.n == 0 for c in cards):
        st.write("No scored predictions yet.")
    else:
        metrics = st.columns(4)
        primary = cards[0]
        with metrics[0]:
            st.metric("RMSE / AR(1)", primary.as_display()["RMSE / AR(1)"])
        with metrics[1]:
            st.metric("80% coverage", primary.as_display()["80% coverage"])
        with metrics[2]:
            st.metric("Direction accuracy", primary.as_display()["Direction accuracy"])
        with metrics[3]:
            st.metric("Sample size", primary.as_display()["Sample size"])
        st.dataframe(
            [c.as_display() for c in cards],
            use_container_width=True,
            hide_index=True,
        )

    # --- Tabs ---
    tab_how, tab_limits = st.tabs(["How it works", "Limits"])
    with tab_how:
        st.markdown(HOW_IT_WORKS)
    with tab_limits:
        st.markdown(LIMITS)


if __name__ == "__main__":
    # `streamlit run` sets __name__ to "__main__"; imports for tests do not render.
    render()
