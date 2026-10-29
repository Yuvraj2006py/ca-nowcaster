"""Failure handling for live ingest / predict: log and skip, optional GitHub issue."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineFailure:
    """Record of a skipped live run due to ingest or upstream failure.

    Inputs: failure context at wall-clock time.
    Outputs: structured failure for JSONL log / GitHub issue body.
    Time allowed to know: failure clock only; no prediction made.
    """

    failed_at: datetime
    stage: str  # e.g. "ingest", "features", "predict"
    message: str
    skipped_predict: bool = True
    details: dict[str, Any] = field(default_factory=dict)


class IngestFailureError(RuntimeError):
    """Raised when refresh fails; callers must skip predict on stale data."""


def append_failure(path: Path | str, failure: PipelineFailure) -> None:
    """Append one failure record as JSONL.

    Inputs: failure log path; PipelineFailure.
    Outputs: none (side effect: append line).
    Time allowed to know: failure fields only.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "failed_at": failure.failed_at.isoformat(),
        "stage": failure.stage,
        "message": failure.message,
        "skipped_predict": failure.skipped_predict,
        "details": failure.details,
    }
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
    logger.error(
        "pipeline failure stage=%s skipped_predict=%s message=%s",
        failure.stage,
        failure.skipped_predict,
        failure.message,
    )


def open_github_issue(
    *,
    title: str,
    body: str,
    token: str | None = None,
    repository: str | None = None,
    http_post: Callable[[str, dict[str, str], bytes], tuple[int, str]] | None = None,
) -> dict[str, Any] | None:
    """Open a GitHub issue for a live-pipeline failure when credentials exist.

    Inputs: title/body; optional GITHUB_TOKEN and GITHUB_REPOSITORY (owner/repo);
            optional http_post for tests.
    Outputs: parsed issue JSON on success; None if token/repo missing (logged skip).
    Time allowed to know: none (ops side-effect only).
    """
    resolved_token = token if token is not None else os.environ.get("GITHUB_TOKEN")
    resolved_repo = repository if repository is not None else os.environ.get("GITHUB_REPOSITORY")
    if not resolved_token or not resolved_repo:
        logger.warning("Skipping GitHub issue creation (missing GITHUB_TOKEN or GITHUB_REPOSITORY)")
        return None

    url = f"https://api.github.com/repos/{resolved_repo}/issues"
    payload = json.dumps(
        {"title": title, "body": body, "labels": ["live-pipeline", "BLOCKED"]}
    ).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {resolved_token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "ca-nowcaster-live-pipeline",
    }

    poster = http_post or _default_http_post
    status, text = poster(url, headers, payload)
    if status >= 300:
        logger.error("GitHub issue creation failed status=%s body=%s", status, text[:500])
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("GitHub issue response was not JSON")
        return None


def record_ingest_failure(
    *,
    failure_log: Path | str,
    message: str,
    details: dict[str, Any] | None = None,
    open_issue: bool = True,
    now: datetime | None = None,
    issue_opener: Callable[..., dict[str, Any] | None] | None = None,
) -> PipelineFailure:
    """Log an ingest failure, skip predict, and optionally open a GitHub issue.

    Inputs: failure log path; message/details; whether to open an issue.
    Outputs: PipelineFailure record.
    Time allowed to know: wall clock for failed_at; no economic data used.
    """
    clock = now or datetime.now(UTC)
    failure = PipelineFailure(
        failed_at=clock,
        stage="ingest",
        message=message,
        skipped_predict=True,
        details=details or {},
    )
    append_failure(failure_log, failure)

    if open_issue:
        opener = issue_opener or open_github_issue
        title = f"BLOCKED: live ingest failure — {clock.date().isoformat()}"
        body = (
            "## Live pipeline ingest failure\n\n"
            "Ingestion failed; **predict was skipped** to avoid forecasting on "
            "stale data.\n\n"
            f"- failed_at: `{failure.failed_at.isoformat()}`\n"
            f"- message: {failure.message}\n"
            f"- details: `{json.dumps(failure.details, default=str)}`\n\n"
            "See `logs/failures.jsonl` and `docs/requests/devops-live-pipeline-workflows.md`.\n"
        )
        opener(title=title, body=body)

    return failure


def _default_http_post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
    """POST JSON via urllib (no extra deps).

    Inputs: url, headers, body bytes.
    Outputs: (status_code, response_text).
    Time allowed to know: none.
    """
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        # GitHub Issues API only (https scheme enforced by constructed URL above).
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            return int(response.status), response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return 599, str(exc)


def failure_as_dict(failure: PipelineFailure) -> dict[str, Any]:
    """Convert PipelineFailure to a JSON-serializable dict.

    Inputs: PipelineFailure.
    Outputs: plain dict.
    Time allowed to know: failure fields only.
    """
    payload = asdict(failure)
    payload["failed_at"] = failure.failed_at.isoformat()
    return payload
