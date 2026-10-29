# Holdout log (locked)

This file is owned by the **Evaluation Skeptic**. Do not edit it from other roles.

## Lock policy (v1)

- **Window:** final **24** calendar months of available target reference months
  (`nowcaster.evaluation.holdout_lock.HOLDOUT_MONTHS`).
- **Walk-forward default:** excludes holdout months and raises if asked to score
  them without unlock (`WalkForwardConfig.holdout_unlocked=True`).
- **Once-per-version rule:** `nowcaster.evaluation.holdout_eval.evaluate_holdout_once`
  refuses a second evaluation of the same `(model_name, model_version)`.
- **Do not burn** the holdout on unfinished models, partial feature sets, or
  exploratory tuning.
- **Phase 3 status:** holdout remains **LOCKED**. Phase 3 candidates are not
  registered yet (`docs/requests/modeling-phase3-candidate-registration.md`).
  No final model version has been scored on holdout. When Modeling marks
  versions final, Evaluation will unlock **once per version** and append a row
  below before publishing refreshed `docs/evaluation_report.md` numbers.

| Date (UTC) | Actor / branch | Model set | Notes |
|------------|----------------|-----------|-------|
| 2026-10-29 | Evaluation Skeptic / `cursor/evaluation-harness-c310` | — | Phase 2 lock documented; no holdout evaluation run. |
| 2026-10-29 | Evaluation Skeptic / `cursor/evaluation-phase3-skeptic-8bfa` | — | Phase 3 tooling landed; holdout **not burned** (no final candidates). Once-per-version API ready. |

CI enforces path edits via the `holdout-guard` job (see `.github/workflows/ci.yml`
and `scripts/ci/holdout_guard.sh`).
