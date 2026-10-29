# Holdout log

This file is owned by the **Evaluation Skeptic**. Do not edit it from other roles.

## Lock policy (v1)

- **Window:** final **24** calendar months of available target reference months
  (`nowcaster.evaluation.holdout_lock.HOLDOUT_MONTHS`).
- **Walk-forward default:** excludes holdout months and raises if asked to score
  them without unlock (`WalkForwardConfig.holdout_unlocked=True`).
- **Once-per-version rule:** `nowcaster.evaluation.holdout_eval.evaluate_holdout_once`
  refuses a second evaluation of the same `(model_name, model_version)`.
- **Do not burn** on unfinished models or exploratory tuning.

## Access log

| Date (UTC) | Actor / branch | Model set | Notes |
|------------|----------------|-----------|-------|
| 2026-10-29 | Evaluation Skeptic / `cursor/evaluation-harness-c310` | — | Phase 2 lock documented; no holdout evaluation run. |
| 2026-10-29 | Evaluation Skeptic / `cursor/evaluation-phase3-skeptic-8bfa` | — | Phase 3 tooling; holdout locked until Modeling #21 merged. |
| 2026-10-29T15:21Z | cursor/evaluation-phase3-skeptic-8bfa | bridge@0.1.0 | final holdout once (synthetic 2015-2022 panel; Phase 3) |
| 2026-10-29T15:21Z | cursor/evaluation-phase3-skeptic-8bfa | dynamic_factor@0.1.0 | final holdout once (synthetic 2015-2022 panel; Phase 3) |
| 2026-10-29T15:21Z | cursor/evaluation-phase3-skeptic-8bfa | gradient_boosting@0.1.0 | final holdout once (synthetic 2015-2022 panel; Phase 3) |
| 2026-10-29T15:21Z | cursor/evaluation-phase3-skeptic-8bfa | direction_classifier@0.1.0 | final holdout once (synthetic 2015-2022 panel; Phase 3) |
| 2026-10-29T15:22Z | cursor/evaluation-phase3-skeptic-8bfa | direction_boosting@0.1.0 | final holdout once (synthetic 2015-2022 panel; Phase 3) |

CI enforces path edits via the `holdout-guard` job (see `.github/workflows/ci.yml`
and `scripts/ci/holdout_guard.sh`).
