"""Build plain-language evaluation verdicts for docs/evaluation_report.md."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nowcaster.evaluation.baselines_loader import (
    PHASE2_BASELINE_NAMES,
    discover_baseline_factories,
)
from nowcaster.evaluation.candidates import (
    PHASE3_CANDIDATE_NAMES,
    PHASE3_DIRECTION_NAMES,
    PHASE3_REGRESSION_NAMES,
    direction_candidate_names,
    discover_candidate_factories,
    list_expected_vs_registered,
    regression_candidate_names,
)
from nowcaster.evaluation.leakage_audit import run_leakage_audit_suite
from nowcaster.evaluation.metrics import (
    CalibrationBin,
    ClassifierMetrics,
    calibration_svg,
    compute_classifier_metrics,
)
from nowcaster.evaluation.significance import (
    BootstrapRMSERatioCI,
    DieboldMarianoResult,
    beats_baseline,
    bootstrap_rmse_ratio_ci,
    diebold_mariano,
)
from nowcaster.evaluation.walk_forward import (
    FoldPrediction,
    WalkForwardConfig,
    WalkForwardResult,
    compare_to_baselines,
    run_walk_forward,
)


@dataclass(frozen=True)
class ModelVerdict:
    """Plain-language verdict for one model vs a reference baseline.

    Inputs: walk-forward + significance results.
    Outputs: structured verdict for the evaluation report.
    Time allowed to know: summary of already-scored OOS folds only.
    """

    model_name: str
    model_version: str
    role: str  # "baseline" | "candidate"
    reference_baseline: str
    headline_rmse: float
    headline_mae: float
    headline_n: int
    full_rmse: float
    full_n: int
    rmse_ratio: float
    mae_ratio: float
    directional_accuracy: float | None
    coverage_80: float | None
    coverage_95: float | None
    dm: DieboldMarianoResult | None
    bootstrap_ci: BootstrapRMSERatioCI | None
    beats_reference: bool
    verdict_text: str
    classifier: ClassifierMetrics | None = None


@dataclass
class EvaluationReportData:
    """All inputs needed to render docs/evaluation_report.md."""

    panel_label: str
    reference_baseline: str
    verdicts: list[ModelVerdict] = field(default_factory=list)
    leakage: dict[str, Any] = field(default_factory=dict)
    candidates_status: dict[str, Any] = field(default_factory=dict)
    holdout_status: str = "LOCKED — not burned (final candidate versions not registered)"
    honest_headline: str = ""
    calibration_svg_path: str | None = None


def _folds_arrays(folds: Sequence[FoldPrediction]) -> tuple[np.ndarray, np.ndarray]:
    actual = np.asarray([f.actual for f in folds], dtype=float)
    pred = np.asarray([f.point for f in folds], dtype=float)
    return actual, pred


def _headline_folds(result: WalkForwardResult) -> list[FoldPrediction]:
    return [f for f in result.folds if not f.is_covid_shock]


def verdict_for_model(
    result: WalkForwardResult,
    reference: WalkForwardResult,
    *,
    role: str,
    n_bootstrap: int = 500,
    seed: int = 0,
) -> ModelVerdict:
    """Compare one model to a reference baseline with DM + bootstrap CI.

    Inputs: candidate/baseline WalkForwardResult; reference baseline result; role.
    Outputs: ModelVerdict.
    Time allowed to know: OOS fold actuals already on the results.
    """
    compared = compare_to_baselines(result, {reference.model_name: reference})
    rel = compared.metrics.vs_baselines_headline[0]
    h_folds = _headline_folds(result)
    r_folds = _headline_folds(reference)
    # Align on shared months for DM / bootstrap.
    h_map = {f.target_ref_month: f for f in h_folds}
    r_map = {f.target_ref_month: f for f in r_folds}
    shared = sorted(set(h_map) & set(r_map))
    dm = None
    boot = None
    if shared:
        actual = [h_map[m].actual for m in shared]
        cand_p = [h_map[m].point for m in shared]
        base_p = [r_map[m].point for m in shared]
        dm = diebold_mariano(actual, cand_p, base_p)
        boot = bootstrap_rmse_ratio_ci(actual, cand_p, base_p, n_bootstrap=n_bootstrap, seed=seed)

    if result.model_name == reference.model_name:
        beats = False
        text = (
            f"{result.model_name} is the reference baseline "
            f"(headline RMSE={result.metrics.headline.rmse:.4f}, n={result.metrics.headline.n}). "
            "It does not 'beat' itself."
        )
    else:
        beats, reason = beats_baseline(
            rel.rmse_ratio,
            bootstrap_ci=boot,
            dm=dm,
        )
        verb = "BEATS" if beats else "DOES NOT BEAT"
        text = (
            f"{result.model_name}@{result.model_version} {verb} reference "
            f"{reference.model_name}: {reason}."
        )

    clf = None
    if result.metrics.classifier.get("available"):
        cm = result.metrics.classifier.get("confusion_matrix")
        bins_raw = result.metrics.classifier.get("calibration_bins") or []
        bins = tuple(
            CalibrationBin(
                lower=b["lower"],
                upper=b["upper"],
                n=b["n"],
                mean_predicted=b["mean_predicted"],
                fraction_positive=b["fraction_positive"],
            )
            for b in bins_raw
        )
        clf = ClassifierMetrics(
            available=True,
            n=int(result.metrics.classifier.get("n") or 0),
            accuracy=result.metrics.classifier.get("accuracy"),
            precision=result.metrics.classifier.get("precision"),
            recall=result.metrics.classifier.get("recall"),
            f1=result.metrics.classifier.get("f1"),
            confusion_matrix=(
                (int(cm[0][0]), int(cm[0][1])),
                (int(cm[1][0]), int(cm[1][1])),
            )
            if cm
            else None,
            calibration_bins=bins,
            note=str(result.metrics.classifier.get("note") or ""),
        )

    return ModelVerdict(
        model_name=result.model_name,
        model_version=result.model_version,
        role=role,
        reference_baseline=reference.model_name,
        headline_rmse=result.metrics.headline.rmse,
        headline_mae=result.metrics.headline.mae,
        headline_n=result.metrics.headline.n,
        full_rmse=result.metrics.full_sample.rmse,
        full_n=result.metrics.full_sample.n,
        rmse_ratio=rel.rmse_ratio,
        mae_ratio=rel.mae_ratio,
        directional_accuracy=result.metrics.headline.directional_accuracy,
        coverage_80=result.metrics.headline.coverage_80,
        coverage_95=result.metrics.headline.coverage_95,
        dm=dm,
        bootstrap_ci=boot,
        beats_reference=beats,
        verdict_text=text,
        classifier=clf,
    )


def _classifier_from_direction_folds(
    folds: Sequence[FoldPrediction],
) -> ClassifierMetrics:
    """Score direction probabilities against beat-previous labels from MoM actuals.

    Label at fold t: 1 if actual_t > actual_{t-1} (matches Modeling's secondary target).
    Predicted class: 1 if point probability >= 0.5.

    Inputs: chronological FoldPrediction list (COVID-excluded for headline).
    Outputs: ClassifierMetrics.
    Time allowed to know: fold actuals only.
    """
    if len(folds) < 2:
        return ClassifierMetrics(
            available=False,
            n=0,
            accuracy=None,
            precision=None,
            recall=None,
            f1=None,
            confusion_matrix=None,
            note="need >=2 folds for beat-previous labels",
        )
    y_true: list[int] = []
    y_pred: list[int] = []
    y_prob: list[float] = []
    for i in range(1, len(folds)):
        y_true.append(1 if folds[i].actual > folds[i - 1].actual else 0)
        p = float(folds[i].point)
        y_prob.append(p)
        y_pred.append(1 if p >= 0.5 else 0)
    return compute_classifier_metrics(y_true, y_pred, y_prob=y_prob)


def _direction_verdict(result: WalkForwardResult) -> ModelVerdict:
    """Build a classifier-focused verdict for direction models (no RMSE vs AR1).

    Inputs: WalkForwardResult whose points are class probabilities in [0, 1].
    Outputs: ModelVerdict with beats_reference=False and plain-language note.
    Time allowed to know: OOS fold actuals already on the result.
    """
    headline_folds = [f for f in result.folds if not f.is_covid_shock]
    clf = _classifier_from_direction_folds(headline_folds)
    acc = clf.accuracy
    text = (
        f"{result.model_name}@{result.model_version} is a direction classifier "
        f"(point = P(beat previous)). Not scored on GDP MoM RMSE vs AR(1). "
        f"Headline accuracy={acc}, F1={clf.f1}."
    )
    return ModelVerdict(
        model_name=result.model_name,
        model_version=result.model_version,
        role="direction_candidate",
        reference_baseline="(n/a — classifier)",
        headline_rmse=result.metrics.headline.rmse,
        headline_mae=result.metrics.headline.mae,
        headline_n=result.metrics.headline.n,
        full_rmse=result.metrics.full_sample.rmse,
        full_n=result.metrics.full_sample.n,
        rmse_ratio=float("nan"),
        mae_ratio=float("nan"),
        directional_accuracy=result.metrics.headline.directional_accuracy,
        coverage_80=result.metrics.headline.coverage_80,
        coverage_95=result.metrics.headline.coverage_95,
        dm=None,
        bootstrap_ci=None,
        beats_reference=False,
        verdict_text=text,
        classifier=clf,
    )


def run_phase3_evaluation(
    X: pd.DataFrame,
    y: pd.Series,
    as_of_by_month: Mapping[date, date],
    *,
    panel_label: str,
    config: WalkForwardConfig | None = None,
    reference_baseline: str = "ar1",
    n_bootstrap: int = 500,
    seed: int = 0,
    holdout_status: str | None = None,
) -> EvaluationReportData:
    """Run walk-forward + significance + leakage audits for baselines and candidates.

    Regression candidates are compared to the reference baseline on RMSE with
    Diebold-Mariano / bootstrap. Direction candidates are scored as classifiers
    only (points are probabilities — not MoM growth).

    Inputs: feature/target panel; as_of map; labels/config/bootstrap knobs;
      optional holdout_status override for the report header.
    Outputs: EvaluationReportData for markdown rendering.
    Time allowed to know: same as walk_forward (holdout excluded by default).
    """
    cfg = config or WalkForwardConfig(min_train_months=24, exclude_holdout=True)
    baseline_factories = discover_baseline_factories() or {}
    if not baseline_factories:
        raise RuntimeError("Phase 2 baselines not discoverable via Modeling registry")

    candidate_factories = discover_candidate_factories()
    direction_names = set(direction_candidate_names()) | set(PHASE3_DIRECTION_NAMES)
    regression_names = set(regression_candidate_names()) | set(PHASE3_REGRESSION_NAMES)

    results: dict[str, WalkForwardResult] = {}
    for name, factory in baseline_factories.items():
        results[name] = run_walk_forward(factory, X, y, as_of_by_month=as_of_by_month, config=cfg)
    for name, factory in candidate_factories.items():
        results[name] = run_walk_forward(factory, X, y, as_of_by_month=as_of_by_month, config=cfg)

    if reference_baseline not in results:
        raise KeyError(f"reference baseline {reference_baseline!r} missing from results")
    reference = results[reference_baseline]

    verdicts: list[ModelVerdict] = []
    for name, result in results.items():
        if name in direction_names:
            verdicts.append(_direction_verdict(result))
            continue
        if name in PHASE2_BASELINE_NAMES:
            role = "baseline"
        elif name in regression_names:
            role = "candidate"
        else:
            role = "candidate"
        verdicts.append(
            verdict_for_model(
                result,
                reference,
                role=role,
                n_bootstrap=n_bootstrap,
                seed=seed,
            )
        )

    leakage: dict[str, Any] = {}
    leakage["baselines"] = {
        k: {
            "passed": v.passed,
            "detail": v.detail,
            "rmse_ratio_vs_reference": v.rmse_ratio_vs_reference,
        }
        for k, v in run_leakage_audit_suite(
            baseline_factories[reference_baseline],
            X,
            y,
            as_of_by_month,
            config=cfg,
            seed=seed,
            reference=reference,
            uses_features=False,
        ).items()
    }
    regression_factories = {n: f for n, f in candidate_factories.items() if n in regression_names}
    if regression_factories:
        first_name = next(iter(regression_factories))
        leakage["first_candidate"] = {
            "model": first_name,
            **{
                k: {
                    "passed": v.passed,
                    "detail": v.detail,
                    "rmse_ratio_vs_reference": v.rmse_ratio_vs_reference,
                }
                for k, v in run_leakage_audit_suite(
                    regression_factories[first_name],
                    X,
                    y,
                    as_of_by_month,
                    config=cfg,
                    seed=seed,
                    uses_features=True,
                ).items()
            },
        }

    cand_status = list_expected_vs_registered()
    beaters = [v for v in verdicts if v.beats_reference and v.role == "candidate"]
    if not candidate_factories:
        honest = (
            "HONEST RESULT: No Phase 3 candidate models are registered. "
            "Nothing has beaten the baselines because nothing beyond last_value / "
            "ar1 / rolling_mean has been submitted for evaluation. "
            "See docs/requests/modeling-phase3-candidate-registration.md."
        )
        holdout = (
            "LOCKED — holdout not burned. Final candidate model versions are not "
            "registered yet; Evaluation will touch holdout once per final version."
        )
    elif not beaters:
        honest = (
            "HONEST RESULT: No regression candidate beats the reference baseline "
            f"({reference_baseline}) on headline RMSE with Diebold-Mariano and "
            "bootstrap CI support. Direction models are scored separately "
            "(classifier metrics only). v1 still ships under the honest-result rule."
        )
        holdout = (
            "Holdout status set by caller; walk-forward table excludes the final "
            "24 months unless unlocked via evaluate_holdout_once."
        )
    else:
        names = ", ".join(v.model_name for v in beaters)
        honest = (
            f"Regression candidates that beat {reference_baseline} (headline, with stats): {names}."
        )
        holdout = (
            "Holdout status set by caller; walk-forward table excludes the final "
            "24 months unless unlocked via evaluate_holdout_once."
        )
    if holdout_status is not None:
        holdout = holdout_status

    return EvaluationReportData(
        panel_label=panel_label,
        reference_baseline=reference_baseline,
        verdicts=verdicts,
        leakage=leakage,
        candidates_status=cand_status,
        holdout_status=holdout,
        honest_headline=honest,
    )


def render_evaluation_report_markdown(data: EvaluationReportData) -> str:
    """Render EvaluationReportData as markdown for docs/evaluation_report.md.

    Inputs: EvaluationReportData.
    Outputs: full markdown document string.
    Time allowed to know: n/a (formatting only).
    """
    lines: list[str] = [
        "# Evaluation report (Phase 3)",
        "",
        "Owned by the **Evaluation Skeptic**. Plain-language verdicts first;",
        "tables second. Honest-result rule: if nothing beats the baseline, say so.",
        "",
        f"**Panel:** {data.panel_label}",
        f"**Reference baseline:** `{data.reference_baseline}`",
        f"**Holdout:** {data.holdout_status}",
        "",
        "## Loud verdict",
        "",
        data.honest_headline,
        "",
        "## Candidate registration",
        "",
        (
            "- Expected: `"
            + ", ".join(data.candidates_status.get("expected", PHASE3_CANDIDATE_NAMES))
            + "`"
        ),
        f"- Registered: `{', '.join(data.candidates_status.get('registered', [])) or '(none)'}`",
        f"- Missing: `{', '.join(data.candidates_status.get('missing', [])) or '(none)'}`",
        "",
        "## Walk-forward metrics (expanding window, holdout excluded)",
        "",
        "Headline metrics **exclude** COVID shock months (2020-03..2020-08).",
        "Full-sample metrics include them. Ratios are candidate / reference "
        f"(`{data.reference_baseline}`); **ratio < 1 is better**.",
        "",
        "| Model | Role | Version | Headline n | Headline RMSE | Full RMSE | "
        "RMSE ratio | MAE ratio | Dir. acc. | Cov80 | Cov95 | Beats ref? |",
        "|-------|------|---------|------------|---------------|-----------|"
        "------------|-----------|-----------|-------|-------|------------|",
    ]
    for v in data.verdicts:
        dir_acc = f"{v.directional_accuracy:.3f}" if v.directional_accuracy is not None else "—"
        c80 = f"{v.coverage_80:.3f}" if v.coverage_80 is not None else "—"
        c95 = f"{v.coverage_95:.3f}" if v.coverage_95 is not None else "—"
        if v.role == "direction_candidate":
            beats = "n/a"
            rmse_r = "n/a"
            mae_r = "n/a"
            # RMSE vs growth target is not meaningful for probability points.
            h_rmse = "n/a"
            f_rmse = "n/a"
        else:
            beats = "yes" if v.beats_reference else "no"
            rmse_r = f"{v.rmse_ratio:.4f}" if np.isfinite(v.rmse_ratio) else "—"
            mae_r = f"{v.mae_ratio:.4f}" if np.isfinite(v.mae_ratio) else "—"
            h_rmse = f"{v.headline_rmse:.4f}"
            f_rmse = f"{v.full_rmse:.4f}"
        lines.append(
            f"| `{v.model_name}` | {v.role} | {v.model_version} | {v.headline_n} | "
            f"{h_rmse} | {f_rmse} | {rmse_r} | {mae_r} | {dir_acc} | {c80} | {c95} | "
            f"{beats} |"
        )

    lines.extend(["", "## Per-model verdicts", ""])
    for v in data.verdicts:
        lines.append(f"### `{v.model_name}` ({v.role})")
        lines.append("")
        lines.append(v.verdict_text)
        lines.append("")
        if v.dm is not None:
            lines.append(
                f"- Diebold-Mariano vs `{v.reference_baseline}`: "
                f"stat={v.dm.statistic:.3f}, p={v.dm.p_value:.4f}, "
                f"mean SE diff={v.dm.mean_loss_diff:.6f}, n={v.dm.n}"
            )
        if v.bootstrap_ci is not None:
            lines.append(
                f"- Bootstrap RMSE-ratio CI "
                f"({v.bootstrap_ci.level:.0%}, {v.bootstrap_ci.n_bootstrap} draws): "
                f"point={v.bootstrap_ci.point_ratio:.4f}, "
                f"[{v.bootstrap_ci.lower:.4f}, {v.bootstrap_ci.upper:.4f}]"
            )
        lines.append("")

    lines.extend(["## Direction classifier metrics", ""])
    any_clf = False
    for v in data.verdicts:
        if v.classifier is None or not v.classifier.available:
            continue
        any_clf = True
        cm = v.classifier.confusion_matrix
        lines.append(f"### `{v.model_name}` (sign of point forecast as class)")
        lines.append("")
        lines.append(
            f"- n={v.classifier.n}, accuracy={v.classifier.accuracy}, "
            f"precision={v.classifier.precision}, recall={v.classifier.recall}, "
            f"F1={v.classifier.f1}"
        )
        if cm is not None:
            lines.append(
                f"- Confusion matrix `[[TN, FP], [FN, TP]]` = "
                f"`[[{cm[0][0]}, {cm[0][1]}], [{cm[1][0]}, {cm[1][1]}]]`"
            )
        if v.classifier.calibration_bins:
            lines.append("- Calibration bins (mean predicted → fraction positive):")
            lines.append("")
            lines.append("| Bin | n | Mean p | Fraction + |")
            lines.append("|-----|---|--------|------------|")
            for b in v.classifier.calibration_bins:
                lines.append(
                    f"| [{b.lower:.1f}, {b.upper:.1f}] | {b.n} | "
                    f"{b.mean_predicted:.3f} | {b.fraction_positive:.3f} |"
                )
            lines.append("")
        lines.append("")
    if not any_clf:
        lines.append("_No classifier metrics available._")
        lines.append("")

    if data.calibration_svg_path:
        lines.extend(
            [
                "## Calibration plot",
                "",
                f"![Calibration reliability]({data.calibration_svg_path})",
                "",
            ]
        )

    lines.extend(["## Leakage audits", ""])
    lines.append(
        "Shuffled-target skill that does **not** collapse (ratio << 1) is a red flag: "
        "either the sample is too small for stable RMSE, or the harness is leaking. "
        "Feature-timing scramble must collapse skill for feature-using models."
    )
    lines.append("")
    for scope, audits in data.leakage.items():
        if scope == "first_candidate" and isinstance(audits, dict) and "model" in audits:
            lines.append(f"### Candidate `{audits['model']}`")
            lines.append("")
            for name, payload in audits.items():
                if name == "model" or not isinstance(payload, dict):
                    continue
                flag = "PASS" if payload.get("passed") else "FAIL (skeptic flag)"
                lines.append(f"- **{name}**: {flag} — {payload.get('detail')}")
            lines.append("")
        elif isinstance(audits, dict):
            lines.append(f"### {scope}")
            lines.append("")
            for name, payload in audits.items():
                if not isinstance(payload, dict):
                    continue
                flag = "PASS" if payload.get("passed") else "FAIL (skeptic flag)"
                lines.append(f"- **{name}**: {flag} — {payload.get('detail')}")
            lines.append("")

    lines.extend(
        [
            "## How I could be wrong",
            "",
            "- Synthetic / fixture panels can overstate or understate real StatCan skill.",
            "- Diebold-Mariano assumes loss differentials are covariance-stationary; "
            "COVID and policy regime shifts may violate that.",
            "- Bootstrap of OOS residuals ignores estimation uncertainty (no re-fit).",
            "- Sign(point) is a weak stand-in for a trained direction classifier.",
            "- Feature-blind baselines cannot fail the feature-timing scramble; "
            "that audit only bites once Modeling registers feature-using candidates.",
            "- Holdout is still locked; out-of-sample optimism in the train/eval pool "
            "may reverse on the final 24 months.",
            "",
            "## Coordination",
            "",
            "- Modeling must register final candidates via "
            "`list_candidates` / `create_candidate` "
            "(see `docs/requests/modeling-phase3-candidate-registration.md`).",
            "- After final versions land, Evaluation will unlock holdout **once per "
            "version**, append `docs/holdout_log.md`, and refresh this report.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_calibration_plot(
    result: WalkForwardResult,
    path: Path,
) -> Path | None:
    """Write SVG calibration plot for one model's direction probabilities.

    Inputs: WalkForwardResult with classifier calibration bins; output path.
    Outputs: path written, or None if no bins.
    Time allowed to know: n/a.
    """
    bins_raw = result.metrics.classifier.get("calibration_bins") or []
    if not bins_raw:
        return None
    bins = tuple(
        CalibrationBin(
            lower=b["lower"],
            upper=b["upper"],
            n=b["n"],
            mean_predicted=b["mean_predicted"],
            fraction_positive=b["fraction_positive"],
        )
        for b in bins_raw
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(calibration_svg(bins), encoding="utf-8")
    return path


def build_synthetic_panel(
    *,
    start: str = "2010-01",
    end: str = "2022-12",
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.Series, dict[date, date]]:
    """Deterministic synthetic panel for CI / report generation without live data.

    Default span 2010-01..2022-12 leaves room for min_train=24, COVID exclusion,
    and a locked final-24 holdout while still yielding a usable headline sample.

    Inputs: optional start/end period labels; RNG seed.
    Outputs: (X, y, as_of_by_month).
    Time allowed to know: synthetic only.
    """
    rng = np.random.default_rng(seed)
    months = pd.period_range(start, end, freq="M")
    index = pd.Index([m.to_timestamp().date() for m in months], name="ref_month")
    y_vals = np.zeros(len(index))
    for i in range(len(index)):
        prev = y_vals[i - 1] if i else 0.0
        y_vals[i] = 0.15 * prev + rng.normal(0.05, 0.25)
        d = index[i]
        if d.year == 2020 and 3 <= d.month <= 8:
            y_vals[i] -= 1.5 + 0.3 * (d.month - 3)
    x0 = np.roll(y_vals, 1)
    x0[0] = 0.0
    x1 = y_vals + rng.normal(0.0, 0.05, size=len(y_vals))
    X = pd.DataFrame({"lag1": x0, "indicator": x1}, index=index)
    y = pd.Series(y_vals, index=index, name="gdp_mom")
    as_of = {
        m: (pd.Timestamp(m) + pd.offsets.MonthEnd(0) + pd.DateOffset(months=2)).date()
        for m in index
    }
    return X, y, as_of
