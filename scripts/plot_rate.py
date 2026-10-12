#!/usr/bin/env python
"""Draw the yearly average solo-citation ratio with its min-max envelope.

This is the ``washed_yearly_rate.png`` figure of the report.  Years holding
fewer than ``--small-sample`` papers are drawn with a hollow marker, because a
mean over one or two papers is not meaningful.

Examples
--------
::

    python scripts/plot_rate.py
    python scripts/plot_rate.py --input data/processed/base3.csv --show
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from solo_citations import citation_ratio, paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", type=Path, default=None,
                        help="table with SCtot, Cited by and Year (default: data/processed/base3.csv)")
    parser.add_argument("--output", type=Path, default=None,
                        help="output PNG (default: report/figures/washed_yearly_rate.png)")
    parser.add_argument("--small-sample", type=int, default=3,
                        help="mark years with fewer than N papers (default: 3)")
    parser.add_argument("--csv", type=Path, default=None,
                        help="also dump the per-year statistics to this CSV")
    parser.add_argument("--show", action="store_true", help="open an interactive window")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    input_csv = args.input or paths.data_processed / "base3.csv"
    if not Path(input_csv).exists():
        print(f"输入表不存在：{input_csv}")
        return 2

    stats, output_png = citation_ratio.plot_yearly_rate(
        input_csv, args.output,
        small_sample_threshold=args.small_sample,
        show=args.show,
    )

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        stats.to_csv(args.csv, index=False)
        print(f"已写出逐年统计：{args.csv}")

    print(stats.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
