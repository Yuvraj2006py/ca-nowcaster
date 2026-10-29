# Locked holdout (Evaluation Skeptic only)

Directory for the final 24-month holdout evaluation artifacts.

- Policy and access log: `docs/holdout_log.md`
- Runtime lock: `nowcaster.evaluation.holdout_lock`
- Once-per-version API: `nowcaster.evaluation.holdout_eval.evaluate_holdout_once`
- Phase 3: holdout remains **locked** until Modeling registers final candidate
  versions. Do not place prediction/score files here until then.

Other roles must not add code or data here. Request changes via `docs/requests/`.
The `holdout-guard` CI job fails PRs from non-Skeptic branches that touch this path.
