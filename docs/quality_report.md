# Data quality status by series

Generated: `2026-10-29T13:50:30Z` (UTC).

## Data source

**Phase 1 fixture store** (synthetic vintages exercising each check). Live
StatCan/BoC rows are not in-repo yet — see
`docs/requests/ingest-raw-store-and-release-timestamps.md`. Re-run
`nowcaster.quality.write_quality_report` against the raw store once Ingestion
lands.

## Scope

Owned by **Data Quality and Timing** (`src/nowcaster/quality/`).
Checks: missing periods, unit changes, sudden level breaks, duplicated rows,
stale series. Timing: `as_of(date)` never returns a value with
`release_timestamp` after the cutoff; pseudo-real-time lags are flagged
as approximations when measured vintages are missing.

## Store snapshot

- Raw rows: **15**
- Distinct series: **5**
- Issues found: **12** (errors=2, warnings=6, info=4)

## Series status

| series_id | status | rows | ref_period min | ref_period max | errors | warnings | notes |
|---|---|---:|---|---|---:|---:|---|
| `(store-wide)` | fail | 15 | — | — | 1 | 1 | 1 duplicated vintage key group(s) (series_id, ref_period, release_timestamp).; 2 fully identical row(s) present. |
| `ca_gdp_basic_prices` | warn | 1 | 2022-01-01 | 2022-01-01 | 0 | 1 | Series looks stale: latest ref_period=2022-01-01; expected next print by ~2022-05-13 (lag=60d, grace=14d). |
| `fixture_clean_index` | ok | 6 | 2023-01-01 | 2023-06-01 | 0 | 0 | No typical lag configured; staleness not assessed. |
| `fixture_dupes` | ok | 2 | 2023-01-01 | 2023-01-01 | 0 | 0 | No typical lag configured; staleness not assessed. |
| `fixture_gap_series` | warn | 4 | 2023-01-01 | 2023-05-01 | 0 | 3 | 1 missing monthly ref_period(s) between 2023-01-01 and 2023-05-01.; Level break 2023-01-01 → 2023-02-01: 100.0% change (threshold 25%).; Level break 2023-02-01 → 2023-04-01: 100.0% change (threshold 25%). |
| `fixture_unit_change` | fail | 2 | 2023-01-01 | 2023-02-01 | 1 | 1 | Suspected unit change 2023-01-01 → 2023-02-01: ratio≈1e+03 (near 1000 or 1/1000).; Level break 2023-01-01 → 2023-02-01: 99900.0% change (threshold 25%).; No typical lag configured; staleness not assessed. |

## Issue detail

- **error** / `duplicated_rows` / `(store)`: 1 duplicated vintage key group(s) (series_id, ref_period, release_timestamp).
- **warning** / `duplicated_rows` / `(store)`: 2 fully identical row(s) present.
- **warning** / `missing_periods` / `fixture_gap_series`: 1 missing monthly ref_period(s) between 2023-01-01 and 2023-05-01.
- **error** / `unit_change` / `fixture_unit_change`: Suspected unit change 2023-01-01 → 2023-02-01: ratio≈1e+03 (near 1000 or 1/1000).
- **warning** / `level_break` / `fixture_gap_series`: Level break 2023-01-01 → 2023-02-01: 100.0% change (threshold 25%).
- **warning** / `level_break` / `fixture_gap_series`: Level break 2023-02-01 → 2023-04-01: 100.0% change (threshold 25%).
- **warning** / `level_break` / `fixture_unit_change`: Level break 2023-01-01 → 2023-02-01: 99900.0% change (threshold 25%).
- **warning** / `stale_series` / `ca_gdp_basic_prices`: Series looks stale: latest ref_period=2022-01-01; expected next print by ~2022-05-13 (lag=60d, grace=14d).
- **info** / `stale_series` / `fixture_clean_index`: No typical lag configured; staleness not assessed.
- **info** / `stale_series` / `fixture_dupes`: No typical lag configured; staleness not assessed.
- **info** / `stale_series` / `fixture_gap_series`: No typical lag configured; staleness not assessed.
- **info** / `stale_series` / `fixture_unit_change`: No typical lag configured; staleness not assessed.

## Timing controls

- `nowcaster.quality.as_of(store, as_of_date)` — latest vintage per
  `(series_id, ref_period)` with `release_timestamp <= as_of_date`.
- `nowcaster.quality.apply_publication_lags(...)` — fills missing
  release times from `typical_lags.yaml` and sets
  `release_is_approximate=true`.
- Phase 1 gate: `tests/gates/test_phase_1.py` asserts no as_of leakage.

## How this report could be wrong

- Fixture or incomplete ingest data may not reflect live StatCan/BoC.
- Typical lags are approximations, not official schedules.
- Level-break thresholds can false-flag volatile series (e.g. commodities).
- Staleness needs a configured lag; unknown series_ids are info-only.
