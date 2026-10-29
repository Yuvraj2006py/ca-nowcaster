# AR(1) baseline

**Name:** `ar1` · **Version:** `0.1.0`

## In plain language

The AR(1) baseline says growth this month is a straight-line blend of a constant
and **last month’s growth**:

\[
y_t = c + \phi\, y_{t-1} + \varepsilon_t
\]

If \(\phi\) is near 1, the series likes to stick where it was. If \(\phi\) is
near 0, growth snaps back toward the constant \(c\). The model learns \(c\) and
\(\phi\) by ordinary least squares on the training history of the target only.

## Why it exists

AR(1) is the classic “use the series’ own recent past” benchmark in macro
forecasting. It is still naive (no external indicators), but it can capture
persistence that pure last-value cannot when growth tends to fade toward a mean.

## Multi-step predictions

When `predict` is asked for several rows at once, the model **chains** forecasts:
the first step uses the last training observation; the second step uses the
first predicted value as the lag; and so on. It never inserts future actuals.
In a typical walk-forward backtest, Evaluation calls `predict` one origin at a
time (one row), so chaining rarely matters—but the behavior is defined.

## How uncertainty is drawn

80% and 95% intervals are Gaussian bands around each point using the standard
deviation of **in-sample one-step residuals** after fitting. The same residual
scale is used at every horizon (no widening with step), which keeps the baseline
simple and slightly optimistic for long multi-step paths.

## What time it is allowed to know

Only `y` in `fit`. Feature columns in `X` are ignored. No look-ahead.

## How Evaluation should call it

```python
from nowcaster.models import create_baseline

model = create_baseline("ar1")
model.fit(X_train, y_train)
pred = model.predict(X_test)
```

## How this baseline could be wrong

A single lag is a blunt instrument for GDP MoM growth. Structural breaks,
COVID-scale outliers, and revision noise can warp \(\phi\). Chained multi-step
paths can drift, and fixed-width intervals will mis-cover if error variance
changes over time. Again: that is fine for a baseline we intend to beat.
