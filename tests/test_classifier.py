import pandas as pd

from parity_monitor.classifier import classify_matches, combine_results


def _matched_row(**overrides):
    row = {
        "symbol": "EURUSD",
        "event_type": "fill",
        "direction": "long",
        "signal_id": "sig-1",
        "bt_timestamp": pd.Timestamp("2026-07-06T09:00:00", tz="UTC"),
        "bt_price": 1.0850,
        "bt_size": 10000,
        "live_timestamp": pd.Timestamp("2026-07-06T09:00:02", tz="UTC"),
        "live_price": 1.0850,
        "live_size": 10000,
    }
    row.update(overrides)
    return row


def test_within_all_thresholds_is_matched():
    df = pd.DataFrame([_matched_row()])
    result = classify_matches(df, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60), 0.1, 1.0)
    assert result.iloc[0]["category"] == "matched"


def test_timing_gap_exceeds_tolerance():
    df = pd.DataFrame([_matched_row(
        live_timestamp=pd.Timestamp("2026-07-06T09:00:10", tz="UTC"),
    )])
    result = classify_matches(df, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60), 0.1, 1.0)
    assert result.iloc[0]["category"] == "timing_divergence"


def test_price_diff_exceeds_tolerance():
    df = pd.DataFrame([_matched_row(live_price=1.0870)])  # ~0.18% above bt_price
    result = classify_matches(df, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60), 0.1, 1.0)
    assert result.iloc[0]["category"] == "price_divergence"


def test_size_diff_exceeds_tolerance():
    df = pd.DataFrame([_matched_row(live_size=10500)])  # 5% above bt_size
    result = classify_matches(df, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60), 0.1, 1.0)
    assert result.iloc[0]["category"] == "size_divergence"


def test_timing_takes_priority_over_price():
    df = pd.DataFrame([_matched_row(
        live_timestamp=pd.Timestamp("2026-07-06T09:00:10", tz="UTC"),
        live_price=1.0870,
    )])
    result = classify_matches(df, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60), 0.1, 1.0)
    assert result.iloc[0]["category"] == "timing_divergence"


def test_combine_results_includes_missing_and_extra():
    classified = classify_matches(
        pd.DataFrame([_matched_row()]),
        pd.Timedelta(seconds=5), pd.Timedelta(seconds=60), 0.1, 1.0,
    )
    missing = pd.DataFrame([{
        "timestamp": pd.Timestamp("2026-07-06T09:05:00", tz="UTC"),
        "symbol": "EURUSD", "event_type": "signal", "direction": "short",
        "price": 1.0900, "size": 5000, "signal_id": "sig-2",
    }])
    extra = pd.DataFrame([{
        "timestamp": pd.Timestamp("2026-07-06T09:06:00", tz="UTC"),
        "symbol": "EURUSD", "event_type": "signal", "direction": "short",
        "price": 1.0905, "size": 5000, "signal_id": "sig-3",
    }])
    combined = combine_results(classified, missing, extra)
    assert set(combined["category"]) == {"matched", "missing_in_live", "extra_in_live"}
    assert len(combined) == 3
