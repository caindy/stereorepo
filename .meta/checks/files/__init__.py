"""Invariants over the tree: what is on disk, and what two files owe each other.

Steps that read the working tree rather than the index — a placeholder that
survived, a link that resolves to nothing, a path that is the scaffold's alone,
a generated page that is behind its assertions or whose framing prose a
portfolio would not inherit, a row added to the Ubiquitous Language with no
reservation behind it, the half the two gate workflows hold equal, and a tool a
composite action guards that the runner image does not install.
One module per family of steps, imported in the order the steps report in
(solorepo's DR-218). `sources.tree()` is the tree as git sees it, which is
the only list of files the gate trusts, and `citations.py` reads prose out of
it (solorepo's DR-150).

History in files.history.md (solorepo's DR-171).
"""
import checks.files.sources  # noqa: I001  # reason: registration order is deliberate
import checks.files.conflicts
import checks.files.templates
import checks.files.markdown
import checks.files.wiki
import checks.files.vocabulary
import checks.files.workflows
import checks.files.control_plane
import checks.files.harness
import checks.files.reviewer
import checks.files.inline_python
import checks.files.arc
import checks.files.justfile
import checks.files.boundary
import checks.files.prose
import checks.files.history
import checks.files.python
import checks.files.rendered  # noqa: F401  # reason: registers check steps
from checks.files.sources import inherited, is_py, meta_sources, template_files, tree
from checks.files.conflicts import CONFLICT_MARKER, conflict_markers
from checks.files.templates import Strict, duplicate_concept_ids, duplicate_keys, surviving_placeholders, template_conventions_agree, template_parses
from checks.files.markdown import FENCED, LINK, markdown_links
from checks.files.wiki import FRONTMATTER, LEAD_COPULA, WIKILINK, ubiquitous_language_wiki_parity, wiki_lead_paragraphs, wiki_synonyms_are_not_avoided, wikilinks
from checks.files.vocabulary import (RESERVATION, VOCABULARIES, added_concepts, concepts_in,
                                     reserved_concepts, vocabulary_mints)
from checks.files.workflows import (NOT_SHARED, REVIEW_WORKFLOW, SCAFFOLD_ONLY, SEED_OWN_JOBS,
                                    SHARED_JOBS, gate_workflows_agree, scaffold_only_paths)
from checks.files.control_plane import (LIB, NUMBER_WORDS, RESTORE_COUNT, RESTORE_LINE,
                                        control_plane_packages, control_plane_restore, scripts_of)
from checks.files.arc import (ACTIONS, BIN_DIRS, DOCKERFILE, GUARD, SEPARATORS, guarded_tools,
                              guarded_tools_installed, installed_commands)
from checks.files.justfile import CONTRACT, FLAGS, IDENTIFIER, INTERPOLATION, JUSTFILE, RECIPE, SUBCOMMAND, justfile_recipe_shape
from checks.files.boundary import CHANNEL, WORKFLOWS, operator_boundary
from checks.files.prose import asserts, declared, inherited_prose, rendering, unread_prose
from checks.files.history import history_entries_of, meta_history_orphans, meta_history_evidence, without_comments
from checks.files.python import CONTINUATION, EDGES, ENTRY_CEILING, ENTRY_LAYER, FILE_SIZES_BASELINE, INTERPRETERS, LINE_LENGTH_RULE, LINES_BASELINE, MODULE_CEILING, MYPY, MYPY_ERROR, RUFF, RUFF_FINDING, TARGET_VERSION, TYPES_BASELINE, UVX_FLAGS, UVX_VALUED, Invocation, ceiling, declared_interpreter, line_counts, meta_doc, meta_file_sizes, meta_interpreter, meta_lines, meta_lints, meta_ruff, meta_types, mypy_errors, past_ceilings, ruff_findings, tool_command, uvx_interpreter_calls
from checks.files.rendered import apm_package, rendered_prose

__all__ = [
    "ACTIONS",
    "BIN_DIRS",
    "CHANNEL",
    "CONFLICT_MARKER",
    "CONTINUATION",
    "CONTRACT",
    "DOCKERFILE",
    "EDGES",
    "ENTRY_CEILING",
    "ENTRY_LAYER",
    "FENCED",
    "FILE_SIZES_BASELINE",
    "FLAGS",
    "FRONTMATTER",
    "GUARD",
    "IDENTIFIER",
    "INTERPOLATION",
    "INTERPRETERS",
    "JUSTFILE",
    "LEAD_COPULA",
    "LIB",
    "LINES_BASELINE",
    "LINE_LENGTH_RULE",
    "LINK",
    "MODULE_CEILING",
    "MYPY",
    "MYPY_ERROR",
    "NOT_SHARED",
    "NUMBER_WORDS",
    "RECIPE",
    "RESERVATION",
    "RESTORE_COUNT",
    "RESTORE_LINE",
    "REVIEW_WORKFLOW",
    "RUFF",
    "RUFF_FINDING",
    "SCAFFOLD_ONLY",
    "SEED_OWN_JOBS",
    "SEPARATORS",
    "SHARED_JOBS",
    "SUBCOMMAND",
    "TARGET_VERSION",
    "TYPES_BASELINE",
    "UVX_FLAGS",
    "UVX_VALUED",
    "VOCABULARIES",
    "WIKILINK",
    "WORKFLOWS",
    "Invocation",
    "Strict",
    "added_concepts",
    "apm_package",
    "arc",
    "asserts",
    "boundary",
    "ceiling",
    "concepts_in",
    "conflict_markers",
    "conflicts",
    "control_plane",
    "control_plane_packages",
    "control_plane_restore",
    "declared",
    "declared_interpreter",
    "duplicate_concept_ids",
    "duplicate_keys",
    "gate_workflows_agree",
    "guarded_tools",
    "guarded_tools_installed",
    "harness",
    "history",
    "history_entries_of",
    "inherited",
    "inherited_prose",
    "inline_python",
    "installed_commands",
    "is_py",
    "justfile",
    "justfile_recipe_shape",
    "line_counts",
    "markdown",
    "markdown_links",
    "meta_doc",
    "meta_file_sizes",
    "meta_history_evidence",
    "meta_history_orphans",
    "meta_interpreter",
    "meta_lines",
    "meta_lints",
    "meta_ruff",
    "meta_sources",
    "meta_types",
    "mypy_errors",
    "operator_boundary",
    "past_ceilings",
    "prose",
    "python",
    "rendered",
    "rendered_prose",
    "rendering",
    "reserved_concepts",
    "reviewer",
    "ruff_findings",
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
    "uvx_interpreter_calls",
    "vocabulary",
    "vocabulary_mints",
    "wiki",
    "wiki_lead_paragraphs",
    "wiki_synonyms_are_not_avoided",
    "wikilinks",
    "without_comments",
    "workflows",
]
"""The module's whole surface, so `from checks import files` and `from checks.files import tree` find what they did."""
