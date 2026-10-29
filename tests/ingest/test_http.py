"""Tests for ingest HTTP helpers (no live network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nowcaster.ingest.http import IngestHttpError, RateLimitedSession


class _FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> object:
        return self._payload


def test_cache_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_request(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs["url"])
        return _FakeResponse({"ok": True})

    session = RateLimitedSession(
        cache_dir=tmp_path / "cache",
        cache_enabled=True,
        min_interval_s=0.0,
        max_retries=0,
    )
    monkeypatch.setattr(session._session, "request", fake_request)

    first = session.request_json("GET", "https://example.test/a")
    second = session.request_json("GET", "https://example.test/a")
    assert first == {"ok": True}
    assert second == {"ok": True}
    assert len(calls) == 1


def test_retries_then_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"n": 0}

    def fake_request(**kwargs):  # type: ignore[no-untyped-def]
        attempts["n"] += 1
        if attempts["n"] < 3:
            return _FakeResponse({"err": True}, status_code=503)
        return _FakeResponse({"ok": True}, status_code=200)

    session = RateLimitedSession(
        cache_dir=tmp_path / "cache",
        cache_enabled=False,
        min_interval_s=0.0,
        max_retries=3,
        backoff_base_s=0.01,
    )
    monkeypatch.setattr(session._session, "request", fake_request)
    data = session.request_json("GET", "https://example.test/retry")
    assert data == {"ok": True}
    assert attempts["n"] == 3


def test_hard_4xx_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(**kwargs):  # type: ignore[no-untyped-def]
        return _FakeResponse({"message": "nope"}, status_code=404)

    session = RateLimitedSession(
        cache_dir=tmp_path / "cache",
        cache_enabled=False,
        min_interval_s=0.0,
        max_retries=0,
    )
    monkeypatch.setattr(session._session, "request", fake_request)
    with pytest.raises(IngestHttpError) as exc:
        session.request_json("GET", "https://example.test/missing")
    assert exc.value.status_code == 404
