"""The assertion graph's shape, five checks: a reference that resolves to nothing, a `composed_of` cycle a path cannot traverse, a Job to be Done whose END goal is not held by its own Persona, a Portfolio with other than one Bounded Context, and a Bootstrap lacking coverage for project-binding Disciplines.
"""


from typing import Any

from checks.collect import check

PROJECT_BINDING_DISCIPLINES: frozenset[str] = frozenset({
    "work:discipline/literate-programming",
    "work:discipline/ratchet",
    "work:discipline/observed-failure",
    "work:discipline/nothing-unconsumed",
    "work:discipline/seeded-artifacts",
    "work:discipline/written-decisions",
})
"""Disciplines binding projects that every registered Bootstrap must implement or exempt."""


@check("unresolved references")
def unresolved_references(index: dict[str, Any], refs: list[tuple[str, str, str]]) -> list[str]:
    """Every URI referenced in an assertion slot exists as an identified object in the index."""
    return [f"{site} -> {target} '{ref}' does not exist"
            for ref, target, site in refs if ref not in index]


@check("composed_of cycles")
def composed_of_cycles(index: dict[str, Any]) -> list[str]:
    """A skill composes tools and may compose skills. It may not compose itself."""
    graph = {i: o.get("composed_of", []) for i, (c, o, _) in index.items() if c == "Capability"}
    problems: list[str] = []
    state: dict[str, str] = {}

    def visit(node: str, trail: list[str]) -> None:
        if state.get(node) == "done":
            return
        if state.get(node) == "open":
            problems.append("composed_of cycle: " + " -> ".join([*trail, node]))
            return
        state[node] = "open"
        for nxt in graph.get(node, []):
            visit(nxt, [*trail, node])
        state[node] = "done"

    for node in graph:
        visit(node, [])
    return problems


@check("served goals")
def served_goals(index: dict[str, Any]) -> list[str]:
    """A Job to be Done serves END goals, and only ones its own Persona holds.

    Neither is expressible in the schema: the tier lives on the target object,
    and ownership crosses a path. Both matter, because the value of the edge is
    the subtraction it allows — an END goal with no Job to be Done is a need
    nobody is serving — and a wrongly-tiered or borrowed goal quietly corrupts
    that arithmetic.

    A `serves` naming nothing in the index is passed over: `unresolved
    references` has already reported it, and the tier of a goal that is not
    there cannot be read anyway.
    """
    problems = []
    for jid, (cls, obj, _) in index.items():
        if cls != "JobToBeDone":
            continue
        persona = obj.get("persona")
        held = {g.get("id") for g in index[persona][1].get("persona_goals", [])} \
            if persona in index else set()
        for gid in obj.get("serves", []):
            if gid not in index:
                continue
            tier = index[gid][1].get("goal_type")
            if tier != "END":
                problems.append(f"{jid}: serves '{gid}', which is {tier}, not END")
            if held and gid not in held:
                problems.append(f"{jid}: serves '{gid}', not held by '{persona}'")
    return problems


@check("one context per portfolio")
def one_context_per_portfolio(index: dict[str, Any]) -> list[str]:
    """A portfolio is exactly one Bounded Context, by construction (stereorepo's DR-014).

    The slot stays multivalued because `DddModel` is generic DDD and a Context
    Map legitimately holds many — stereorepo's own map has three. What is singular
    is a portfolio's *own* context, so that is checked rather than typed
    (stereorepo's DR-037): one declaration in `domain_vocabulary.yaml`, and the Portfolio
    names it.
    """
    problems = []
    own = [i for i, (cls, _, where) in index.items()
           if cls == "BoundedContext" and where == "domain_vocabulary.yaml"]
    if len(own) > 1:
        problems.append("domain_vocabulary.yaml declares " + str(len(own))
                        + " Bounded Contexts; a portfolio is exactly one: " + ", ".join(sorted(own)))
    for pid, (cls, obj, _) in index.items():
        if cls != "Portfolio":
            continue
        named = obj.get("bounded_context")
        if own and named not in own:
            problems.append(f"{pid} names '{named}', which is not the context declared in "
                            "domain_vocabulary.yaml")
    return problems


@check("bootstrap discipline coverage")
def bootstrap_discipline_coverage(index: dict[str, Any]) -> list[str]:
    """Every Bootstrap implements or exempts all project-binding Disciplines (Article 7).

    Validates that each Bootstrap declared in the assertions explicitly accounts
    for every Discipline in `PROJECT_BINDING_DISCIPLINES`. An implemented
    Discipline must declare gate steps in `held_by`; an exempt Discipline must
    supply an `exemption_reason`. Disciplines binding projects cannot be marked
    `portfolio_scoped`.

    Args:
        index: Identified objects mapping entity identifier to (class_name, object_dict, file_name).

    Returns:
        list[str]: Diagnostic problem messages for missing, incomplete, or invalid declarations.
    """
    problems: list[str] = []
    bootstraps = [
        (bid, obj)
        for bid, (cls, obj, _) in index.items()
        if cls == "Bootstrap"
    ]
    for bid, obj in sorted(bootstraps):
        impls = obj.get("discipline_implementations") or []
        seen: set[str] = set()
        for entry in impls:
            disc = entry.get("discipline")
            if not disc:
                problems.append(f"{bid}: discipline entry missing 'discipline' reference")
                continue
            if disc in seen:
                problems.append(f"{bid}: discipline '{disc}' declared more than once")
            seen.add(disc)
            status = entry.get("status")
            if status == "implemented":
                held_by = entry.get("held_by") or []
                if not held_by:
                    problems.append(
                        f"{bid}: discipline '{disc}' is implemented but names no gate steps "
                        "in 'held_by'"
                    )
            elif status == "exempt":
                reason = entry.get("exemption_reason")
                if not reason or not str(reason).strip():
                    problems.append(
                        f"{bid}: discipline '{disc}' is exempt but carries no 'exemption_reason'"
                    )
            elif status == "portfolio_scoped":
                if disc in PROJECT_BINDING_DISCIPLINES:
                    problems.append(
                        f"{bid}: project-binding discipline '{disc}' cannot be "
                        "marked 'portfolio_scoped'"
                    )
            else:
                problems.append(
                    f"{bid}: discipline '{disc}' has invalid status '{status}'"
                )
        missing = PROJECT_BINDING_DISCIPLINES - seen
        for disc in sorted(missing):
            problems.append(f"{bid}: missing discipline entry for '{disc}'")
    return problems

