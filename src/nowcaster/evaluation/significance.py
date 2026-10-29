"""Diebold-Mariano tests and bootstrap CIs on RMSE ratios.

Phase 3 skeptic tools: ask whether a candidate's loss is significantly better
than a baseline, and whether RMSE ratios are stable under resampling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class DieboldMarianoResult:
    """Diebold-Mariano test of equal predictive accuracy.

    Inputs: aligned loss differentials (candidate vs baseline).
    Outputs: DM statistic, two-sided p-value under asymptotic normality,
      and mean loss differential (candidate - baseline; negative favors candidate).
    Time allowed to know: caller-supplied losses only (post-release actuals).
    """

    statistic: float
    p_value: float
    mean_loss_diff: float
    n: int
    alternative: str = "two-sided"


@dataclass(frozen=True)
class BootstrapRMSERatioCI:
    """Bootstrap confidence interval for candidate/baseline RMSE ratio.

    Ratio < 1 favors the candidate. CI that includes 1 means no clear win.
    """

    point_ratio: float
    lower: float
    upper: float
    level: float
    n_bootstrap: int
    n_obs: int


def _as_1d(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float).reshape(-1)
    if arr.ndim != 1:
        raise ValueError(f"expected 1-d array, got shape {arr.shape}")
    return arr


def squared_error_loss(actual: Any, predicted: Any) -> np.ndarray:
    """Per-observation squared errors.

    Inputs: aligned actuals and predictions.
    Outputs: 1-d array of (pred - actual)^2.
    Time allowed to know: caller-supplied actuals only.
    """
    a = _as_1d(actual)
    p = _as_1d(predicted)
    if a.size != p.size:
        raise ValueError("actual and predicted must have equal length")
    return (p - a) ** 2


def diebold_mariano(
    actual: Any,
    candidate_pred: Any,
    baseline_pred: Any,
    *,
    h: int = 1,
) -> DieboldMarianoResult:
    """Diebold-Mariano test on squared-error loss (Harvey/HLN small-sample adj.).

    Tests H0: E[L_candidate - L_baseline] = 0 against two-sided alternative.
    Uses Newey-West HAC variance for h-step forecasts (h=1 for one-step OOS).

    Inputs: aligned actuals; candidate and baseline point predictions; forecast
      horizon h (default 1 for monthly expanding-window one-step folds).
    Outputs: DieboldMarianoResult.
    Time allowed to know: caller-supplied actuals only.
    """
    loss_c = squared_error_loss(actual, candidate_pred)
    loss_b = squared_error_loss(actual, baseline_pred)
    d = loss_c - loss_b
    n = int(d.size)
    if n < 2:
        return DieboldMarianoResult(
            statistic=float("nan"),
            p_value=float("nan"),
            mean_loss_diff=float(np.mean(d)) if n else float("nan"),
            n=n,
        )

    mean_d = float(np.mean(d))
    # Newey-West HAC with lag h-1 (Harvey et al. adjustment for small samples).
    lag = max(h - 1, 0)
    gamma0 = float(np.mean((d - mean_d) ** 2))
    gamma_sum = 0.0
    for k in range(1, lag + 1):
        cov = float(np.mean((d[k:] - mean_d) * (d[:-k] - mean_d)))
        weight = 1.0 - k / (lag + 1)
        gamma_sum += 2.0 * weight * cov
    var_d = (gamma0 + gamma_sum) / n
    if var_d <= 0.0 or not np.isfinite(var_d):
        # Degenerate differential (identical forecasts).
        return DieboldMarianoResult(
            statistic=0.0 if mean_d == 0.0 else float("nan"),
            p_value=1.0 if mean_d == 0.0 else float("nan"),
            mean_loss_diff=mean_d,
            n=n,
        )

    dm = mean_d / np.sqrt(var_d)
    # Harvey, Leybourne, Newbold (1997) small-sample adjustment.
    hln = dm * np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    # Two-sided normal p-value (erfc avoids scipy dependency).
    p_value = float(math.erfc(abs(hln) / np.sqrt(2.0)))
    return DieboldMarianoResult(
        statistic=float(hln),
        p_value=p_value,
        mean_loss_diff=mean_d,
        n=n,
    )


def bootstrap_rmse_ratio_ci(
    actual: Any,
    candidate_pred: Any,
    baseline_pred: Any,
    *,
    level: float = 0.95,
    n_bootstrap: int = 1000,
    seed: int = 0,
) -> BootstrapRMSERatioCI:
    """Percentile bootstrap CI for RMSE(candidate) / RMSE(baseline).

    Resamples observation indices with replacement (i.i.d. bootstrap of OOS
    folds). Does not re-fit models — operates on locked walk-forward residuals.

    Inputs: aligned actuals and point predictions; CI level; bootstrap draws; seed.
    Outputs: BootstrapRMSERatioCI.
    Time allowed to know: caller-supplied actuals only.
    """
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be in (0, 1), got {level}")
    a = _as_1d(actual)
    c = _as_1d(candidate_pred)
    b = _as_1d(baseline_pred)
    if not (a.size == c.size == b.size):
        raise ValueError("actual, candidate_pred, and baseline_pred must match length")
    n = int(a.size)
    if n == 0:
        return BootstrapRMSERatioCI(
            point_ratio=float("nan"),
            lower=float("nan"),
            upper=float("nan"),
            level=level,
            n_bootstrap=n_bootstrap,
            n_obs=0,
        )

    def _rmse(pred: np.ndarray, act: np.ndarray) -> float:
        return float(np.sqrt(np.mean((pred - act) ** 2)))

    point = _rmse(c, a) / _rmse(b, a) if _rmse(b, a) > 0 else float("nan")
    rng = np.random.default_rng(seed)
    ratios = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        rb = _rmse(b[idx], a[idx])
        rc = _rmse(c[idx], a[idx])
        ratios[i] = rc / rb if rb > 0 else float("nan")
    finite = ratios[np.isfinite(ratios)]
    alpha = 1.0 - level
    if finite.size == 0:
        lower = upper = float("nan")
    else:
        lower = float(np.quantile(finite, alpha / 2))
        upper = float(np.quantile(finite, 1.0 - alpha / 2))
    return BootstrapRMSERatioCI(
        point_ratio=float(point),
        lower=lower,
        upper=upper,
        level=level,
        n_bootstrap=n_bootstrap,
        n_obs=n,
    )


def beats_baseline(
    rmse_ratio: float,
    *,
    bootstrap_ci: BootstrapRMSERatioCI | None = None,
    dm: DieboldMarianoResult | None = None,
    alpha: float = 0.05,
) -> tuple[bool, str]:
    """Honest win rule: ratio < 1 and (optional) statistical support.

    A loud "does not beat" is the default. Statistical significance is required
    when DM / bootstrap results are supplied.

    Inputs: point RMSE ratio; optional bootstrap CI and DM result; alpha.
    Outputs: (beats, plain-language reason).
    Time allowed to know: n/a (summary stats only).
    """
    if not np.isfinite(rmse_ratio) or rmse_ratio >= 1.0:
        return False, f"RMSE ratio {rmse_ratio:.4f} is not below 1 (no improvement)"

    reasons: list[str] = [f"point RMSE ratio={rmse_ratio:.4f} < 1"]
    if bootstrap_ci is not None:
        if not np.isfinite(bootstrap_ci.upper) or bootstrap_ci.upper >= 1.0:
            return (
                False,
                f"RMSE ratio point estimate {rmse_ratio:.4f} < 1 but "
                f"{bootstrap_ci.level:.0%} bootstrap CI upper "
                f"{bootstrap_ci.upper:.4f} includes/exceeds 1 — not a clear win",
            )
        reasons.append(
            f"{bootstrap_ci.level:.0%} bootstrap CI "
            f"[{bootstrap_ci.lower:.4f}, {bootstrap_ci.upper:.4f}] entirely below 1"
        )
    if dm is not None:
        # Negative mean_loss_diff favors candidate; require significant rejection.
        if not np.isfinite(dm.p_value) or dm.p_value >= alpha or dm.mean_loss_diff >= 0:
            return (
                False,
                f"RMSE improved in point estimate but Diebold-Mariano does not "
                f"reject equal accuracy at alpha={alpha} "
                f"(DM={dm.statistic:.3f}, p={dm.p_value:.4f}, "
                f"mean SE diff={dm.mean_loss_diff:.6f})",
            )
        reasons.append(f"DM p={dm.p_value:.4f} < {alpha} with negative loss differential")
    return True, "; ".join(reasons)
