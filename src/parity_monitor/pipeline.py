"""End-to-end orchestration: load logs, match, classify, and summarize."""

import pandas as pd

from parity_monitor.classifier import classify_matches, combine_results
from parity_monitor.matcher import match_events
from parity_monitor.report import compute_summary
from parity_monitor.schema import load_log


def run(
    backtest_path: str,
    live_path: str,
    time_tolerance_fills_seconds: float = 5.0,
    time_tolerance_signals_seconds: float = 60.0,
    price_tolerance_pct: float = 0.1,
    size_tolerance_pct: float = 1.0,
    worst_offenders_n: int = 5,
) -> tuple[pd.DataFrame, dict]:
    backtest_df = load_log(backtest_path)
    live_df = load_log(live_path)

    time_tolerance_fills = pd.Timedelta(seconds=time_tolerance_fills_seconds)
    time_tolerance_signals = pd.Timedelta(seconds=time_tolerance_signals_seconds)

    match_result = match_events(backtest_df, live_df, time_tolerance_fills, time_tolerance_signals)
    classified = classify_matches(
        match_result.matched, time_tolerance_fills, time_tolerance_signals,
        price_tolerance_pct, size_tolerance_pct,
    )
    results_df = combine_results(classified, match_result.missing_in_live, match_result.extra_in_live)
    summary = compute_summary(results_df, worst_offenders_n=worst_offenders_n)
    return results_df, summary
