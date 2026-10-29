"""Refresh orchestration tests with fixture-backed HTTP (no live calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nowcaster.ingest import cli
from nowcaster.ingest.http import RateLimitedSession
from nowcaster.ingest.refresh import refresh_all
from nowcaster.ingest.store import RawStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ingest"


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def fixture_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> RateLimitedSession:
    session = RateLimitedSession(
        cache_dir=tmp_path / "cache", cache_enabled=False, min_interval_s=0.0
    )

    def fake_request_json(method, url, *, params=None, json_body=None, use_cache=True):  # noqa: ANN001
        if "getCubeMetadata" in url:
            return _load("statcan_cube_36100434.json")
        if "getBulkVectorDataByRange" in url:
            return _load("statcan_bulk_65201210.json")
        if "getDataFromVectorsAndLatestNPeriods" in url:
            return _load("statcan_latest_65201210.json")
        if "STATIC_ATABLE_V39079" in url:
            return _load("valet_STATIC_ATABLE_V39079.json")
        raise AssertionError(f"Unexpected URL in refresh test: {method} {url}")

    monkeypatch.setattr(session, "request_json", fake_request_json)
    return session


def test_refresh_twice_no_duplicates(
    tmp_path: Path, fixture_session: RateLimitedSession
) -> None:
    store_path = tmp_path / "raw.duckdb"
    registry = FIXTURES / "mini_registry.yaml"
    first = refresh_all(
        registry_path=registry, store_path=store_path, session=fixture_session
    )
    second = refresh_all(
        registry_path=registry, store_path=store_path, session=fixture_session
    )
    assert first.total_fetched > 0
    assert first.total_inserted > 0
    assert second.total_inserted == 0
    assert second.total_skipped == second.total_fetched
    store = RawStore(store_path)
    assert store.count_rows() == first.total_rows_after
    store.close()


def test_cli_twice(
    tmp_path: Path, fixture_session: RateLimitedSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_path = tmp_path / "cli.duckdb"
    registry = FIXTURES / "mini_registry.yaml"

    def fake_refresh_all(**kwargs):  # noqa: ANN003
        return refresh_all(
            registry_path=registry,
            store_path=store_path,
            session=fixture_session,
        )

    monkeypatch.setattr(cli, "refresh_all", fake_refresh_all)
    monkeypatch.setattr(
        cli,
        "run_double_refresh",
        lambda **_kwargs: (fake_refresh_all(), fake_refresh_all()),
    )
    code = cli.main(["--twice", "--registry", str(registry), "--store", str(store_path)])
    assert code == 0
