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
import checks.files.sources  # noqa: I001  # reason: registration order is deliberate
import checks.files.templates
import checks.files.markdown
import checks.files.wiki
import checks.files.workflows
import checks.files.justfile
import checks.files.prose
import checks.files.history
import checks.files.python
import checks.files.rendered  # noqa: F401  # reason: registers check steps
from checks.files.sources import inherited, is_py, meta_sources, template_files, tree
from checks.files.templates import Strict, duplicate_concept_ids, duplicate_keys, surviving_placeholders, template_conventions_agree, template_parses
from checks.files.markdown import FENCED, LINK, markdown_links
from checks.files.wiki import FRONTMATTER, LEAD_COPULA, WIKILINK, ubiquitous_language_wiki_parity, wiki_lead_paragraphs, wiki_synonyms_are_not_avoided, wikilinks
from checks.files.workflows import LIB, NOT_SHARED, NUMBER_WORDS, RESTORE_COUNT, RESTORE_LINE, RESTORE_PROSE, REVIEW_WORKFLOW, SCAFFOLD_ONLY, SEED_OWN_JOBS, SHARED_JOBS, control_plane_packages, control_plane_restore, gate_workflows_agree, scaffold_only_paths, scripts_of
from checks.files.justfile import CONTRACT, FLAGS, IDENTIFIER, INTERPOLATION, JUSTFILE, RECIPE, SUBCOMMAND, justfile_recipe_shape
from checks.files.prose import asserts, declared, inherited_prose, rendering, unread_prose
from checks.files.history import history_entries_of, meta_history_orphans, meta_history_evidence, without_comments
from checks.files.python import MYPY, MYPY_ERROR, RUFF, TYPES_BASELINE, meta_doc, meta_lints, meta_ruff, meta_types, mypy_errors, tool_command
from checks.files.rendered import apm_package, rendered_prose

__all__ = [
    "CONTRACT",
    "FENCED",
    "FLAGS",
    "FRONTMATTER",
    "IDENTIFIER",
    "INTERPOLATION",
    "JUSTFILE",
    "LEAD_COPULA",
    "LIB",
    "LINK",
    "MYPY",
    "MYPY_ERROR",
    "NOT_SHARED",
    "NUMBER_WORDS",
    "RECIPE",
    "RESTORE_COUNT",
    "RESTORE_LINE",
    "RESTORE_PROSE",
    "REVIEW_WORKFLOW",
    "RUFF",
    "SCAFFOLD_ONLY",
    "SEED_OWN_JOBS",
    "SHARED_JOBS",
    "SUBCOMMAND",
    "TYPES_BASELINE",
    "WIKILINK",
    "Strict",
    "apm_package",
    "asserts",
    "control_plane_packages",
    "control_plane_restore",
    "declared",
    "duplicate_concept_ids",
    "duplicate_keys",
    "gate_workflows_agree",
    "history",
    "history_entries_of",
    "inherited",
    "inherited_prose",
    "is_py",
    "justfile",
    "justfile_recipe_shape",
    "markdown",
    "markdown_links",
    "meta_doc",
    "meta_history_evidence",
    "meta_history_orphans",
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
    "wiki_synonyms_are_not_avoided",
    "wikilinks",
    "without_comments",
    "workflows",
]
"""The module's whole surface, so `from checks import files` and `from checks.files import tree` find what they did."""
