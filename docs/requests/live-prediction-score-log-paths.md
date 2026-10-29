# Request: Live Pipeline — prediction/score log paths for the dashboard

**From:** Dashboard Engineer (Role 7)
**To:** Live Pipeline Engineer (Role 6)
**Date:** 2026-10-29

## Need

The Streamlit app reads **only** append-only logs matching
`contracts.PREDICTION_LOG_COLUMNS` and `contracts.SCORE_COLUMNS`.
Please write:

| Artifact | Default path | Formats |
|----------|--------------|---------|
| Predictions | `data/logs/predictions.csv` | `.csv` (preferred) or `.parquet` |
| Scores | `data/logs/scores.csv` | `.csv` or `.parquet` |
| Optional meta | `data/logs/dashboard_meta.json` | JSON |

Overrides via env (already in `.env.example`):

- `NOWCASTER_PREDICTION_LOG`
- `NOWCASTER_SCORE_LOG`
- `NOWCASTER_DASHBOARD_META`
- `NOWCASTER_PRODUCTION_MODEL` (default `ar1`)
- `NOWCASTER_BASELINE_MODEL` (default `last_value`)

## Behavior if missing

If the prediction log is absent or empty, the dashboard falls back to bundled
fixtures and shows a “sample logs” banner. Production remains **AR(1)** until
Evaluation clears a better candidate (honest-result rule).

## Please also

- Log both production (`ar1` for now) and comparison baseline (`last_value`)
  rows for the same `target_ref_month` so the headline can show them side by side.
- Do not require the dashboard to call StatCan/BoC.
