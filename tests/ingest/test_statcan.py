"""StatCan client tests using recorded fixtures (no live calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nowcaster.ingest.http import RateLimitedSession
from nowcaster.ingest.statcan import StatCanClient, product_id_from_table_id

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ingest"


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StatCanClient:
    session = RateLimitedSession(
        cache_dir=tmp_path / "cache", cache_enabled=False, min_interval_s=0.0
    )

    mapping = {
        ("POST", "getCubeMetadata"): _load("statcan_cube_36100434.json"),
        ("POST", "getDataFromVectorsAndLatestNPeriods"): _load("statcan_latest_65201210.json"),
        ("POST", "getBulkVectorDataByRange"): _load("statcan_bulk_65201210.json"),
        ("POST", "getSeriesInfoFromCubePidCoord"): _load("statcan_series_info_gdp.json"),
        ("GET", "getChangedSeriesList"): _load("statcan_changed_series_list.json"),
    }

    def fake_request_json(method, url, *, params=None, json_body=None, use_cache=True):  # noqa: ANN001
        for (m, endpoint), payload in mapping.items():
            if method.upper() == m and endpoint in url:
                return payload
        raise AssertionError(f"Unexpected request {method} {url}")

    monkeypatch.setattr(session, "request_json", fake_request_json)
    return StatCanClient(session=session)


def test_product_id_from_table_id() -> None:
    assert product_id_from_table_id("36-10-0434-01") == 36100434


def test_get_cube_metadata(client: StatCanClient) -> None:
    cube = client.get_cube_metadata(36100434)
    assert "Gross domestic product" in cube["cubeTitleEn"]
    assert int(cube["productId"]) == 36100434


def test_get_series_info(client: StatCanClient) -> None:
    info = client.get_series_info_from_coord(36100434, "1.1.1.1.0.0.0.0.0.0")
    assert info["vectorId"] == 65201210


def test_latest_n(client: StatCanClient) -> None:
    points = client.get_latest_n_periods(65201210, latest_n=3)
    assert len(points) == 3
    assert "releaseTime" in points[0]
    assert points[0]["value"] is not None


def test_bulk_range(client: StatCanClient) -> None:
    data = client.get_bulk_range([65201210], "2020-01-01T00:00", "2026-10-29T00:00")
    assert 65201210 in data
    assert len(data[65201210]) == 6
    assert data[65201210][0]["refPer"].startswith("1997")


def test_changed_registry_vectors(client: StatCanClient) -> None:
    rows = client.changed_registry_vectors({65201210, 2062811})
    assert len(rows) == 1
    assert rows[0]["vectorId"] == 65201210
