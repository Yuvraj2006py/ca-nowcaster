"""Ingest failure: log + skip predict; optional GitHub issue."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nowcaster.live.failures import open_github_issue, record_ingest_failure


def test_record_ingest_failure_writes_jsonl_and_calls_issue(tmp_path: Path) -> None:
    fail_path = tmp_path / "failures.jsonl"
    opened: list[dict[str, str]] = []

    def fake_opener(*, title: str, body: str, **_kwargs: object) -> dict[str, object]:
        opened.append({"title": title, "body": body})
        return {"number": 1, "html_url": "https://example.test/1"}

    failure = record_ingest_failure(
        failure_log=fail_path,
        message="connection reset",
        details={"source": "statcan"},
        open_issue=True,
        now=datetime(2023, 2, 15, 14, 0, 0, tzinfo=UTC),
        issue_opener=fake_opener,
    )
    assert failure.skipped_predict is True
    assert fail_path.exists()
    line = json.loads(fail_path.read_text(encoding="utf-8").strip())
    assert line["stage"] == "ingest"
    assert line["message"] == "connection reset"
    assert len(opened) == 1
    assert "BLOCKED" in opened[0]["title"]


def test_open_github_issue_skips_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert open_github_issue(title="t", body="b") is None


def test_open_github_issue_posts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "org/ca-nowcaster")

    def fake_post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
        assert "org/ca-nowcaster/issues" in url
        assert "Bearer fake-token" in headers["Authorization"]
        return 201, '{"number": 42, "html_url": "https://github.com/org/ca-nowcaster/issues/42"}'

    result = open_github_issue(title="t", body="b", http_post=fake_post)
    assert result is not None
    assert result["number"] == 42
