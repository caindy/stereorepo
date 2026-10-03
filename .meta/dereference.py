#!/usr/bin/env -S uvx --python 3.13 --with linkml --with pyyaml python
"""The reading of a citation, run before the hand-off (stereorepo's DR-332, DR-336).

    just dereference                 what this branch wrote or affected, against origin/main
    just dereference --sample        a rotating sample of 20 citations from the durable set
    just dereference --all           every citation in the durable set: uncapped,
                                     and about fifteen hundred questions
    .meta/dereference.py --pairs     the deterministic half alone, asking nothing

A12 asks that a citation carry the claim it names. stereorepo's DR-331 checked the
four shapes of that claim a string search reaches and said the rest was a
reading and nobody's check; this is the rest, and it is somebody's — whoever
wrote the citation's, with the second seat still behind it. Each pair is a
sentence that cites an entry and the entry itself, and the question asked of
each is the one a careful reader asks: does the target support this sentence,
and which of its words say so.

**Not a gate.** It prints A21's three marks because that is the shape a reader
here reads, and it is in no Project's `gate` string. A gate's red is a fact a
re-run cannot overturn; this one's is a model's reading, which the same input
can answer differently, and stereorepo's DR-332 says why that may not be where a
landing is decided. Its `x` is a finding the author answers — by fixing the
sentence, or by leaving it and saying why — and nothing requires the step. The
`x` report closes by saying that much, because a reader who does not know it
re-runs until the finding clears.

What it reads, and what it leaves alone. The durable set, the shape of a
citation and the entry a citation names are `check.py`'s, imported rather than
written again: two extractors would drift about what a citation is
(stereorepo's DR-332). What is this file's own is the unit — a sentence,
because that is what a reader reads and what a claim is made in, where
`check.py` needs a whole file flattened to one string. A citation of an Issue
is left out, because every paraphrase failure this was built for named an
entry.

The scope is the diff and the ground that moved. About fifteen hundred citations
stand in the durable set, and reading them all is a bill nobody wants twice a
day; what anyone wants read is what this branch wrote, plus any existing
citation whose target entry moved under it (stereorepo's DR-336). `--sample` offers
a deterministic rotating window across the durable set without adding an
external state file, and `--all` is there for the run that wants the record.

History in dereference.history.md (stereorepo's DR-171).
"""

import sys

from lib.dereference import META, ROOT, cli
from lib.dereference.asking import MODEL, QUESTION, ask, available
from lib.dereference.cli import main
from lib.dereference.reading import (
    CHECKS,
    CONTEXT,
    ITEM,
    MANY,
    SENTENCE,
    articles,
    as_it_was,
    citations,
    git,
    scope,
    sentences,
    spans,
    target,
)
from lib.dereference.report import report

__all__ = [
    "CHECKS",
    "CONTEXT",
    "ITEM",
    "MANY",
    "META",
    "MODEL",
    "QUESTION",
    "ROOT",
    "SENTENCE",
    "articles",
    "as_it_was",
    "ask",
    "available",
    "citations",
    "cli",
    "git",
    "main",
    "report",
    "scope",
    "sentences",
    "spans",
    "target",
]
"""The script's whole surface, so the probes that load it by path find `citations`, `scope` and
`report` where they did."""

if __name__ == "__main__":
    sys.exit(cli.main())
