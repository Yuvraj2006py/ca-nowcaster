"""Append-only prediction / score log contract tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from nowcaster.contracts import PredictionLogEntry
from nowcaster.live.prediction_log import append_prediction, load_prediction_log, make_prediction_id
from nowcaster.live.score_log import append_score, load_score_log, score_prediction


def test_append_prediction_and_reject_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "predictions.csv"
    clock = datetime(2023, 2, 15, 14, 0, 0, tzinfo=UTC)
    entry = PredictionLogEntry(
        prediction_id=make_prediction_id(target_ref_month=date(2022, 12, 1), predicted_at=clock),
        target_ref_month=date(2022, 12, 1),
        predicted_at=clock,
        model_name="ar1",
        model_version="0.1.0",
        features_hash="abc",
        point=0.001,
        lower_80=-0.01,
        upper_80=0.01,
        lower_95=-0.02,
        upper_95=0.02,
        direction_beat_prev=True,
    )
    append_prediction(path, entry)
    frame = load_prediction_log(path)
    assert len(frame) == 1
    assert frame.iloc[0]["model_name"] == "ar1"

    with pytest.raises(ValueError, match="already logged"):
        append_prediction(path, entry)

    # Different model version for same month is allowed (append-only, new key).
    other = PredictionLogEntry(
        prediction_id=make_prediction_id(target_ref_month=date(2022, 12, 1), predicted_at=clock),
        target_ref_month=date(2022, 12, 1),
        predicted_at=clock,
        model_name="ar1",
        model_version="0.2.0",
        features_hash="abc",
        point=0.002,
        lower_80=-0.01,
        upper_80=0.01,
        lower_95=-0.02,
        upper_95=0.02,
        direction_beat_prev=False,
    )
    append_prediction(path, other)
    assert len(load_prediction_log(path)) == 2


def test_score_prediction_metrics(tmp_path: Path) -> None:
    clock = datetime(2023, 2, 28, 16, 0, 0, tzinfo=UTC)
    pred = PredictionLogEntry(
        prediction_id="pred-test",
        target_ref_month=date(2022, 12, 1),
        predicted_at=clock,
        model_name="ar1",
        model_version="0.1.0",
        features_hash="abc",
        point=0.10,
        lower_80=0.05,
        upper_80=0.15,
        lower_95=0.0,
        upper_95=0.20,
        direction_beat_prev=True,
    )
    score = score_prediction(pred, actual=0.08, scored_at=clock, previous_actual=0.05)
    assert score.error == pytest.approx(0.02)
    assert score.abs_error == pytest.approx(0.02)
    assert score.actual_in_80 is True
    assert score.actual_in_95 is True
    assert score.direction_correct is True

    path = tmp_path / "scores.csv"
    append_score(path, score)
    assert len(load_score_log(path)) == 1
    with pytest.raises(ValueError, match="already scored"):
        append_score(path, score)
