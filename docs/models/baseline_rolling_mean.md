# Rolling-mean baseline

**Name:** `rolling_mean` · **Version:** `0.1.0` · **Default window:** 3 months

## In plain language

The rolling-mean baseline says: “guess the average of the last few months of
growth.” With the default window of three, if the last three known MoM growth
rates were `0.1%`, `0.0%`, and `-0.1%`, the point forecast is `0.0%`.

It smooths away one-month noise. It still ignores every external indicator.

## Why it exists

Last-value can be jumpy; AR(1) can cling to a bad shock. A short trailing average
is another honest null model: “growth wanders around a local mean.” Evaluation
uses it alongside the other baselines so a candidate must beat more than one
flavor of naive forecast.

## Window

Construct with `create_baseline("rolling_mean", window=6)` (or any integer ≥ 1)
to change the lookback. The registry default used by `iter_baselines()` is
`window=3`. Training requires at least `window` observations.

## How uncertainty is drawn

On the training sample, for each time \(t\) with a full preceding window, we
compute the error \(y_t - \mathrm{mean}(y_{t-w:t})\). The sample standard
deviation of those errors sets the width of Gaussian 80% and 95% intervals
around the forecast. If the series is shorter than `window + 1`, there are no
in-sample errors and the residual scale floors to a tiny positive value so
intervals are not literally zero-width.

## What time it is allowed to know

Only the training `y` window. At predict time the point is the mean of the
**last `window` training observations**—it does not roll forward with predicted
values. `X` supplies row count only.

## How Evaluation should call it

```python
from nowcaster.models import create_baseline, iter_baselines

model = create_baseline("rolling_mean", window=3)
model.fit(X_train, y_train)
pred = model.predict(X_test)

# Or all Phase 2 baselines with defaults:
for model in iter_baselines():
    ...
```

## How this baseline could be wrong

A fixed window is arbitrary; three months may be too short after a regime shift
or too long when the cycle turns quickly. Because predict does not update the
window with its own forecasts, multi-row batches repeat the same point—which is
correct for “no future y,” but weak as a multi-horizon path. Intervals assume
stable error variance. Beat this honestly; do not tune the window on the holdout.
