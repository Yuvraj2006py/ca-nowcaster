phase: 3
tasks:
  - id: CN-1
    role: human
    status: done
    pr: null
  - id: CN-2
    role: Orchestrator
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/1
  - id: CN-3
    role: DevOps
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/11
  - id: CN-9
    role: Ingestion
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/14
  - id: CN-10
    role: Data Quality
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/13
  - id: CN-13
    role: Modeling
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/16
  - id: CN-12
    role: Feature
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/17
  - id: CN-14
    role: Evaluation
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/18
  - id: CN-15
    role: Modeling
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/21
    note: "Phase 3 candidates (bridge, DFM, GBM, direction) merged to main"
  - id: CN-16
    role: Evaluation
    status: doing
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/20
    note: "DIRTY after #21 — rebase onto main required before merge; holdout not burned"
next_action: Evaluation rebases and greens #20, then opens follow-up holdout/verdicts PR (once per final model version); do not start Phase 4 until Skeptic holdout/verdicts land.
last_updated: 2026-10-29T15:12:00Z

## Status note

Phase 3 **in progress** (not complete). Modeling candidates [#21](https://github.com/Yuvraj2006py/ca-nowcaster/pull/21) are on `main` (main `ci` green). Evaluation [#20](https://github.com/Yuvraj2006py/ca-nowcaster/pull/20) conflicts with main after #21 — DevOps asked Skeptic to rebase; will squash-merge only when CLEAN + all checks green. Holdout stays locked until a Skeptic follow-up burns it once per final `(name, version)`. **Do not start Phase 4.**

### PRs

| PR | Result |
|----|--------|
| [#1](https://github.com/Yuvraj2006py/ca-nowcaster/pull/1) | Merged — Phase 0 skeleton |
| [#2](https://github.com/Yuvraj2006py/ca-nowcaster/pull/2) | Merged — CI workflow + holdout guard |
| [#11](https://github.com/Yuvraj2006py/ca-nowcaster/pull/11) | Merged green — pip-audit freeze |
| [#13](https://github.com/Yuvraj2006py/ca-nowcaster/pull/13) | Merged — Data Quality as_of gate + quality report |
| [#14](https://github.com/Yuvraj2006py/ca-nowcaster/pull/14) | Merged green — Ingestion clients + registry + refresh CLI |
| [#15](https://github.com/Yuvraj2006py/ca-nowcaster/pull/15) | Merged — Phase 1 complete / Phase 2 next_action |
| [#16](https://github.com/Yuvraj2006py/ca-nowcaster/pull/16) | Merged — Phase 2 Modeling baselines |
| [#17](https://github.com/Yuvraj2006py/ca-nowcaster/pull/17) | Merged — Feature leakage-safe monthly frame |
| [#18](https://github.com/Yuvraj2006py/ca-nowcaster/pull/18) | Merged green — Evaluation harness + joint Phase 2 gate |
| [#19](https://github.com/Yuvraj2006py/ca-nowcaster/pull/19) | Merged — Phase 2 complete / Phase 3 next_action |
| [#20](https://github.com/Yuvraj2006py/ca-nowcaster/pull/20) | Open DIRTY — Evaluation infra; rebase after #21 |
| [#21](https://github.com/Yuvraj2006py/ca-nowcaster/pull/21) | Merged green — Phase 3 Modeling candidates |

### Auto-merge / human taps (still recommended)

1. https://github.com/Yuvraj2006py/ca-nowcaster/settings → **Allow auto-merge**
2. Branch ruleset on `main`: require PR + require status check **`ci`** + block force pushes
3. Actions: allow GitHub Actions to create/approve PRs (Dependabot)
