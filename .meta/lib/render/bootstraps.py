"""Generates per-language standard conformance tables and bootstrap README documents.
"""

from __future__ import annotations

from typing import Any

from lib.render import META, record

NO_BOOTSTRAP = "no bootstrap asserted for {bootstrap}"
"""Message raised when requested bootstrap identifier is not found in assertions."""


def bootstrap_table(bootstrap: str | dict[str, Any], lang: str | None = None) -> str:
    """Renders the markdown conformance table for a language bootstrap.

    Parameters:
        bootstrap: The bootstrap entity mapping or its identifier CURIE.
        lang: Target programming language name (e.g. 'Python', 'Rust').
            Derived from bootstrap identifier when omitted.

    Returns:
        str: GitHub-flavored markdown conformance table.

    Raises:
        LookupError: If the bootstrap identifier does not resolve in assertions.
    """
    entry: dict[str, Any]
    if isinstance(bootstrap, str):
        data = record.load("assertions/bootstraps.yaml") or {}
        found = next((b for b in data.get("bootstraps") or [] if b.get("id") == bootstrap), None)
        if found is None:
            raise LookupError(NO_BOOTSTRAP.format(bootstrap=bootstrap))
        entry = found
    else:
        entry = bootstrap

    if lang is None:
        lang = str(entry.get("id", "")).rsplit("/", 1)[-1].capitalize()

    disciplines: dict[str, str] = {}
    for rel in ("assertions/disciplines.yaml", "assertions/imported/disciplines.yaml"):
        for d in (record.load(rel) or {}).get("disciplines") or []:
            disciplines[d["id"]] = d["name"]

    b_dir = META.parent / "bootstraps" / lang.lower()
    lines = [f"| Discipline | How, in {lang} | Held by |", "|---|---|---|"]
    for impl in entry.get("discipline_implementations") or []:
        d_name = disciplines.get(impl["discipline"], impl["discipline"])
        expo = impl.get("exposition", "")
        expo_cell = f"[`{expo}`]({expo})" if expo else "—"
        if impl.get("status") == "exempt":
            held_cell = "nothing here — the portfolio's gate, and it says why"
        else:
            held_items: list[str] = []
            for h in impl.get("held_by") or []:
                if (b_dir / h).exists():
                    held_items.append(f"[`{h}`]({h})")
                else:
                    held_items.append(f"`{h}`")
            held_cell = ", ".join(held_items) if held_items else "—"
        lines.append(f"| {d_name} | {expo_cell} | {held_cell} |")
    return "\n".join(lines)


def bootstrap_readme(lang: str) -> str:
    """Renders a language bootstrap README from assertions.

    Parameters:
        lang: Programming language name (e.g. 'Python', 'Rust').

    Returns:
        str: Rendered markdown document for the bootstrap README.

    Raises:
        LookupError: If the bootstrap is not declared in assertions.
    """
    target = f"../bootstraps/{lang.lower()}/README.md"
    data = record.load("assertions/bootstraps.yaml") or {}
    bootstrap_id = f"work:bootstrap/{lang.lower()}"
    bootstrap = next((b for b in data.get("bootstraps") or [] if b.get("id") == bootstrap_id), None)
    if bootstrap is None:
        raise LookupError(NO_BOOTSTRAP.format(bootstrap=bootstrap_id))

    table = bootstrap_table(bootstrap, lang)
    out = [
        record.BANNER.format(src="assertions/bootstraps.yaml"),
        record.authored(target, "preamble"),
        table + "\n",
        record.authored(target, "postamble"),
    ]
    return "\n".join(out)


def python_readme() -> str:
    """Renders bootstraps/python/README.md from assertions.

    Returns:
        str: Rendered markdown content for bootstraps/python/README.md.
    """
    return bootstrap_readme("Python")


def rust_readme() -> str:
    """Renders bootstraps/rust/README.md from assertions.

    Returns:
        str: Rendered markdown content for bootstraps/rust/README.md.
    """
    return bootstrap_readme("Rust")
