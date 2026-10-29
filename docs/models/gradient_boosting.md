# Gradient boosting

**Name:** `gradient_boosting` · **Version:** `0.1.0`

## In plain language

Gradient boosting builds a crowd of small decision trees that correct each
other’s mistakes. Unlike the bridge, it can learn **nonlinear** patterns —
for example “retail collapse only hurts GDP when employment is also weak.”

## Why it exists

It is the honest nonlinear comparison model for v1: same feature frame, same
walk-forward protocol, no deep learning (scope freeze). If trees do not beat
baselines and the bridge, Evaluation should say so.

## How it is trained

Uses sklearn `HistGradientBoostingRegressor` (native NaN support, so ragged
edges need no median fill).

On each training window:

1. Holds out a chronological **calibration tail** (~25%) for intervals.
2. Tunes `max_depth`, `learning_rate`, and `max_iter` with expanding CV on the
   earlier training portion only.
3. Fits on the pre-calibration portion, records absolute residuals on the
   calibration tail, then **refits on the full training window**.
4. Logs `tuning_evaluations`.

## How uncertainty is drawn

**Split conformal** absolute-residual quantiles give symmetric 80% and 95%
intervals (no Gaussian assumption). This is the tree-friendly path called for
in the Phase 3 brief.

## What time it is allowed to know

Training rows only. Calibration residuals never come from the evaluation fold.

## How Evaluation should call it

```python
from nowcaster.models import create_candidate

model = create_candidate("gradient_boosting")
pred = model.fit(X_train, y_train).predict(X_test)
```

## How this model could be wrong

Short monthly samples overfit trees even with shallow depth. Conformal
coverage is only guaranteed under exchangeability, which macro regimes
violate. If signal is mostly linear, boosting adds variance without lowering
RMSE versus the bridge. Hyperparameter grids are intentionally small — a
wider search on the same window could look better and still be overfit.
