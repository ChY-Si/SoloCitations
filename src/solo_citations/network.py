"""Stage 3-4 of the pipeline: citation-network construction and SC aggregation.

Stage 3 (:class:`EIDNetworkBuilder`) walks the per-paper dumps produced by
stages 1-2 and, for every target paper, labels each node of its three-layer
citation network with the binary solo-citation flag ``SC``:

``SC = 1``  the citing paper cites the target paper but none of the target
            paper's references (a *solo citation*);
``SC = 0``  otherwise (a *duet* or *prelude* citation).

Stage 4 (:func:`aggregate`) sums the flags over the citing papers of each
target and joins the published year and citation count of the target, which
yields ``SCtot`` and the ratio ``R_SC = SCtot / Cited by`` used in the report.

Input layout expected by stage 3, one directory per target paper::

    <target_eid>/
      REFs.csv                       references of the target paper
      Cits.csv                       papers citing the target paper
      <target_eid>'sCitsREF/
        <citing_eid>'sREFs.csv       references of one citing paper

The ``<target_eid>'sREFs`` sub-directory variant and a flat ``*REFs*.csv``
layout are both accepted, matching the two shapes found in the archived dumps.
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import pandas as pd

from . import paths

__all__ = ["EIDNetworkBuilder", "aggregate", "EID_PATTERN"]

#: Scopus EID, e.g. ``2-s2.0-85009319792``.
EID_PATTERN = re.compile(r"2-s2\.0-\d+")

NODE_COLUMNS = ["EID", "SC"]


class EIDNetworkBuilder:
    """Build the three-layer citation network of one target paper at a time."""

    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.eid_pattern = EID_PATTERN

    # -- helpers ---------------------------------------------------------
    def extract_eid(self, text):
        """Return the first EID embedded in ``text``, or ``None``."""
        match = self.eid_pattern.search(text)
        return match.group(0) if match else None

    @staticmethod
    def _read_eids(csv_path):
        """Yield the valid EIDs listed in the ``EID`` column of a CSV file."""
        with open(csv_path, "r", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                eid = (row.get("EID") or "").strip()
                if eid and EID_PATTERN.fullmatch(eid):
                    yield eid

    # -- stage 3 ---------------------------------------------------------
    def process_main_paper(self, main_paper_dir):
        """Return ``(target_eid, {node_eid: sc_flag})`` for one target paper."""
        main_paper_dir = Path(main_paper_dir)
        main_paper_eid = main_paper_dir.name
        nodes_set = set()

        # 1. references of the target paper
        main_paper_refs = set()
        ref_dir = main_paper_dir / f"{main_paper_eid}'sREFs"
        if ref_dir.is_dir():
            for name in sorted(os.listdir(ref_dir)):
                if name.endswith(".csv"):
                    main_paper_refs.update(self._read_eids(ref_dir / name))
        else:
            for name in sorted(os.listdir(main_paper_dir)):
                if name.endswith(".csv") and "REFs" in name:
                    main_paper_refs.update(self._read_eids(main_paper_dir / name))
        nodes_set |= main_paper_refs

        # 2. papers citing the target paper
        points_to_main_set = set()
        cits_file = main_paper_dir / "Cits.csv"
        if cits_file.exists():
            points_to_main_set = set(self._read_eids(cits_file))
            nodes_set |= points_to_main_set

        # 3. references of those citing papers
        cit_cites_main_ref = set()
        cits_ref_dir = main_paper_dir / f"{main_paper_eid}'sCitsREF"
        if cits_ref_dir.is_dir():
            for name in sorted(os.listdir(cits_ref_dir)):
                if not name.endswith(".csv"):
                    continue
                cit_eid = self.extract_eid(name)
                if not cit_eid:
                    continue
                nodes_set.add(cit_eid)
                for ref_eid in self._read_eids(cits_ref_dir / name):
                    nodes_set.add(ref_eid)
                    # The citing paper shares a reference with the target:
                    # it is a duet rather than a solo citation.
                    if ref_eid in main_paper_refs:
                        cit_cites_main_ref.add(cit_eid)

        nodes_set.add(main_paper_eid)

        nodes = {}
        for node in nodes_set:
            is_solo = node in points_to_main_set and node not in cit_cites_main_ref
            nodes[node] = 1 if is_solo else 0
        return main_paper_eid, nodes

    def validate_data(self, main_paper_eid, nodes):
        """Warn about node keys that are not valid EIDs (never fatal)."""
        for node in nodes:
            if not self.eid_pattern.fullmatch(node):
                print(f"警告: 无效的EID格式: {node}")

    def write_network_output(self, main_paper_eid, nodes):
        """Write ``<target_eid>_nodes.csv`` and return its path."""
        nodes_file = self.output_dir / f"{main_paper_eid}_nodes.csv"
        with open(nodes_file, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(NODE_COLUMNS)
            for node, sc in nodes.items():
                if self.eid_pattern.fullmatch(node):
                    writer.writerow([node, int(sc)])
        return nodes_file

    def build_networks(self, limit=None):
        """Process every target-paper directory in ``input_dir``.

        Returns the number of networks written.
        """
        done = 0
        for name in sorted(os.listdir(self.input_dir)):
            if limit is not None and done >= limit:
                break
            main_paper_path = self.input_dir / name
            if not main_paper_path.is_dir():
                continue
            print(f"处理主文献: {name}", flush=True)
            main_paper_eid, nodes = self.process_main_paper(main_paper_path)
            self.validate_data(main_paper_eid, nodes)
            self.write_network_output(main_paper_eid, nodes)
            print(f"生成网络文件: {main_paper_eid}_nodes.csv", flush=True)
            done += 1
        return done

    def build_one(self, main_paper_eid):
        """Process a single target paper given by EID. Returns node count."""
        main_paper_eid, nodes = self.process_main_paper(self.input_dir / main_paper_eid)
        self.validate_data(main_paper_eid, nodes)
        self.write_network_output(main_paper_eid, nodes)
        return len(nodes)


# -- stage 4 -------------------------------------------------------------
def sc_totals(network_dir=None):
    """Return a ``{eid: SC total}`` mapping over the generated node files."""
    network_dir = Path(network_dir) if network_dir else paths.network_dir
    totals = {}
    if not network_dir.is_dir():
        return totals
    for name in sorted(os.listdir(network_dir)):
        if not name.endswith("_nodes.csv"):
            continue
        eid = name[: -len("_nodes.csv")]
        frame = pd.read_csv(network_dir / name)
        totals[eid] = int(frame["SC"].sum())
    return totals


def aggregate(
    sample_csv=None,
    network_dir=None,
    output_csv=None,
    *,
    year_column="Year",
    cited_column="Cited by",
    eid_column="EID",
    title_column="Title",
):
    """Join SC totals onto the sampled metadata and write the result table.

    Papers without a generated network get ``SCtot = 0``, exactly as the
    original course script did.  The returned frame carries the columns
    ``eid``, ``Year``, ``SCtot``, ``Cited by`` and, when available, ``Title``.
    """
    sample_csv = Path(sample_csv) if sample_csv else paths.DEFAULT_SCOPUS_EXPORT
    output_csv = Path(output_csv) if output_csv else paths.data_processed / "eid_sc_tot.csv"

    meta = pd.read_csv(sample_csv, usecols=lambda c: c in {
        eid_column, year_column, cited_column, title_column,
    })
    if eid_column not in meta.columns:
        raise KeyError(f"{sample_csv} has no {eid_column!r} column")

    totals = sc_totals(network_dir)

    rows = []
    for record in meta.to_dict("records"):
        eid = record[eid_column]
        row = {
            "eid": eid,
            "Year": record.get(year_column),
            "SCtot": totals.get(eid, 0),
            "Cited by": record.get(cited_column),
        }
        if title_column in record:
            row["Title"] = record[title_column]
        rows.append(row)

    result = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False)
    print(f"Done. Created {output_csv} with {len(result)} rows", flush=True)
    return result
