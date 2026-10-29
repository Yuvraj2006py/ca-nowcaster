# Failure modes and recovery (v1)

Owned by Security (documentation) with Live Pipeline / DevOps implementing runtime behavior. Do not loosen CI to “recover.”

| Failure mode | Detection | Recovery | Owner |
|--------------|-----------|----------|-------|
| Upstream StatCan/Valet HTTP 5xx / timeout | Ingest logs `IngestHttpError` after retries; refresh exit ≠ 0 | Retry with backoff (already in `RateLimitedSession`); on scheduled job failure, leave store unchanged and alert via Actions failure / BLOCKED issue after two fix cycles (`docs/ci-failure-handling.md`) | Ingestion / Live |
| Upstream HTTP 4xx (auth/path) | Hard fail, no retry | Fix registry/URL; do not cache error bodies as success | Ingestion |
| Corrupt / empty registry | `RegistryError` or empty-series refuse in `refresh_all` | Revert registry PR; do not invent series IDs | Ingestion / Orchestrator |
| Duplicate vintage insert | Unique index + `INSERT OR IGNORE`; `--twice` CLI check | Idempotent by design; if second pass inserts >0, treat as bug and BLOCKED | Ingestion |
| Look-ahead / as_of leakage | Phase 1 gate + feature leakage tests | Fail CI; do not ship | Quality / Feature / Evaluation |
| Model worse than baseline | Evaluation report honest-result rule | Still ship v1 per plan; do not hide metrics | Evaluation |
| Holdout burned twice | `HoldoutLockedError` / holdout-guard CI | Revert; only Skeptic branches may touch holdout paths | Evaluation / DevOps |
| CI red on PR | `ci` aggregate job | Fix cause; never disable pip-audit/bandit/secret scan; two failed fix cycles → BLOCKED issue | Author / DevOps |
| Red `main` | Failed push workflow | Revert merge via PR; no force-push | DevOps |
| Dependency CVE | pip-audit `--strict` | Bump pin in PR; Dependabot weekly; do not `--ignore-vuln` without Orchestrator written waiver | DevOps |
| Secret committed | TruffleHog + hygiene scan | Rotate if real; purge from history; keep ignore rules | Security / human |
| Disk HTTP cache poison / stale | Unexpected series values vs live | Delete `NOWCASTER_CACHE_DIR`; set `NOWCASTER_HTTP_CACHE=0` on scheduled runners | Live / Ingestion |
| Live predict job double-run | (pending Live) | Must key prediction log on `(target_ref_month, model_name, model_version)` and skip if already logged | Live |
| Dashboard cannot read logs | Missing artifact path | Fail visibly with static message; never accept user file paths | Dashboard |
| Streamlit Community Cloud outage | External | Document status; data/logs remain in repo/store | Dashboard / Docs |

## Scheduled-runner defaults (when Live adds the workflow)

- `NOWCASTER_HTTP_CACHE=0` (or ephemeral workspace).
- No secrets required for public StatCan/BoC pulls.
- Workflow `permissions` default read; write only for the prediction-commit job.
- Actions pinned to commit SHAs (same policy as `ci.yml`).
