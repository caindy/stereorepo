#!/usr/bin/env python3
"""Information retrieval facade indexing repository assertions, decisions, and wiki concepts.

Constructs and queries an in-memory Okapi BM25 ranking index over YAML assertions
under `.meta/assertions/` and markdown concept pages under `wiki/` (stereorepo's DR-103,
stereorepo's DR-192, stereorepo's DR-194, stereorepo's DR-195). Re-exports search index
classes, tokenizers, and CLI dispatchers from `lib.search`.
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
