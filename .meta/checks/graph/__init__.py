"""Invariants over the assertion graph, and the Decision record's arithmetic.

What the schemas state and LinkML cannot check: a reference that resolves to
nothing, a cycle a path cannot traverse, a membership that crosses a file
boundary, and the three counts over the Decision record that a rule cannot make
(stereorepo's DR-150). One module per subject, imported in the order the steps
report in (stereorepo's DR-345). History in graph.history.md (stereorepo's DR-171).
"""
import checks.graph.structure  # noqa: I001  # reason: registration order is deliberate
import checks.graph.record
import checks.graph.artifacts  # noqa: F401  # reason: registers check steps
from checks.graph.structure import (
    PROJECT_BINDING_DISCIPLINES,
    bootstrap_discipline_coverage,
    composed_of_cycles,
    one_context_per_portfolio,
    served_goals,
    unresolved_references,
)
from checks.graph.record import OPTIONS_REQUIRED_FROM, SCAFFOLD, SEEDED_BELOW, decision_alternatives, decision_level, decision_numbering, decision_supersession, withdrawn_decisions
from checks.graph.artifacts import (
    OPERATIONAL_GLOBS,
    RECORD,
    artifact_paths,
    enacted_decisions,
    is_path_excluded,
    load_excluded_paths,
    operational_artifacts,
    reserved_article_numbers,
)

__all__ = [
    "OPERATIONAL_GLOBS",
    "OPTIONS_REQUIRED_FROM",
    "PROJECT_BINDING_DISCIPLINES",
    "RECORD",
    "SCAFFOLD",
    "SEEDED_BELOW",
    "artifact_paths",
    "artifacts",
    "bootstrap_discipline_coverage",
    "composed_of_cycles",
    "decision_alternatives",
    "decision_level",
    "decision_numbering",
    "decision_supersession",
    "enacted_decisions",
    "is_path_excluded",
    "load_excluded_paths",
    "one_context_per_portfolio",
    "operational_artifacts",
    "record",
    "reserved_article_numbers",
    "served_goals",
    "structure",
    "unresolved_references",
    "withdrawn_decisions",
]
"""The module's whole surface, so `graph.decision_numbering` and the rest resolve as they did."""
