# Request: Modeling — export baseline factories

From: Evaluation Skeptic (Phase 2 harness)
To: Modeling Engineer

## Status: fulfilled by PR #16

Modeling shipped the requested registry API:

```python
from nowcaster.models import create_baseline, iter_baselines
```

Names: `last_value`, `ar1`, `rolling_mean` — each implements `NowcastModel`
(`fit` / `predict` → point + 80%/95% intervals).

Evaluation wires the Phase 2 harness and gate to that API via
`nowcaster.evaluation.baselines_loader` (no edits under `src/nowcaster/models/`).

## Original need (kept for audit trail)

Export the three v1 baselines so Evaluation can discover them without importing
private modules; zero-arg constructible through a stable registry.
