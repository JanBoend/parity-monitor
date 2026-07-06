"""Divergence classification for matched backtest/live event pairs."""

import pandas as pd

RESULT_COLUMNS = [
    "symbol", "event_type", "direction", "signal_id",
    "bt_timestamp", "bt_price", "bt_size",
    "live_timestamp", "live_price", "live_size",
    "time_gap_seconds", "price_diff_pct", "size_diff_pct",
    "category",
]


def classify_matches(
    matched_df: pd.DataFrame,
    time_tolerance_fills: pd.Timedelta,
    time_tolerance_signals: pd.Timedelta,
    price_tolerance_pct: float,
    size_tolerance_pct: float,
) -> pd.DataFrame:
    """Classify each matched backtest/live pair as matched or one of the
    divergence categories. Priority when multiple thresholds are exceeded:
    timing > price > size.
    """
    if matched_df.empty:
        return matched_df.assign(
            time_gap_seconds=pd.Series(dtype=float),
            price_diff_pct=pd.Series(dtype=float),
            size_diff_pct=pd.Series(dtype=float),
            category=pd.Series(dtype=str),
        )

    df = matched_df.copy()
    df["time_gap_seconds"] = (df["live_timestamp"] - df["bt_timestamp"]).abs().dt.total_seconds()
    df["price_diff_pct"] = df.apply(_price_diff_pct, axis=1)
    df["size_diff_pct"] = df.apply(_size_diff_pct, axis=1)

    def category_for(row) -> str:
        tolerance = time_tolerance_fills if row["event_type"] == "fill" else time_tolerance_signals
        if row["time_gap_seconds"] > tolerance.total_seconds():
            return "timing_divergence"
        if abs(row["price_diff_pct"]) > price_tolerance_pct:
            return "price_divergence"
        if abs(row["size_diff_pct"]) > size_tolerance_pct:
            return "size_divergence"
        return "matched"

    df["category"] = df.apply(category_for, axis=1)
    return df


def _price_diff_pct(row) -> float:
    if row["bt_price"] == 0:
        return 0.0 if row["live_price"] == 0 else float("inf")
    return (row["live_price"] - row["bt_price"]) / row["bt_price"] * 100


def _size_diff_pct(row) -> float:
    if row["bt_size"] == 0:
        return 0.0 if row["live_size"] == 0 else float("inf")
    return (row["live_size"] - row["bt_size"]) / row["bt_size"] * 100


def combine_results(
    classified_df: pd.DataFrame,
    missing_in_live: pd.DataFrame,
    extra_in_live: pd.DataFrame,
) -> pd.DataFrame:
    """Merge classified matches with unmatched backtest/live events into one
    results table with a consistent set of columns (RESULT_COLUMNS)."""
    missing = missing_in_live.rename(columns={
        "timestamp": "bt_timestamp", "price": "bt_price", "size": "bt_size",
    }).assign(
        live_timestamp=pd.NaT, live_price=float("nan"), live_size=float("nan"),
        time_gap_seconds=float("nan"), price_diff_pct=float("nan"), size_diff_pct=float("nan"),
        category="missing_in_live",
    )
    extra = extra_in_live.rename(columns={
        "timestamp": "live_timestamp", "price": "live_price", "size": "live_size",
    }).assign(
        bt_timestamp=pd.NaT, bt_price=float("nan"), bt_size=float("nan"),
        time_gap_seconds=float("nan"), price_diff_pct=float("nan"), size_diff_pct=float("nan"),
        category="extra_in_live",
    )
    combined = pd.concat([classified_df, missing, extra], ignore_index=True)
    return combined[RESULT_COLUMNS]
