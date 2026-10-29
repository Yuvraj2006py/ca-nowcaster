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
    status: doing
    pr: null
    note: "Phase 3 candidates (bridge, DFM, GBM, direction) registered; PR opening"
  - id: CN-16
    role: Evaluation
    status: doing
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/20
    note: "Skeptic report open; waiting on Modeling candidates then holdout burn"
next_action: Merge Modeling Phase 3 candidates PR when CI green; Evaluation rebases #20, refreshes report, burns holdout once per (name, version=0.1.0).
last_updated: 2026-10-29T15:05:00Z

## Status note

Phase 3 in progress. Modeling ships candidate registry (`list_candidates` /
`create_candidate` / `iter_candidates`) with final versions **`0.1.0`**:
`bridge`, `dynamic_factor`, `gradient_boosting`, `direction_classifier`
(+ comparison `direction_boosting`). Baselines untouched. Evaluation #20 has
metrics/audits but no candidates yet — ready to discover after this Modeling PR
lands. Holdout stays locked until Skeptic burns once per final version.

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
| [#20](https://github.com/Yuvraj2006py/ca-nowcaster/pull/20) | Open — Evaluation Skeptic Phase 3 (awaiting candidates) |

### Auto-merge / human taps (still recommended)

1. https://github.com/Yuvraj2006py/ca-nowcaster/settings → **Allow auto-merge**
2. Branch ruleset on `main`: require PR + require status check **`ci`** + block force pushes
3. Actions: allow GitHub Actions to create/approve PRs (Dependabot)
