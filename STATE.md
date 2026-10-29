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
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/16
    note: "Phase 2 baselines merged to main (#16)"
  - id: CN-5a
    role: Feature
    status: doing
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/17
    note: "CI green on 9b4bdd1 after rebase onto main post-#16; DevOps pinged to merge"
  - id: CN-5c
    role: Evaluation
    status: todo
    pr: null
    note: "Walk-forward harness on baselines + features still needed for Phase 2 gate"
next_action: DevOps merge Feature PR #17 (CI green); Evaluation wires harness to complete Phase 2 gate.
last_updated: 2026-10-29T14:35:00Z

## Status note

Phase 2 in progress. Modeling baselines (`last_value`, `ar1`, `rolling_mean`) are on
`main` (#16) with `create_baseline` / `iter_baselines` and `docs/models/`. Feature
Engineer: monthly feature frame with MoM/YoY/log-diff/rolling/lags, ragged-edge
strategies (carry / AR1 / leave_missing), `build_features(as_of_date)` +
`features_hash`, leakage nesting tests, `docs/feature_summary.md`, Feature-half of
`tests/gates/test_phase_2.py` (PR #17, rebased onto main). Evaluation still needs
to run baselines end-to-end through the backtest harness.

### Refresh command

```bash
pip install -e ".[dev]"
nowcaster-ingest-refresh --twice
# or: python -m nowcaster.ingest.cli --twice
```

### PRs

| PR | Result |
|----|--------|
| [#1](https://github.com/Yuvraj2006py/ca-nowcaster/pull/1) | Merged — Phase 0 skeleton |
| [#2](https://github.com/Yuvraj2006py/ca-nowcaster/pull/2) | Merged — CI workflow + holdout guard |
| [#11](https://github.com/Yuvraj2006py/ca-nowcaster/pull/11) | Merged green — pip-audit freeze |
| [#13](https://github.com/Yuvraj2006py/ca-nowcaster/pull/13) | Merged — Data Quality as_of gate + quality report |
| [#14](https://github.com/Yuvraj2006py/ca-nowcaster/pull/14) | Merged green — Ingestion clients + registry + refresh CLI |
| [#15](https://github.com/Yuvraj2006py/ca-nowcaster/pull/15) | Merged — Phase 1 complete / Phase 2 next_action |
| [#16](https://github.com/Yuvraj2006py/ca-nowcaster/pull/16) | Merged — Phase 2 Modeling baselines + harness registry |
| [#17](https://github.com/Yuvraj2006py/ca-nowcaster/pull/17) | Open — Feature leakage-safe monthly frame + summary |

### Auto-merge / human taps (still recommended)

1. https://github.com/Yuvraj2006py/ca-nowcaster/settings → **Allow auto-merge**
2. Branch ruleset on `main`: require PR + require status check **`ci`** + block force pushes
3. Actions: allow GitHub Actions to create/approve PRs (Dependabot)
