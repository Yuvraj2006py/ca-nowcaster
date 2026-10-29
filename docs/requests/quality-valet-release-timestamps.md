# Request for Data Quality: Valet release_timestamp convention

**From:** Ingestion (Role 1)
**To:** Data Quality and Timing (Role 2)

## Context

StatCan WDS points include `releaseTime`; we store that as `release_timestamp`.

Bank of Canada Valet observation payloads do **not** include a separate release timestamp—only the observation date `d`.

## What Ingestion did

For Valet series (`STATIC_ATABLE_V39079`, `FXMUSDCAD`, `M.BCPI`), `release_timestamp` is stamped as **America/Toronto 16:30 on the observation date** (Valet’s documented FX publish window), converted to UTC. This is recorded in `src/nowcaster/ingest/refresh.py` (`_valet_release_timestamp`).

## Ask

Please review whether this lag assumption is acceptable for `as_of` views, or propose a stricter rule (e.g. next business day, or `retrieved_at`-only for historical Valet). Do **not** require Ingestion to invent earlier publication times.

No code changes requested in `quality/` from this note until you decide.
