phase: 0
tasks:
  - id: CN-1
    role: human
    status: done
    pr: null
  - id: CN-2
    role: Orchestrator
    status: done
    pr: pending
  - id: CN-3
    role: DevOps
    status: todo
    pr: null
next_action: After this Phase 0 PR merges, DevOps must build CI (ruff, pytest, phase-gate tests, pip-audit, bandit, secret scan), enable auto-merge on green, add the holdout guard, and wire tests/gates/ into the workflow — do not start ingestion or models until that lands.
last_updated: 2026-10-29T13:01:33Z
