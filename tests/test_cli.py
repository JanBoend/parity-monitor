from parity_monitor.cli import main


def _write(path, rows):
    header = "timestamp,symbol,event_type,direction,price,size,signal_id"
    path.write_text("\n".join([header, *rows]) + "\n")


def test_cli_runs_and_prints_summary(tmp_path, capsys):
    bt_path = tmp_path / "backtest.csv"
    live_path = tmp_path / "live.csv"
    _write(bt_path, ["2026-07-06T09:00:00Z,EURUSD,fill,long,1.0850,10000,sig-1"])
    _write(live_path, ["2026-07-06T09:00:02Z,EURUSD,fill,long,1.0850,10000,sig-1"])

    exit_code = main([str(bt_path), str(live_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Match rate" in captured.out


def test_cli_writes_report_file(tmp_path):
    bt_path = tmp_path / "backtest.csv"
    live_path = tmp_path / "live.csv"
    report_path = tmp_path / "out.md"
    _write(bt_path, ["2026-07-06T09:00:00Z,EURUSD,fill,long,1.0850,10000,sig-1"])
    _write(live_path, ["2026-07-06T09:00:02Z,EURUSD,fill,long,1.0850,10000,sig-1"])

    exit_code = main([
        str(bt_path), str(live_path),
        "--report", "md", "--report-path", str(report_path),
    ])

    assert exit_code == 0
    assert report_path.exists()


def test_cli_invalid_schema_returns_error_exit_code(tmp_path, capsys):
    bt_path = tmp_path / "backtest.csv"
    live_path = tmp_path / "live.csv"
    bt_path.write_text("not,a,valid,schema\n1,2,3,4\n")
    _write(live_path, ["2026-07-06T09:00:02Z,EURUSD,fill,long,1.0850,10000,sig-1"])

    exit_code = main([str(bt_path), str(live_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error:" in captured.err
