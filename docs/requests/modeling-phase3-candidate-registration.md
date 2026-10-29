# Request: Modeling — register Phase 3 candidates

From: Evaluation Skeptic (Phase 3)
To: Modeling Engineer
Status: **fulfilled** by [#21](https://github.com/Yuvraj2006py/ca-nowcaster/pull/21)

## Need

Export Phase 3 candidate models through a stable registry so Evaluation can
discover them **without editing** `src/nowcaster/models/`:

```python
from nowcaster.models import list_candidates, create_candidate

list_candidates()  # -> iterable of registered names
create_candidate("bridge")  # -> unfitted NowcastModel
```

## Expected names (v1 plan)

| Name | Notes |
|------|--------|
| `bridge` | Bridge regression |
| `dynamic_factor` | DynamicFactorMQ |
| `gradient_boosting` | Gradient boosting regressor |
| `direction_classifier` | Binary: did growth beat previous month |

Each must implement `NowcastModel` (`fit` / `predict` → point + 80%/95% intervals).

**Modeling note:** `direction_classifier` point predictions **are** calibrated
probabilities in `[0, 1]` (threshold 0.5 for the boolean). Extra comparison model
`direction_boosting` is also registered. All final versions: **`0.1.0`**.

## Versioning / holdout

- Bump `model.version` for every final candidate set Evaluation should score once.
- Evaluation calls `evaluate_holdout_once` **once per (name, version)** and
  appends `docs/holdout_log.md`.

**Modeling signal:** final versions `0.1.0` for
`bridge` / `dynamic_factor` / `gradient_boosting` / `direction_classifier`
(and optional `direction_boosting`) are on `main` via #21 — ready for holdout burn.

## Coordination

- Evaluation follow-up PR refreshes `docs/evaluation_report.md` with candidate
  verdicts and burns holdout once per final `(name, 0.1.0)`.
