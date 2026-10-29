"""Locked final-24-month holdout policy for Phase 2+.

Do not burn the holdout on unfinished models. The harness refuses to score
holdout months unless explicitly unlocked (Phase 5 / final model set only).
Every unlock must be recorded in docs/holdout_log.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from nowcaster.evaluation.covid import normalize_ref_month

HOLDOUT_MONTHS: int = 24


@dataclass(frozen=True)
class HoldoutWindow:
    """Calendar span reserved as the locked evaluation holdout.

    Inputs: sorted unique first-of-month target dates available for evaluation.
    Outputs: holdout months (final HOLDOUT_MONTHS) and the earlier in-sample pool.
    Time allowed to know: calendar labels of available target months only.
    """

    all_months: tuple[date, ...]
    holdout_months: tuple[date, ...]
    train_eval_months: tuple[date, ...]

    @property
    def n_holdout(self) -> int:
        return len(self.holdout_months)


class HoldoutLockedError(RuntimeError):
    """Raised when code attempts to score the locked holdout without unlock."""


def resolve_holdout_window(ref_months: list[date] | tuple[date, ...]) -> HoldoutWindow:
    """Split sorted unique ref months into train/eval pool vs final holdout.

    Inputs: target reference months (any order; duplicates ignored).
    Outputs: HoldoutWindow with final HOLDOUT_MONTHS reserved.
    Time allowed to know: month labels only; does not look at target values.
    """
    unique_sorted = tuple(sorted({normalize_ref_month(m) for m in ref_months}))
    if len(unique_sorted) <= HOLDOUT_MONTHS:
        # Too short to reserve a full holdout — treat everything as non-holdout
        # for unit fixtures; production series must be longer.
        return HoldoutWindow(
            all_months=unique_sorted,
            holdout_months=(),
            train_eval_months=unique_sorted,
        )
    holdout = unique_sorted[-HOLDOUT_MONTHS:]
    pool = unique_sorted[:-HOLDOUT_MONTHS]
    return HoldoutWindow(
        all_months=unique_sorted,
        holdout_months=holdout,
        train_eval_months=pool,
    )


def assert_holdout_not_scored(
    scored_months: list[date] | tuple[date, ...],
    holdout: HoldoutWindow,
    *,
    unlocked: bool = False,
) -> None:
    """Refuse scoring holdout months unless explicitly unlocked.

    Inputs: months about to be scored; holdout window; unlock flag.
    Outputs: None, or raises HoldoutLockedError.
    Time allowed to know: month labels only.
    """
    if unlocked:
        return
    holdout_set = set(holdout.holdout_months)
    overlap = sorted({normalize_ref_month(m) for m in scored_months} & holdout_set)
    if overlap:
        raise HoldoutLockedError(
            "Refusing to score locked holdout months "
            f"{overlap[0]}..{overlap[-1]} ({len(overlap)} months). "
            "Do not burn the final 24-month holdout on unfinished models. "
            "Record any intentional unlock in docs/holdout_log.md."
        )
