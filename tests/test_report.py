import pandas as pd

from parity_monitor.report import compute_summary, print_summary


def _row(category, **overrides):
    row = {
        "symbol": "EURUSD", "event_type": "fill", "direction": "long", "signal_id": "sig-1",
        "bt_timestamp": pd.Timestamp("2026-07-06T09:00:00", tz="UTC"), "bt_price": 1.0850, "bt_size": 10000,
        "live_timestamp": pd.Timestamp("2026-07-06T09:00:02", tz="UTC"), "live_price": 1.0850, "live_size": 10000,
        "time_gap_seconds": 2.0, "price_diff_pct": 0.0, "size_diff_pct": 0.0,
        "category": category,
    }
    row.update(overrides)
    return row


def test_match_rate_excludes_extra_in_live():
    df = pd.DataFrame([
        _row("matched"),
        _row("matched"),
        _row("missing_in_live"),
        _row("extra_in_live"),
    ])
    summary = compute_summary(df)
    # comparable_total = 4 - 1 (extra) = 3; matched = 2 -> 66.7%
    assert round(summary["match_rate_pct"], 1) == 66.7
    assert summary["total_events"] == 4


def test_worst_offenders_prioritises_missing_in_live():
    df = pd.DataFrame([
        _row("matched"),
        _row("price_divergence", price_diff_pct=5.0),
        _row("missing_in_live"),
    ])
    summary = compute_summary(df, worst_offenders_n=2)
    worst = summary["worst_offenders"]
    assert len(worst) == 2
    assert worst.iloc[0]["category"] == "missing_in_live"


def test_worst_offenders_orders_by_magnitude_within_category():
    df = pd.DataFrame([
        _row("price_divergence", signal_id="small", price_diff_pct=0.5),
        _row("price_divergence", signal_id="big", price_diff_pct=5.0),
    ])
    summary = compute_summary(df, worst_offenders_n=2)
    worst = summary["worst_offenders"]
    assert worst.iloc[0]["signal_id"] == "big"


def test_print_summary_smoke(capsys):
    summary = compute_summary(pd.DataFrame([_row("matched")]))
    print_summary(summary)
    captured = capsys.readouterr()
    assert "Match rate" in captured.out
    assert "Total events compared" in captured.out


def test_match_rate_is_none_when_nothing_comparable(capsys):
    # Only extra_in_live rows: nothing from the backtest side to compare
    # against. 0.0% would misleadingly read as "total mismatch" instead of
    # "nothing to compare".
    df = pd.DataFrame([
        _row("extra_in_live"),
        _row("extra_in_live"),
    ])
    summary = compute_summary(df)
    assert summary["match_rate_pct"] is None

    print_summary(summary)
    captured = capsys.readouterr()
    assert "N/A" in captured.out
    assert "0.0%" not in captured.out


def test_worst_offenders_n_larger_than_available_returns_all():
    df = pd.DataFrame([
        _row("matched"),
        _row("price_divergence", price_diff_pct=5.0),
        _row("missing_in_live"),
    ])
    summary = compute_summary(df, worst_offenders_n=100)
    # only 2 non-matched rows exist, even though n=100 was requested
    assert len(summary["worst_offenders"]) == 2


def test_negative_worst_offenders_n_returns_zero_rows():
    df = pd.DataFrame([
        _row("price_divergence", price_diff_pct=5.0),
        _row("missing_in_live"),
    ])
    summary = compute_summary(df, worst_offenders_n=-1)
    assert len(summary["worst_offenders"]) == 0


def test_tie_order_preserves_combine_results_row_order():
    # Multiple missing_in_live rows all have magnitude 0.0 (no time/price/size
    # divergence value applies), so they tie within their severity tier.
    # sort_values on multiple columns dispatches to np.lexsort (stable), so
    # ties should preserve the original row order.
    df = pd.DataFrame([
        _row("missing_in_live", signal_id="third"),
        _row("missing_in_live", signal_id="first"),
        _row("missing_in_live", signal_id="second"),
    ])
    summary = compute_summary(df, worst_offenders_n=3)
    worst = summary["worst_offenders"]
    assert list(worst["signal_id"]) == ["third", "first", "second"]
