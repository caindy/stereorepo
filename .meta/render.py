#!/usr/bin/env python3
"""Compiler facade generating prose satellites, skills, and templates from assertions.

Derives documentation, templates, skills, and configuration artifacts directly
from declarative YAML models under `.meta/assertions/` (stereorepo's DR-026,
stereorepo's DR-059, solorepo's DR-060). Re-exports compilation targets, markdown
formatters, and file writers from `lib.render`.
"""
from lib.render import META, bootstraps, cli, pages, skills, targets, writers
from lib.render.bootstraps import (
    bootstrap_readme,
    bootstrap_table,
    python_readme,
    rust_readme,
)
from lib.render.decisions import decision_form, decisions
from lib.render.pages import (
    charter,
    disciplines,
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
    search_skill,
    technical_writing_skill,
    wikisplain_skill,
)
from lib.render.targets import (
    TARGETS,
    gitattributes,
    rendered,
    snapshot,
    unrendered,
)
from lib.render.writers import apm_primitives, justfile

__all__ = [
    "ASKED",
    "BANNER",
    "COUNT",
    "ENTRY",
    "META",
    "NUMBERS",
    "RECORD",
    "TARGETS",
    "accounted_by",
    "all_artifacts",
    "apm_primitives",
    "artifacts",
    "authored",
    "bootstrap_readme",
    "bootstrap_table",
    "bootstraps",
    "charter",
    "cli",
    "counted",
    "counts",
    "decision_form",
    "decisions",
    "disciplines",
    "gitattributes",
    "justfile",
    "load",
    "pages",
    "prechecks",
    "python_readme",
    "record",
    "rendered",
    "rust_readme",
    "search_skill",
    "skills",
    "snapshot",
    "specialize",
    "targets",
    "technical_writing_skill",
    "unrendered",
    "vocabulary",
    "wikisplain_skill",
    "woven",
    "writers",
]
"""The script's whole surface, so `import render` still finds every name it did: the gate reads
`ASKED`, `rendered` and `unrendered`, and the skills' renderers, through this module's name.

The modules are exported beside the names, so a probe stands a collaborator in at the module that
defines it — except `decisions` and `record`, whose names the surface already holds as functions
and which a probe reaches as `lib.render.decisions` and `lib.render.record`
(stereorepo's DR-217)."""

if __name__ == "__main__":
    cli.main()
