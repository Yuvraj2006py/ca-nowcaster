# ca-nowcaster

Live, self-scoring nowcasting system for Canadian GDP growth using Statistics Canada and Bank of Canada data.

**Status:** Phase 0 (setup). See `STATE.md`, `AGENTS.md`, and `docs/gates.md`.

## Quick start (after Phase 0 merges)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/gates/test_phase_0.py
```

## Layout

See `AGENTS.md` for roles and rules. Shared schemas live in `src/nowcaster/contracts.py`.
