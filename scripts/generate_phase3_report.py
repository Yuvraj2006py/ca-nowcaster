#!/usr/bin/env python3
"""Generate docs/evaluation_report.md + holdout burns for Phase 3 finals.

Inputs: Modeling registry on main (list_candidates / create_candidate @ 0.1.0).
Outputs: refreshed evaluation_report.md, holdout_log.md rows, calibration SVG.
Time allowed to know: synthetic panel only (not live StatCan vintages).
"""

from __future__ import annotations

from pathlib import Path

from nowcaster.evaluation.baselines_loader import discover_baseline_factories
from nowcaster.evaluation.candidates import discover_candidate_factories
from nowcaster.evaluation.holdout_eval import (
    HoldoutEvalRegistry,
    evaluate_holdout_once,
    reset_session_holdout_registry,
)
from nowcaster.evaluation.metrics import classifier_metrics_to_dict
from nowcaster.evaluation.report import (
    _classifier_from_direction_folds,
    build_synthetic_panel,
    render_evaluation_report_markdown,
    run_phase3_evaluation,
    write_calibration_plot,
)
from nowcaster.evaluation.walk_forward import WalkForwardConfig, run_walk_forward

ROOT = Path(__file__).resolve().parents[1]
ACTOR = "cursor/evaluation-phase3-skeptic-8bfa"
HOLDOUT_NAMES = (
    "bridge",
    "dynamic_factor",
    "gradient_boosting",
    "direction_classifier",
    "direction_boosting",
)


def main() -> None:
    X, y, as_of = build_synthetic_panel(start="2015-01", end="2022-12", seed=42)
    cfg = WalkForwardConfig(min_train_months=24, exclude_holdout=True)
    cands = discover_candidate_factories()
    bases = discover_baseline_factories() or {}

    reset_session_holdout_registry()
    registry = HoldoutEvalRegistry()
    log_path = ROOT / "docs" / "holdout_log.md"
    holdout_rows: list[str] = []
    holdout_cfg = WalkForwardConfig(min_train_months=24)
    for name in HOLDOUT_NAMES:
        if name not in cands:
            continue
        factory = cands[name]
        probe = factory()
        print(f"holdout {probe.name}@{probe.version} ...", flush=True)
        result = evaluate_holdout_once(
            factory,
            X,
            y,
            as_of_by_month=as_of,
            config=holdout_cfg,
            registry=registry,
            actor_branch=ACTOR,
            log_path=log_path,
            notes=(
                f"final holdout once for {probe.name}@{probe.version} "
                "(synthetic 2015-2022 panel; Phase 3)"
            ),
        )
        holdout_rows.append(
            f"{probe.name}@{probe.version}: n={result.metrics.headline.n} "
            f"rmse={result.metrics.headline.rmse:.4f} "
            f"dir_acc={result.metrics.headline.directional_accuracy}"
        )
        print(f"  done {holdout_rows[-1]}", flush=True)

    holdout_status = (
        "BURNED once per final candidate (name, version=0.1.0) on synthetic panel — "
        "see docs/holdout_log.md. Live StatCan refresh requires a version bump to re-score."
    )
    print("walk-forward suite (holdout excluded)...", flush=True)
    data = run_phase3_evaluation(
        X,
        y,
        as_of,
        panel_label=(
            "synthetic monthly panel (2015-01..2022-12; holdout final 24 months burned "
            "once per candidate@0.1.0; COVID headline exclusion 2020-03..2020-08). "
            "Not live StatCan."
        ),
        config=cfg,
        reference_baseline="ar1",
        n_bootstrap=300,
        seed=0,
        holdout_status=holdout_status,
    )

    cal_name = "direction_classifier" if "direction_classifier" in cands else "ar1"
    cal_factory = cands.get(cal_name) or bases["ar1"]
    cal_result = run_walk_forward(cal_factory, X, y, as_of_by_month=as_of, config=cfg)
    if cal_name.startswith("direction"):
        clf = _classifier_from_direction_folds(
            [f for f in cal_result.folds if not f.is_covid_shock]
        )
        cal_result.metrics.classifier.update(classifier_metrics_to_dict(clf))
    svg_path = ROOT / "docs" / "evaluation_calibration_direction.svg"
    written = write_calibration_plot(cal_result, svg_path)
    if written:
        data.calibration_svg_path = "evaluation_calibration_direction.svg"

    md = render_evaluation_report_markdown(data)
    md += "## Holdout scores (once per final version)\n\n"
    md += (
        "Synthetic-panel holdout (final 24 months). One unlock per "
        "`(name, version)` via `evaluate_holdout_once`.\n\n"
    )
    md += "| Model@version | Notes |\n|---------------|-------|\n"
    for row in holdout_rows:
        key, _, rest = row.partition(":")
        md += f"| `{key}` | {rest.strip()} |\n"
    md += "\n"
    (ROOT / "docs" / "evaluation_report.md").write_text(md, encoding="utf-8")
    print("HONEST:", data.honest_headline)
    for v in data.verdicts:
        print(f"  {v.model_name} role={v.role} beats={v.beats_reference} rmse_r={v.rmse_ratio}")
    print("wrote", ROOT / "docs" / "evaluation_report.md")


if __name__ == "__main__":
    main()
