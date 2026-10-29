"""Tests for as-of target MoM extraction."""

from __future__ import annotations

from datetime import date

import pandas as pd

from nowcaster.live.target import actual_mom_for_month, next_unpublished_month, target_mom_as_of


def test_target_mom_respects_as_of(live_store: pd.DataFrame) -> None:
    # Before Dec 2022 GDP release (2023-02-28), Dec must be absent.
    early = target_mom_as_of(live_store, date(2023, 2, 15))
    assert early.last_published_ref_month == date(2022, 11, 1)
    assert pd.Period("2022-12", freq="M") not in early.mom.index

    late = target_mom_as_of(live_store, date(2023, 2, 28))
    assert late.last_published_ref_month == date(2022, 12, 1)
    assert pd.Period("2022-12", freq="M") in late.mom.index


def test_next_unpublished_and_actual(live_store: pd.DataFrame) -> None:
    history = target_mom_as_of(live_store, date(2023, 2, 15))
    assert next_unpublished_month(history) == date(2022, 12, 1)

    assert actual_mom_for_month(live_store, date(2022, 12, 1), as_of_date=date(2023, 2, 15)) is None
    actual = actual_mom_for_month(live_store, date(2022, 12, 1), as_of_date=date(2023, 2, 28))
    assert actual is not None
    assert isinstance(actual, float)
