# Evaluation harness (Phase 2)

Owned by the **Evaluation Skeptic**.

## What Phase 2 ships

- Expanding-window walk-forward backtest (`nowcaster.evaluation.walk_forward`)
  at per-fold as-of dates.
- Metrics scaffolding: RMSE, MAE, RMSE/MAE ratios vs baselines, directional
  accuracy, 80%/95% interval coverage.
- COVID shock months excluded from **headline** metrics; full-sample metrics
  always reported alongside.
- Leakage audit hooks: shuffled targets + timing-randomized as-of maps
  (`nowcaster.evaluation.leakage_audit`) for CI wiring later.
- Holdout lock: final 24 months reserved; harness refuses to score them unless
  explicitly unlocked. See `docs/holdout_log.md`.

## Baseline wiring (Modeling PR #16)

The harness loads Phase 2 baselines only through Modeling's registry:

```python
from nowcaster.models import create_baseline, iter_baselines

model = create_baseline("last_value")  # also: ar1, rolling_mean
for baseline in iter_baselines(["last_value", "ar1", "rolling_mean"]):
    ...
```

`nowcaster.evaluation.discover_baseline_factories()` and
`iter_phase2_baselines()` wrap that API for the walk-forward suite and gate.

## Phase 3 (see `docs/evaluation_report.md`)

Phase 3 adds Diebold-Mariano, bootstrap RMSE-ratio CIs, classifier metrics +
calibration plot, leakage collapse audits, and the once-per-version holdout
API. Holdout stays locked until Modeling registers final candidate versions
(`docs/requests/modeling-phase3-candidate-registration.md`).

## Gate

`tests/gates/test_phase_2.py` is shared with Feature (#17):

- Feature half: `build_features` contract + leakage nesting + summary docs
- Evaluation/Modeling half: `create_baseline` / `iter_baselines` through walk-forward
- Joint: `MonthlyFeatureBuilder.build_features(as_of)` → baselines → harness

See `docs/requests/evaluation-phase2-gate-coordination.md`.
