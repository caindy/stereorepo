"""Invariants over the tree: what is on disk, and what two files owe each other.

Steps that read the working tree rather than the index — a placeholder that
survived, a link that resolves to nothing, a path that is the scaffold's alone,
a generated page that is behind its assertions or whose framing prose a
portfolio would not inherit, and the half the two gate workflows hold equal.
One module per family of steps, imported in the order the steps report in
(solorepo's DR-218). `sources.tree()` is the tree as git sees it, which is
the only list of files the gate trusts, and `citations.py` reads prose out of
it (solorepo's DR-150).

History in files.history.md (solorepo's DR-171).
"""
import files.sources  # noqa: I001  # reason: registration order is deliberate
import files.templates
import files.markdown
import files.wiki
import files.workflows
import files.prose
import files.history
import files.python
import files.rendered  # noqa: F401  # reason: registers check steps
from files.sources import inherited, is_py, meta_sources, template_files, tree
from files.templates import Strict, duplicate_keys, surviving_placeholders, template_conventions_agree, template_parses
from files.markdown import FENCED, LINK, markdown_links
from files.wiki import LEAD_COPULA, WIKILINK, ubiquitous_language_wiki_parity, wiki_lead_paragraphs, wikilinks
from files.workflows import LIB, NOT_SHARED, NUMBER_WORDS, RESTORE_COUNT, RESTORE_LINE, RESTORE_PROSE, REVIEW_WORKFLOW, SCAFFOLD_ONLY, SEED_OWN_JOBS, SHARED_JOBS, control_plane_packages, control_plane_restore, gate_workflows_agree, scaffold_only_paths, scripts_of
from files.prose import asserts, declared, inherited_prose, rendering, unread_prose
from files.history import history_entries_of, meta_history_orphans, meta_history_receipts, without_comments
from files.python import MYPY, MYPY_ERROR, RUFF, TYPES_BASELINE, meta_doc, meta_lints, meta_ruff, meta_types, mypy_errors, tool_command
from files.rendered import apm_package, rendered_prose

__all__ = [
    "FENCED",
    "LEAD_COPULA",
    "LIB",
    "LINK",
    "MYPY",
    "MYPY_ERROR",
    "NOT_SHARED",
    "NUMBER_WORDS",
    "RESTORE_COUNT",
    "RESTORE_LINE",
    "RESTORE_PROSE",
    "REVIEW_WORKFLOW",
    "RUFF",
    "SCAFFOLD_ONLY",
    "SEED_OWN_JOBS",
    "SHARED_JOBS",
    "TYPES_BASELINE",
    "WIKILINK",
    "Strict",
    "apm_package",
    "asserts",
    "control_plane_packages",
    "control_plane_restore",
    "declared",
    "duplicate_keys",
    "gate_workflows_agree",
    "history",
    "history_entries_of",
    "inherited",
    "inherited_prose",
    "is_py",
    "markdown",
    "markdown_links",
    "meta_doc",
    "meta_history_orphans",
    "meta_history_receipts",
    "meta_lints",
    "meta_ruff",
    "meta_sources",
    "meta_types",
    "mypy_errors",
    "prose",
    "python",
    "rendered",
    "rendered_prose",
    "rendering",
    "scaffold_only_paths",
    "scripts_of",
    "sources",
    "surviving_placeholders",
    "template_conventions_agree",
    "template_files",
    "template_parses",
    "templates",
    "tool_command",
    "tree",
    "ubiquitous_language_wiki_parity",
    "unread_prose",
    "wiki",
    "wiki_lead_paragraphs",
    "wikilinks",
    "without_comments",
    "workflows",
]
"""The module's whole surface, so `import files` and `from files import tree` find what they did."""
