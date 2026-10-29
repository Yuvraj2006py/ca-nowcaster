"""COVID shock month definitions for headline metric variants.

Headline metrics exclude acute COVID months; full-sample metrics are also
reported so readers can see both. Phase 2 scaffolding only — no model verdicts.
"""

from __future__ import annotations

from datetime import date

# Acute Canadian monthly-GDP COVID shock window used for headline exclusion.
# Inclusive first-of-month dates. Configurable override via WalkForwardConfig.
DEFAULT_COVID_SHOCK_MONTHS: frozenset[date] = frozenset(
    {
        date(2020, 3, 1),
        date(2020, 4, 1),
        date(2020, 5, 1),
        date(2020, 6, 1),
        date(2020, 7, 1),
        date(2020, 8, 1),
    }
)


def normalize_ref_month(value: date) -> date:
    """Normalize a calendar date to first-of-month reference month.

    Inputs: any date.
    Outputs: date with day=1 in the same year/month.
    Time allowed to know: calendar label only; no observations.
    """
    return date(value.year, value.month, 1)


def is_covid_shock_month(
    ref_month: date,
    shock_months: frozenset[date] | None = None,
) -> bool:
    """Return True if ref_month is in the COVID shock exclusion set.

    Inputs: target reference month; optional override set of first-of-month dates.
    Outputs: bool.
    Time allowed to know: calendar membership only.
    """
    months = shock_months if shock_months is not None else DEFAULT_COVID_SHOCK_MONTHS
    return normalize_ref_month(ref_month) in {normalize_ref_month(m) for m in months}


def mask_covid_months(
    ref_months: list[date],
    shock_months: frozenset[date] | None = None,
) -> list[bool]:
    """Boolean mask: True where the month is a COVID shock month (to exclude).

    Inputs: list of reference months; optional shock set.
    Outputs: list[bool] aligned to ref_months (True = exclude from headline).
    Time allowed to know: calendar membership only.
    """
    return [is_covid_shock_month(m, shock_months) for m in ref_months]
