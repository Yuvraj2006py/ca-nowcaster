# Request: Ingestion → Data Quality

From: Data Quality and Timing (Role 2)
To: Ingestion Engineer (Role 1)
Date: 2026-10-29

## Need

Quality reads **only** the shared raw-store contract
(`series_id`, `ref_period`, `value`, `release_timestamp`, `retrieved_at`).
Please expose (or document the path of) an append-only store that Quality can
load without importing ingest internals — e.g. `data/raw/observations.parquet`
or a DuckDB table with those exact columns.

## Release timestamps

For each vintage, set `release_timestamp` to when the value became **public**
(StatCan The Daily / WDS release time, or BoC Valet observation time) — not
solely `retrieved_at`. When the true vintage time is unknown for history,
leave `release_timestamp` null so Quality can apply
`apply_publication_lags` (pseudo-real-time) and flag approximations.

## Registry

Once series IDs are verified in `series_registry.yaml`, please align ids with
(or tell us to update) `src/nowcaster/quality/typical_lags.yaml` so lag
defaults match. Optional future contract field:
`typical_publication_lag_days` on each registry entry (Orchestrator change
request if you agree).

## Out of scope for this request

Do not change feature or model code. Quality will not edit `src/nowcaster/ingest/`.
