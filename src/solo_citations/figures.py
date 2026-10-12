"""Bibliometric figures derived from the Scopus exports (report figures 1 and 2).

Both figures come from files already in the repository - no Scopus API access is
needed - but they use **two different data sources**, which mirrors the report:

``article_year.png``
    Publications per year of the exported record set
    (``data/raw/scopus_export_*.csv``).  The subset retained as the 243 core
    papers is highlighted on top of the full export.

``author_nation.png``
    Country distribution.  The exported CSV carries no affiliation column, so
    this figure is built from the Scopus "Refine results" panel export
    (``data/raw/overall.csv``), which counts the country field over the *whole*
    query result set just as the report text describes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import paths

__all__ = [
    "article_year_counts",
    "sample_year_counts",
    "refine_panel",
    "panel_counts",
    "author_countries",
    "plot_article_year",
    "plot_author_nation",
]

#: ``City, Region, Country`` - the country is the last comma-separated field.
_COUNTRY_TAIL = re.compile(r",\s*([^,;]+?)\s*$")

#: Header of the wide dimension table inside a Scopus refine export.
_PANEL_HEADER = "OPEN ACCESS"

#: Heading lines of that file, in order.
_PANEL_TITLE = "Scopus refine results values"
_PANEL_QUERY = "Your query"


def _default_export() -> Path:
    return paths.DEFAULT_SCOPUS_EXPORT


# -- figure 1: publications per year -------------------------------------
def article_year_counts(sample_csv=None, *, year_column="Year"):
    """Publications per year over the exported record set, indexed by year."""
    sample_csv = Path(sample_csv) if sample_csv else _default_export()
    frame = pd.read_csv(sample_csv, usecols=[year_column])
    years = pd.to_numeric(frame[year_column], errors="coerce").dropna().astype(int)
    counts = years.value_counts().sort_index()
    counts.name = "articles"
    return counts


def sample_year_counts(table_csv=None, *, year_column="Year"):
    """Publications per year of the retained core papers (``base3.csv``)."""
    table_csv = Path(table_csv) if table_csv else paths.data_processed / "base3.csv"
    frame = pd.read_csv(table_csv, usecols=[year_column])
    years = pd.to_numeric(frame[year_column], errors="coerce").dropna().astype(int)
    counts = years.value_counts().sort_index()
    counts.name = "articles"
    return counts


def plot_article_year(
    sample_csv=None,
    output_png=None,
    *,
    table_csv=None,
    full_panel=False,
    show=False,
    color="#4c72b0",
    sample_color="#c44e52",
    dpi=150,
):
    """Bar chart of publications per year (report figure ``article_year.png``).

    ``full_panel=False`` (default) counts only the exported records, which are
    the papers with at least 50 citations.  ``full_panel=True`` counts the whole
    query result set from the refine panel instead, which is the basis of the
    3138 figures quoted in the report; the core-paper subset is drawn on top in
    both cases.
    """
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_png = Path(output_png) if output_png else paths.figures_dir / "article_year.png"

    if full_panel:
        counts = panel_counts("YEAR").copy()
        counts.index = counts.index.astype(int)
        counts = counts.sort_index()
        counts.name = "articles"
        source_label = f"full query result ({int(counts.sum())} records)"
    else:
        counts = article_year_counts(sample_csv)
        source_label = f"Scopus export ({int(counts.sum())} records)"

    table_csv = Path(table_csv) if table_csv else paths.data_processed / "base3.csv"
    subset = sample_year_counts(table_csv) if table_csv.exists() else None

    years = list(range(int(counts.index.min()), int(counts.index.max()) + 1))
    full = counts.reindex(years, fill_value=0)

    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.bar(years, full.to_numpy(), color=color, width=0.8, label=source_label)

    if subset is not None and len(subset):
        selected = subset.reindex(years, fill_value=0)
        ax.bar(years, selected.to_numpy(), color=sample_color, width=0.8,
               label=f"core papers ({int(subset.sum())}, cited by >= 50)")
        first_year = int(subset.index.min())
        ax.axvline(first_year - 0.5, color="gray", linestyle="--", linewidth=1.2)
        ax.annotate(
            f"core sample starts {first_year}",
            xy=(first_year - 0.5, full.max() * 0.95),
            xytext=(6, 0), textcoords="offset points",
            fontsize=9, color="#555555", va="top",
        )

    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Number of articles", fontsize=12)
    ax.set_title("Publications per Year", fontsize=14)
    step = max(1, len(years) // 22)
    ax.set_xticks(years[::step])
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=dpi)
    if show:
        plt.show()
    plt.close(fig)
    print(f"Done. Saved as {output_png}", flush=True)
    return counts, subset, output_png


# -- figure 2: country distribution --------------------------------------
def refine_panel(overall_csv=None):
    """Parse a Scopus "Refine results" export into long-form counts.

    The file is not a rectangular CSV.  It opens with a title line and the query
    line, then holds a wide table whose header names the dimensions::

        "OPEN ACCESS",,"YEAR",,"AUTHOR NAME",,...,"COUNTRY",,"SOURCE TYPE",

    and whose data rows carry one ``value, count`` pair per dimension, with the
    first value unpaired because its header occupies the first field::

        "All Open Access","1217","2026","61",...,"United States","1350",...

    Fields are quoted and may contain commas (``"Regan, S.P."``), so the rows are
    parsed with :mod:`csv` and the pairs are read positionally from the end of
    the header.  Returns a frame with the columns ``dimension, value, count``.
    """
    import csv as _csv
    import io

    overall_csv = Path(overall_csv) if overall_csv else paths.data_raw / "overall.csv"
    if not overall_csv.exists():
        raise FileNotFoundError(f"Scopus refine export not found: {overall_csv}")

    lines = overall_csv.read_text(encoding="utf-8-sig").splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.lstrip('"').startswith(_PANEL_HEADER)),
        None,
    )
    if start is None:
        raise ValueError(f"no refine dimension table found in {overall_csv}")

    def cells(line):
        return [cell.strip() for cell in next(_csv.reader(io.StringIO(line)))]

    header = cells(lines[start])
    # Column indices holding a dimension name; the rest are the paired slots.
    named = [i for i, cell in enumerate(header) if cell]
    if not named:
        raise ValueError(f"unusable refine header in {overall_csv}")
    dimensions = [header[i] for i in named]
    expected = 2 * len(dimensions) - 1

    records = []
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        fields = cells(line)
        if len(fields) < expected:
            fields += [""] * (expected - len(fields))
        # Read the pairs backwards from the end; field 0 is always the first value.
        pairs: dict[int, tuple[str, str]] = {0: (fields[0], "")}
        cursor = len(fields)
        for column in reversed(named[1:]):
            cursor -= 2
            if cursor <= 0:
                break
            pairs[column] = (fields[cursor], fields[cursor + 1])
        for column, dimension in zip(named, dimensions):
            value, raw = pairs.get(column, ("", ""))
            if not value:
                continue
            try:
                count = int(raw)
            except ValueError:
                continue
            records.append({"dimension": dimension, "value": value, "count": count})
    return pd.DataFrame(records)


def panel_counts(dimension, overall_csv=None, *, top=None):
    """Counts of one refine dimension, largest first."""
    panel = refine_panel(overall_csv)
    rows = panel[panel["dimension"] == dimension]
    series = rows.set_index("value")["count"].sort_values(ascending=False)
    if top:
        series = series.head(top)
    series.name = "papers"
    series.index.name = dimension.lower().replace(" ", "_")
    return series


def author_countries(overall_csv=None, *, top=None):
    """Country distribution over the whole query result set."""
    return panel_counts("COUNTRY", overall_csv, top=top)


def plot_author_nation(
    overall_csv=None,
    output_png=None,
    *,
    top=20,
    show=False,
    color="#dd8452",
    dpi=150,
):
    """Horizontal bar chart of the most frequent author countries."""
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_png = Path(output_png) if output_png else paths.figures_dir / "author_nation.png"
    counts = author_countries(overall_csv, top=top).iloc[::-1]

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(counts.index, counts.to_numpy(), color=color)
    for position, value in enumerate(counts.to_numpy()):
        ax.text(value, position, f" {value}", va="center", fontsize=9)
    ax.set_xlabel("Number of records in the query result set", fontsize=12)
    ax.set_title(f"Author countries, top {len(counts)}", fontsize=14)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=dpi)
    if show:
        plt.show()
    plt.close(fig)
    print(f"Done. Saved as {output_png}", flush=True)
    return counts, output_png
