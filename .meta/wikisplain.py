#!/usr/bin/env python3
"""Operational authoring tool for Knowledge Management wiki concepts (solorepo's DR-187).

This tool provides a deterministic workflow for checking duplicates, scaffolding,
and verifying maintainer-facing wiki concept pages under `wiki/<context>/<slug>.md`
following Wikipedia editorial conventions (MOS:LEAD bold lead definitions,
closed-world wikilinks, and Bounded Context partitioning).

History in wikisplain.history.md (solorepo's DR-171).
"""

from __future__ import annotations

import pathlib
import sys

try:
    import yaml  # noqa: F401  # reason: the import is the test of whether PyYAML is installed
except ImportError:
    import subprocess
    cmd = ["uvx", "--python", "3.13", "--with", "pyyaml", "python",
           str(pathlib.Path(__file__).resolve()), *sys.argv[1:]]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

from lib.wikisplain import cli
from lib.wikisplain.cli import main
from lib.wikisplain.duplicates import avoided_synonyms, find_duplicates
from lib.wikisplain.lead import LEAD_COPULA, format_lead_sentence, slugify
from lib.wikisplain.links import (
    FENCED_RE,
    WIKILINK_RE,
    embed_wikilinks,
    extract_known_concepts,
)
from lib.wikisplain.pages import Page, generate_page, verify_page

__all__ = [
    "FENCED_RE",
    "LEAD_COPULA",
    "WIKILINK_RE",
    "Page",
    "avoided_synonyms",
    "cli",
    "embed_wikilinks",
    "extract_known_concepts",
    "find_duplicates",
    "format_lead_sentence",
    "generate_page",
    "main",
    "slugify",
    "verify_page",
]
"""The script's whole surface, so `wikisplain probes` in `.meta/checks/probes/knowledge.py`, which loads
this file by path, finds `avoided_synonyms`, `find_duplicates`, `format_lead_sentence`, `generate_page`,
`slugify` and `verify_page` where it did."""

if __name__ == "__main__":
    sys.exit(cli.main())
