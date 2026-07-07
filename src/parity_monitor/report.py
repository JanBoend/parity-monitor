"""Summary computation and terminal/report output for parity-monitor results."""

import os
import sys

import pandas as pd

_ANSI = {
    "green": "\033[32m",
    "red": "\033[91m",       # bright red — highest-severity category
    "magenta": "\033[35m",
    "yellow": "\033[33m",
}
_BOLD = "\033[1m"
_RESET = "\033[0m"

_CATEGORY_COLOR = {
    "matched": "green",
    "missing_in_live": "red",
    "extra_in_live": "magenta",
    "timing_divergence": "yellow",
    "price_divergence": "yellow",
    "size_divergence": "yellow",
}


def color_enabled(stream=None, force_disable: bool = False) -> bool:
    """Decide whether to emit ANSI color: only to a real TTY, never when
    NO_COLOR is set, never when force_disable (the --no-color flag) is set."""
    if force_disable:
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    stream = stream if stream is not None else sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


def _colorize(text: str, color: str, enabled: bool, *, bold: bool = False) -> str:
    """Wrap text in ANSI codes when enabled; return it untouched otherwise."""
    if not enabled:
        return text
    prefix = ""
    if bold:
        prefix += _BOLD
    if color in _ANSI:
        prefix += _ANSI[color]
    if not prefix:
        return text
    return f"{prefix}{text}{_RESET}"


CATEGORY_SEVERITY = {
    "missing_in_live": 0,
    "timing_divergence": 1,
    "price_divergence": 2,
    "size_divergence": 3,
    "extra_in_live": 4,
    "matched": 5,
}


def compute_summary(results_df: pd.DataFrame, worst_offenders_n: int = 5) -> dict:
    total = len(results_df)
    if total == 0:
        counts: dict = {}
    else:
        counts = results_df["category"].value_counts().to_dict()
    matched = counts.get("matched", 0)
    extra = counts.get("extra_in_live", 0)
    comparable_total = total - extra
    # None (not 0.0) when there's nothing comparable — 0.0 would misleadingly
    # read as "everything failed to match" rather than "nothing to compare".
    match_rate_pct = (matched / comparable_total * 100) if comparable_total > 0 else None

    non_matched = results_df[results_df["category"] != "matched"].copy()
    non_matched["_severity_rank"] = non_matched["category"].map(CATEGORY_SEVERITY)
    non_matched["_magnitude"] = non_matched.apply(_magnitude, axis=1)
    n = max(worst_offenders_n, 0)
    # Multi-column sort_values dispatches to np.lexsort, which is stable, so
    # ties (e.g. multiple missing_in_live rows, all at magnitude 0.0) preserve
    # combine_results' original row order deterministically.
    worst = non_matched.sort_values(
        ["_severity_rank", "_magnitude"], ascending=[True, False]
    ).head(n)

    return {
        "total_events": total,
        "match_rate_pct": match_rate_pct,
        "category_counts": counts,
        "worst_offenders": worst.drop(columns=["_severity_rank", "_magnitude"]),
    }


def _magnitude(row) -> float:
    if row["category"] == "timing_divergence":
        return abs(row["time_gap_seconds"]) if pd.notna(row["time_gap_seconds"]) else 0.0
    if row["category"] == "price_divergence":
        return abs(row["price_diff_pct"]) if pd.notna(row["price_diff_pct"]) else 0.0
    if row["category"] == "size_divergence":
        return abs(row["size_diff_pct"]) if pd.notna(row["size_diff_pct"]) else 0.0
    return 0.0


