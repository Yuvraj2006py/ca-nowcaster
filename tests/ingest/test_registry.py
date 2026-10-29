"""Registry loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from nowcaster.ingest.registry import RegistryError, load_registry

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ingest"
REPO_REGISTRY = Path(__file__).resolve().parents[2] / "series_registry.yaml"


def test_load_mini_registry() -> None:
    rows = load_registry(FIXTURES / "mini_registry.yaml")
    assert len(rows) == 2
    assert rows[0].series_id == "ca_gdp_basic_prices"
    assert rows[0].vector_id == "65201210"
    assert rows[1].valet_series == "STATIC_ATABLE_V39079"


def test_repo_registry_has_verified_entries_only() -> None:
    rows = load_registry(REPO_REGISTRY)
    assert len(rows) >= 8
    for row in rows:
        assert row.verified_at is not None
        assert row.verification_notes.strip()
        if row.source == "statcan":
            assert row.table_id and row.vector_id
            assert row.vector_id.isdigit() or row.vector_id.lstrip("vV").isdigit()
        else:
            assert row.valet_series
            assert row.table_id is None
            assert row.vector_id is None


def test_rejects_invented_statcan_without_ids(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
series:
  - series_id: bad
    source: statcan
    table_id: null
    vector_id: null
    valet_series: null
    name: bad
    frequency: monthly
    unit: x
    verified_at: "2026-01-01T00:00:00+00:00"
    verification_notes: nope
    target_role: indicator
""",
        encoding="utf-8",
    )
    with pytest.raises(RegistryError):
        load_registry(path)
