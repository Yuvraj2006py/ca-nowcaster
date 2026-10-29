"""CLI entry points for live predict, score, and dry-run jobs."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from nowcaster.ingest.refresh import configure_logging
from nowcaster.live.dry_run import assert_dry_run_ok, run_dry_run
from nowcaster.live.failures import IngestFailureError
from nowcaster.live.predict_job import run_predict_job
from nowcaster.live.score_job import run_score_job
from nowcaster.live.store_io import load_raw_store_frame


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    text = value.strip()
    if len(text) == 7 and text[4] == "-":
        text = f"{text}-01"
    return date.fromisoformat(text[:10])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nowcaster-live",
        description="Live nowcast pipeline: predict, score, or dry-run.",
    )
    parser.add_argument("--log-level", default=None, help="Logging level")
    sub = parser.add_subparsers(dest="command", required=True)

    predict = sub.add_parser("predict", help="Refresh (optional) and append a prediction")
    predict.add_argument("--as-of", type=str, default=None, help="YYYY-MM-DD as-of cutoff")
    predict.add_argument("--store", type=Path, default=None)
    predict.add_argument("--prediction-log", type=Path, default=None)
    predict.add_argument("--failure-log", type=Path, default=None)
    predict.add_argument("--registry", type=Path, default=None)
    predict.add_argument("--no-refresh", action="store_true")
    predict.add_argument(
        "--simulate-ingest-failure",
        action="store_true",
        help="Skip predict and log a simulated API failure (dry-run aid)",
    )
    predict.add_argument("--no-github-issue", action="store_true")
    predict.add_argument("--allow-duplicate-month", action="store_true")

    score = sub.add_parser("score", help="Score predictions whose actuals are public")
    score.add_argument("--as-of", type=str, default=None)
    score.add_argument("--store", type=Path, default=None)
    score.add_argument("--prediction-log", type=Path, default=None)
    score.add_argument("--score-log", type=Path, default=None)

    dry = sub.add_parser(
        "dry-run",
        help="Historical replay on an existing store + failed-API simulation",
    )
    dry.add_argument("--store", type=Path, required=True, help="Existing raw store path")
    dry.add_argument("--predict-as-of", type=str, required=True)
    dry.add_argument("--score-as-of", type=str, required=True)
    dry.add_argument("--work-dir", type=Path, required=True)
    dry.add_argument("--registry", type=Path, default=None)
    dry.add_argument("--no-failed-api", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI main.

    Inputs: argv flags.
    Outputs: 0 on success; non-zero on ingest failure / dry-run assertion failure.
    Time allowed to know: as-of flags constrain data visibility.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    if args.command == "predict":
        try:
            result = run_predict_job(
                as_of_date=_parse_date(args.as_of),
                store_path=args.store,
                prediction_path=args.prediction_log,
                failure_path=args.failure_log,
                registry_path=args.registry,
                refresh=not args.no_refresh,
                open_issue_on_ingest_failure=not args.no_github_issue,
                allow_duplicate_month=args.allow_duplicate_month,
                simulate_ingest_failure=(
                    "CLI --simulate-ingest-failure" if args.simulate_ingest_failure else None
                ),
            )
        except IngestFailureError as exc:
            print(f"INGEST_FAILURE: {exc}", file=sys.stderr)
            return 2
        print(f"predict: status={result.status} as_of={result.as_of_date} {result.message}")
        if result.entry is not None:
            print(
                f"  id={result.entry.prediction_id} month={result.entry.target_ref_month} "
                f"point={result.entry.point:.6f}"
            )
        return 0 if result.status in {"predicted", "skipped_duplicate"} else 1

    if args.command == "score":
        result = run_score_job(
            as_of_date=_parse_date(args.as_of),
            store_path=args.store,
            prediction_path=args.prediction_log,
            score_path=args.score_log,
        )
        print(f"score: {result.message} as_of={result.as_of_date}")
        for entry in result.scored:
            print(
                f"  id={entry.prediction_id} actual={entry.actual:.6f} "
                f"abs_error={entry.abs_error:.6f}"
            )
        return 0

    if args.command == "dry-run":
        frame = load_raw_store_frame(args.store)
        if frame.empty:
            print("ERROR: store is empty; cannot dry-run", file=sys.stderr)
            return 2
        result = run_dry_run(
            store_frame=frame,
            predict_as_of=_parse_date(args.predict_as_of),  # type: ignore[arg-type]
            score_as_of=_parse_date(args.score_as_of),  # type: ignore[arg-type]
            work_dir=args.work_dir,
            registry_path=args.registry,
            simulate_failed_api=not args.no_failed_api,
            predicted_at=datetime.fromisoformat(
                f"{args.predict_as_of}T12:00:00+00:00"
                if len(args.predict_as_of) >= 10
                else f"{args.predict_as_of}-01T12:00:00+00:00"
            ),
            scored_at=datetime.fromisoformat(
                f"{args.score_as_of}T12:00:00+00:00"
                if len(args.score_as_of) >= 10
                else f"{args.score_as_of}-01T12:00:00+00:00"
            ),
        )
        try:
            assert_dry_run_ok(result)
        except AssertionError as exc:
            print(f"DRY_RUN_FAILED: {exc}", file=sys.stderr)
            return 3
        assert result.predict is not None and result.predict.entry is not None
        assert result.score is not None
        print(
            f"dry-run ok: predicted={result.predict.entry.prediction_id} "
            f"scored={len(result.score.scored)} "
            f"failed_api={result.failed_api.status if result.failed_api else None}"
        )
        print(f"  prediction_log={result.prediction_log}")
        print(f"  score_log={result.score_log}")
        print(f"  failure_log={result.failure_log}")
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
