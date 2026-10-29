# Direction classifier (boosting)

**Name:** `direction_boosting` · **Version:** `0.1.0`

## In plain language

Same secondary question as logistic — **did MoM growth beat the previous
month?** — but answered with gradient-boosted trees so nonlinear feature
interactions can enter the probability.

## Why it exists

It is the tree comparison for the classifier track. If it does not beat
calibrated logistic on accuracy / Brier / calibration, Evaluation should prefer
the simpler model.

## How it is trained

Labels: `1` if `y_t > y_{t-1}` else `0`. Uses
`HistGradientBoostingClassifier` (NaN-safe). Tunes depth / learning rate /
iterations with expanding CV inside the training window, calibrates
probabilities, and builds conformal probability intervals from a training
calibration tail. Logs `tuning_evaluations`.

## How uncertainty is drawn

Conformal absolute-residual bands on calibrated probabilities, clipped to
`[0, 1]`.

## What time it is allowed to know

Training window only; no test-month actuals.

## How Evaluation should call it

```python
from nowcaster.models import create_candidate

model = create_candidate("direction_boosting")
pred = model.fit(X_train, y_train).predict(X_test)
# Primary Evaluation name is direction_classifier (logistic); this is the tree comparison.
```

## How this model could be wrong

Boosted classifiers overfit short, imbalanced direction histories. Calibration
plus conformal on tiny tails can produce over-wide or mis-nested intervals
after clipping. As with logistic, do not confuse probability points with MoM
growth forecasts when computing RMSE.
