"""Import shim for the scripts in ``scripts/``.

Importing this module makes ``import solo_citations`` work when the scripts are
run straight from a checkout, without installing the package first.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

__all__ = ["SRC_DIR"]

SRC_DIR = _SRC
