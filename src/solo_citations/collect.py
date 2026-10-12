"""Stages 1-2 of the pipeline: collect citation relations from the Scopus API.

Stage 1, :func:`collect_targets`, records for every target paper its reference
list (``REFs.csv``) and the list of papers citing it (``Cits.csv``).

Stage 2, :func:`collect_citing_references`, expands every citing paper found in
stage 1 and records *its* reference list under
``<target>\\<target>'sCitsREF\\<citing>'sREFs.csv``.

Both stages are resumable: files already on disk are skipped unless
``overwrite`` is set, and a plain-text done-list records completed targets so a
long batch can be interrupted and restarted.
"""

from __future__ import annotations

import csv
import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from pathlib import Path

from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout

from . import paths

__all__ = [
    "read_eids",
    "collect_targets",
    "collect_citing_references",
    "process_target",
    "process_citing_paper",
]

_TRANSIENT = (Timeout, RequestsConnectionError)

DEFAULT_WORKERS = 10
DEFAULT_MAX_PENDING = 500


# -- shared helpers ------------------------------------------------------
def read_eids(path, *, column="EID", limit=None):
    """Read a list of EIDs from any CSV file that has an ``EID`` column."""
    eids = []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            eid = (row.get(column) or "").strip()
            if eid:
                eids.append(eid)
            if limit is not None and len(eids) >= limit:
                break
    return eids


def _read_done_set(done_file):
    if done_file and os.path.exists(done_file):
        with open(done_file, "r", encoding="utf-8") as handle:
            return {line.strip() for line in handle if line.strip()}
    return set()


def _append_done(done_file, eid, lock):
    if not done_file:
        return
    with lock:
        with open(done_file, "a", encoding="utf-8") as handle:
            handle.write(eid + "\n")


def _write_refs(target_eid, references):
    """Write an ``EID,DOI`` table of references and return its path."""
    destination = paths.data_interim / target_eid / "REFs.csv"

    def to_eid(reference):
        raw = getattr(reference, "id", None)
        if raw is None:
            return None
        raw = str(raw).strip()
        return raw if raw.startswith("2-s2.0-") else f"2-s2.0-{raw}"

    with open(destination, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["EID", "DOI"])
        for reference in references:
            eid = to_eid(reference)
            if eid:
                writer.writerow([eid, getattr(reference, "doi", "")])
    return destination


# -- stage 1 -------------------------------------------------------------
def collect_targets(
    eids,
    *,
    workers=DEFAULT_WORKERS,
    out_dir=None,
    done_file=None,
    overwrite=False,
    retries=3,
    page_size=200,
    timeout=60,
    progress_every=25,
):
    """Stage 1: fetch ``REFs.csv`` and ``Cits.csv`` for each target EID.

    Returns ``(succeeded, failed)`` lists of EIDs.  Requires
    :func:`solo_citations.scopus.init` to have been called.
    """
    from pybliometrics.scopus import AbstractRetrieval, ScopusSearch

    out_dir = Path(out_dir) if out_dir else paths.data_interim
    done_file = Path(done_file) if done_file else out_dir / "done_b_eids.txt"
    lock = threading.Lock()

    done = _read_done_set(done_file) if not overwrite else set()
    pending = [eid for eid in eids if overwrite or eid not in done]
    print(f"共 {len(eids)} 个EID，待处理 {len(pending)} 个（已跳过 {len(done)} 个）", flush=True)

    def worker(target_eid):
        directory = out_dir / target_eid
        directory.mkdir(parents=True, exist_ok=True)
        ref_ok = cit_ok = False

        for attempt in range(retries):
            try:
                paper = AbstractRetrieval(target_eid, view="REF", timeout=timeout)
                _write_refs(target_eid, getattr(paper, "references", []) or [])
                ref_ok = True
                break
            except _TRANSIENT:
                if attempt < retries - 1:
                    time.sleep(0.5)
            except Exception as exc:  # noqa: BLE001 - reported, not raised
                print(f"[{target_eid}] 获取参考文献失败: {exc}", flush=True)
                break

        query = f'REF("{target_eid}")'
        for attempt in range(retries):
            try:
                first = ScopusSearch(query, start=0, size=page_size, timeout=timeout)
                total = first.get_results_size() or 0
                rows = [(c.eid, c.doi) for c in (first.results or [])]

                pages = (total + page_size - 1) // page_size
                for page in range(1, pages):
                    time.sleep(0.1)
                    more = ScopusSearch(query, start=page * page_size, size=page_size,
                                        timeout=timeout)
                    rows.extend((c.eid, c.doi) for c in (more.results or []))

                with open(directory / "Cits.csv", "w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["EID", "DOI"])
                    writer.writerows(rows)
                cit_ok = True
                break
            except _TRANSIENT:
                if attempt < retries - 1:
                    time.sleep(0.5)
            except Exception as exc:  # noqa: BLE001
                print(f"[{target_eid}] 获取施引文献失败: {exc}", flush=True)
                break

        return target_eid, ref_ok, cit_ok

    succeeded, failed = [], []
    finished = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(worker, eid): eid for eid in pending}
        for future in as_completed(futures):
            target_eid = futures[future]
            finished += 1
            try:
                target_eid, ref_ok, cit_ok = future.result(timeout=600)
            except Exception as exc:  # noqa: BLE001
                print(f"处理 {target_eid} 时发生异常: {exc}", flush=True)
                failed.append(target_eid)
                continue
            if ref_ok and cit_ok:
                succeeded.append(target_eid)
                _append_done(done_file, target_eid, lock)
            else:
                failed.append(target_eid)
            if finished % progress_every == 0 or finished == len(pending):
                print(f"[{finished}/{len(pending)}] 成功 {len(succeeded)}，失败 {len(failed)}",
                      flush=True)

    return succeeded, failed


