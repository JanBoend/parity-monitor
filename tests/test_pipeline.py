from parity_monitor.pipeline import run


def _write(path, rows):
    header = "timestamp,symbol,event_type,direction,price,size,signal_id"
    path.write_text("\n".join([header, *rows]) + "\n")


def test_run_end_to_end(tmp_path):
    bt_path = tmp_path / "backtest.csv"
    live_path = tmp_path / "live.csv"
    _write(bt_path, [
        "2026-07-06T09:00:00Z,EURUSD,fill,long,1.0850,10000,sig-1",
        "2026-07-06T09:05:00Z,EURUSD,fill,short,1.0900,5000,sig-2",
        "2026-07-06T09:10:00Z,EURUSD,fill,long,1.0800,8000,sig-3",
    ])
    _write(live_path, [
        "2026-07-06T09:00:02Z,EURUSD,fill,long,1.0850,10000,sig-1",   # matched
        "2026-07-06T09:05:00Z,EURUSD,fill,short,1.0950,5000,sig-2",  # price divergence
        # sig-3 never executed live -> missing_in_live
        "2026-07-06T09:20:00Z,EURUSD,fill,long,1.0700,3000,sig-4",   # extra_in_live
    ])

    results_df, summary = run(str(bt_path), str(live_path))

    categories = sorted(results_df["category"].tolist())
    assert categories == ["extra_in_live", "matched", "missing_in_live", "price_divergence"]
    assert summary["total_events"] == 4

    # Row-level checks: verify the SPECIFIC known backtest-only/live-only rows
    # land in the correct category (not just that both category names appear
    # somewhere in the output). This catches a missing_in_live/extra_in_live
    # argument swap in the combine_results call, which the set-based
    # assertion above cannot detect when there's exactly one row per category.
    by_signal = results_df.set_index("signal_id")
    assert by_signal.loc["sig-3", "category"] == "missing_in_live"
    assert by_signal.loc["sig-3", "bt_price"] == 1.0800
    assert by_signal.loc["sig-4", "category"] == "extra_in_live"
    assert by_signal.loc["sig-4", "live_price"] == 1.0700


def test_run_uses_consistent_tolerance_between_match_and_classify(tmp_path):
    # sig-1 fills are 20 seconds apart: this must fail to match at the
    # default 5.0s time_tolerance_fills, but succeed and classify as
    # "matched" (not "timing_divergence") when a 30.0s tolerance is passed
    # through. This guards the single most safety-critical invariant in the
    # pipeline: match_events and classify_matches must receive the SAME
    # Timedelta, not independently-derived/stale values.
    bt_path = tmp_path / "backtest.csv"
    live_path = tmp_path / "live.csv"
    _write(bt_path, [
        "2026-07-06T09:00:00Z,EURUSD,fill,long,1.0850,10000,sig-1",
    ])
    _write(live_path, [
        "2026-07-06T09:00:20Z,EURUSD,fill,long,1.0850,10000,sig-1",
    ])

    results_df, summary = run(str(bt_path), str(live_path), time_tolerance_fills_seconds=30.0)

    assert len(results_df) == 1
    assert results_df.loc[0, "category"] == "matched"
    assert summary["total_events"] == 1
