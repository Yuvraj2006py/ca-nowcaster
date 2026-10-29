# Request: Dashboard must not accept free-text or file paths

**From:** Security and Reliability Reviewer (Role 8)  
**To:** Dashboard Engineer (Role 7)  
**Priority:** High for Phase 4 gate (H1 in `docs/security_review.md`)

## Problem

`src/nowcaster/app/` is a stub. Build-plan Part 4 requires the dashboard to read stored logs only — no user input.

## Ask

1. Streamlit UI: no `st.text_input`, `st.text_area`, `st.file_uploader`, `st.chat_input`, or widgets that accept arbitrary file paths.
2. Data paths come from constants / env documented in `.env.example` (e.g. prediction log path), not from the browser.
3. On missing logs: show a static error message; do not prompt for upload.
4. No `eval` / `exec` / pickle of uploaded content.
5. Hygiene test `tests/security/test_hygiene.py` will fail CI if forbidden Streamlit widgets appear under `src/nowcaster/app/`.

## Out of scope for Security

Security will not build the dashboard; will re-check after the Dashboard PR.
