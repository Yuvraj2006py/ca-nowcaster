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
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/2
next_action: After CI PR merges to main (human merge if needed), start Phase 1 — Ingestion + Data Quality (Roles 1–2); do not start features or models.
last_updated: 2026-10-29T13:25:00Z

## Status note

PR #1 (Phase 0 skeleton) is **merged** to `main`. CI did not land in that merge (CI commit arrived on the branch after merge). DevOps follow-up is PR #2 on `cursor/devops-ci-9deb`.

Phase remains **0** until `main` has Phase 0 **and** CI.

## Human taps required

Repo `allow_auto_merge` is **false**. Cursor integration cannot enable auto-merge. Actions showed **zero** workflow runs before CI existed on a PR — confirm Actions are enabled.

### A. Enable GitHub Actions (if workflows do not appear on PR #2)

1. Open https://github.com/Yuvraj2006py/ca-nowcaster/settings/actions
2. Under **Actions permissions**, choose **Allow all actions and reusable workflows** (or allow necessary actions)
3. Save

### B. Enable auto-merge on the repo (one-time)

1. Open https://github.com/Yuvraj2006py/ca-nowcaster/settings
2. **General** → **Pull Requests** → check **Allow auto-merge**
3. Prefer squash merging enabled
4. **Settings** → **Actions** → **General** → allow GitHub Actions to create and approve pull requests (Dependabot / bot PRs)

### C. Branch protection / ruleset on `main` (one-time)

1. **Settings** → **Rules** → **Rulesets** (or **Branches**)
2. Require a pull request before merging
3. Require status checks; add check name **`ci`** after it has run once on PR #2
4. Block force pushes and deletions

### D. Merge PR #2 (CI) when green

1. Open https://github.com/Yuvraj2006py/ca-nowcaster/pull/2
2. Wait for green: **`ci`**, **`lint-test-security`**, **`holdout-guard`** (and GitGuardian if present)
3. **Enable auto-merge** (squash) if step B is done; otherwise **Squash and merge**
4. Confirm merge to `main`

DevOps stops after CI is green if merge permission is denied. Do not start ingestion until `main` has CI.
