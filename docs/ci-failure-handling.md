# CI failure handling (DevOps)

Do not loosen checks. Do not merge red PRs. Do not edit feature or model code from this role.

## Required checks (every PR)

| Check | Purpose |
|-------|---------|
| `lint-test-security` | ruff, pytest (incl. `tests/gates/` + `tests/security/`), pip-audit, bandit, secret-path hygiene, TruffleHog secret scan |
| `holdout-guard` | Non–Evaluation-Skeptic branches may not touch holdout paths |
| `ci` | Aggregate gate for branch protection |

Third-party Actions are pinned to commit SHAs. Workflow `permissions` default to `contents: read`.

## Retry and BLOCKED

1. First CI failure on a PR: fix the cause on the same branch; re-push. Do not disable jobs.
2. Second consecutive CI failure for the same root cause after a real fix attempt: open a GitHub issue titled `BLOCKED: CI <short cause>`, label or tag Orchestrator, set the matching `STATE.md` task to `BLOCKED`, and stop.
3. Task-level autonomous retry cap remains three attempts (Part 6); CI-specific BLOCKED fires at two failed fix cycles so humans are paged earlier for infra.

## Comments on failure

When commenting on a failed PR, include:

- Which job failed (`lint-test-security` vs `holdout-guard`)
- The failing step and a one-line cause
- Whether this is attempt 1 or 2
- Link to `docs/ci-failure-handling.md`
- Explicit: checks will not be loosened

## Holdout guard violations

If `holdout-guard` fails: do not approve. Author must revert holdout path changes and file `docs/requests/evaluation-skeptic-<topic>.md`.

Allowed branch name substrings: `evaluation`, `skeptic`, `holdout` (plus bootstrap `phase-0-setup` / `devops` for guard scaffolding only).

## Red `main`

1. Revert the breaking merge with a revert PR (do not force-push `main`).
2. Require green `ci` before any further feature merges.
3. Record the incident and revert PR URL in `STATE.md`.

## Auto-merge

When repo settings allow auto-merge and checks are green, DevOps enables auto-merge (squash preferred) on the PR. If the integration token cannot merge or auto-merge is disabled, write exact human taps into root `STATE.md` and stop after CI is green.

## Weekly dependencies

Dependabot (`.github/dependabot.yml`) opens weekly pip and GitHub Actions PRs. Those PRs must pass the same CI; pip-audit must stay green.
