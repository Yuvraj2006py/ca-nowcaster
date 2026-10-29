# Bridge regression

**Name:** `bridge` · **Version:** `0.1.0`

## In plain language

A bridge equation asks: given this month’s faster indicators (jobs, retail,
prices, FX, commodities, and lagged GDP growth features), what MoM GDP growth
should we expect? The answer is a **linear** blend of those features. Elastic
net shrinks noisy coefficients and can zero out weak ones so correlated
indicators do not overfit a short Canadian sample.

## Why it exists

Bridge regressions are the workhorse of statistical nowcasting. They are
simple enough to audit, fast to refit every month, and a fair first test of
whether the Feature frame has any signal beyond the naive baselines.

## How it is trained

On each walk-forward training window the model:

1. Fills missing feature cells with **training-column medians**.
2. Standardizes features.
3. Searches a small grid of elastic-net `alpha` and `l1_ratio` with
   **expanding-window CV inside the training window only**.
4. Refits on the full training window with the winning hyperparameters.
5. Records `tuning_evaluations` = (#grid points)×(#CV folds used).

## How uncertainty is drawn

80% and 95% intervals are Gaussian bands around the point using the standard
deviation of **in-sample residuals** after the final fit.

## What time it is allowed to know

Only rows passed to `fit`. Hyperparameter search never sees the evaluation
test month. Feature values must already respect `as_of` (Feature Engineer).

## How Evaluation should call it

```python
from nowcaster.models import create_candidate

model = create_candidate("bridge")
pred = model.fit(X_train, y_train).predict(X_test)
# model.tuning_evaluations, model.best_params_
```

## How this model could be wrong

Linearity is a strong assumption for COVID-scale swings. Median imputation can
distort ragged edges. In-sample residual intervals are often too narrow
out-of-sample. If elastic net zeros the useful indicators, the bridge collapses
toward an intercept — Evaluation should report that honestly versus baselines.
