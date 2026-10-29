# Live pipeline (Role 6)

Scheduled self-scoring nowcast with an honest public record.

## Production model: AR(1)

**Chosen model:** `ar1` @ `0.1.0` (`nowcaster.models.baselines.AR1Baseline`).

**Why not a Phase 3 candidate?** The Evaluation Skeptic's Phase 3 report
(`docs/evaluation_report.md`) states the honest result: no regression candidate
beats the AR(1) reference on headline RMSE with Diebold-Mariano significance and
bootstrap CI support. Direction classifiers are scored separately and are not
used as the GDP MoM point nowcast. Under the honest-result rule, v1 ships with
AR(1) rather than a candidate that failed to clear the skeptic bar.

Constants live in `src/nowcaster/live/production.py`.

## Jobs

| Job | Module | What it does |
|-----|--------|----------------|
| Predict | `live.predict_job` | Refresh raw store → `build_features(as_of)` → fit AR(1) on as-of MoM history → append `logs/predictions.csv` **before** the official release for the next unpublished month |
| Score | `live.score_job` | When the official MoM for a logged `target_ref_month` is public, append `logs/scores.csv` |
| Dry-run | `live.dry_run` | Historical replay (predict + score) plus failed-API simulation |

CLI: `nowcaster-live predict | score | dry-run`.

## Tamper evidence

Predictions and scores are append-only CSVs under `logs/`. The scheduled GitHub
Actions workflows commit those files with a UTC timestamp in the commit message
so the public git history is the audit trail (`predicted_at` / `scored_at` are
also stored in each row).

## Failure handling

If ingestion fails (or `--simulate-ingest-failure`):

1. Append a line to `logs/failures.jsonl`
2. **Skip predict** — never forecast on stale data
3. When `GITHUB_TOKEN` + `GITHUB_REPOSITORY` are set, open a GitHub issue
   titled `BLOCKED: live ingest failure — <date>`

## Dry-run

```bash
nowcaster-live dry-run \
  --store data/raw.duckdb \
  --predict-as-of 2023-06-15 \
  --score-as-of 2023-08-28 \
  --work-dir /tmp/nowcaster-dry-run
```

Tests use an in-memory fixture store (no live network).

## Workflows

See `.github/workflows/live-predict.yml` and `live-score.yml`. DevOps coordination
for Actions permissions: `docs/requests/devops-live-pipeline-workflows.md`.
