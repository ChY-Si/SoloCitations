"""Central path definitions for the SoloCitations pipeline.

Every script and module resolves its inputs and outputs through this module, so
the pipeline can be re-run from any working directory.  Defaults follow the
layout of this repository::

    SoloCitations/
      data/raw/         input data exported from Scopus (committed, small)
      data/interim/     generated per-paper citation dumps (large, git-ignored)
      data/processed/   aggregated results (committed, small)
        network/        per-paper SC node lists produced by stage 3
      report/figures/   figures used by the LaTeX report
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "project_root",
    "paths",
    "data_raw",
    "data_interim",
    "data_processed",
    "network_dir",
    "figures_dir",
    "scopus_cfg",
    "ensure_dirs",
    "DEFAULT_SCOPUS_EXPORT",
]


def project_root() -> Path:
    """Return the repository root.

    ``SOLOCITATIONS_ROOT`` overrides the auto-detected location, which is the
    parent of the ``src`` directory this file lives in.
    """
    env = os.environ.get("SOLOCITATIONS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else default


_ROOT = project_root()

#: Input data exported from Scopus.
data_raw = _env_path("SOLOCITATIONS_DATA_RAW", _ROOT / "data" / "raw")

#: Per-paper ``REFs.csv``/``Cits.csv`` dumps and two-level expansions (large).
data_interim = _env_path("SOLOCITATIONS_DATA_INTERIM", _ROOT / "data" / "interim")

#: Aggregated results.
data_processed = _env_path("SOLOCITATIONS_DATA_PROCESSED", _ROOT / "data" / "processed")

#: Per-paper SC node lists built by stage 3.
network_dir = _env_path("SOLOCITATIONS_NETWORK_DIR", data_processed / "network")

#: Figures consumed by the LaTeX report.
figures_dir = _env_path("SOLOCITATIONS_FIGURES_DIR", _ROOT / "report" / "figures")

#: Location of the generated pybliometrics configuration (git-ignored).
scopus_cfg = _env_path("SOLOCITATIONS_SCOPUS_CFG", _ROOT / "config" / "pybliometrics.generated.cfg")

#: The Scopus export that defines the sample of 243 core papers.
DEFAULT_SCOPUS_EXPORT = (
    data_raw / "scopus_export_May 26-2026_1368e081-84f1-42f9-aa2a-c851febd6f38.csv"
)

#: pybliometrics writes its request cache here.
cache_dir = data_interim / "scopus_cache"

paths = {
    "root": _ROOT,
    "data_raw": data_raw,
    "data_interim": data_interim,
    "data_processed": data_processed,
    "network_dir": network_dir,
    "figures_dir": figures_dir,
    "scopus_cfg": scopus_cfg,
}


def ensure_dirs() -> None:
    """Create every directory the pipeline writes into."""
    for directory in (data_raw, data_interim, data_processed, network_dir,
                      figures_dir, scopus_cfg.parent, cache_dir):
        directory.mkdir(parents=True, exist_ok=True)