def print_summary(summary: dict, color: bool = False) -> None:
    print(f"Total events compared: {summary['total_events']}")
    rate = summary["match_rate_pct"]
    if rate is None:
        print("Match rate: N/A (no comparable events)")
    else:
        shown = round(rate, 1)  # color the displayed (rounded) value so color and number never disagree
        if shown >= 100.0:
            rate_color = "green"
        elif shown <= 0.0:
            rate_color = "red"
        else:
            rate_color = "yellow"
        print(_colorize(f"Match rate: {shown:.1f}%", rate_color, color, bold=True))
    print()
    print("Breakdown by category:")
    for category, count in sorted(summary["category_counts"].items()):
        label = _colorize(category, _CATEGORY_COLOR.get(category, ""), color)
        print(f"  {label}: {count}")
    print()
    if not summary["worst_offenders"].empty:
        print(f"Top {len(summary['worst_offenders'])} worst offenders:")
        for _, row in summary["worst_offenders"].iterrows():
            print(f"  {_format_offender(row, color)}")


def _format_offender(row, color: bool = False) -> str:
    category = row["category"]
    tag = _colorize(f"[{category}]", _CATEGORY_COLOR.get(category, ""), color)
    prefix = f"{tag} {row['symbol']} signal_id={row['signal_id']}"
    if category == "missing_in_live":
        return f"{prefix} bt_timestamp={row['bt_timestamp']} bt_price={row['bt_price']}"
    if category == "extra_in_live":
        return f"{prefix} live_timestamp={row['live_timestamp']} live_price={row['live_price']}"
    if category == "timing_divergence":
        return f"{prefix} bt_timestamp={row['bt_timestamp']} time_gap_seconds={row['time_gap_seconds']}"
    if category == "price_divergence":
        return f"{prefix} bt_timestamp={row['bt_timestamp']} price_diff_pct={row['price_diff_pct']}"
    if category == "size_divergence":
        return f"{prefix} bt_timestamp={row['bt_timestamp']} size_diff_pct={row['size_diff_pct']}"
    return prefix


def write_report(results_df: pd.DataFrame, summary: dict, path: str, fmt: str) -> None:
    """Render results_df/summary as an HTML or Markdown report and write it to path.

    Overwrites path if it already exists. The parent directory must already
    exist — this raises FileNotFoundError otherwise (it does not create
    intermediate directories).
    """
    if fmt not in ("html", "md"):
        raise ValueError(f"Unsupported report format: {fmt}. Must be 'html' or 'md'.")
    content = _render_markdown(results_df, summary) if fmt == "md" else _render_html(results_df, summary)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _render_markdown(results_df: pd.DataFrame, summary: dict) -> str:
    match_rate = (
        "N/A (no comparable events)"
        if summary["match_rate_pct"] is None
        else f"{summary['match_rate_pct']:.1f}%"
    )
    lines = [
        "# Parity Monitor Report",
        "",
        f"Total events compared: {summary['total_events']}",
        f"Match rate: {match_rate}",
        "",
        "## Category breakdown",
        "",
    ]
    for category, count in sorted(summary["category_counts"].items()):
        lines.append(f"- **{category}**: {count}")
    lines.append("")
    lines.append("## All events")
    lines.append("")
    # Note: unlike _render_html (which uses to_html's escape=True default),
    # to_markdown does NOT escape special characters — a value containing
    # "<script>" passes through raw into the .md output. Accepted as a known
    # limitation: this is a local CLI tool rendering the user's own trading
    # data, not a web-facing renderer of untrusted third-party input.
    lines.append(results_df.to_markdown(index=False))
    lines.append("")
    return "\n".join(lines)


def _render_html(results_df: pd.DataFrame, summary: dict) -> str:
    match_rate = (
        "N/A (no comparable events)"
        if summary["match_rate_pct"] is None
        else f"{summary['match_rate_pct']:.1f}%"
    )
    rows_html = results_df.to_html(index=False)
    counts_html = "".join(
        f"<li><strong>{category}</strong>: {count}</li>"
        for category, count in sorted(summary["category_counts"].items())
    )
    return f"""<!DOCTYPE html>
<html>
<head><title>Parity Monitor Report</title></head>
<body>
<h1>Parity Monitor Report</h1>
<p>Total events compared: {summary['total_events']}</p>
<p>Match rate: {match_rate}</p>
<h2>Category breakdown</h2>
<ul>{counts_html}</ul>
<h2>All events</h2>
{rows_html}
</body>
</html>
"""
