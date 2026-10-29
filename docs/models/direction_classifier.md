# Direction classifier (logistic)

**Name:** `direction_classifier` · **Version:** `0.1.0`

## In plain language

The secondary target asks a yes/no question: **did this month’s MoM growth beat
last month’s?** Logistic regression turns the feature frame into a calibrated
probability of “yes.” That probability is the model’s point prediction.

## Why it exists

Recruiters and interviewers often care about directional skill and confusion
matrices. A calibrated logistic model is the simplest honest classifier before
trying trees.

## How it is trained

Labels are built inside `fit` from the primary series: `1` if `y_t > y_{t-1}`,
else `0` (the first month is dropped). Features are median-imputed and scaled.
`C` (L2 strength) is tuned with expanding CV on the training window. Probabilities
are calibrated with `CalibratedClassifierCV` (sigmoid). Absolute probability
residuals on a training calibration tail feed conformal intervals.
`tuning_evaluations` counts CV fits.

## How uncertainty is drawn

Conformal bands on the probability scale, clipped to `[0, 1]`.

## What time it is allowed to know

Training X/y only. Evaluation still passes MoM growth `y`; the model derives
labels and must not see the test month’s actual growth.

## How Evaluation should call it

```python
from nowcaster.models import create_candidate

model = create_candidate("direction_classifier")
pred = model.fit(X_train, y_train).predict(X_test)
# pred.points[i] = P(growth beats previous month)
direction = pred.points[i] >= 0.5
```

## How this model could be wrong

“Beat previous month” is a different question from “growth is positive,” and
near-zero months make labels noisy under revisions. Calibration can fail when
a window has few class flips (COVID). Probabilities are not MoM growth
forecasts — do not score them with RMSE against growth levels.
