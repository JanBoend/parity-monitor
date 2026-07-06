import pandas as pd

from parity_monitor.matcher import match_events


def _row(ts, symbol="EURUSD", event_type="fill", direction="long",
         price=1.0850, size=10000, signal_id=pd.NA):
    return {
        "timestamp": pd.Timestamp(ts, tz="UTC"),
        "symbol": symbol,
        "event_type": event_type,
        "direction": direction,
        "price": price,
        "size": size,
        "signal_id": signal_id,
    }


def test_exact_match_by_signal_id():
    bt = pd.DataFrame([_row("2026-07-06T09:00:00", signal_id="sig-1")])
    live = pd.DataFrame([_row("2026-07-06T09:00:04", signal_id="sig-1")])

    result = match_events(bt, live, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60))

    assert len(result.matched) == 1
    assert result.matched.iloc[0]["signal_id"] == "sig-1"
    assert result.missing_in_live.empty
    assert result.extra_in_live.empty


def test_nearest_timestamp_match_within_tolerance():
    bt = pd.DataFrame([_row("2026-07-06T09:00:00")])
    live = pd.DataFrame([_row("2026-07-06T09:00:03")])

    result = match_events(bt, live, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60))

    assert len(result.matched) == 1
    assert result.missing_in_live.empty
    assert result.extra_in_live.empty


def test_outside_tolerance_becomes_missing_and_extra():
    bt = pd.DataFrame([_row("2026-07-06T09:00:00")])
    live = pd.DataFrame([_row("2026-07-06T09:00:10")])

    result = match_events(bt, live, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60))

    assert result.matched.empty
    assert len(result.missing_in_live) == 1
    assert len(result.extra_in_live) == 1


def test_different_symbol_never_matches():
    bt = pd.DataFrame([_row("2026-07-06T09:00:00", symbol="EURUSD")])
    live = pd.DataFrame([_row("2026-07-06T09:00:01", symbol="GBPUSD")])

    result = match_events(bt, live, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60))

    assert result.matched.empty
    assert len(result.missing_in_live) == 1
    assert len(result.extra_in_live) == 1
