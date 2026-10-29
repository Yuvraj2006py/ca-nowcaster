# Security and reliability review (Phase 4)

**Role:** Security and Reliability Reviewer (Role 8)  
**Scope:** Read-only on feature/model code; CI and config edits allowed.  
**Reviewed against:** Part 4 checklist in the build plan + live tree on `main` at review time.  
**Date:** 2026-10-29

## Verdict

CI secret scanning, Dependabot, pinned Actions SHAs, pip-audit, bandit, and ingest HTTP timeouts are already in place and should stay strict. Highest residual risk for Phase 4 is incomplete live/dashboard surface (stubs), weak host allowlisting for env-overridden API bases, and incomplete observation-level API schema validation. Fixes landed in this PR harden CI/config and add hygiene tests; feature/model/live/dashboard code changes go through `docs/requests/`.

## Checklist status

| Check | Status |
|-------|--------|
| Secret scanning / `.env` ignored / no tokens in logs | Pass (hardened this PR) |
| Pinned deps | Pass (`pyproject.toml` pins) |
| pip-audit + bandit in CI | Pass |
| Dependabot | Pass (weekly pip + Actions) |
| Actions least privilege + SHA-pinned | Pass (hardened this PR) |
| API response schema validation | Partial — structural checks only; request filed |
| No `eval` / `exec` / unpickling untrusted files | Pass (hygiene test added) |
| Dashboard: no free-text input / no file paths | N/A yet (stub); request + hygiene guard |
| Timeouts | Pass (ingest HTTP `timeout=`) |
| Idempotent jobs | Partial — raw store yes; live jobs not built |
| Documented recovery per failure mode | Added in `docs/failure_modes.md` |

## Findings (ranked by severity)

### High

#### H1 — Live pipeline and dashboard not implemented (Phase 4 gate risk)

- **Where:** `src/nowcaster/live/__init__.py`, `src/nowcaster/app/__init__.py` (stubs only); no scheduled workflow under `.github/workflows/`.
- **Risk:** No production predict/score job yet means no idempotency, no failure recovery path in code, and no dashboard attack surface to review end-to-end. Phase 4 gate cannot close until Live and Dashboard land and this review is re-checked against their PRs.
- **Fix / accepted risk:** Owned by Live Pipeline and Dashboard. Requests: `docs/requests/live-idempotent-jobs-and-recovery.md`, `docs/requests/dashboard-no-user-input.md`. Security re-review after those PRs merge. **Not accepted as final.**

### Medium

#### M1 — Env-overridable API base URLs enable SSRF-style redirects

- **Where:** `STATCAN_BASE_URL` / `BOC_VALET_BASE_URL` in `src/nowcaster/ingest/statcan.py`, `boc_valet.py`.
- **Risk:** A compromised env (CI secret, host, or malicious local `.env`) can point the HTTP client at an internal or attacker-controlled host. Public v1 has no API keys, but the runner can still be used as an open proxy / metadata scraper.
- **Fix:** Allowlist hosts to official StatCan and BoC Valet origins (reject other schemes/hosts). Request: `docs/requests/ingest-base-url-allowlist.md`.

#### M2 — API responses lack field-level schema validation

- **Where:** StatCan / Valet clients check status and a few keys; observation `value` / `releaseTime` / Valet cells are lightly typed at conversion time only.
- **Risk:** Malformed or hostile JSON can raise late, write NaNs/unexpected types, or skip validation of required publication timestamps — undermining as-of honesty downstream.
- **Fix:** Validate required fields and types per endpoint before store insert (fail closed). Request: `docs/requests/ingest-api-schema-validation.md`.

#### M3 — TruffleHog `--only-verified` can miss unverified high-entropy secrets

- **Where:** `.github/workflows/ci.yml` secret-scan step.
- **Risk:** Unverified patterns (new token formats, private keys without live verification) may not fail CI.
- **Fix (this PR):** Keep verified TruffleHog (no loosen), and add a deterministic tracked-file hygiene scan for common secret path/name patterns plus a pytest hygiene suite. Do **not** drop TruffleHog.

