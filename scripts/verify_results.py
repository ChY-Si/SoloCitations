#!/usr/bin/env python
"""Check that the shipped results are internally consistent.

Runs with no network access and no Scopus API key.  Two checks are performed:

1. every ``SCtot`` in ``data/processed/base3.csv`` equals the sum of the ``SC``
   column of the matching ``data/processed/network/<eid>_nodes.csv``;
2. ``Rate`` equals ``SCtot / Cited by``.

With ``--rebuild`` the network of one paper is rebuilt from
``data/interim/<eid>`` and compared node by node against the shipped file,
which proves that the ported stage-3 code reproduces the archived result.

Exit code 0 means all selected checks passed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

import _bootstrap  # noqa: F401

from solo_citations import network, paths


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--table", type=Path, default=None,
                        help="result table (default: data/processed/base3.csv)")
    parser.add_argument("--network-dir", type=Path, default=None,
                        help="shipped node lists (default: data/processed/network)")
    parser.add_argument("--rebuild", metavar="EID", default=None,
                        help="rebuild this paper from data/interim and diff it")
    parser.add_argument("--interim", type=Path, default=None,
                        help="directory of raw per-paper dumps (default: data/interim)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    table_path = args.table or paths.data_processed / "base3.csv"
    network_dir = args.network_dir or paths.network_dir
    failures = 0

    if not Path(table_path).exists():
        print(f"[跳过] 结果表不存在：{table_path}")
    else:
        table = pd.read_csv(table_path)
        print(f"检查 {table_path}（{len(table)} 行）")

        missing, mismatch = [], []
        for record in table.to_dict("records"):
            nodes_file = Path(network_dir) / f"{record['eid']}_nodes.csv"
            if not nodes_file.exists():
                missing.append(record["eid"])
                continue
            total = int(pd.read_csv(nodes_file)["SC"].sum())
            if total != int(record["SCtot"]):
                mismatch.append((record["eid"], int(record["SCtot"]), total))

        if missing:
            print(f"  [失败] {len(missing)} 篇缺少节点文件，例如 {missing[:3]}")
            failures += 1
        if mismatch:
            print(f"  [失败] {len(mismatch)} 篇 SCtot 与节点文件不一致，例如 {mismatch[:3]}")
            failures += 1
        if not missing and not mismatch:
            print(f"  [通过] {len(table)} 篇的 SCtot 与节点文件全部一致")

        expected = table["SCtot"] / table["Cited by"]
        if "Rate" in table.columns:
            drift = (table["Rate"] - expected).abs().max()
            if drift < 1e-9:
                print("  [通过] Rate == SCtot / Cited by")
            else:
                print(f"  [失败] Rate 与 SCtot / Cited by 最大偏差 {drift}")
                failures += 1

    if args.rebuild:
        interim = args.interim or paths.data_interim
        source = Path(interim) / args.rebuild
        shipped = Path(network_dir) / f"{args.rebuild}_nodes.csv"
        if not source.is_dir():
            print(f"[跳过] 没有中间数据可重建：{source}")
        elif not shipped.exists():
            print(f"[跳过] 没有可比对的归档结果：{shipped}")
        else:
            print(f"重建 {args.rebuild} 并与归档结果逐节点比对")
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                builder = network.EIDNetworkBuilder(interim, tmp)
                builder.build_one(args.rebuild)
                rebuilt = pd.read_csv(Path(tmp) / f"{args.rebuild}_nodes.csv")
            archived = pd.read_csv(shipped)
            merged = rebuilt.merge(archived, on="EID", how="outer",
                                   suffixes=("_new", "_old"), indicator=True)
            only_new = int((merged["_merge"] == "left_only").sum())
            only_old = int((merged["_merge"] == "right_only").sum())
            differing = int(((merged["_merge"] == "both")
                             & (merged["SC_new"] != merged["SC_old"])).sum())
            if only_new or only_old or differing:
                print(f"  [失败] 新增 {only_new}，缺失 {only_old}，SC 不同 {differing}")
                failures += 1
            else:
                print(f"  [通过] {len(rebuilt)} 个节点完全一致，"
                      f"SC 合计 {int(rebuilt['SC'].sum())}")

    if failures:
        print(f"\n验证未通过（{failures} 项失败）")
        return 1
    print("\n验证通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
