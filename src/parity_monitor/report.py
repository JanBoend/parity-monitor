"""Summary computation and terminal/report output for parity-monitor results."""

import pandas as pd

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


def print_summary(summary: dict) -> None:
    print(f"Total events compared: {summary['total_events']}")
    if summary["match_rate_pct"] is None:
        print("Match rate: N/A (no comparable events)")
    else:
        print(f"Match rate: {summary['match_rate_pct']:.1f}%")
    print()
    print("Breakdown by category:")
    for category, count in sorted(summary["category_counts"].items()):
        print(f"  {category}: {count}")
    print()
    if not summary["worst_offenders"].empty:
        print(f"Top {len(summary['worst_offenders'])} worst offenders:")
        for _, row in summary["worst_offenders"].iterrows():
            print(f"  {_format_offender(row)}")


def _format_offender(row) -> str:
    category = row["category"]
    prefix = f"[{category}] {row['symbol']} signal_id={row['signal_id']}"
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
