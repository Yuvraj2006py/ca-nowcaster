"""Plain-language copy for How it works / Limits tabs.

No data I/O. Safe static strings for the Streamlit UI.
"""

from __future__ import annotations

HOW_IT_WORKS = """
### What is a nowcast?

Official monthly GDP for Canada arrives weeks after the month ends.
A **nowcast** is an early estimate of that number — a forecast of the *present* —
using faster indicators (jobs, retail, manufacturing, prices, exchange rates)
that show up sooner.

### What you are looking at

1. **This month's nowcast** — our point estimate of month-over-month real GDP
   growth, with 80% and 95% ranges. Beside it: a simple baseline for comparison.
2. **History chart** — past nowcasts (line + shaded ranges) vs the official
   number once it is published (dashed orange).
3. **Scoreboard** — how accurate those past nowcasts were: error vs the
   AR(1) baseline, whether actuals fell inside our ranges, and whether we
   got the direction of change right.

### How the pipeline works

- Public Statistics Canada and Bank of Canada data are refreshed on a schedule.
- Features are built with a hard cutoff: only values that were already public
  as of that date (no peeking at future releases).
- A model writes a prediction **before** the official GDP release.
- After the release, we score ourselves and update the scoreboard.

This page **only reads stored logs**. It does not call live data APIs.
"""

LIMITS = """
### Honest limits

- **No candidate beat AR(1).** Walk-forward evaluation (Phase 3) found that
  bridge, dynamic-factor, and gradient-boosting candidates did **not** clearly
  beat a simple AR(1) baseline on headline RMSE with statistical support
  (Diebold-Mariano + bootstrap). Direction classifiers are scored separately.
- **Production model is AR(1)** until a candidate wins a fair rematch.
  The headline baseline shown beside it is a last-value naive forecast.
- **Sample logs may be on screen.** If the live prediction log is empty,
  the page shows bundled sample history so the UI is reviewable. That is
  labeled at the top — not real live GDP nowcasts.
- **Uncertainty is real.** 80%/95% bands are model-based intervals, not
  guarantees. Coverage on the scoreboard should be near 80%/95% if calibrated.
- **Not advice.** This is a public research demo for Canadian GDP growth
  nowcasting. It is not investment, trading, or policy advice.
- **Revisions happen.** Statistics Canada revises history; scores use the
  vintage available when we scored.
"""


def month_label(ts) -> str:
    """Format a timestamp as 'August 2024' for the headline."""
    return ts.strftime("%B %Y")
