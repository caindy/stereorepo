"""Invariants over the assertion graph, and the Decision record's arithmetic.

What the schemas state and LinkML cannot check: a reference that resolves to
nothing, a cycle a path cannot traverse, a membership that crosses a file
boundary, and the three counts over the Decision record that a rule cannot make
(solorepo's DR-150). One module per subject, imported in the order the steps
report in (solorepo's DR-218). History in graph.history.md (solorepo's DR-171).
"""
import checks.graph.structure  # noqa: I001  # reason: registration order is deliberate
import checks.graph.record
import checks.graph.artifacts  # noqa: F401  # reason: registers check steps
from checks.graph.structure import audit_invariants, collaboration_membership, composed_of_cycles, hop, one_context_per_portfolio, served_goals, unresolved_references
from checks.graph.record import DELETION, OPTIONS_REQUIRED_FROM, RESERVATION, decision_alternatives, decision_level, decision_numbering, decision_supersession, deleted_decision_numbers, reserved_decision_numbers, withdrawn_decisions
from checks.graph.artifacts import RECORD, artifact_paths, enacted_decisions, reserved_article_numbers

__all__ = [
    "DELETION",
    "OPTIONS_REQUIRED_FROM",
    "RECORD",
    "RESERVATION",
    "artifact_paths",
    "artifacts",
    "audit_invariants",
    "collaboration_membership",
    "composed_of_cycles",
    "decision_alternatives",
    "decision_level",
    "decision_numbering",
    "decision_supersession",
    "deleted_decision_numbers",
    "enacted_decisions",
    "hop",
    "one_context_per_portfolio",
    "record",
    "reserved_article_numbers",
    "reserved_decision_numbers",
    "served_goals",
    "structure",
    "unresolved_references",
    "withdrawn_decisions",
]
"""The module's whole surface, so `graph.decision_numbering` and the rest resolve as they did."""
