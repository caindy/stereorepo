"""The prose a render frames a page with: what a portfolio inherits and what it would never read, read off the render the gate builds once.
"""
import functools
import sys
from collections.abc import Collection
from typing import Any

import yaml

from checks.collect import (
    META,
    check,
)
from checks.files import scaffold


@functools.cache
def rendering() -> tuple[Any, Any, Any]:
    """The render the three steps below read, run once and shared between them.

    `render.ASKED` is filled as the render runs, so what `inherited prose`
    reads exists only after it. Both steps name a source off this rather than
    rendering for themselves, so the gate builds the pages once and the two
    agree about which render they are describing.
    """
    sys.path.insert(0, str(META))
    import render
    snap = render.snapshot()
    return render, render.rendered(snap), snap


def declared(rel: str) -> dict[str, dict[str, Any]]:
    """The Artifacts one assertion file holds, by path."""
    path = META / "assertions" / rel
    data = (yaml.safe_load(path.read_text()) if path.is_file() else None) or {}
    return {a["path"]: a for a in data.get("artifacts") or []}


def asserts(entry: dict[str, Any] | None, slot: str, block: str) -> bool:
    """Whether this entry carries that prose: the slot, or the named block in it."""
    if not entry or not entry.get(slot):
        return False
    if not block:
        return True
    return any(p.get("name") == block for p in entry[slot])


@check("inherited prose")
def inherited_prose(asked: Collection[tuple[str, str, str]]) -> list[str]:
    """Prose a generator reads is asserted where Specialization copies it.

    `Artifact.preamble` moved the framing prose of the generated pages out of
    `render.py` (stereorepo's DR-144). `assertions/structure.yaml` is the wrong
    home for it: its own first line says the file is the portfolio's and never
    synced, and step three of Specialization replaces it with `template/`'s,
    which declares one Artifact. The renderer is inherited and would then ask
    every portfolio for prose nothing asserts — a portfolio red on its first
    render, found by nothing here, because the scaffold's own copy has the
    entries.

    `asked` is what a render actually asked for, collected by `authored()` as
    it ran. Not the slots by name: a slot named here that no generator reads
    would fail an Artifact for prose nothing wants, and `description` is
    `WorkEntity`'s, carried by most of what `assertions/` declares as plain
    documentation. Not a list typed beside the call sites either, which would
    be the second copy this change exists to remove.

    `SPECIALIZE.md` is the exception the copy set already names: a portfolio
    specializes nothing and renders no such page, so its prose is the
    scaffold's own and stays one level up.
    """
    own = declared("structure.yaml")
    return [f"{own[rel]['id']} asserts the "
            f"{f'{slot} block {block!r}' if block else slot} render.py reads for "
            f"{rel}, which a portfolio renders, in the file Specialization "
            f"replaces — move it to assertions/imported/structure.yaml"
            for rel, slot, block in sorted(asked)
            if asserts(own.get(rel), slot, block) and not rel.startswith(scaffold.SCAFFOLD_ONLY)]


@check("unread prose")
def unread_prose(asked: Collection[tuple[str, str, str]]) -> list[str]:
    """Prose asserted that no render asks for (stereorepo's DR-152).

    A8's other half, for the prose stereorepo's DR-144 and stereorepo's DR-152 moved
    out of `render.py`.
    `inherited prose` holds where a block is asserted; this holds whether
    anything reads it at all. Without it, a generator that stops reading a block
    — renamed, reworded into the derived part, dropped with the section it
    framed — leaves the block behind in the assertions, saying something about a
    page that no longer says it. That residue is invisible: the page still
    renders, the byte-compare still passes, and the only reader left is whoever
    opens the assertion and believes it.

    Only the three slots minted to be read by a generator, and never
    `description`: that one is `WorkEntity`'s, and most of what `assertions/`
    declares carries one as documentation for a reader rather than for a render.
    """
    entries: list[dict[str, Any]] = []
    for rel in ("imported/structure.yaml", "structure.yaml"):
        entries.extend(declared(rel).values())
    for rel in ("imported/disciplines.yaml", "disciplines.yaml"):
        path = META / "assertions" / rel
        data = (yaml.safe_load(path.read_text()) if path.is_file() else None) or {}
        entries.extend(data.get("disciplines") or [])
    problems: list[str] = []
    for entry in entries:
        host = entry.get("path") or entry.get("id")
        for slot in ("preamble", "postamble"):
            if entry.get(slot) and (host, slot, "") not in asked:
                problems.append(f"{entry['id']} asserts a {slot} no render asks for")
        for prose in entry.get("woven") or []:
            if (host, "woven", prose["name"]) not in asked:
                problems.append(f"{entry['id']} asserts a woven block named "
                                f"{prose['name']!r} no render asks for")
    return problems
