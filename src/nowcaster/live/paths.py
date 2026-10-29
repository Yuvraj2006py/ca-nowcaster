"""Filesystem paths for live prediction / score artifacts.

Public logs live under ``logs/`` (tracked in git for tamper-evident history).
Raw store remains under ``data/`` (gitignored; refreshed by ingest).
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_PREDICTION_LOG = REPO_ROOT / "logs" / "predictions.csv"
DEFAULT_SCORE_LOG = REPO_ROOT / "logs" / "scores.csv"
DEFAULT_FAILURE_LOG = REPO_ROOT / "logs" / "failures.jsonl"
DEFAULT_RAW_STORE = Path(os.environ.get("RAW_STORE_PATH", "data/raw.duckdb"))


def prediction_log_path(override: Path | str | None = None) -> Path:
    """Resolve prediction log path.

    Inputs: optional override path or PREDICTION_LOG_PATH env.
    Outputs: Path to append-only prediction CSV.
    Time allowed to know: none.
    """
    if override is not None:
        return Path(override)
    env = os.environ.get("PREDICTION_LOG_PATH")
    return Path(env) if env else DEFAULT_PREDICTION_LOG


def score_log_path(override: Path | str | None = None) -> Path:
    """Resolve score log path.

    Inputs: optional override path or SCORE_LOG_PATH env.
    Outputs: Path to append-only score CSV.
    Time allowed to know: none.
    """
    if override is not None:
        return Path(override)
    env = os.environ.get("SCORE_LOG_PATH")
    return Path(env) if env else DEFAULT_SCORE_LOG


def failure_log_path(override: Path | str | None = None) -> Path:
    """Resolve failure log path.

    Inputs: optional override path or FAILURE_LOG_PATH env.
    Outputs: Path to append-only JSONL failure log.
    Time allowed to know: none.
    """
    if override is not None:
        return Path(override)
    env = os.environ.get("FAILURE_LOG_PATH")
    return Path(env) if env else DEFAULT_FAILURE_LOG


def raw_store_path(override: Path | str | None = None) -> Path:
    """Resolve raw store path.

    Inputs: optional override or RAW_STORE_PATH env.
    Outputs: Path to DuckDB/SQLite store.
    Time allowed to know: none.
    """
    if override is not None:
        return Path(override)
    return Path(os.environ.get("RAW_STORE_PATH", str(DEFAULT_RAW_STORE)))
