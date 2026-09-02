#!/usr/bin/env python3
"""The gate for the .meta Project.

Five invariants are stated in the schemas and enforceable by none of them. Four
cross a path LinkML cannot traverse; the fifth crosses a file boundary, because
two tree roots are two documents and references between them resolve to nothing
a validator will look at.

    uvx --with linkml --with pyyaml python .meta/check.py

Run `linkml-validate` first — this checks what that cannot, and assumes the
documents are otherwise well formed. It also runs render.py's staleness check, so
one command is the whole gate.

Which slots hold references is read off the schema rather than listed here: a
slot is a reference when its range is a class with an identifier and it is not
inlined. Listing them by hand would drift from the schemas the moment either
moved.
"""
import pathlib
import re
import sys

import yaml
from linkml_runtime import SchemaView

META = pathlib.Path(__file__).parent
ROOT = META.parent
TEMPLATE = ROOT / "template"
TOKEN = re.compile(r"__[A-Z][A-Z0-9_]*__")
SCHEMAS = ("work_ontology.yaml", "ddd_ontology.yaml")


def tree_root(sv):
    for name, cls in sv.all_classes().items():
        if cls.tree_root:
            return name
    return None


def view_for(data, views):
    """The schema whose container accepts every top-level key in this document."""
    for sv in views:
        root = tree_root(sv)
        if root and set(data) <= set(sv.class_slots(root)):
            return sv, root
    return None, None


def walk(obj, cls, sv, index, refs, where):
    """Collect identified objects into `index` and reference sites into `refs`."""
    if not isinstance(obj, dict):
        return
    ident = sv.get_identifier_slot(cls)
    if ident and ident.name in obj:
        index[obj[ident.name]] = (cls, obj, where)
    for key, val in obj.items():
        try:
            slot = sv.induced_slot(key, cls)
        except Exception:
            continue
        if slot is None or slot.range not in sv.all_classes():
            continue
        target = slot.range
        values = val if isinstance(val, list) else [val]
        if sv.get_identifier_slot(target) and not (slot.inlined or slot.inlined_as_list):
            for v in values:
                if isinstance(v, str):
                    refs.append((v, target, f"{where}: {cls}.{key}"))
        else:
            for v in values:
                walk(v, target, sv, index, refs, where)


def views():
    return [SchemaView(str(META / s)) for s in SCHEMAS]


