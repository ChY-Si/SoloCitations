"""Scopus API access helpers.

API keys are **never** stored in the repository.  They are read, in order of
precedence, from

1. the ``SCOPUS_API_KEYS`` environment variable (comma or whitespace separated),
2. the file ``config/scopus_keys.txt`` (git-ignored), one key per line.

This module then writes a throw-away ``pybliometrics`` configuration file that
points the request cache at ``data/interim/scopus_cache`` and initialises the
library.  Call :func:`init` once per process before issuing any request.

Multiple keys are rotated by pybliometrics itself; the value written to the
configuration is what pybliometrics expects, ``API_KEYS = <k1>,<k2>,...``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import paths

__all__ = ["load_keys", "write_config", "init", "has_keys", "KEY_FILE"]

#: Optional key file outside version control.
KEY_FILE = paths.project_root() / "config" / "scopus_keys.txt"

_SPLIT = re.compile(r"[,;\s]+")

_CONFIG_HEADER = """\
; GENERATED FILE - do not edit, do not commit.
; Produced by solo_citations.scopus.write_config().
; Secrets live in the SCOPUS_API_KEYS environment variable or in
; config/scopus_keys.txt, never in this repository.

"""

_TEMPLATE = """\
[Directories]
AbstractRetrieval = {cache}/Scopus/abstract_retrieval
AffiliationRetrieval = {cache}/Scopus/affiliation_retrieval
AffiliationSearch = {cache}/Scopus/affiliation_search
AuthorRetrieval = {cache}/Scopus/author_retrieval
AuthorSearch = {cache}/Scopus/author_search
CitationOverview = {cache}/Scopus/citation_overview
ScopusSearch = {cache}/Scopus/scopus_search
SerialTitleSearch = {cache}/Scopus/serial_search
SerialTitleISSN = {cache}/Scopus/serial_title
PlumXMetrics = {cache}/Scopus/plumx
SubjectClassifications = {cache}/Scopus/subject_classification
ArticleEntitlement = {cache}/ScienceDirect/article_entitlement
ArticleMetadata = {cache}/ScienceDirect/article_metadata
ArticleRetrieval = {cache}/ScienceDirect/article_retrieval
NonserialTitle = {cache}/ScienceDirect/nonserial_title
ObjectMetadata = {cache}/ScienceDirect/object_metadata
ObjectRetrieval = {cache}/ScienceDirect/object_retrieval
PublicationLookup = {cache}/Scival/publication_lookup
AuthorMetrics = {cache}/Scival/author_metrics
InstitutionLookupMetrics = {cache}/Scival/institution_metrics
TopicLookupMetrics = {cache}/Scival/topic_metrics
ScDirSubjectClassifications = {cache}/ScienceDirect/subject_classification
ScienceDirectSearch = {cache}/ScienceDirect/science_direct_search

[Authentication]
APIKey = API_KEYS = {keys}
InstToken = {inst_token}

[Requests]
Timeout = {timeout}
Retries = {retries}
"""


def load_keys() -> list[str]:
    """Return the configured Scopus API keys, without duplicates."""
    raw = os.environ.get("SCOPUS_API_KEYS", "")
    if not raw and KEY_FILE.exists():
        raw = KEY_FILE.read_text(encoding="utf-8")
        # Drop comments and blank lines.
        raw = "\n".join(
            line for line in raw.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    seen: dict[str, None] = {}
    for key in _SPLIT.split(raw.strip()):
        key = key.strip()
        if len(key) == 32 and key not in seen:
            seen[key] = None
    return list(seen)


def has_keys() -> bool:
    """True when at least one usable API key is available."""
    return bool(load_keys())


def write_config(
    cfg_path: Path | str | None = None,
    *,
    timeout: int = 60,
    retries: int = 5,
) -> Path:
    """Write the generated pybliometrics configuration and return its path."""
    keys = load_keys()
    if not keys:
        raise RuntimeError(
            "No Scopus API key found.\n"
            "Set the SCOPUS_API_KEYS environment variable, or create "
            f"{KEY_FILE} with one key per line.\n"
            "See config/scopus_keys.example.txt."
        )
    destination = Path(cfg_path) if cfg_path else paths.scopus_cfg
    destination.parent.mkdir(parents=True, exist_ok=True)
    cache = str(paths.cache_dir).replace("\\", "/")
    destination.write_text(
        _CONFIG_HEADER
        + _TEMPLATE.format(
            cache=cache,
            keys=",".join(keys),
            inst_token=os.environ.get("SCOPUS_INST_TOKEN", ""),
            timeout=timeout,
            retries=retries,
        ),
        encoding="utf-8",
    )
    return destination


def init(cfg_path: Path | str | None = None) -> Path:
    """Write the configuration and initialise pybliometrics. Returns its path."""
    import pybliometrics

    destination = write_config(cfg_path)
    pybliometrics.scopus.init(config_path=str(destination))
    return destination
