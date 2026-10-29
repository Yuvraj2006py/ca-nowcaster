# Request: Feature → Modeling + Evaluation

From: Feature Engineer (Role 3)
To: Modeling Engineer (Role 4), Evaluation Skeptic (Role 5)
Date: 2026-10-29

## Need

Phase 2 gate requires **baselines run end-to-end through the backtest harness**.
Feature owns leakage-safe `build_features` + `docs/feature_summary.md` and added
Feature-half assertions in `tests/gates/test_phase_2.py`.

Please add Modeling/Evaluation assertions to the same gate module (or sibling
`tests/gates/test_phase_2_*.py`) without editing `src/nowcaster/features/`:

1. Baselines (last value, AR(1), rolling mean) implement the model contract.
2. Evaluation harness can call `MonthlyFeatureBuilder.build_features(as_of)` and
   run an expanding-window backtest on those baselines.
3. Gate test: at least one baseline completes a walk-forward on fixture features.

## Integration contract

```python
from nowcaster.features import MonthlyFeatureBuilder, FeatureRecipe

builder = MonthlyFeatureBuilder(raw_store_df, series_meta=..., recipe=FeatureRecipe())
X, meta = builder.build_features(as_of_date)
# X.index.name == "ref_month" (Period[M]); meta.features_hash is SHA-256 hex
```

Ragged-edge strategies: `leave_missing` (default), `carry`, `ar1`.

## Out of scope for this request

Do not change feature or quality code. Feature will not edit `src/nowcaster/models/`
or `src/nowcaster/evaluation/`.
