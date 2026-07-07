# parity-monitor

Does your live trading bot actually do what your backtest says it does?

I found out the hard way that mine didn't — a live signal-matching bug meant my
live bot's trades didn't match its validated backtest. `parity-monitor` is the
tool I built to catch that class of bug automatically: point it at a backtest
replay log and a live trade log, and it tells you exactly where they diverge
and why (timing lag, slippage, a missing signal, a sizing mismatch).

Runs entirely on your own machine, self-hosted. Your logs never leave it.

## Install

```
pip install parity-monitor
```

Requires Python 3.10+.

## Quick start

Clone the repo to try the bundled example logs:

```
git clone https://github.com/<your-username>/parity-monitor.git
cd parity-monitor
parity-monitor examples/backtest.csv examples/live.csv
```

Or point it at your own backtest/live CSV logs (see Log format below):

```
parity-monitor your_backtest.csv your_live.csv
```

## Log format

Both files are CSV with this schema:

| column | type | required | notes |
|---|---|---|---|
| timestamp | ISO 8601 UTC | yes | |
| symbol | string | yes | |
| event_type | `signal` or `fill` | yes | |
| direction | `long`, `short`, or `flat` | yes | |
| price | float | yes | |
| size | float | yes | |
| signal_id | string | no | improves matching accuracy when present |

## Options

```
--time-tolerance-fills SECONDS     default 5
--time-tolerance-signals SECONDS   default 60
--price-tolerance-pct PCT          default 0.1
--size-tolerance-pct PCT           default 1.0
--report {html,md}                 write a detailed report file
--report-path PATH                 report file location
--worst-offenders N                default 5
```

## How matching works

Events are matched first by `signal_id` (when present on both sides), then by
nearest timestamp within the configured tolerance for anything left. Matched
pairs are then classified — in priority order timing > price > size — into
`matched`, `timing_divergence`, `price_divergence`, or `size_divergence`.
Backtest events with no live counterpart are `missing_in_live` (the
highest-severity category — it usually means a live logic bug or a failed
execution). Live events with no backtest counterpart are `extra_in_live`.

## License

MIT. See [LICENSE](LICENSE) for details.
