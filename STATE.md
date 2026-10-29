phase: 0
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
    status: doing
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/11
next_action: After pip-audit fix PR merges and `ci` is green on main, start Phase 1 — Ingestion + Data Quality (Roles 1–2); do not start features or models.
last_updated: 2026-10-29T13:16:00Z

## Status note

- PR #1 Phase 0 skeleton: **merged**
- PR #2 CI workflow: **merged** while `lint-test-security` was still running; `pip-audit` then failed on main (`--strict --skip-editable` treats the editable local dist as a collection failure). Checks were **not** loosened.
- PR #11: fix-forward for pip-audit (freeze `--exclude-editable` + audit with `--strict --no-deps`). This is CI fix attempt **1** for that root cause.
- Dependabot opened PRs #3–#10 after workflows landed; leave them until `ci` is green on main and review separately.

Phase remains **0** until `main` has Phase 0 + **green** CI.

## Human taps required

Repo `allow_auto_merge` is **false**. Do not merge red PRs.

### A. Enable auto-merge (one-time)

1. https://github.com/Yuvraj2006py/ca-nowcaster/settings
2. **General** → **Pull Requests** → **Allow auto-merge**
3. Keep squash merging enabled
4. **Actions** → **General** → allow GitHub Actions to create and approve PRs

### B. Branch protection on `main` (one-time — prevents merging before green)

1. **Settings** → **Rules** → **Rulesets** (or **Branches**)
2. Require a pull request before merging
3. Require status checks to pass; require check name **`ci`**
4. Block force pushes and deletions

### C. Merge PR #11 when green

1. Open https://github.com/Yuvraj2006py/ca-nowcaster/pull/11
2. Wait for green **`ci`** / **`lint-test-security`** / **`holdout-guard`**
3. Squash-merge (or enable auto-merge if A is done)
4. Confirm a subsequent push/`ci` run on `main` is green

If PR #11 CI fails again for the same pip-audit cause after this fix, open a GitHub issue `BLOCKED: CI pip-audit` and set CN-3 to BLOCKED (see `docs/ci-failure-handling.md`).