#### M4 — Scheduled live job permissions and secrets not yet constrained

- **Where:** Future workflow for refresh/predict/score (not present).
- **Risk:** A broad `contents: write` scheduled job is a common over-privilege pattern for “commit prediction logs.”
- **Fix:** When Live/DevOps add the workflow: default `permissions: contents: read`; grant write only to the job that commits prediction logs; pin actions by SHA; document recovery. Request filed under Live.

### Low

#### L1 — Bandit reports only `assert` usage (B101)

- **Where:** ingest/store internals; CI uses `bandit -r src -ll` (medium+).
- **Risk:** Asserts stripped under `python -O` could skip invariant checks.
- **Accepted risk:** Internal invariants, not security boundaries; replacing with explicit raises is a nice-to-have for Ingestion, not blocking. **Do not disable B101 globally.**

#### L2 — Dependency hashes not locked

- **Where:** `pyproject.toml` pins versions but CI installs without `--require-hashes`.
- **Risk:** Supply-chain swap of a same-version artifact is harder without hashes.
- **Accepted risk for v1** given pinned versions + pip-audit on every PR. Recommend DevOps add a hashed lockfile post-v1 (`BACKLOG`).

#### L3 — HTTP disk cache has no integrity TTL beyond content hash of request

- **Where:** `src/nowcaster/ingest/http.py` cache under `NOWCASTER_CACHE_DIR`.
- **Risk:** Local cache poisoning if an attacker can write that directory.
- **Accepted risk:** Cache is local/dev; production scheduled runs should set `NOWCASTER_HTTP_CACHE=0` or use a fresh runner workspace (documented in failure modes).

#### L4 — CLI accepts arbitrary `--registry` / `--store` paths

- **Where:** `nowcaster.ingest.cli`.
- **Risk:** Operator can point at unexpected files; not a remote attacker path today.
- **Accepted risk** for operator CLI; dashboard must not expose path inputs (request to Dashboard).

#### L5 — Dependabot Action major bumps must keep SHA pins

- **Where:** Open Dependabot PRs for `actions/checkout`, `setup-python`, `dorny/paths-filter`.
- **Risk:** Merging tag-only refs would undo SHA pinning.
- **Fix:** DevOps merges only when the PR updates the commit SHA comment form already used in `ci.yml`. Security will reject tag-only Action refs.

### Informational / pass notes

- `.env` / `.env.local` / `*.pem` / `.streamlit/secrets.toml` ignored; `.env.example` has no secrets.
- No `eval` / `exec` / `pickle.load` / unsafe `yaml.load` in `src/` (guarded by tests).
- Workflow top-level `permissions: contents: read`; checkouts use `persist-credentials: false` (this PR).
- Raw store insert is idempotent on `(series_id, ref_period, release_timestamp)`.
- Holdout guard restricts who may edit holdout paths.
- Public StatCan/BoC data: no API tokens required for v1.

## Fixes landed in this PR (CI / config only)

1. Checkout `persist-credentials: false`; pin `pip==25.0.1` in CI install step.
2. Explicit job `permissions: contents: read`.
3. Tracked-file secret-path hygiene step (fails on committed `.env`, keys, etc.).
4. `tests/security/test_hygiene.py` — forbidden dynamic execution / pickle / Streamlit free-text widgets.
5. Stronger `.gitignore` secret patterns (still keeps `.env.example`).
6. `docs/failure_modes.md` recovery matrix.
7. Role requests under `docs/requests/` for Ingestion, Live, Dashboard.

## How I could be wrong

- Live/Dashboard PRs may already be in flight with safe designs; findings H1/M4 would then downgrade after merge.
- Host allowlisting may break intentional mock servers in tests if Ingestion does not provide a test-only override.
- A hashed lockfile might be more urgent if pip-audit starts failing on transitive streamlit/pillow churn.
