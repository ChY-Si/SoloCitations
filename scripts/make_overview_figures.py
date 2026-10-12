#!/usr/bin/env python
"""Rebuild the two bibliometric overview figures of the report.

Needs no Scopus API access.

* ``article_year.png``  - publications per year of the exported record set, with
  the 243 core papers highlighted;
* ``author_nation.png`` - country distribution taken from the Scopus "Refine
  results" panel export, which counts countries over the whole query result set
  (the exported CSV itself has no affiliation column).

Examples
--------
::

    python scripts/make_overview_figures.py
    python scripts/make_overview_figures.py --top 15 --show
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from solo_citations import figures, paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sample", type=Path, default=None,
                        help="Scopus export CSV (default: data/raw/scopus_export_*.csv)")
    parser.add_argument("--table", type=Path, default=None,
                        help="core-paper table highlighted in the year figure (default: base3.csv)")
    parser.add_argument("--overall", type=Path, default=None,
                        help="Scopus refine panel export (default: data/raw/overall.csv)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="output directory (default: report/figures)")
    parser.add_argument("--top", type=int, default=20,
                        help="how many countries to plot (default: 20)")
    parser.add_argument("--full-query", action="store_true",
                        help="count the whole 3138-record query result set instead of "
                             "the 262 exported records in the year figure")
    parser.add_argument("--show", action="store_true", help="open interactive windows")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    sample = args.sample or paths.DEFAULT_SCOPUS_EXPORT
    if not args.full_query and not Path(sample).exists():
        print(f"导出数据不存在：{sample}", file=sys.stderr)
        return 2

    out_dir = args.out_dir or paths.figures_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- figure 1: publications per year ----
    print(f"发文量数据源：{sample}", flush=True)
    counts, subset, _ = figures.plot_article_year(
        sample, out_dir / "article_year.png",
        table_csv=args.table, full_panel=args.full_query, show=args.show)
    print(f"  年度记录 {int(counts.sum())} 篇，年份范围 {counts.index.min()}-{counts.index.max()}",
          flush=True)
    if subset is not None:
        print(f"  其中核心文献 {int(subset.sum())} 篇，"
              f"年份范围 {subset.index.min()}-{subset.index.max()}", flush=True)

    # ---- figure 2: country distribution ----
    overall = args.overall or (paths.data_raw / "overall.csv")
    if not Path(overall).exists():
        print(f"[跳过] 国家分布数据不存在：{overall}", file=sys.stderr)
        return 0
    print(f"国家分布数据源：{overall}", flush=True)
    nations, _ = figures.plot_author_nation(
        overall, out_dir / "author_nation.png", top=args.top, show=args.show)
    print(nations.head(args.top).to_string(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
