# Locked holdout (Evaluation Skeptic only)

Directory for the final 24-month holdout evaluation artifacts.

- Policy and access log: `docs/holdout_log.md`
- Runtime lock: `nowcaster.evaluation.holdout_lock`
- Phase 2: **no holdout scores**. Do not place prediction/score files here yet.
- Phase 3+: one unlock per final model set, logged in `docs/holdout_log.md`.

Other roles must not add code or data here. Request changes via `docs/requests/`.
The `holdout-guard` CI job fails PRs from non-Skeptic branches that touch this path.
