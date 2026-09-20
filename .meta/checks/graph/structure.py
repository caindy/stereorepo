"""The assertion graph's shape, six checks: a reference that resolves to nothing, a `composed_of` cycle a path cannot traverse, a Collaboration whose members cross a file boundary, an audit whose Permission is not the Remit's or whose target is not the Securable's, a Job to be Done whose END goal is not held by its own Persona, and a Portfolio with other than one Bounded Context.
"""


from typing import Any

from checks.collect import check


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


def hop(index: dict[str, Any], start: str, *slots: str) -> str | None:
    """Follow a chain of single-valued references, or give up quietly."""
    cur = start
    for slot in slots:
        if cur not in index:
            return None
        cur = index[cur][1].get(slot)
        if not isinstance(cur, str):
            return None
    return cur


@check("collaboration membership")
def collaboration_membership(index: dict[str, Any]) -> list[str]:
    """Every Job in a Collaboration answers the Collaboration's Challenge."""
    problems = []
    for cid, (cls, obj, _) in index.items():
        if cls != "Collaboration":
            continue
        for job in obj.get("jobs", []):
            reached = hop(index, job, "agency", "remit", "goal", "challenge")
            if reached is not None and reached != obj.get("challenge"):
                problems.append(
                    f"{cid}: job '{job}' answers '{reached}', not '{obj.get('challenge')}'")
    return problems


@check("audit invariants")
def audit_invariants(index: dict[str, Any]) -> list[str]:
    """An authorising Permission comes from the Remit; a target is in the Securable."""
    problems = []
    for aid, (cls, obj, _) in index.items():
        if cls != "AuditRecord":
            continue
        perm = obj.get("under_permission")
        if perm:
            remit = hop(index, obj.get("execution", ""), "job", "agency", "remit")
            granted = index.get(remit, (None, {}, None))[1].get("permissions", []) if remit else None
            if granted is not None and perm not in granted:
                problems.append(f"{aid}: '{perm}' is not among the Remit's Permissions")
        target, securable = obj.get("target"), obj.get("securable")
        if target and securable in index:
            members = index[securable][1].get("members")
            if members is not None and target not in members:
                problems.append(f"{aid}: target '{target}' is not a member of '{securable}'")
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
    """A portfolio is exactly one Bounded Context, by construction (solorepo's DR-014).

    The slot stays multivalued because `DddModel` is generic DDD and a Context
    Map legitimately holds many — solorepo's own map has three. What is singular
    is a portfolio's *own* context, so that is checked rather than typed
    (solorepo's DR-037): one declaration in `domain_vocabulary.yaml`, and the Portfolio
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
