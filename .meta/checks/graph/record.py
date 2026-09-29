"""The Decision record's arithmetic: alternatives, supersession, level, withdrawal, and numbering (stereorepo's DR-297).
"""
from typing import Any

import yaml

from checks.citations.loaders import OUTMODED_BELOW
from checks.collect import META, check

OPTIONS_REQUIRED_FROM = 60
"""The first number issued after the model existed.

A ratchet, and a number rather than a date because the entries recording the
conversion were written the same day it landed. Everything below this line was
converted from prose that never named an alternative, and backfilling one would
be inventing a rejection, which stereorepo's DR-050 forbids. Everything at or above it was
written against a class that says what a Decision is, so an accepted entry
naming no alternative is a non-decision and fails.

Never lowered. Raising it would be the loosening the Ratchet Discipline is about,
justified at the moment it is made and paid for afterwards.
"""


@check("decision alternatives")
def decision_alternatives(index: dict[str, Any]) -> list[str]:
    """One option is chosen, and it is stated at all from number 60 onward.

    A recommendation is held to the same rule as something in force. It is the
    closing of the alternatives that makes a decision, and that happens when the
    question is answered rather than when the answer is built.

    LinkML can require the slot and cannot count across the list, so a Decision
    with two chosen alternatives — or with a rejected one and none chosen — is
    well formed and says nothing. Nor can it exempt the converted entries, which
    a bare `required: true` would fail for telling the truth about what was
    recorded before the model existed.
    """
    problems = []
    for did, (cls, obj, _) in index.items():
        if cls != "Decision":
            continue
        alternatives = obj.get("alternatives") or []
        if not alternatives:
            if obj.get("status") in ("ADOPTED", "RECOMMENDED") \
                    and int(did.rsplit("/", 1)[-1]) >= OPTIONS_REQUIRED_FROM:
                problems.append(f"{did}: adopted and states no alternatives; if the alternative "
                                "was doing nothing, say so — that is an option and it has a reason")
            continue
        chosen = [a for a in alternatives if a.get("chosen")]
        if len(chosen) != 1:
            problems.append(f"{did}: {len(chosen)} chosen of {len(alternatives)} alternatives; exactly one is")
    return problems


@check("decision supersession")
def decision_supersession(index: dict[str, Any]) -> list[str]:
    """Supersession resolves, does not loop, and the two directions agree.

    Resolution is already covered by the reference check. What is not is the
    direction: `status: SUPERSEDED` claims a whole entry is dead, so the
    successor it names has to exist and has to be later. A record that says an
    entry was replaced by one written before it is a record nobody can order.
    """
    problems: list[str] = []
    graph: dict[str, list[str]] = {}
    for did, (cls, obj, _) in index.items():
        if cls != "Decision":
            continue
        graph[did] = list(obj.get("supersedes") or [])
        later = obj.get("superseded_by")
        if later and later in index and later <= did:
            problems.append(f"{did}: superseded by '{later}', which is not later")
        if obj.get("status") == "WITHDRAWN" and obj.get("superseded_by"):
            problems.append(f"{did}: withdrawn and superseded; a hole is not a replacement")
        for earlier in graph[did]:
            if earlier in index and earlier >= did:
                problems.append(f"{did}: supersedes '{earlier}', which is not earlier")
    state: dict[str, str] = {}

    def visit(node: str, trail: list[str]) -> None:
        if state.get(node) == "done":
            return
        if state.get(node) == "open":
            problems.append("supersedes cycle: " + " -> ".join([*trail, node]))
            return
        state[node] = "open"
        for nxt in graph.get(node, []):
            visit(nxt, [*trail, node])
        state[node] = "done"

    for node in graph:
        visit(node, [])
    return problems


@check("decision level")
def decision_level(index: dict[str, Any]) -> list[str]:
    """A Decision is the Portfolio's, a Product's or a Project's, and not two of
    these (stereorepo's DR-093).

    The level is who shares the matter, and an entry naming both a Product and
    a Project claims two readerships for one question. Each slot is typed and
    its reference resolved with every other; what no schema states is that at
    most one is set, which is a count across two slots rather than a constraint
    on either.
    """
    return [f"{did}: names both product '{obj['product']}' and project "
            f"'{obj['project']}'; a Decision is at one level"
            for did, (cls, obj, _) in sorted(index.items())
            if cls == "Decision" and obj.get("product") and obj.get("project")]


@check("withdrawn decisions")
def withdrawn_decisions(index: dict[str, Any]) -> list[str]:
    """A withdrawn Decision says why it is a hole.

    The `Decision` rule in `.meta/work/decisions.yaml` requires
    `withdrawn_because` when `status` is `WITHDRAWN`, but since nothing runs
    `linkml-validate` against these entries, we enforce this rule here.
    """
    problems = []
    for did, (cls, obj, _) in index.items():
        if cls != "Decision":
            continue
        if obj.get("status") == "WITHDRAWN" and not obj.get("withdrawn_because"):
            problems.append(f"{did}: status is WITHDRAWN but lacks 'withdrawn_because'")
    return problems


SEEDED_BELOW = OUTMODED_BELOW
"""The first number this record issued after it was pruned (stereorepo's DR-297).

A hole below it is an outmoded entry, which git holds, and a hole at or above
it is a deletion. Applies to the scaffold's own record only: a portfolio's
record starts at `DR-001` and holds every number it issues.
"""

SCAFFOLD = "work:portfolio/stereorepo"
"""The Portfolio whose record was seeded, and so the only one `SEEDED_BELOW` applies to."""


@check("decision numbering")
def decision_numbering(index: dict[str, Any]) -> list[str]:
    """Numbers are stable identifiers, so every one is distinct and a hole is a deletion.

    A Decision is numbered rather than named because it is an occurrence: two
    entries with the same claim are two decisions, and the sequence says which
    came first (stereorepo's DR-125). A gap means an entry was deleted rather than
    withdrawn, which is the failure the WITHDRAWN status exists to prevent: a
    citation to a number that resolves to nothing is indistinguishable from a
    citation to a number that was never issued. Duplicates cannot be seen in the
    index, which would have silently kept the last, so they are counted from the
    documents instead.

    The next number is the highest the record holds plus one, on `main`. Work
    in a repository is serial, so no two branches race for it (stereorepo's DR-297).
    In the scaffold's own record, a hole below `SEEDED_BELOW` is an outmoded
    entry, and is not reported.
    """
    seen = [d.rsplit("/", 1)[-1] for d, (cls, _, _) in index.items() if cls == "Decision"]
    if not seen:
        return []
    ids = [d["id"]
           for path in sorted((META / "assertions" / "decisions").glob("DR-*.yaml"))
           for d in (yaml.safe_load(path.read_text()) or {}).get("decisions") or []]
    problems = [f"the record declares {len(ids)} entries and {len(set(ids))} are distinct"] \
        if len(ids) != len(set(ids)) else []
    numbers = sorted(int(n) for n in seen)
    seeded = any(cls == "Portfolio" and ident == SCAFFOLD for ident, (cls, _, _) in index.items())
    floor = SEEDED_BELOW if seeded else 1
    missing = sorted(set(range(floor, numbers[-1] + 1)) - set(numbers))
    if missing:
        shown = ", ".join(f"DR-{n:03d}" for n in missing[:10])
        more = f" and {len(missing) - 10} more" if len(missing) > 10 else ""
        problems.append(f"no entry for {shown}{more}; a number withdrawn stays in the "
                        "record as a hole")
    return problems
