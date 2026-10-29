# Request: Features → Modeling / Evaluation (Phase 2 baselines)

From: Modeling Engineer (Role 4)
To: Feature Engineer (Role 3)
Date: 2026-10-29
Status: informational — baselines ship with fixtures; no Feature code edited

## Context

Phase 2 baselines (`last_value`, `ar1`, `rolling_mean`) implement
`NowcastModel` and **ignore feature columns**. They only need:

- `y`: 1-d MoM growth aligned to the training index (finite floats, time-ordered)
- `X`: any row-aligned scaffold whose `.shape[0]` (or `len`) is the number of
  periods to score — zero columns is fine

Synthetic fixture used in tests:
`tests/fixtures/models/synthetic_mom_growth.csv`.

## What we need when Features lands

For the Evaluation harness to run baselines end-to-end on real data without
editing `src/nowcaster/models/`:

1. `build_features(as_of_date) -> (DataFrame, FeatureFrameMeta)` with index =
   target reference month.
2. A documented way to obtain the aligned primary target `y` (MoM growth of
   monthly real GDP at basic prices) for rows in that frame, using only
   releases ≤ `as_of_date`.
3. Stable column naming / `features_hash` so prediction logs can record what
   was used (baselines will still ignore columns).

## Out of scope for this request

Do not change model code. Modeling will not edit `src/nowcaster/features/`.
Phase 3 models (bridge, DynamicFactorMQ, boosting, classifiers) will file a
separate request for required columns once Phase 2 gates.
