"""What prose claims about the record, read against the record.

A12 asks three things of a citation, and the steps here resolve them in turn:
the number it names, and then the claim it goes on to make — an Article that
resolves, a quotation that appears where it is attributed, a relation that is
the slot it claims to be, and a line that reads what it is cited for (stereorepo's DR-150).
One module per subject (stereorepo's DR-218); every name is re-exported here, so
`from checks.citations import FOREIGN` resolves as it did.

History in citations.history.md (stereorepo's DR-171).
"""
import checks.citations.loaders  # noqa: I001  # reason: registration order is deliberate
import checks.citations.prose
import checks.citations.record
import checks.citations.claims  # noqa: F401  # reason: registers check steps
from checks.citations import slots as slots
from checks.citations.loaders import DR, FOREIGN, ISSUE, ISSUE_FOREIGN, LEGACY, SCAFFOLD, copied_files, durable, issue_citation
from checks.citations.prose import ARTICLE, BLOCK, CITE, GAP, HEDGED, NEAREST, SAYS, SPAN, comments, entry_text, flat, normalise, prose, scalars
from checks.citations.record import cited_decisions, enacting_citations, inherited_citations
from checks.citations.slots import cited_schema_slots
from checks.citations.claims import (
    ELISION,
    PATH_LINE,
    QUOTED,
    RELATIONS,
    STATED,
    SUBJECT,
    cited_articles,
    cited_discipline_steps,
    path_and_line_claims,
    quoted_claims,
    refused_ordinal_step_citations,
    stated_relations,
)

__all__ = [
    "ARTICLE",
    "BLOCK",
    "CITE",
    "DR",
    "ELISION",
    "FOREIGN",
    "GAP",
    "HEDGED",
    "ISSUE",
    "ISSUE_FOREIGN",
    "LEGACY",
    "NEAREST",
    "PATH_LINE",
    "QUOTED",
    "RELATIONS",
    "SAYS",
    "SCAFFOLD",
    "SPAN",
    "STATED",
    "SUBJECT",
    "cited_articles",
    "cited_decisions",
    "cited_discipline_steps",
    "cited_schema_slots",
    "claims",
    "comments",
    "copied_files",
    "durable",
    "enacting_citations",
    "entry_text",
    "flat",
    "inherited_citations",
    "issue_citation",
    "loaders",
    "normalise",
    "path_and_line_claims",
    "prose",
    "quoted_claims",
    "record",
    "refused_ordinal_step_citations",
    "scalars",
    "slots",
    "stated_relations",
]
"""The module's whole surface, so every importer finds what it did."""
