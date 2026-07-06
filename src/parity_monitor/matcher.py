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

    # Pre-extract to plain Python tuples via itertuples() so the O(n*m) scan
    # below doesn't pay pandas' per-access Series-boxing cost on every cell.
    bt_records = list(bt.itertuples(index=True))
    live_records = list(live.itertuples(index=True))

    def tolerance_for(event_type: str) -> pd.Timedelta:
        return time_tolerance_fills if event_type == "fill" else time_tolerance_signals

    # Pass 1: exact match by signal_id (when present on both sides).
    for bt_rec in bt_records:
        i = bt_rec.Index
        if pd.isna(bt_rec.signal_id):
            continue
        for live_rec in live_records:
            j = live_rec.Index
            if live_matched[j] or pd.isna(live_rec.signal_id):
                continue
            if (
                bt_rec.signal_id == live_rec.signal_id
                and bt_rec.symbol == live_rec.symbol
                and bt_rec.event_type == live_rec.event_type
                and bt_rec.direction == live_rec.direction
            ):
                matched_rows.append(_pair_row(bt_rec, live_rec))
                bt_matched[i] = True
                live_matched[j] = True
                break

    # Pass 2: nearest-timestamp match within tolerance for everything left.
    # Collect ALL valid (gap, bt_i, live_j) candidates first, then claim them
    # globally in ascending-gap order. This guarantees a genuinely nearest
    # match rather than whichever bt row happens to be iterated first — a
    # bt row processed later in DataFrame order can still "win" a live row
    # away from an earlier bt row if its gap is smaller.
    candidates = []
    for bt_rec in bt_records:
        i = bt_rec.Index
        if bt_matched[i]:
            continue
        for live_rec in live_records:
            j = live_rec.Index
            if live_matched[j]:
                continue
            if (
                bt_rec.symbol != live_rec.symbol
                or bt_rec.event_type != live_rec.event_type
                or bt_rec.direction != live_rec.direction
            ):
                continue
            gap = abs(bt_rec.timestamp - live_rec.timestamp)
            if gap <= tolerance_for(bt_rec.event_type):
                candidates.append((gap, i, j))

    for gap, i, j in sorted(candidates, key=lambda c: c[0]):
        if bt_matched[i] or live_matched[j]:
            continue
        matched_rows.append(_pair_row(bt_records[i], live_records[j]))
        bt_matched[i] = True
        live_matched[j] = True

    matched_df = pd.DataFrame(matched_rows) if matched_rows else _empty_matched_frame()
    missing_in_live = bt[~pd.Series(bt_matched)].reset_index(drop=True)
    extra_in_live = live[~pd.Series(live_matched)].reset_index(drop=True)
    return MatchResult(matched=matched_df, missing_in_live=missing_in_live, extra_in_live=extra_in_live)


def _pair_row(bt_row, live_row) -> dict:
    return {
        "symbol": bt_row.symbol,
        "event_type": bt_row.event_type,
        "direction": bt_row.direction,
        "signal_id": bt_row.signal_id,
        "bt_timestamp": bt_row.timestamp,
        "bt_price": bt_row.price,
        "bt_size": bt_row.size,
        "live_timestamp": live_row.timestamp,
        "live_price": live_row.price,
        "live_size": live_row.size,
    }


def _empty_matched_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=MATCHED_COLUMNS)
