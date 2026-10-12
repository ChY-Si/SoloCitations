#!/usr/bin/env python
"""Stage 4: aggregate the SC totals onto the sample metadata.

Reads the ``<target_eid>_nodes.csv`` files produced by stage 3 and the sampled
paper metadata (year, citation count), then writes a table with
``eid, Year, SCtot, Cited by`` and the derived ratio ``R_SC = SCtot / Cited by``.

Examples
--------
::

    python scripts/aggregate_sc.py --sample data/raw/scopus_export_May\\ 26-2026_*.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from solo_citations import citation_ratio, network, paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sample", type=Path, default=None,
                        help="sampled paper metadata with an EID column")
    parser.add_argument("--network-dir", type=Path, default=None,
                        help="directory of <target>_nodes.csv files")
    parser.add_argument("--output", type=Path, default=None,
                        help="output CSV (default: data/processed/eid_sc_tot.csv)")
    parser.add_argument("--with-rate", action="store_true",
                        help="also add the R_SC column")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    sample = args.sample or paths.DEFAULT_SCOPUS_EXPORT
    if not Path(sample).exists():
        print(f"样本元数据不存在：{sample}", file=sys.stderr)
        return 2

    network_dir = args.network_dir or paths.network_dir
    if not Path(network_dir).is_dir():
        print(f"警告：网络输出目录不存在，所有 SCtot 将记为 0：{network_dir}", file=sys.stderr)

    frame = network.aggregate(sample, network_dir, args.output)

    if args.with_rate:
        frame = citation_ratio.add_rate(frame)
        destination = Path(args.output) if args.output else paths.data_processed / "eid_sc_tot.csv"
        destination = destination.with_name(destination.stem + "_with_rate.csv")
        frame.to_csv(destination, index=False)
        print(f"已写出带 R_SC 的表：{destination}", flush=True)

    matched = int((frame["SCtot"] > 0).sum())
    print(f"其中 {matched} / {len(frame)} 篇有 SC 数据。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
