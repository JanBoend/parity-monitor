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
