phase: 1
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
    status: doing
    pr: null
    note: "PR opening — StatCan+Valet clients, verified registry, refresh CLI"
  - id: CN-10
    role: Data Quality
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/13
next_action: Merge Ingestion PR when CI green; then Phase 1 gate / Phase 2.
last_updated: 2026-10-29T14:05:00Z

## Status note

Phase 1 in progress. Data Quality (#13) is on `main`. Ingestion implements StatCan WDS + BoC Valet clients, verified `series_registry.yaml` (10 series), DuckDB raw store with vintage dedupe, and `nowcaster-ingest-refresh` CLI. Live `--twice` refresh: first inserted 5240 rows, second inserted 0. Coordinates with Quality via raw-store contract / Valet release-timestamp request docs.

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
| [#14](https://github.com/Yuvraj2006py/ca-nowcaster/pull/14) | Open — Ingestion clients + registry + refresh CLI |

### Auto-merge / human taps (still recommended)

1. https://github.com/Yuvraj2006py/ca-nowcaster/settings → **Allow auto-merge**
2. Branch ruleset on `main`: require PR + require status check **`ci`** + block force pushes
3. Actions: allow GitHub Actions to create/approve PRs (Dependabot)
