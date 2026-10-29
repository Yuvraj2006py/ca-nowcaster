"""Phase 0 gate: repo skeleton and shared contracts exist."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase_0_root_artifacts_exist() -> None:
    required = [
        "AGENTS.md",
        "BACKLOG.md",
        "STATE.md",
        "series_registry.yaml",
        "pyproject.toml",
        ".gitignore",
        ".env.example",
        "docs/gates.md",
        "src/nowcaster/contracts.py",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Phase 0 missing artifacts: {missing}"


def test_phase_0_package_layout_exists() -> None:
    packages = [
        "src/nowcaster/__init__.py",
        "src/nowcaster/ingest/__init__.py",
        "src/nowcaster/quality/__init__.py",
        "src/nowcaster/features/__init__.py",
        "src/nowcaster/models/__init__.py",
        "src/nowcaster/evaluation/__init__.py",
        "src/nowcaster/live/__init__.py",
        "src/nowcaster/app/__init__.py",
    ]
    missing = [p for p in packages if not (ROOT / p).exists()]
    assert not missing, f"Phase 0 missing package files: {missing}"


def test_phase_0_directory_layout_exists() -> None:
    dirs = [
        "data",
        "docs",
        "tests",
        "tests/gates",
        ".github/workflows",
        "src/nowcaster/ingest",
        "src/nowcaster/quality",
        "src/nowcaster/features",
        "src/nowcaster/models",
        "src/nowcaster/evaluation",
        "src/nowcaster/live",
        "src/nowcaster/app",
    ]
    missing = [d for d in dirs if not (ROOT / d).is_dir()]
    assert not missing, f"Phase 0 missing directories: {missing}"


def test_phase_0_agents_contains_ten_rules() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for n in range(1, 11):
        assert f"{n}." in text, f"AGENTS.md missing rule {n}"


def test_phase_0_series_registry_documents_schema() -> None:
    text = (ROOT / "series_registry.yaml").read_text(encoding="utf-8")
    assert "series:" in text
    assert "series_id" in text
    assert "verified_at" in text


def test_phase_0_contracts_importable() -> None:
    from nowcaster.contracts import (  # noqa: F401
        FeatureBuilder,
        NowcastModel,
        PredictionLogEntry,
        RawObservation,
        ScoreEntry,
        SeriesDefinition,
    )
