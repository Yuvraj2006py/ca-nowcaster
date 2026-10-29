# Holdout log (locked)

This file is owned by the **Evaluation Skeptic**. Do not edit it from other roles.

## Lock policy (v1)

- **Window:** final **24** calendar months of available target reference months
  (`nowcaster.evaluation.holdout_lock.HOLDOUT_MONTHS`).
- **Phase 2:** harness scaffolding only. Walk-forward **excludes** holdout
  months by default and raises if asked to score them without unlock.
- **Do not burn** the holdout on unfinished models, partial feature sets, or
  exploratory tuning.
- **Phase 3 / final:** touch once per final model set; record the access below
  before any unlock (`WalkForwardConfig.holdout_unlocked=True`).

| Date (UTC) | Actor / branch | Model set | Notes |
|------------|----------------|-----------|-------|
| 2026-10-29 | Evaluation Skeptic / `cursor/evaluation-harness-c310` | — | Phase 2 lock documented; no holdout evaluation run. |

CI enforces path edits via the `holdout-guard` job (see `.github/workflows/ci.yml`
and `scripts/ci/holdout_guard.sh`).
