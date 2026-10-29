# Model card — ca-nowcaster v1

**Production model:** `ar1` @ `0.1.0` (`nowcaster.models.baselines.AR1Baseline`)  
**Status:** Shipped under the honest-result rule (Phase 3 / Phase 5).  
**Owner docs:** Evaluation Skeptic verdicts in [`evaluation_report.md`](evaluation_report.md);
live wiring in [`live_pipeline.md`](live_pipeline.md).

## Intended use

- **Primary:** Point nowcast of Canadian monthly real GDP MoM growth at basic prices
  (target derived from StatCan table `36-10-0434-01` / registry series
  `ca_gdp_basic_prices`), issued **before** the official release for that month.
- **Secondary (eval only):** Direction — whether growth beats the previous month
  (classifier candidates; not the production point nowcast).
- **Audience:** Portfolio / interview demo of leakage-safe economic ML and honest
  evaluation — not trading advice, betting, or policy decisions.

## Data

| Kind | Source | Notes |
|------|--------|--------|
| Target levels | Statistics Canada WDS | Verified in `series_registry.yaml` (table / vector IDs) |
| Indicators | StatCan + Bank of Canada Valet | Employment/hours, CPI, retail, manufacturing, housing, policy rate, FX, commodities — only after metadata verification |
| Store | Append-only vintages | `series_id`, `ref_period`, `value`, `release_timestamp`, `retrieved_at` |
| Features | `build_features(as_of_date)` | Uses only values with `release_timestamp <= as_of_date` |
| Eval panel (reported metrics) | Synthetic monthly panel | 2015-01..2022-12; COVID headline exclusion 2020-03..2020-08; holdout = final 24 months |

Public endpoints only for v1; no paid data and no API keys required.

## Evaluation summary (from `docs/evaluation_report.md` only)

**Loud verdict:** No regression candidate beats reference baseline `ar1` on headline
RMSE with Diebold-Mariano and bootstrap CI support. Direction models are scored
separately. v1 still ships.

Walk-forward (expanding window, holdout excluded; headline n = 42 for regression models):

| Model | Role | Headline RMSE | RMSE ratio vs ar1 | Cov80 | Cov95 | Beats ref? |
|-------|------|---------------|-------------------|-------|-------|------------|
| `ar1` | baseline (production) | 0.5876 | 1.0000 | 0.857 | 0.905 | (reference) |
| `last_value` | baseline | 0.5642 | 0.9601 | 0.786 | 0.881 | no |
| `rolling_mean` | baseline | 0.6174 | 1.0507 | 0.738 | 0.905 | no |
| `bridge` | candidate | 0.0652 | 0.1110 | 0.762 | 0.857 | no |
| `dynamic_factor` | candidate | 0.7193 | 1.2242 | 0.786 | 0.857 | no |
| `gradient_boosting` | candidate | 0.2578 | 0.4388 | 0.905 | 0.976 | no |

Why “no” for bridge / GBM despite lower point RMSE: Diebold-Mariano and/or 95%
bootstrap RMSE-ratio CI did not clear the skeptic bar (see per-model verdicts in
the evaluation report). Example: `bridge` DM p = 0.2641; `gradient_boosting`
bootstrap CI upper = 1.5349.

Direction classifiers (headline, not MoM RMSE vs AR(1)):

- `direction_classifier@0.1.0`: accuracy = 0.7804878048780488, F1 = 0.8 (n = 41)
- `direction_boosting@0.1.0`: accuracy = 0.3170731707317073, F1 = 0.3333333333333333 (n = 41)

Holdout burned **once** per final candidate `@0.1.0` (n = 24); see
[`holdout_log.md`](holdout_log.md). Live StatCan re-score needs a version bump.

## Training / prediction protocol

1. Fit only on rows whose features were built with a valid as-of cutoff.
2. Predict point + 80% / 95% intervals (`PredictionIntervals` in `contracts.py`).
3. Append prediction to the public log **before** the official release.
4. Score after the actual’s `release_timestamp` (append-only score log).

Production jobs use `ar1` only (`src/nowcaster/live/production.py`).

## Failure modes

| Mode | What happens | Mitigation |
|------|----------------|------------|
| Look-ahead / leakage | Model sees unpublished values | `as_of` gate, feature leakage tests, Evaluation audits |
| Overconfident intervals | Actual outside 80%/95% bands more than labeled rate | Report coverage; AR(1) headline Cov80 = 0.857, Cov95 = 0.905 |
| Candidate looks better in-sample | Point RMSE ratio &lt; 1 without significance | Require DM + bootstrap; honest-result ships baseline |
| Data revisions | Later vintage changes history | Append-only vintages; revision deep-dive deferred to `BACKLOG.md` |
| Ingest outage | Stale store | Skip predict; log failure; never forecast on stale data |
| Holdout burned twice | Inflated final claim | Once-per-version lock + CI holdout-guard |

See also [`failure_modes.md`](failure_modes.md) and [`security_review.md`](security_review.md).

## Out of scope / misuse

Do not use for trading, betting, credit decisions, or as a substitute for Statistics
Canada releases. Deep learning, paid feeds, user accounts, and regional breakdowns
are frozen out of v1 (`AGENTS.md` / `BACKLOG.md`).

## How this card could be wrong

- Synthetic-panel metrics may not match live StatCan skill after refresh.
- Bootstrap of OOS residuals ignores re-fit uncertainty (Evaluation caveat).
- Regime shifts (COVID, policy) can break Diebold-Mariano assumptions.
