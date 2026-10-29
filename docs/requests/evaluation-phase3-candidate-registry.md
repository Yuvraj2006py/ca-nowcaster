# Modeling → Evaluation: Phase 3 candidates registered

From: Modeling Engineer (Role 4)
To: Evaluation Skeptic (Role 5)
Date: 2026-10-29
Status: **fulfilled** — answers `modeling-phase3-candidate-registration.md`

## Registry API (stable; no model-code edits needed from Skeptic)

```python
from nowcaster.models import list_candidates, create_candidate, iter_candidates

list_candidates()
# ['bridge', 'dynamic_factor', 'gradient_boosting',
#  'direction_classifier', 'direction_boosting']

model = create_candidate("bridge")  # unfitted NowcastModel
pred = model.fit(X_train, y_train).predict(X_test)
```

Baselines unchanged: `create_baseline` / `iter_baselines` / `list_baselines`.

## Expected Phase 3 names (all registered at version `0.1.0`)

| Name | Class | Intervals | Notes |
|------|-------|-----------|-------|
| `bridge` | Elastic-net bridge | Gaussian residual | Tuned on train CV |
| `dynamic_factor` | DynamicFactorMQ | Gaussian residual | Factors/orders tuned on train |
| `gradient_boosting` | HistGradientBoostingRegressor | Split conformal | Tree-friendly intervals |
| `direction_classifier` | Calibrated logistic | Conformal on probability | Point = P(beat previous) |
| `direction_boosting` | Calibrated HGB classifier | Conformal on probability | Extra comparison (not in expected-4) |

After `fit`, candidates expose `tuning_evaluations: int` and `best_params_: dict`.

## Final versions ready for holdout

These `0.1.0` builds are the **final Phase 3 candidate versions** for
`evaluate_holdout_once` — one burn per `(name, version)`. Please rebase onto
this Modeling PR (or `main` after merge), refresh `docs/evaluation_report.md`,
then unlock holdout once per registered final version.

Do **not** treat experimental kwargs in unit tests as alternate versions; the
zero-arg `create_candidate(name)` constructors are what Evaluation should score.

## Docs

One-page plain-language pages under `docs/models/`:
`bridge.md`, `dynamic_factor.md`, `gradient_boosting.md`,
`direction_classifier.md`, `direction_boosting.md`.
