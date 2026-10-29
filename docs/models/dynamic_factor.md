# Dynamic factor model

**Name:** `dynamic_factor` · **Version:** `0.1.0`

## In plain language

Many monthly indicators move together because they share a few underlying
“business cycle” forces. A **dynamic factor model** estimates those latent
factors from the feature panel (which may have holes at the ragged edge) and
reads off what GDP growth those factors imply when the official GDP cell is
still missing.

## Why it exists

DynamicFactorMQ (statsmodels) is a standard macro nowcasting tool: it was
built for mixed-frequency, missing-at-the-edge panels. Even though v1 features
are monthly-only, the same machinery handles publication holes without ad-hoc
imputation.

## How it is trained

On each training window the model:

1. Stacks feature columns plus the MoM GDP target into one endogenous panel.
2. Searches a small grid of `factors` ∈ {1, 2} and `factor_orders` ∈ {1, 2}
   with expanding-window CV **inside the training window** (RMSE of filtered
   target predictions on the validation slice).
3. Refits DynamicFactorMQ with EM on the full training panel.
4. Logs `tuning_evaluations` as the number of CV EM fits.

At predict time, feature rows are **appended with the target masked as NaN**;
the Kalman filter’s expectation for the target is the point forecast (`refit=False`).

## How uncertainty is drawn

Gaussian 80%/95% bands using the std of in-sample filtered prediction errors
for the target series.

## What time it is allowed to know

Training panel only. Appended predict rows must not carry future GDP actuals
(they are NaN by construction).

## How Evaluation should call it

```python
from nowcaster.models import create_candidate

model = create_candidate("dynamic_factor")
pred = model.fit(X_train, y_train).predict(X_test)
```

## How this model could be wrong

EM may stop short of convergence on short windows. A one- or two-factor
structure can miss sector-specific shocks. Gaussian intervals ignore state
uncertainty. If features are mostly noise, factors fit idiosyncrasies and lose
to AR(1). Slow relative to bridge/GBM — fine for monthly nowcasts, awkward if
Evaluation’s fold count is huge without narrowing the grid.
