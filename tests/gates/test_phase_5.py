"""Phase 5 gate: README, model card, interview notes, resume bullets exist.

Documentation and Interview Coach owns this gate. Checks that ship docs exist
and that resume/README claims stay grounded in the Evaluation Skeptic report
(no invented beat-baseline RMSE claims).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase_5_ship_docs_exist() -> None:
    required = [
        "README.md",
        "STATE.md",
        "docs/model_card.md",
        "docs/interview_notes.md",
        "docs/evaluation_report.md",
        "docs/streamlit_deploy.md",
        "docs/gates.md",
        "docs/live_pipeline.md",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Phase 5 ship docs missing: {missing}"


def test_phase_5_readme_honest_result_and_run_hints() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "ar(1)" in lower or "ar1" in lower
    assert "honest" in lower
    assert "evaluation_report" in lower
    assert "streamlit" in lower
    assert "streamlit_deploy" in lower
    assert "how to run" in lower or "pip install" in lower
    # Must not claim candidates beat the baseline in the README headline story.
    assert "no regression candidate beat" in lower or "no candidate" in lower


def test_phase_5_model_card_covers_contract_topics() -> None:
    text = (ROOT / "docs" / "model_card.md").read_text(encoding="utf-8")
    lower = text.lower()
    for needle in (
        "intended use",
        "data",
        "evaluation",
        "failure",
        "ar1",
        "evaluation_report",
    ):
        assert needle in lower, f"model card missing topic: {needle}"


def test_phase_5_interview_notes_topics_and_resume_bullets() -> None:
    text = (ROOT / "docs" / "interview_notes.md").read_text(encoding="utf-8")
    lower = text.lower()
    for topic in (
        "baseline",
        "leakage",
        "confusion matrix",
        "interval",
        "revision",
        "more time",
    ):
        assert topic in lower, f"interview notes missing topic: {topic}"
    assert "resume" in lower
    # Three options, grounded in reported figures.
    assert "0.5876" in text  # AR(1) headline RMSE from evaluation_report
    assert "42" in text
    assert text.count("Built ") >= 3 or text.count("built ") >= 3


def test_phase_5_resume_numbers_subset_of_evaluation_report() -> None:
    """Key resume figures must appear in (or derive from) the evaluation report."""
    report = (ROOT / "docs" / "evaluation_report.md").read_text(encoding="utf-8")
    notes = (ROOT / "docs" / "interview_notes.md").read_text(encoding="utf-8")
    marker = "Three resume bullet options"
    assert marker in notes
    resume_section = notes.split(marker, 1)[1]
    # Direct strings from docs/evaluation_report.md.
    for snippet in (
        "0.5876",
        "0.1110",
        "0.2641",
        "2015-01",
        "2022-12",
        "2020-03",
        "2020-08",
    ):
        assert snippet in resume_section, f"expected resume to cite {snippet}"
        assert snippet in report, f"{snippet} missing from evaluation_report"
    # Coverage percents are 100 * Cov80/Cov95 from the AR(1) row.
    assert "0.857" in report and "0.905" in report
    assert "85.7%" in resume_section
    assert "90.5%" in resume_section
    assert "42" in resume_section and "42" in report
    assert "24" in resume_section and "24" in report
    assert "300" in resume_section and "300" in report


def test_phase_5_state_marks_ship() -> None:
    text = (ROOT / "STATE.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "phase 5" in lower or "phase: 5" in lower
    assert "final summary" in lower or "v1 ship" in lower
    assert "streamlit" in lower
    assert "ar1" in lower or "ar(1)" in lower
