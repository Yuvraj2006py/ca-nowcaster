"""CLI entry points for ingestion refresh.

Inputs: optional CLI flags for registry/store paths and double-refresh mode.
Outputs: process exit code; logs to stderr/stdout via logging.
Time allowed to know: wall clock for retrieved_at only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nowcaster.ingest.refresh import configure_logging, refresh_all, run_double_refresh


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nowcaster-ingest-refresh",
        description="Refresh all verified series_registry.yaml series into the raw store.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Path to series_registry.yaml (default: repo root)",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="Path to DuckDB/SQLite raw store (default: RAW_STORE_PATH or data/raw.duckdb)",
    )
    parser.add_argument(
        "--twice",
        action="store_true",
        help="Run refresh twice and require the second pass to insert 0 rows.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Logging level (default: LOG_LEVEL env or INFO)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI main.

    Inputs: argv flags.
    Outputs: 0 on success; non-zero on failure / duplicate-insert on --twice.
    Time allowed to know: wall clock only.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    if args.twice:
        first, second = run_double_refresh(registry_path=args.registry, store_path=args.store)
        print(
            f"first: inserted={first.total_inserted} skipped={first.total_skipped} "
            f"rows={first.total_rows_after}"
        )
        print(
            f"second: inserted={second.total_inserted} skipped={second.total_skipped} "
            f"rows={second.total_rows_after}"
        )
        if second.total_inserted != 0:
            print(
                "ERROR: second refresh inserted rows; duplicate prevention failed",
                file=sys.stderr,
            )
            return 2
        return 0

    summary = refresh_all(registry_path=args.registry, store_path=args.store)
    print(
        f"refresh: series={len(summary.results)} fetched={summary.total_fetched} "
        f"inserted={summary.total_inserted} skipped={summary.total_skipped} "
        f"rows={summary.total_rows_after} store={summary.store_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
