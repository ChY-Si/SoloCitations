#!/usr/bin/env python
"""Stage 3: build the three-layer citation network and the SC node lists.

Every target-paper directory under ``--input`` is processed independently and
written to ``--output`` as ``<target_eid>_nodes.csv`` with columns ``EID,SC``.

Examples
--------
Rebuild everything in the default locations::

    python scripts/build_networks.py

Rebuild and check against the archived result::

    python scripts/build_networks.py --input data/interim \\
        --output data/processed/network
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from solo_citations import network, paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", type=Path, default=None,
                        help="directory holding one sub-directory per target paper")
    parser.add_argument("--output", type=Path, default=None,
                        help="directory for the <target>_nodes.csv files")
    parser.add_argument("--eid", action="append", default=None,
                        help="only build this target paper (repeatable)")
    parser.add_argument("--limit", type=int, default=None, help="only the first N directories")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    input_dir = args.input or paths.data_interim
    output_dir = args.output or paths.network_dir

    if not Path(input_dir).is_dir():
        print(f"输入目录不存在：{input_dir}", file=sys.stderr)
        return 2

    builder = network.EIDNetworkBuilder(input_dir, output_dir)

    if args.eid:
        for eid in args.eid:
            count = builder.build_one(eid)
            print(f"生成网络文件: {eid}_nodes.csv（{count} 个节点）", flush=True)
        return 0

    done = builder.build_networks(limit=args.limit)
    print(f"网络构建完成！共处理 {done} 篇主文献，输出目录：{output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
