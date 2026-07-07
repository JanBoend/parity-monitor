# Contributing to parity-monitor

Thanks for your interest in improving parity-monitor. It's a small, focused tool
and contributions are welcome.

## Development setup

```
git clone https://github.com/JanBoend/parity-monitor.git
cd parity-monitor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running the tests

```
pytest
```

Every change should keep the suite green, and new behavior needs new tests. The
CI workflow runs the full suite on Python 3.10–3.13 for every pull request.

## The log schema

Both the backtest and live logs are CSV with these columns:

| column | type | required |
|---|---|---|
| timestamp | ISO 8601 UTC | yes |
| symbol | string | yes |
| event_type | `signal` or `fill` | yes |
| direction | `long`, `short`, or `flat` | yes |
| price | float | yes |
| size | float | yes |
| signal_id | string | no |

## Regenerating the demo GIF

The README demo is produced with [vhs](https://github.com/charmbracelet/vhs):

```
vhs demo.tape
```

## Pull requests

Keep changes focused, include tests, and make sure `pytest` passes before opening
a PR.