def collect(views):
    index, refs, skipped = {}, [], []
    for path in sorted((META / "assertions").rglob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if not data:
            continue
        sv, root = view_for(data, views)
        if sv is None:
            skipped.append(path.name)
            continue
        for key, val in data.items():
            slot = sv.induced_slot(key, root)
            for item in (val if isinstance(val, list) else [val]):
                walk(item, slot.range, sv, index, refs, path.name)
    return index, refs, skipped


def unresolved_references(index, refs):
    return [f"{site} -> {target} '{ref}' does not exist"
            for ref, target, site in refs if ref not in index]


def composed_of_cycles(index):
    """A skill composes tools and may compose skills. It may not compose itself."""
    graph = {i: o.get("composed_of", []) for i, (c, o, _) in index.items() if c == "Capability"}
    problems, state = [], {}

    def visit(node, trail):
        if state.get(node) == "done":
            return
        if state.get(node) == "open":
            problems.append("composed_of cycle: " + " -> ".join(trail + [node]))
            return
        state[node] = "open"
        for nxt in graph.get(node, []):
            visit(nxt, trail + [node])
        state[node] = "done"

    for node in graph:
        visit(node, [])
    return problems


def hop(index, start, *slots):
    """Follow a chain of single-valued references, or give up quietly."""
    cur = start
    for slot in slots:
        if cur not in index:
            return None
        cur = index[cur][1].get(slot)
        if not isinstance(cur, str):
            return None
    return cur


def collaboration_membership(index):
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


def audit_invariants(index):
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


def served_goals(index):
    """A Job to be Done serves END goals, and only ones its own Persona holds.

    Neither is expressible in the schema: the tier lives on the target object,
    and ownership crosses a path. Both matter, because the value of the edge is
    the subtraction it allows — an END goal with no Job to be Done is a need
    nobody is serving — and a wrongly-tiered or borrowed goal quietly corrupts
    that arithmetic.
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
                continue  # already reported as an unresolved reference
            tier = index[gid][1].get("goal_type")
            if tier != "END":
                problems.append(f"{jid}: serves '{gid}', which is {tier}, not END")
            if held and gid not in held:
                problems.append(f"{jid}: serves '{gid}', not held by '{persona}'")
    return problems


def _template_files():
    if not TEMPLATE.is_dir():
        return []
    return [(f, ROOT / f.relative_to(TEMPLATE)) for f in sorted(TEMPLATE.rglob("*")) if f.is_file()]


def surviving_placeholders():
    """No template token survives anywhere outside `template/`.

    Scanning only the files `template/` shadows was exact and also useless:
    Specialization deletes `template/` before running the gate, so by the time
    the check ran there was nothing left to compare against and it passed
    vacuously. Scanning everything else keeps it alive in a portfolio, where it
    is the only thing standing between a half-filled skeleton and a first commit.

    The cost is that prose here may not spell a token literally. That is cheap,
    and a literal token outside `template/` is a defect in any case.
    """
    problems = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or TEMPLATE in path.parents or ".git" in path.parts:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        found = sorted(set(TOKEN.findall(text)))
        if found:
            problems.append(f"{path.relative_to(ROOT)}: {', '.join(found)} was never filled in")
    return problems


def template_parses(views):
    """The template is data and is not linted in place. It is checked by filling
    it in and testing the result, which is the only version anyone runs.
    """
    problems = []
    for src, _ in _template_files():
        if src.suffix != ".yaml":
            continue
        filled = TOKEN.sub("placeholder", src.read_text())
        rel = src.relative_to(ROOT)
        try:
            data = yaml.safe_load(filled)
        except yaml.YAMLError as exc:
            problems.append(f"{rel}: does not parse once filled in — {exc}")
            continue
        if not data:
            continue
        sv, _ = view_for(data, views)
        if sv is None:
            problems.append(f"{rel}: no container accepts {sorted(data)}")
    return problems


CHECKS = (
    ("unresolved references", lambda i, r: unresolved_references(i, r)),
    ("composed_of cycles", lambda i, r: composed_of_cycles(i)),
    ("collaboration membership", lambda i, r: collaboration_membership(i)),
    ("audit invariants", lambda i, r: audit_invariants(i)),
    ("served goals", lambda i, r: served_goals(i)),
    ("surviving placeholders", lambda i, r: surviving_placeholders()),
)

if __name__ == "__main__":
    schemas = views()
    index, refs, skipped = collect(schemas)
    for name in skipped:
        print(f"?  {name}: no container accepts its top-level keys")
    failed = bool(skipped)
    for label, check in CHECKS + (("template parses", lambda i, r: template_parses(schemas)),):
        problems = check(index, refs)
        print(("x  " if problems else "ok ") + label + (f" ({len(problems)})" if problems else ""))
        for p in problems:
            print(f"     {p}")
        failed |= bool(problems)

    sys.path.insert(0, str(META))
    import render
    stale = []
    for name, fn in render.TARGETS.items():
        rendered, path = fn(), META / name
        if rendered is None:
            # Nothing to render here, so nothing should have been rendered.
            if path.exists():
                stale.append(f"{name} exists but nothing renders it")
            continue
        if not path.exists() or path.read_text() != rendered.rstrip("\n") + "\n":
            stale.append(name)
    print(("x  " if stale else "ok ") + "rendered prose" + (f": {', '.join(stale)}" if stale else ""))
    failed |= bool(stale)

    print(f"\n{len(index)} identified objects, {len(refs)} references")
    sys.exit(1 if failed else 0)
