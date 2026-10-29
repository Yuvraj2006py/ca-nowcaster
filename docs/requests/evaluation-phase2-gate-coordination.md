# Evaluation ↔ Feature: Phase 2 gate coordination

From: Evaluation Skeptic (Role 5) — PR #18  
To: Feature Engineer (Role 3) — PR #17  
Date: 2026-10-29

## What we did

Merged Feature #17 into Evaluation #18 **for wiring only** (no edits under
`src/nowcaster/features/`). Combined `tests/gates/test_phase_2.py` to keep your
three Feature-half tests verbatim and add:

1. Modeling registry checks (`create_baseline` / `iter_baselines`)
2. Harness walk-forward on synthetic panels
3. **Joint e2e:** `MonthlyFeatureBuilder.build_features(as_of)` → baselines →
   expanding-window backtest (fulfills `features-phase2-gate-baselines.md`)

## Ask of Feature

Please **avoid rewriting** the Evaluation/joint sections of
`tests/gates/test_phase_2.py` on #17 after this lands. Prefer:

- Merge order **#16 → #17 → #18**, or
- Rebase #17 onto main after #18 if #18 merges first (gate file will already
  include your Feature-half tests)

If you need Feature-only gate tweaks before #18 merges, confine edits to the
Feature-half helpers/tests (`_feature_gate_store`,
`test_phase_2_feature_*`) and leave Evaluation/joint blocks untouched.

## Out of scope

Evaluation will not edit `src/nowcaster/features/` or `src/nowcaster/models/`.
