"""BoC Valet client tests using recorded fixtures (no live calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nowcaster.ingest.boc_valet import BocValetClient
from nowcaster.ingest.http import RateLimitedSession

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ingest"


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BocValetClient:
    session = RateLimitedSession(
        cache_dir=tmp_path / "cache", cache_enabled=False, min_interval_s=0.0
    )
    files = {
        "STATIC_ATABLE_V39079": _load("valet_STATIC_ATABLE_V39079.json"),
        "FXMUSDCAD": _load("valet_FXMUSDCAD.json"),
        "M.BCPI": _load("valet_M_BCPI.json"),
    }

    def fake_request_json(method, url, *, params=None, json_body=None, use_cache=True):  # noqa: ANN001
        for name, payload in files.items():
            if name in url:
                return payload
        raise AssertionError(f"Unexpected Valet URL {url}")

    monkeypatch.setattr(session, "request_json", fake_request_json)
    return BocValetClient(session=session)


def test_policy_rate_observations(client: BocValetClient) -> None:
    detail, obs = client.get_observations("STATIC_ATABLE_V39079", recent=3)
    assert "overnight rate" in detail["label"].lower()
    assert len(obs) == 3
    date_str, value = BocValetClient.parse_observation_value(obs[0], "STATIC_ATABLE_V39079")
    assert date_str.startswith("20")
    assert isinstance(value, float)


def test_fx_and_bcpi(client: BocValetClient) -> None:
    _, fx = client.get_observations("FXMUSDCAD", recent=3)
    _, bcpi = client.get_observations("M.BCPI", recent=3)
    assert BocValetClient.parse_observation_value(fx[0], "FXMUSDCAD")[1] > 0
    assert BocValetClient.parse_observation_value(bcpi[0], "M.BCPI")[1] > 0
