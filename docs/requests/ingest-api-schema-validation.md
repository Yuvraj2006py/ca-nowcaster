# Request: Field-level API response schema validation

**From:** Security and Reliability Reviewer (Role 8)  
**To:** Ingestion Engineer (Role 1)  
**Priority:** Medium (M2 in `docs/security_review.md`)

## Problem

Clients check WDS/Valet `status` and a few keys, but observation rows are not validated against an explicit schema before `RawObservation` construction. Bad types or missing `releaseTime` can fail late or skip honesty guarantees.

## Ask

1. Define small validators (dict schemas or explicit checks) for:
   - StatCan `vectorDataPoint`: require `refPer`, numeric `value`, parseable `releaseTime`
   - Valet observation: require `d`, series cell with numeric `v` (or skip empty with log)
2. Fail closed on required-field violations for StatCan; keep Valet empty-cell skip but type-check non-empty cells.
3. Cover validators with fixture-based tests (malformed payloads).
4. Do not invent API fields; only enforce fields already used and verified in the registry notes.

## Out of scope for Security

No edits under `src/nowcaster/ingest/` from the Security role.
