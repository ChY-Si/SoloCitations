"""Solo-citation analysis of laser inertial confinement fusion energy literature.

Package layout
--------------
``paths``            every input/output location used by the pipeline
``scopus``           API-key handling and pybliometrics initialisation
``collect``          stages 1-2: citation relations fetched from the Scopus API
``network``          stages 3-4: three-layer network, SC flag, SC aggregation
``citation_ratio``   per-year ``R_SC`` statistics and the trend figure
``figures``          the two bibliometric overview figures of the report

The command-line entry points live in ``scripts/`` and stay importable both as
``python scripts/<name>.py`` and as ``python -m scripts.<name>``.
"""

__version__ = "1.0.0"
