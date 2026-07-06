"""Event matching between backtest and live logs."""

from dataclasses import dataclass

import pandas as pd

MATCHED_COLUMNS = [
    "symbol", "event_type", "direction", "signal_id",
    "bt_timestamp", "bt_price", "bt_size",
    "live_timestamp", "live_price", "live_size",
]


@dataclass
class MatchResult:
    matched: pd.DataFrame          # one row per matched pair, MATCHED_COLUMNS
    missing_in_live: pd.DataFrame  # backtest rows with no live counterpart
    extra_in_live: pd.DataFrame    # live rows with no backtest counterpart


def match_events(
    backtest_df: pd.DataFrame,
    live_df: pd.DataFrame,
    time_tolerance_fills: pd.Timedelta,
    time_tolerance_signals: pd.Timedelta,
) -> MatchResult:
    """Match backtest events to live events.

    Deliberately a simple O(n*m) nested-loop nearest-neighbor search rather
    than a vectorized join — realistic log sizes are hundreds to low
    thousands of rows, so this is fast enough and much easier to reason
    about correctly than a vectorized alternative.
    """
    bt = backtest_df.reset_index(drop=True)
    live = live_df.reset_index(drop=True)
    bt_matched = [False] * len(bt)
    live_matched = [False] * len(live)
    matched_rows = []

    def tolerance_for(event_type: str) -> pd.Timedelta:
        return time_tolerance_fills if event_type == "fill" else time_tolerance_signals

    # Pass 1: exact match by signal_id (when present on both sides).
    for i, bt_row in bt.iterrows():
        if pd.isna(bt_row["signal_id"]):
            continue
        for j, live_row in live.iterrows():
            if live_matched[j] or pd.isna(live_row["signal_id"]):
                continue
            if (
                bt_row["signal_id"] == live_row["signal_id"]
                and bt_row["symbol"] == live_row["symbol"]
                and bt_row["event_type"] == live_row["event_type"]
                and bt_row["direction"] == live_row["direction"]
            ):
                matched_rows.append(_pair_row(bt_row, live_row))
                bt_matched[i] = True
                live_matched[j] = True
                break

    # Pass 2: nearest-timestamp match within tolerance for everything left.
    for i, bt_row in bt.iterrows():
        if bt_matched[i]:
            continue
        best_j = None
        best_gap = None
        for j, live_row in live.iterrows():
            if live_matched[j]:
                continue
            if (
                bt_row["symbol"] != live_row["symbol"]
                or bt_row["event_type"] != live_row["event_type"]
                or bt_row["direction"] != live_row["direction"]
            ):
                continue
            gap = abs(bt_row["timestamp"] - live_row["timestamp"])
            if gap <= tolerance_for(bt_row["event_type"]) and (best_gap is None or gap < best_gap):
                best_gap = gap
                best_j = j
        if best_j is not None:
            matched_rows.append(_pair_row(bt_row, live.loc[best_j]))
            bt_matched[i] = True
            live_matched[best_j] = True

    matched_df = pd.DataFrame(matched_rows) if matched_rows else _empty_matched_frame()
    missing_in_live = bt[~pd.Series(bt_matched)].reset_index(drop=True)
    extra_in_live = live[~pd.Series(live_matched)].reset_index(drop=True)
    return MatchResult(matched=matched_df, missing_in_live=missing_in_live, extra_in_live=extra_in_live)


def _pair_row(bt_row: pd.Series, live_row: pd.Series) -> dict:
    return {
        "symbol": bt_row["symbol"],
        "event_type": bt_row["event_type"],
        "direction": bt_row["direction"],
        "signal_id": bt_row["signal_id"],
        "bt_timestamp": bt_row["timestamp"],
        "bt_price": bt_row["price"],
        "bt_size": bt_row["size"],
        "live_timestamp": live_row["timestamp"],
        "live_price": live_row["price"],
        "live_size": live_row["size"],
    }


def _empty_matched_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=MATCHED_COLUMNS)
