# Request: DevOps — Phase 3 Evaluation merge path

From: Evaluation Skeptic
To: DevOps / Orchestrator
Re: [#20](https://github.com/Yuvraj2006py/ca-nowcaster/pull/20)

## Ask

When CI on #20 is green, **merge the harness/metrics/report scaffolding**. That is intentional.

## Constraints

- **Do not** treat #20 as a holdout burn. Holdout remains locked until Modeling
  Candidates publishes **final** model versions.
- After Modeling’s candidate PR merges (or is rebaseable), Evaluation will open a
  **follow-up PR** that:
  1. Refreshes `docs/evaluation_report.md` with candidate verdicts
  2. Runs holdout **once per final `(name, version)`** and appends `docs/holdout_log.md`
  3. Pings DevOps for merge

Either order (merge #20 first, or wait to rebase onto Modeling) is fine; holdout
only once, and only on final versions.

## Update (Modeling #21)

Modeling [#21](https://github.com/Yuvraj2006py/ca-nowcaster/pull/21) registers
`bridge`, `dynamic_factor`, `gradient_boosting`, `direction_classifier`,
`direction_boosting` at version **0.1.0**.

**Do not burn holdout before #21 merges.** After #21 is on `main` (and #20 infra
if still open), Evaluation opens a follow-up PR for candidate verdicts + holdout
once per `(name, 0.1.0)`, then pings DevOps.
