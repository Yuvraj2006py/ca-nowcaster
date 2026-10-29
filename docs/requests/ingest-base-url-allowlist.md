# Request: Allowlist StatCan / Valet base URLs

**From:** Security and Reliability Reviewer (Role 8)  
**To:** Ingestion Engineer (Role 1)  
**Priority:** Medium (M1 in `docs/security_review.md`)

## Problem

`STATCAN_BASE_URL` and `BOC_VALET_BASE_URL` (and constructor `base_url=`) accept any URL. A compromised environment can turn the ingest client into an SSRF probe against internal hosts.

## Ask

1. Resolve effective base URL, then allow only:
   - `https://www150.statcan.gc.ca/t1/wds/rest` (and documented StatCan WDS hosts if verification needs a second official host)
   - `https://www.bankofcanada.ca/valet`
2. Reject non-HTTPS and any other host with a clear error.
3. For unit tests, prefer injecting a fake `session` / transport rather than arbitrary public URLs; if a test override is required, gate it behind an explicit `NOWCASTER_ALLOW_INSECURE_BASE_URL=1` used only in tests.
4. Add tests that a private IP / `http://` base URL is refused.

## Out of scope for Security

Do not edit ingest code from the Security branch; this request is the handoff.
