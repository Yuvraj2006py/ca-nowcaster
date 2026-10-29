# Request: Modeling — register Phase 3 candidates

From: Evaluation Skeptic (Phase 3)
To: Modeling Engineer
Status: **fulfilled** by Modeling PR (Phase 3 candidates)

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
The direction classifier may also expose probabilities via `extras` or a documented
`predict_proba`-style attribute; until then Evaluation uses `sign(point)`.

**Modeling note:** `direction_classifier` point predictions **are** calibrated
probabilities in `[0, 1]` (threshold 0.5 for the boolean). Extra comparison model
`direction_boosting` is also registered. All final versions: **`0.1.0`**.

## Versioning / holdout

- Bump `model.version` for every final candidate set Evaluation should score once.
- Do **not** ask Evaluation to unlock holdout until versions are final.
- Evaluation will call `evaluate_holdout_once` **once per (name, version)** and
  append `docs/holdout_log.md`.

**Modeling signal:** final versions `0.1.0` for
`bridge` / `dynamic_factor` / `gradient_boosting` / `direction_classifier`
(and optional `direction_boosting`) are ready for the holdout burn after this
registry lands on `main`.

## Coordination

- Evaluation PR evaluates baselines now and leaves holdout **LOCKED**.
- When this registry lands on `main` (or on a Modeling PR), Evaluation rebases,
  re-runs walk-forward + DM/bootstrap, refreshes `docs/evaluation_report.md`,
  then burns holdout once per final version.
