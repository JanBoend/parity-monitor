"""Command-line interface for parity-monitor."""

import argparse
import sys

from parity_monitor.pipeline import run
from parity_monitor.report import color_enabled, print_summary, write_report
from parity_monitor.schema import SchemaError


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parity-monitor",
        description="Compare a backtest replay log against a live trade log and report where they diverge.",
    )
    parser.add_argument("backtest_log", help="Path to the backtest replay log CSV")
    parser.add_argument("live_log", help="Path to the live trade log CSV")
    parser.add_argument(
        "--time-tolerance-fills", type=float, default=5.0,
        help="Seconds of timestamp tolerance for 'fill' events (default: 5)",
    )
    parser.add_argument(
        "--time-tolerance-signals", type=float, default=60.0,
        help="Seconds of timestamp tolerance for 'signal' events (default: 60)",
    )
    parser.add_argument(
        "--price-tolerance-pct", type=float, default=0.1,
        help="Percent price difference allowed before flagging price divergence (default: 0.1)",
    )
    parser.add_argument(
        "--size-tolerance-pct", type=float, default=1.0,
        help="Percent size difference allowed before flagging size divergence (default: 1.0)",
    )
    parser.add_argument(
        "--report", choices=["html", "md"], default=None,
        help="Also write a detailed report file in this format",
    )
    parser.add_argument(
        "--report-path", default=None,
        help="Path for the report file (default: parity_report.<format> in the current directory)",
    )
    parser.add_argument(
        "--worst-offenders", type=int, default=5,
        help="Number of worst-offending events to list in the summary (default: 5)",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored terminal output (also respects the NO_COLOR env var)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        results_df, summary = run(
            args.backtest_log,
            args.live_log,
            time_tolerance_fills_seconds=args.time_tolerance_fills,
            time_tolerance_signals_seconds=args.time_tolerance_signals,
            price_tolerance_pct=args.price_tolerance_pct,
            size_tolerance_pct=args.size_tolerance_pct,
            worst_offenders_n=args.worst_offenders,
        )
    except SchemaError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print_summary(summary, color=color_enabled(force_disable=args.no_color))

    if args.report:
        report_path = args.report_path or f"parity_report.{args.report}"
        try:
            write_report(results_df, summary, report_path, args.report)
        except OSError as e:
            sys.stdout.flush()
            print(f"error: could not write report to '{report_path}': {e}", file=sys.stderr)
            return 1
        print(f"\nDetailed report written to {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
