#!/usr/bin/env python
"""Stage 1+2: collect references and citing papers from the Scopus API.

Examples
--------
Collect every paper of the shipped Scopus export (243 core papers)::

    python scripts/collect_citations.py --from-export

Collect a handful of papers first to check the API keys::

    python scripts/collect_citations.py --from-export --limit 5

Collect a single paper by EID::

    python scripts/collect_citations.py 2-s2.0-85132685902

Only stage 1 (references + citing list), skipping the expensive expansion::

    python scripts/collect_citations.py --from-export --stage 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401  (sets up sys.path)

from solo_citations import collect, paths, scopus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("eids", nargs="*", help="target EIDs (default: read from the sample CSV)")
    parser.add_argument("--from-export", action="store_true",
                        help="read the target EIDs from the Scopus export")
    parser.add_argument("--sample", type=Path, default=None,
                        help="CSV with an EID column (default: data/raw/scopus_export_*.csv)")
    parser.add_argument("--limit", type=int, default=None, help="only process the first N EIDs")
    parser.add_argument("--stage", choices=["1", "2", "12"], default="12",
                        help="which collection stages to run (default: both)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="where the per-paper dumps are written")
    parser.add_argument("--workers", type=int, default=None,
                        help="parallel threads (stage 1 default 10, stage 2 default 16)")
    parser.add_argument("--overwrite", action="store_true",
                        help="re-fetch papers that are already on disk")
    parser.add_argument("--cfg", type=Path, default=None,
                        help="pybliometrics config to generate (secrets stay outside the repo)")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not scopus.has_keys():
        print(
            "未找到 Scopus API key。\n"
            "请设置环境变量 SCOPUS_API_KEYS（多个 key 用逗号分隔），\n"
            f"或创建 {scopus.KEY_FILE}，每行一个 key。\n"
            "可参考 config/scopus_keys.example.txt。",
            file=sys.stderr,
        )
        return 2

    eids = list(args.eids)
    if args.from_export or not eids:
        sample = args.sample or paths.DEFAULT_SCOPUS_EXPORT
        eids += collect.read_eids(sample, limit=args.limit)
    elif args.limit:
        eids = eids[: args.limit]
    if not eids:
        print("没有待处理的 EID。", file=sys.stderr)
        return 2

    paths.ensure_dirs()
    cfg = scopus.init(args.cfg)
    print(f"已初始化 Scopus 客户端（配置文件：{cfg}）", flush=True)
    print(f"共 {len(eids)} 个 EID，阶段 {args.stage}", flush=True)

    out_dir = args.out_dir or paths.data_interim

    if args.stage in ("1", "12"):
        workers = args.workers or collect.DEFAULT_WORKERS
        succeeded, failed = collect.collect_targets(
            eids, workers=workers, out_dir=out_dir, overwrite=args.overwrite,
        )
        print(f"\n阶段一完成：成功 {len(succeeded)}，失败 {len(failed)}", flush=True)
        eids = succeeded
        if failed:
            print(f"失败的 EID：{failed}", flush=True)

    if args.stage in ("2", "12") and eids:
        workers = args.workers or 16
        succeeded, failed = collect.collect_citing_references(
            eids, workers=workers, out_dir=out_dir, overwrite=args.overwrite,
        )
        print(f"\n阶段二完成：成功 {len(succeeded)}，有失败 {len(failed)}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
