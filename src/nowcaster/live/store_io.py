"""Load the raw store as a DataFrame for feature / target construction.

Calls ingest RawStore.fetch_all only; does not invent release timestamps.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nowcaster.ingest.store import RawStore
from nowcaster.quality.frame import empty_raw_frame, normalize_raw_frame


def load_raw_store_frame(store_path: Path | str | None = None) -> pd.DataFrame:
    """Load all raw vintages into a RAW_STORE_COLUMNS DataFrame.

    Inputs: optional store path (default RAW_STORE_PATH / data/raw.duckdb).
    Outputs: normalized DataFrame; empty frame if the store file is missing.
    Time allowed to know: whatever vintages are already persisted; no live API.
    """
    path = Path(store_path) if store_path is not None else None
    if path is not None and not path.exists():
        return empty_raw_frame()

    store = RawStore(path)
    try:
        rows = store.fetch_all()
    finally:
        store.close()
    if not rows:
        return empty_raw_frame()
    return normalize_raw_frame(pd.DataFrame.from_records(rows))
