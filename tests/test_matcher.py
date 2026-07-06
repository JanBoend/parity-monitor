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


def test_nearest_match_is_globally_greedy_not_order_dependent():
    # One live row is within tolerance of two bt rows, at different distances
    # (gap=4s and gap=1s, tolerance=5s). The bt row with the larger gap (4s)
    # is listed FIRST in DataFrame order. A naive row-order-greedy pass 2
    # would let the first-iterated bt row (gap=4s) claim the only live row,
    # leaving the objectively nearer bt row (gap=1s) stuck in missing_in_live.
    # The correct, order-independent behavior is: the nearer bt row (gap=1s)
    # wins the match, and the farther one (gap=4s) is left unmatched.
    bt = pd.DataFrame([
        _row("2026-07-06T09:00:04"),  # gap to live = 4s, appears first
        _row("2026-07-06T09:00:01"),  # gap to live = 1s, appears second
    ])
    live = pd.DataFrame([_row("2026-07-06T09:00:00")])

    result = match_events(bt, live, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60))

    assert len(result.matched) == 1
    matched_bt_ts = result.matched.iloc[0]["bt_timestamp"]
    assert matched_bt_ts == pd.Timestamp("2026-07-06T09:00:01", tz="UTC")

    assert len(result.missing_in_live) == 1
    assert result.missing_in_live.iloc[0]["timestamp"] == pd.Timestamp("2026-07-06T09:00:04", tz="UTC")

    assert result.extra_in_live.empty


def test_exact_tolerance_boundary_matches():
    # gap == tolerance exactly must be treated as within tolerance (inclusive).
    bt = pd.DataFrame([_row("2026-07-06T09:00:00")])
    live = pd.DataFrame([_row("2026-07-06T09:00:05")])

    result = match_events(bt, live, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60))

    assert len(result.matched) == 1
    assert result.missing_in_live.empty
    assert result.extra_in_live.empty


def test_duplicate_signal_id_on_backtest_side_matches_deterministically():
    # Two bt rows share the same signal_id; only one live row carries that
    # signal_id. Chosen behavior: the first bt row (in DataFrame order) that
    # finds the live row claims it via the exact signal_id match in pass 1;
    # the other bt row has no live signal_id left to match, so it falls
    # through to pass 2 nearest-timestamp matching. Since no other live rows
    # exist, it ends up unmatched (missing_in_live). This is deterministic
    # and doesn't silently double-count a single live fill against two
    # different backtest rows.
    bt = pd.DataFrame([
        _row("2026-07-06T09:00:00", signal_id="sig-dup"),
        _row("2026-07-06T09:05:00", signal_id="sig-dup"),
    ])
    live = pd.DataFrame([_row("2026-07-06T09:00:02", signal_id="sig-dup")])

    result = match_events(bt, live, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60))

    assert len(result.matched) == 1
    assert result.matched.iloc[0]["bt_timestamp"] == pd.Timestamp("2026-07-06T09:00:00", tz="UTC")
    assert len(result.missing_in_live) == 1
    assert result.missing_in_live.iloc[0]["timestamp"] == pd.Timestamp("2026-07-06T09:05:00", tz="UTC")
    assert result.extra_in_live.empty


def test_signal_id_present_on_backtest_only_falls_through_to_nearest_match():
    # bt row has a signal_id but no live row has any signal_id at all
    # (e.g. live log doesn't populate signal_id yet). Pass 1 can't match
    # since the live side has no signal_id to compare against, so it must
    # fall through cleanly to pass 2 nearest-timestamp matching rather than
    # erroring or silently failing to match.
    bt = pd.DataFrame([_row("2026-07-06T09:00:00", signal_id="sig-1")])
    live = pd.DataFrame([_row("2026-07-06T09:00:02", signal_id=pd.NA)])

    result = match_events(bt, live, pd.Timedelta(seconds=5), pd.Timedelta(seconds=60))

    assert len(result.matched) == 1
    assert result.matched.iloc[0]["signal_id"] == "sig-1"
    assert result.missing_in_live.empty
    assert result.extra_in_live.empty
