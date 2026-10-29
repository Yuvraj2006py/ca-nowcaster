phase: 2
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
    status: doing
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/16
    note: "Phase 2 baselines PR #16 CI green — ready to merge; Evaluation can import create_baseline/iter_baselines"
next_action: Merge Modeling baselines PR #16 (CI green); Evaluation wires harness; Feature continues leakage-safe frame.
last_updated: 2026-10-29T14:26:00Z

## Status note

Phase 2 in progress. Modeling implements Phase 2 **baselines only** under `src/nowcaster/models/`: `last_value`, `ar1`, `rolling_mean`, each with `fit` / `predict` → point + 80%/95% intervals, plus `create_baseline` / `iter_baselines` for the evaluation harness. Plain-language pages in `docs/models/`. Features API still incomplete — baselines use synthetic fixtures and `docs/requests/features-baseline-xy-contract.md`.

### PRs

| PR | Result |
|----|--------|
| [#1](https://github.com/Yuvraj2006py/ca-nowcaster/pull/1) | Merged — Phase 0 skeleton |
| [#2](https://github.com/Yuvraj2006py/ca-nowcaster/pull/2) | Merged — CI workflow + holdout guard |
| [#11](https://github.com/Yuvraj2006py/ca-nowcaster/pull/11) | Merged green — pip-audit freeze |
| [#13](https://github.com/Yuvraj2006py/ca-nowcaster/pull/13) | Merged — Data Quality as_of gate + quality report |
| [#14](https://github.com/Yuvraj2006py/ca-nowcaster/pull/14) | Merged green — Ingestion clients + registry + refresh CLI |
| [#15](https://github.com/Yuvraj2006py/ca-nowcaster/pull/15) | Merged — Phase 1 complete / Phase 2 next_action |
| [#16](https://github.com/Yuvraj2006py/ca-nowcaster/pull/16) | Open, CI green — Phase 2 Modeling baselines + harness registry |

### Auto-merge / human taps (still recommended)

1. https://github.com/Yuvraj2006py/ca-nowcaster/settings → **Allow auto-merge**
2. Branch ruleset on `main`: require PR + require status check **`ci`** + block force pushes
3. Actions: allow GitHub Actions to create/approve PRs (Dependabot)
