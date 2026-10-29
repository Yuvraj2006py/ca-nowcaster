"""Security hygiene guards for CI (Role 8).

These tests must stay strict. Do not weaken patterns to make a feature PR pass;
file a docs/requests/ note instead if a check is wrong.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

# Dynamic code execution / unsafe deserialization in product code.
FORBIDDEN_SRC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("eval(", re.compile(r"(?<![\w.])eval\s*\(")),
    ("exec(", re.compile(r"(?<![\w.])exec\s*\(")),
    ("pickle.load", re.compile(r"pickle\s*\.\s*loads?\s*\(")),
    ("joblib.load", re.compile(r"joblib\s*\.\s*load\s*\(")),
    ("yaml.load(", re.compile(r"yaml\s*\.\s*load\s*\(")),  # require safe_load
    ("marshal.loads", re.compile(r"marshal\s*\.\s*loads?\s*\(")),
)

# Dashboard must read stored logs only — no free-text or path upload surface.
FORBIDDEN_STREAMLIT: tuple[str, ...] = (
    "st.text_input",
    "st.text_area",
    "st.file_uploader",
    "st.chat_input",
    "st.dataframe_editor",  # free-form edit surface
)

SECRETISH_TRACKED = re.compile(
    r"(^|/)\.env($|\.(?!example$))|"
    r"\.pem$|"
    r"(^|/)id_rsa|"
    r"credentials\.json$|"
    r"service-account.*\.json$|"
    r"\.streamlit/secrets\.toml$",
    re.IGNORECASE,
)


def _iter_py_files(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*.py") if p.is_file())


def test_gitignore_covers_dotenv() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text
    assert ".env.local" in text or ".env.*" in text
    assert "*.pem" in text
    assert ".streamlit/secrets.toml" in text


def test_env_example_has_no_secret_values() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    lowered = example.lower()
    for needle in ("sk-", "ghp_", "github_pat_", "begin private key", "aws_secret"):
        assert needle not in lowered
    # Placeholders only — blank overrides are fine.
    for line in example.splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key.strip() in {"STATCAN_BASE_URL", "BOC_VALET_BASE_URL"}:
            assert value.strip() == ""


def test_src_has_no_forbidden_dynamic_execution() -> None:
    offenders: list[str] = []
    for path in _iter_py_files(SRC):
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN_SRC_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{path.relative_to(ROOT)}: {label}")
    assert not offenders, "Forbidden patterns in src:\n" + "\n".join(offenders)


def test_dashboard_has_no_free_text_widgets() -> None:
    app_dir = SRC / "nowcaster" / "app"
    offenders: list[str] = []
    for path in _iter_py_files(app_dir):
        text = path.read_text(encoding="utf-8")
        for widget in FORBIDDEN_STREAMLIT:
            if widget in text:
                offenders.append(f"{path.relative_to(ROOT)}: {widget}")
    assert not offenders, (
        "Dashboard must not expose free-text / upload widgets "
        "(see docs/requests/dashboard-no-user-input.md):\n" + "\n".join(offenders)
    )


def test_ci_pins_actions_by_sha() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    uses = re.findall(r"uses:\s*([^\s#]+)", workflow)
    assert uses, "expected actions in ci.yml"
    for ref in uses:
        # owner/name@<40-char hex>
        assert re.search(r"@[0-9a-f]{40}$", ref), f"Action not SHA-pinned: {ref}"


def test_ci_permissions_are_read_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert re.search(r"permissions:\s*\n\s+contents:\s*read", workflow)
    assert "contents: write" not in workflow


def test_no_secretish_paths_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    tracked_secretish = [p for p in tracked if SECRETISH_TRACKED.search(p.replace("\\", "/"))]
    assert not tracked_secretish, f"Secret-ish paths tracked: {tracked_secretish}"


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        ".github/dependabot.yml",
        "docs/security_review.md",
        "docs/failure_modes.md",
    ],
)
def test_security_artifacts_exist(path: str) -> None:
    assert (ROOT / path).is_file()
