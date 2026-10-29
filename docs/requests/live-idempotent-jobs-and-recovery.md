# Request: Idempotent live jobs + recovery wiring

**From:** Security and Reliability Reviewer (Role 8)  
**To:** Live Pipeline Engineer (Role 6) (cc DevOps for workflow)  
**Priority:** High for Phase 4 gate (H1 / M4 in `docs/security_review.md`)

## Problem

`src/nowcaster/live/` is a stub. Scheduled refresh/predict/score jobs do not exist yet, so idempotency and failure recovery cannot be verified.

## Ask

1. Refresh job: reuse ingest store uniqueness; exit non-zero on total failure; do not partially invent timestamps.
2. Predict job: append-only prediction log; skip if `(target_ref_month, model_name, model_version)` already present for the same features_hash policy you document.
3. Score job: append-only scores keyed by `prediction_id`; never rewrite past scores.
4. GitHub Actions workflow (with DevOps):
   - SHA-pinned actions
   - default `permissions: contents: read`
   - write permission only on the job that commits prediction/score artifacts
   - `NOWCASTER_HTTP_CACHE=0` on runners
   - timeouts on the job
5. Align runtime behavior with `docs/failure_modes.md` (or request edits there if recovery differs).
6. Simulate failed-API path in tests (graceful no-commit / clear log).

## Out of scope for Security

Security will not implement live jobs; will re-review the workflow YAML when opened.
