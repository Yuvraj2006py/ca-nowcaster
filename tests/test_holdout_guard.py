"""Tests for the holdout path guard used in CI."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "holdout_guard.sh"


@pytest.mark.parametrize(
    "branch",
    [
        "cursor/evaluation-skeptic-abc1",
        "cursor/holdout-touch-abc1",
        "cursor/phase-0-setup-83aa",
        "cursor/devops-ci-9deb",
        "Evaluation-Skeptic-work",
    ],
)
def test_holdout_guard_allows_skeptic_and_bootstrap_branches(branch: str) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "HEAD_REF": branch},
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "branch",
    [
        "cursor/ingestion-client-9deb",
        "cursor/feature-lags-9deb",
        "cursor/modeling-bridge-9deb",
        "main",
    ],
)
def test_holdout_guard_rejects_other_branches(branch: str) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "HEAD_REF": branch},
    )
    assert result.returncode == 1, result.stdout
    assert "REFUSED" in result.stderr


def test_ci_workflow_and_holdout_stub_exist() -> None:
    assert (ROOT / ".github" / "workflows" / "ci.yml").is_file()
    assert (ROOT / "docs" / "holdout_log.md").is_file()
    assert (ROOT / "docs" / "ci-failure-handling.md").is_file()
    assert (ROOT / "src" / "nowcaster" / "evaluation" / "holdout" / "README.md").is_file()
    assert SCRIPT.is_file()
