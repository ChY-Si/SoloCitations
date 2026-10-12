"""Yearly aggregation of the solo-citation ratio ``R_SC`` and its figure.

``R_SC = SCtot / Cited by`` for every target paper, grouped by publication
year, reduced to the mean and the min/max envelope drawn in the report.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import paths

__all__ = ["add_rate", "yearly_stats", "plot_yearly_rate"]

#: Column names accepted for the ratio input table.
_EID_CANDIDATES = ("eid", "EID")
_RATE_CANDIDATES = ("Rate", "rate")


def add_rate(frame, sc_column="SCtot", cited_column="Cited by"):
    """Return a copy of ``frame`` with a ``rate`` column added."""
    out = frame.copy()
    denominator = pd.to_numeric(out[cited_column], errors="coerce")
    numerator = pd.to_numeric(out[sc_column], errors="coerce")
    out["rate"] = numerator / denominator.replace(0, np.nan)
    return out


def yearly_stats(frame, *, year_column="Year"):
    """Per-year mean/max/min of the rate plus the EIDs attaining the extremes."""
    data = frame
    if "rate" not in data.columns:
        data = add_rate(data)

    grouped = data.groupby(year_column)["rate"]
    stats = grouped.mean().rename("rate").to_frame()
    stats["max_rate"] = grouped.max()
    stats["min_rate"] = grouped.min()

    id_column = next((c for c in _EID_CANDIDATES if c in data.columns), None)
    if id_column is not None:
        maxima = data.loc[grouped.idxmax()][[year_column, id_column, "rate"]]
        maxima = maxima.rename(columns={id_column: "max_eid", "rate": "max_eid_rate"})
        minima = data.loc[grouped.idxmin()][[year_column, id_column, "rate"]]
        minima = minima.rename(columns={id_column: "min_eid", "rate": "min_eid_rate"})
        stats = stats.merge(maxima, on=year_column).merge(minima, on=year_column)

    stats["up_len"] = stats["max_rate"] - stats["rate"]
    stats["down_len"] = stats["rate"] - stats["min_rate"]
    return stats.reset_index()


def plot_yearly_rate(
    input_csv=None,
    output_png=None,
    *,
    small_sample_threshold=3,
    show=False,
):
    """Draw the yearly average ``R_SC`` with its min-max envelope.

    Years that contain fewer than ``small_sample_threshold`` papers are marked
    with a hollow marker, since a mean over one or two papers is noisy.
    """
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    input_csv = Path(input_csv) if input_csv else paths.data_processed / "base3.csv"
    output_png = Path(output_png) if output_png else paths.figures_dir / "washed_yearly_rate.png"

    frame = pd.read_csv(input_csv)
    rate_column = next((c for c in _RATE_CANDIDATES if c in frame.columns), None)
    if rate_column and "rate" not in frame.columns:
        frame = frame.rename(columns={rate_column: "rate"})
    stats = yearly_stats(frame)

    counts = frame.groupby("Year")["rate"].size().rename("n")
    stats = stats.merge(counts, on="Year")
    stats["small"] = stats["n"] < small_sample_threshold

    yerr = [stats["down_len"].to_numpy(), stats["up_len"].to_numpy()]

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(
        stats["Year"], stats["rate"], marker="o", linewidth=2, markersize=6,
        label="Avg rate (SC / Cited by)", color="#1f77b4", zorder=3,
    )
    if stats["small"].any():
        ax.scatter(
            stats.loc[stats["small"], "Year"], stats.loc[stats["small"], "rate"],
            s=110, facecolors="white", edgecolors="#1f77b4", linewidths=1.8,
            zorder=4, label=f"Year with fewer than {small_sample_threshold} papers",
        )
    ax.errorbar(
        stats["Year"], stats["rate"], yerr=yerr, fmt="none", color="gray",
        elinewidth=1, capsize=6, capthick=2, label="Max-Min range", zorder=2,
    )

    ax.set_xlabel("Year", fontsize=14)
    ax.set_ylabel("rate = SC / Cited by", fontsize=14)
    ax.set_title("Yearly Average Rate with Ranges", fontsize=16)
    ax.legend(fontsize=10)
    ax.set_xticks(sorted(stats["Year"].unique()))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    print(f"Done. Saved as {output_png}", flush=True)
    return stats, output_png
