#!/usr/bin/env python3
"""Render the prose satellites from the assertions they describe.

`disciplines.md` and `vocabulary.md` list things that `.meta/assertions/` already
holds. Maintaining both by hand is the drift these Disciplines exist to prevent,
so the prose derives and the assertions are the source (solorepo's DR-026). The decision
record joined them once it too was assertions (solorepo's DR-059), and PR First compiles the
same way into a skill (solorepo's DR-060).

    uvx --with pyyaml python .meta/render.py           # write
    uvx --with pyyaml python .meta/render.py --check   # fail if stale
    uvx --with pyyaml python .meta/render.py --landed 11   # what a Challenge got

Definitions in the vocabulary are one-line glosses. The full reasoning stays on
the class, per Literate Programming; these are for recognising a term, not for
applying it.
"""
from lib.render import META, cli
from lib.render.decisions import decision_form, decisions, landed
from lib.render.pages import (
    charter,
    disciplines,
    form,
    issue_template,
    pull_request_template,
    roadmap_template,
    specialize,
    vocabulary,
)
from lib.render.record import (
    ASKED,
    BANNER,
    COUNT,
    ENTRY,
    NUMBERS,
    RECORD,
    accounted_by,
    all_artifacts,
    artifacts,
    authored,
    counted,
    counts,
    load,
    prechecks,
    record,
    woven,
)
from lib.render.skills import (
    BODY,
    DEREFERENCE,
    READING,
    channel,
    pr_first_reviewer_skill,
    pr_first_skill,
    skill,
    technical_writing_skill,
    verb_line,
    wikisplain_skill,
)
from lib.render.targets import TARGETS, gitattributes, rendered, unrendered
from lib.render.writers import apm_primitives, justfile

__all__ = [
    "ASKED",
    "BANNER",
    "BODY",
    "COUNT",
    "DEREFERENCE",
    "ENTRY",
    "META",
    "NUMBERS",
    "READING",
    "RECORD",
    "TARGETS",
    "accounted_by",
    "all_artifacts",
    "apm_primitives",
    "artifacts",
    "authored",
    "channel",
    "charter",
    "cli",
    "counted",
    "counts",
    "decision_form",
    "decisions",
    "disciplines",
    "form",
    "gitattributes",
    "issue_template",
    "justfile",
    "landed",
    "load",
    "pr_first_reviewer_skill",
    "pr_first_skill",
    "prechecks",
    "pull_request_template",
    "record",
    "rendered",
    "roadmap_template",
    "skill",
    "specialize",
    "technical_writing_skill",
    "unrendered",
    "verb_line",
    "vocabulary",
    "wikisplain_skill",
    "woven",
]
"""The script's whole surface, so `import render` still finds every name it did: the gate reads
`ASKED`, `rendered` and `unrendered`, and the skills' renderers, through this module's name."""

if __name__ == "__main__":
    cli.main()
