# Last-value baseline

**Name:** `last_value` · **Version:** `0.1.0`

## In plain language

The last-value baseline says: “whatever GDP growth was last month is our best
guess for this month.” It does not look at jobs, retail, prices, or any other
indicator. It only remembers the most recent official growth rate that was
already known at training time.

If last month’s month-over-month growth was `+0.2%`, the model’s point forecast
for every period you ask it to score is also `+0.2%`.

## Why it exists

Before we celebrate a fancy model, we need a stubbornly simple rival. If a
machine-learning nowcast cannot beat “repeat the last number,” it is not earning
its complexity. Evaluation always compares candidates against this baseline.

## How uncertainty is drawn

Around the point forecast we draw **80%** and **95%** prediction intervals from
the size of past month-to-month changes in the training window (the standard
deviation of first differences), assuming roughly bell-shaped errors. Wider
historical swings → wider bands. These bands are honest about noise in the
series; they are **not** a claim that the true process is Gaussian forever.

## What time it is allowed to know

Only the target history passed into `fit`. It never peeks at later official
releases or at feature columns. `predict(X)` uses `X` only to learn **how many**
rows to return.

## How Evaluation should call it

```python
from nowcaster.models import create_baseline

model = create_baseline("last_value")
model.fit(X_train, y_train)   # X_train may have zero feature columns
pred = model.predict(X_test)  # points + intervals per row
```

## How this baseline could be wrong

Repeating the last value fails when growth mean-reverts or when a shock is
already fading. Intervals based on historical differences can under-cover during
regime changes (for example COVID). That is acceptable for a baseline: its job
is to be simple and hard to game, not to be the best forecast.
