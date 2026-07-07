import sys
from unittest.mock import patch

import pytest

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


def test_cli_report_write_failure_returns_error_exit_code(tmp_path, capsys):
    bt_path = tmp_path / "backtest.csv"
    live_path = tmp_path / "live.csv"
    bad_report_path = tmp_path / "no_such_dir" / "out.md"
    _write(bt_path, ["2026-07-06T09:00:00Z,EURUSD,fill,long,1.0850,10000,sig-1"])
    _write(live_path, ["2026-07-06T09:00:02Z,EURUSD,fill,long,1.0850,10000,sig-1"])

    exit_code = main([
        str(bt_path), str(live_path),
        "--report", "md", "--report-path", str(bad_report_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error:" in captured.err
    assert "Traceback" not in captured.err
    assert "Match rate" in captured.out


def test_cli_report_write_failure_flushes_stdout_before_stderr_error(tmp_path, capsys):
    # capsys captures stdout/stderr as independent streams, so it can't
    # directly observe interleaving under a merged/redirected stream (e.g.
    # `cmd > combined.txt 2>&1`). Instead, assert the concrete mechanism that
    # fixes that ordering bug -- sys.stdout.flush() -- is actually called
    # before the stderr error is printed, and that the summary content made
    # it into stdout regardless.
    bt_path = tmp_path / "backtest.csv"
    live_path = tmp_path / "live.csv"
    bad_report_path = tmp_path / "no_such_dir" / "out.md"
    _write(bt_path, ["2026-07-06T09:00:00Z,EURUSD,fill,long,1.0850,10000,sig-1"])
    _write(live_path, ["2026-07-06T09:00:02Z,EURUSD,fill,long,1.0850,10000,sig-1"])

    with patch.object(sys.stdout, "flush", wraps=sys.stdout.flush) as mock_flush:
        exit_code = main([
            str(bt_path), str(live_path),
            "--report", "md", "--report-path", str(bad_report_path),
        ])

    assert exit_code == 1
    assert mock_flush.called
    captured = capsys.readouterr()
    assert "Match rate" in captured.out
    assert "error:" in captured.err


def test_cli_no_arguments_exits_with_code_2():
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 2


def test_cli_invalid_report_choice_exits_with_code_2(tmp_path):
    bt_path = tmp_path / "backtest.csv"
    live_path = tmp_path / "live.csv"
    _write(bt_path, ["2026-07-06T09:00:00Z,EURUSD,fill,long,1.0850,10000,sig-1"])
    _write(live_path, ["2026-07-06T09:00:02Z,EURUSD,fill,long,1.0850,10000,sig-1"])

    with pytest.raises(SystemExit) as exc_info:
        main([str(bt_path), str(live_path), "--report", "txt"])

    assert exc_info.value.code == 2


def test_cli_help_smoke(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "backtest_log" in captured.out
    assert "live_log" in captured.out
