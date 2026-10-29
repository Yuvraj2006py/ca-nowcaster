"""Feature summary table generation for docs/feature_summary.md."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from nowcaster.features.builder import MonthlyFeatureBuilder
from nowcaster.features.recipe import FeatureSpec


def missing_rates(frame: pd.DataFrame) -> dict[str, float]:
    """Fraction of rows that are NaN per feature column.

    Inputs: feature DataFrame from build_features.
    Outputs: mapping column -> missing rate in [0, 1].
    Time allowed to know: whatever is already in ``frame``.
    """
    if frame.empty:
        return {}
    rates = frame.isna().mean()
    return {str(k): float(v) for k, v in rates.items()}


def build_summary_rows(
    specs: list[FeatureSpec],
    rates: dict[str, float] | None = None,
) -> list[dict[str, object]]:
    """Combine FeatureSpec metadata with optional empirical missing rates.

    Inputs: feature specs; optional missing-rate map from a built frame.
    Outputs: list of dict rows for a markdown table.
    Time allowed to know: rates reflect the as_of used to build that frame.
    """
    rates = rates or {}
    rows: list[dict[str, object]] = []
    for spec in specs:
        rows.append(
            {
                "name": spec.name,
                "source": f"{spec.source}:{spec.source_series_id}",
                "transform": spec.transform,
                "lag": spec.lag,
                "missing_rate": rates.get(spec.name),
                "notes": spec.notes,
            }
        )
    return rows


def render_feature_summary_markdown(
    rows: list[dict[str, object]],
    *,
    as_of_date: date | None = None,
    features_hash: str | None = None,
    ragged_strategy: str | None = None,
    title: str = "Feature summary",
) -> str:
    """Render a markdown feature summary document.

    Inputs: summary rows; optional provenance fields.
    Outputs: markdown string.
    Time allowed to know: as_of_date of the frame used for missing rates.
    """
    lines: list[str] = [
        f"# {title}",
        "",
        "Owned by **Feature Engineer** (`src/nowcaster/features/`).",
        "",
        "Index = target reference month. Features are built only from values",
        "with `release_timestamp <= as_of_date` via `quality.as_of`.",
        "",
    ]
    if as_of_date is not None:
        lines.append(f"- **as_of_date (for missing rates):** `{as_of_date.isoformat()}`")
    if features_hash is not None:
        lines.append(f"- **features_hash:** `{features_hash}`")
    if ragged_strategy is not None:
        lines.append(f"- **ragged_edge strategy:** `{ragged_strategy}`")
    lines.extend(
        [
            "",
            "## Feature table",
            "",
            "| name | source | transform | lag | missing_rate | notes |",
            "|---|---|---|---:|---:|---|",
        ]
    )
    for row in rows:
        miss = row.get("missing_rate")
        miss_s = "—" if miss is None else f"{float(miss):.3f}"
        notes = str(row.get("notes") or "").replace("|", "/")
        lines.append(
            f"| `{row['name']}` | `{row['source']}` | `{row['transform']}` | "
            f"{row['lag']} | {miss_s} | {notes} |"
        )
    lines.extend(
        [
            "",
            "## Ragged-edge strategies (v1)",
            "",
            "| strategy | behavior |",
            "|---|---|",
            "| `leave_missing` | Trailing NaNs stay missing (models that support NaN / masking). |",
            "| `carry` | Carry last published level into trailing months. |",
            "| `ar1` | Simple AR(1) on level differences, then integrate forward. |",
            "",
            "## How I could be wrong",
            "",
            "- Missing rates depend on the as_of date and store contents; live rates",
            "  will differ from fixture rates used in CI docs.",
            "- YoY / rolling windows create structural leading NaNs unrelated to",
            "  publication lag.",
            "- AR(1) ragged fill is a crude imputer — not a structural nowcast.",
            "",
        ]
    )
    return "\n".join(lines)


def write_feature_summary(
    path: Path | str,
    builder: MonthlyFeatureBuilder,
    *,
    as_of_date: date,
) -> Path:
    """Build features at as_of_date and write docs/feature_summary.md.

    Inputs: output path; configured builder; as_of cutoff for missing rates.
    Outputs: path written.
    Time allowed to know: only as_of-filtered store contents.
    """
    frame, meta = builder.build_features(as_of_date)
    rows = build_summary_rows(builder.feature_specs(), missing_rates(frame))
    text = render_feature_summary_markdown(
        rows,
        as_of_date=meta.as_of_date,
        features_hash=meta.features_hash,
        ragged_strategy=builder.recipe.ragged_strategy,
    )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out
