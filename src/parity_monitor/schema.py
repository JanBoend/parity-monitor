"""CSV log schema definition and loading/validation for parity-monitor."""

import pandas as pd

REQUIRED_COLUMNS = [
    "timestamp",
    "symbol",
    "event_type",
    "direction",
    "price",
    "size",
    "signal_id",
]

EVENT_TYPES = {"signal", "fill"}
DIRECTIONS = {"long", "short", "flat"}


class SchemaError(Exception):
    """Raised when a log file does not conform to the parity-monitor CSV schema."""


def load_log(path: str) -> pd.DataFrame:
    """Load and validate a backtest or live trade log CSV.

    Raises SchemaError if required columns are missing or values are invalid.
    """
    df = pd.read_csv(path, dtype=str)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise SchemaError(
            f"Log file '{path}' is missing required column(s): {', '.join(missing)}"
        )

    df = df[REQUIRED_COLUMNS].copy()

    bad_event_types = set(df["event_type"].unique()) - EVENT_TYPES
    if bad_event_types:
        raise SchemaError(
            f"Log file '{path}' has invalid event_type value(s): "
            f"{', '.join(sorted(bad_event_types))}. Must be one of: "
            f"{', '.join(sorted(EVENT_TYPES))}"
        )

    bad_directions = set(df["direction"].unique()) - DIRECTIONS
    if bad_directions:
        raise SchemaError(
            f"Log file '{path}' has invalid direction value(s): "
            f"{', '.join(sorted(bad_directions))}. Must be one of: "
            f"{', '.join(sorted(DIRECTIONS))}"
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")
    df["price"] = df["price"].astype(float)
    df["size"] = df["size"].astype(float)
    df["signal_id"] = df["signal_id"].replace("", pd.NA)

    df = df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    return df
