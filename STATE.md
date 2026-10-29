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
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/1
next_action: After Phase 0 + CI merge to main (human merge of PR #1), start Phase 1 — Ingestion + Data Quality (Roles 1–2); do not start features or models.
last_updated: 2026-10-29T13:20:00Z

## Human taps required (integration cannot merge / auto-merge)

Repo `allow_auto_merge` is currently **false**, and the Cursor GitHub App lacks merge permission. CI lands on PR #1; a human must merge once checks are green.

### A. Enable auto-merge on the repo (one-time)

1. Open https://github.com/Yuvraj2006py/ca-nowcaster/settings
2. Under **General** → **Pull Requests**, check **Allow auto-merge**
3. Prefer **Allow squash merging** (keep or enable)
4. **Settings** → **Actions** → **General** → Workflow permissions: allow GitHub Actions to create and approve pull requests (if Dependabot/auto-merge bots need it)

### B. Branch protection / ruleset on `main` (one-time)

1. **Settings** → **Rules** → **Rulesets** (or **Branches**)
2. Require a pull request before merging
3. Require status checks to pass; add check name **`ci`** (aggregate job from `.github/workflows/ci.yml`) after the workflow has run once
4. Block force pushes and deletions

### C. Merge PR #1 now (Phase 0 + CI)

1. Open https://github.com/Yuvraj2006py/ca-nowcaster/pull/1
2. Wait until checks are green: **`ci`**, **`lint-test-security`**, **`holdout-guard`**, and GitGuardian
3. Click **Enable auto-merge** (squash) if step A is done; otherwise click **Squash and merge**
4. Confirm merge to `main`

DevOps stops here until that merge completes. Do not start ingestion until `main` has Phase 0 + CI.
