#!/usr/bin/env python3
"""Retrieval over the repository assertions, decisions, and wiki by meaning (solorepo's DR-103, solorepo's DR-192, solorepo's DR-194, solorepo's DR-195).

Provides an in-memory Okapi BM25 search index over all identified objects
declared in .meta/assertions/*.yaml and concepts defined in wiki/**/*.md.
Enables agents and the solo to find relevant decisions, articles, disciplines,
and roles using natural language queries without relying on exact substring grep.

Usage:
    python3 .meta/search.py "<query>" [--limit N] [--detail] [--json]
    python3 .meta/search.py --benchmark
"""

from lib.search import META, ROOT, cli
from lib.search.benchmark import run_benchmark
from lib.search.bm25 import SearchIndex, SearchResult, extract_strings, tokenize
from lib.search.build import build_index
from lib.search.cli import main

__all__ = [
    "META",
    "ROOT",
    "SearchIndex",
    "SearchResult",
    "build_index",
    "cli",
    "extract_strings",
    "main",
    "run_benchmark",
    "tokenize",
]
"""The script's whole surface, so `search probes` in `.meta/checks/probes/tools/search.py`, which
loads this file by path, finds `build_index` and `run_benchmark` where it did."""

if __name__ == "__main__":
    cli.main()
