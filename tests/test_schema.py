import pandas as pd
import pytest

from parity_monitor.schema import load_log, SchemaError, REQUIRED_COLUMNS


def _write_csv(tmp_path, rows):
    path = tmp_path / "log.csv"
    header = "timestamp,symbol,event_type,direction,price,size,signal_id"
    path.write_text("\n".join([header, *rows]) + "\n")
    return path


def test_load_valid_log(tmp_path):
    path = _write_csv(tmp_path, [
        "2026-07-06T09:00:00Z,EURUSD,signal,long,1.0850,10000,sig-1",
        "2026-07-06T09:00:05Z,EURUSD,fill,long,1.0851,10000,sig-1",
    ])
    df = load_log(str(path))
    assert list(df.columns) == REQUIRED_COLUMNS
    assert len(df) == 2
    assert str(df["timestamp"].dtype).startswith("datetime64")


def test_signal_id_blank_is_allowed(tmp_path):
    path = _write_csv(tmp_path, [
        "2026-07-06T09:00:00Z,EURUSD,signal,long,1.0850,10000,",
    ])
    df = load_log(str(path))
    assert pd.isna(df.loc[0, "signal_id"])


def test_load_missing_column_raises(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text(
        "timestamp,symbol,event_type,direction,price,size\n"
        "2026-07-06T09:00:00Z,EURUSD,signal,long,1.0850,10000\n"
    )
    with pytest.raises(SchemaError, match="signal_id"):
        load_log(str(path))


def test_load_invalid_event_type_raises(tmp_path):
    path = _write_csv(tmp_path, [
        "2026-07-06T09:00:00Z,EURUSD,bogus,long,1.0850,10000,sig-1",
    ])
    with pytest.raises(SchemaError, match="event_type"):
        load_log(str(path))


def test_load_invalid_direction_raises(tmp_path):
    path = _write_csv(tmp_path, [
        "2026-07-06T09:00:00Z,EURUSD,signal,sideways,1.0850,10000,sig-1",
    ])
    with pytest.raises(SchemaError, match="direction"):
        load_log(str(path))
