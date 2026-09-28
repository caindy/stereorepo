"""The lead sentence of a concept page: its slug, and the bold definition that opens it with a copula (MOS:LEAD).
"""
from __future__ import annotations

import re

LEAD_COPULA = re.compile(
    r"^\*\*(?:`(?P<backticked>[^`]+)`|(?P<plain>[^*]+))\*\*\s+"
    r"(?P<copula>is|are|was|were|refers to|serves as|organizes|provides|names|represents)\b",
    re.IGNORECASE,
)


def slugify(text: str) -> str:
    """Convert a title or concept string into a canonical lowercase slug (stereorepo's DR-187)."""
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[_\s]+", "-", cleaned)
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned.strip("-")


def format_lead_sentence(title: str, definition: str) -> str:
    """Format a MOS:LEAD compliant bold copular lead sentence for a concept (stereorepo's DR-187).

    The definition supplies its own copula where it opens with one — `is`,
    `are`, `refers to` and the rest — and is given `is` where it does not, so
    the lead reads as one sentence either way. An empty definition is led with
    a placeholder rather than left bare.
    """
    title_clean = title.strip()
    def_clean = definition.strip()

    if not def_clean:
        def_clean = "a concept within maintainer exposition"

    match = re.match(
        r"^(?:is|are|was|were|refers to|serves as|organizes|provides|names|represents)\b\s*",
        def_clean,
        re.IGNORECASE,
    )
    copula_body = def_clean if match else f"is {def_clean}"

    if not copula_body.endswith("."):
        copula_body = copula_body + "."

    return f"**{title_clean}** {copula_body}"