def process_target(target_eid, out_dir=None, *, retries=3, page_size=200, timeout=60):
    """Collect ``REFs.csv`` and ``Cits.csv`` for a single target EID (stage 1)."""
    succeeded, _ = collect_targets(
        [target_eid], workers=1, out_dir=out_dir, overwrite=True,
        retries=retries, page_size=page_size, timeout=timeout, done_file=None,
    )
    return bool(succeeded)


# -- stage 2 -------------------------------------------------------------
def process_citing_paper(citing_eid, target_eid, out_dir=None, *, retries=3, timeout=60):
    """Fetch the references of one citing paper; returns a status string."""
    from pybliometrics.scopus import AbstractRetrieval

    out_dir = Path(out_dir) if out_dir else paths.data_interim
    destination = out_dir / target_eid / f"{target_eid}'sCitsREF" / f"{citing_eid}'sREFs.csv"
    if destination.exists():
        return "skipped"

    for attempt in range(retries):
        try:
            paper = AbstractRetrieval(citing_eid, view="REF", timeout=timeout)
            if not hasattr(paper, "references"):
                return "done"
            references = paper.references or []
            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(destination, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["EID", "DOI"])
                for reference in references:
                    raw = str(getattr(reference, "id", "")).strip()
                    if not raw:
                        continue
                    eid = raw if raw.startswith("2-s2.0-") else f"2-s2.0-{raw}"
                    writer.writerow([eid, getattr(reference, "doi", "")])
            return "done"
        except _TRANSIENT:
            if attempt < retries - 1:
                time.sleep(0.5)
            else:
                return "failed"
        except Exception:  # noqa: BLE001
            return "failed"
    return "failed"


def collect_citing_references(
    eids,
    *,
    workers=16,
    max_pending=DEFAULT_MAX_PENDING,
    out_dir=None,
    done_file=None,
    failed_file=None,
    overwrite=False,
    retries=3,
    timeout=60,
    progress_every=10,
):
    """Stage 2: expand every citing paper of every target EID.

    Uses a sliding window of at most ``max_pending`` outstanding tasks so memory
    stays flat on the very large expansions (some targets have >3000 citers).
    Returns ``(succeeded, failed)`` lists of target EIDs.
    """
    out_dir = Path(out_dir) if out_dir else paths.data_interim
    done_file = Path(done_file) if done_file else out_dir / "done_c_eids.txt"
    failed_file = Path(failed_file) if failed_file else out_dir / "failed_c_eids.csv"
    lock = threading.Lock()

    done = _read_done_set(done_file) if not overwrite else set()
    todo = [eid for eid in eids if overwrite or eid not in done]
    print(f"共 {len(eids)} 个EID，待处理 {len(todo)} 个（已跳过 {len(done)} 个）", flush=True)

    stats = {eid: {"done": 0, "failed": 0, "skipped": 0} for eid in todo}
    failed_targets = set()

    def tasks():
        for target_eid in todo:
            cits = out_dir / target_eid / "Cits.csv"
            if not cits.exists():
                print(f"警告: {cits} 不存在，跳过 {target_eid}", flush=True)
                continue
            with open(cits, "r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                next(reader, None)
                for row in reader:
                    if not row or not row[0]:
                        continue
                    yield target_eid, row[0]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {}
        iterator = tasks()
        for _ in range(max_pending):
            try:
                target_eid, citing_eid = next(iterator)
            except StopIteration:
                break
            pending[executor.submit(
                process_citing_paper, citing_eid, target_eid, out_dir,
                retries=retries, timeout=timeout,
            )] = (target_eid, citing_eid)

        completed = 0
        start = last_report = time.time()
        while pending:
            finished, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for future in finished:
                target_eid, _citing = pending.pop(future)
                try:
                    status = future.result()
                except Exception:  # noqa: BLE001
                    status = "failed"
                stats[target_eid][status] += 1
                if status == "failed":
                    failed_targets.add(target_eid)
                completed += 1

            now = time.time()
            if now - last_report >= progress_every:
                elapsed = now - start
                speed = completed / elapsed if elapsed else 0.0
                print(f"[进度] {completed} 篇  速度 {speed:.1f} 篇/s", flush=True)
                last_report = now

            while len(pending) < max_pending:
                try:
                    target_eid, citing_eid = next(iterator)
                except StopIteration:
                    break
                pending[executor.submit(
                    process_citing_paper, citing_eid, target_eid, out_dir,
                    retries=retries, timeout=timeout,
                )] = (target_eid, citing_eid)

    succeeded = []
    for target_eid in todo:
        entry = stats[target_eid]
        total = sum(entry.values())
        if total == 0:
            continue
        print(f"  {target_eid}: 共{total}篇, 成功{entry['done']}, "
              f"失败{entry['failed']}, 跳过{entry['skipped']}", flush=True)
        if entry["failed"] == 0:
            succeeded.append(target_eid)
            _append_done(done_file, target_eid, lock)

    if failed_targets:
        failed_file.parent.mkdir(parents=True, exist_ok=True)
        with open(failed_file, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["EID"])
            writer.writerows([[eid] for eid in sorted(failed_targets)])
        print(f"{len(failed_targets)} 个EID有失败，已保存到 {failed_file}", flush=True)

    return succeeded, sorted(failed_targets)
