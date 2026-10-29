# Request: DevOps — live pipeline workflow permissions

From: Live Pipeline Engineer (Role 6)
To: DevOps and Release Agent (Role 10)
Date: 2026-10-29
Status: open

## Context

Phase 4 live jobs land as **new** workflow files (not edits to `ci.yml`):

- `.github/workflows/live-predict.yml`
- `.github/workflows/live-score.yml`

CI (`ci.yml`) is untouched — checks are not loosened.

## Ask

1. Confirm the new workflows may use:
   - `permissions: contents: write` (commit append-only `logs/predictions.csv` /
     `logs/scores.csv` / `logs/failures.jsonl` for tamper-evident history)
   - `permissions: issues: write` (open `BLOCKED: live ingest failure` issues)
2. Ensure the default `GITHUB_TOKEN` can push commits to `main` from Actions
   (branch protection / allow GitHub Actions to bypass or open a bot PR — your call;
   Live Pipeline prefers direct commit of log appends with a timestamped message).
3. Do **not** weaken `lint-test-security`, holdout-guard, pip-audit, bandit, or
   TruffleHog on PRs.

## Out of scope for Live

No changes to feature/model/evaluation packages beyond calling their public APIs.
No edits to shared CI job definitions in this request.
