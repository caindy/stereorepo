#!/usr/bin/env python3
"""The gate for the .meta Project.

Invariants stated in the schemas and enforceable by none of them. Some cross a
path LinkML cannot traverse; one crosses a file boundary, because two tree roots
are two documents and references between them resolve to nothing a validator will
look at; and three are arithmetic over a list, which a rule cannot count.

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


class Strict(yaml.SafeLoader):
    """A loader that notices a key written twice.

    PyYAML takes the last of a repeated key without a word, so an editing slip
    becomes a value that is right by luck rather than by construction. It was
    right by luck once here — a script that added `broader` to concepts that
    already had one left 29 duplicates, every pair identical, and the render was
    correct for no reason anyone had checked.
    """


_DUPLICATES = []


def _note_duplicates(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            _DUPLICATES.append((key, key_node.start_mark.line + 1))
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _note_duplicates)


def duplicate_keys():
    """Every YAML the gate reads, including the schemas and the seed."""
    problems = []
    for path in sorted([*META.rglob("*.yaml"), *TEMPLATE.rglob("*.yaml")]):
        _DUPLICATES.clear()
        try:
            yaml.load(path.read_text(), Loader=Strict)
        except yaml.YAMLError:
            continue  # `template parses` owns malformed documents.
        problems += [f"{path.relative_to(ROOT)}:{line} '{key}' written twice"
                     for key, line in _DUPLICATES]
    return problems


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
        if path.is_symlink() or not path.is_file() \
                or TEMPLATE in path.parents or ".git" in path.parts:
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


def one_context_per_portfolio(index):
    """A portfolio is exactly one Bounded Context, by construction (DR-014).

    The slot stays multivalued because `DddModel` is generic DDD and a Context
    Map legitimately holds many — solorepo's own map has three. What is singular
    is a portfolio's *own* context, so that is what is checked: one declaration
    in `domain_vocabulary.yaml`, and the Portfolio names it.
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


OPTIONS_REQUIRED_FROM = 60
"""The first number issued after the model existed.

A ratchet, and a number rather than a date because the entries recording the
conversion were written the same day it landed. Everything below this line was
converted from prose that never named an alternative, and backfilling one would
be inventing a rejection, which DR-050 forbids. Everything at or above it was
written against a class that says what a Decision is, so an accepted entry
naming no alternative is a non-decision and fails.

Never lowered. Raising it would be the loosening the Ratchet Discipline is about,
justified at the moment it is made and paid for afterwards.
"""


def decision_options(index):
    """One option is chosen, and it is stated at all from DR-060 onward.

    A recommendation is held to the same rule as something in force. It is the
    closing of the alternatives that makes a decision, and that happens when the
    question is answered rather than when the answer is built.

    LinkML can require the slot and cannot count across the list, so a Decision
    with two chosen options — or with a rejected option and no chosen one — is
    well formed and says nothing. Nor can it exempt the converted entries, which
    a bare `required: true` would fail for telling the truth about what was
    recorded before the model existed.
    """
    problems = []
    for did, (cls, obj, _) in index.items():
        if cls != "Decision":
            continue
        options = obj.get("options") or []
        if not options:
            if obj.get("status") in ("ADOPTED", "RECOMMENDED") \
                    and int(did.rsplit("/", 1)[-1]) >= OPTIONS_REQUIRED_FROM:
                problems.append(f"{did}: accepted and states no options; if the alternative "
                                "was doing nothing, say so — that is an option and it has a reason")
            continue
        chosen = [o for o in options if o.get("chosen")]
        if len(chosen) != 1:
            problems.append(f"{did}: {len(chosen)} options chosen of {len(options)}; exactly one is")
    return problems


def decision_supersession(index):
    """Supersession resolves, does not loop, and the two directions agree.

    Resolution is already covered by the reference check. What is not is the
    direction: `status: SUPERSEDED` claims a whole entry is dead, so the
    successor it names has to exist and has to be later. A record that says an
    entry was replaced by one written before it is a record nobody can order.
    """
    problems, graph = [], {}
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
    state = {}

    def visit(node, trail):
        if state.get(node) == "done":
            return
        if state.get(node) == "open":
            problems.append("supersedes cycle: " + " -> ".join(trail + [node]))
            return
        state[node] = "open"
        for nxt in graph.get(node, []):
            visit(nxt, trail + [node])
        state[node] = "done"

    for node in graph:
        visit(node, [])
    return problems


def decision_numbering(index):
    """Numbers are stable identifiers, so the sequence is contiguous and unused.

    A gap means an entry was deleted rather than withdrawn, which is the failure
    the WITHDRAWN status exists to prevent: a citation to a number that resolves
    to nothing is indistinguishable from a citation to a number that was never
    issued. Duplicates cannot be seen here — the index would have silently kept
    the last — so they are counted from the document instead.
    """
    seen = [d.rsplit("/", 1)[-1] for d, (cls, _, _) in index.items() if cls == "Decision"]
    if not seen:
        return []
    raw = yaml.safe_load((META / "assertions" / "decisions.yaml").read_text()) or {}
    ids = [d["id"] for d in raw.get("decisions") or []]
    problems = [f"decisions.yaml declares {len(ids)} entries and {len(set(ids))} are distinct"] \
        if len(ids) != len(set(ids)) else []
    numbers = sorted(int(n) for n in seen)
    missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
    if missing:
        # Truncated, because one mistyped number makes every number after it
        # missing, and a check that answers with nine hundred lines is one
        # nobody reads to the end of.
        shown = ", ".join(f"DR-{n:03d}" for n in missing[:10])
        more = f" and {len(missing) - 10} more" if len(missing) > 10 else ""
        problems.append(f"no entry for {shown}{more}; a number withdrawn stays "
                        "in the record as a hole")
    return problems


DR = re.compile(r"\bDR-(\d{3})\b")


def cited_decisions(index):
    """A DR cited in prose resolves to an entry.

    An Article citation is a typed reference and has been checked since the
    references check existed; a DR citation is plain text in a paragraph, and
    nothing looked at it. `roadmap.md` cited DR-058 in three places for an entry
    nobody wrote, and the collision was found only because that was the next
    number to issue.

    Generated pages are scanned along with the rest. A citation inside a
    `rationale` block is prose inside the data, and it reaches a reader through
    `decisions.md` exactly as any other paragraph does, so it is held to the same
    rule rather than exempted for where it is stored.
    """
    known = {d.rsplit("/", 1)[-1] for d, (cls, _, _) in index.items() if cls == "Decision"}
    if not known:
        return []
    problems = []
    for path in sorted(ROOT.rglob("*.md")):
        if path.is_symlink() or TEMPLATE in path.parents or ".git" in path.parts:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for num in sorted(set(DR.findall(text)) - known):
            problems.append(f"{path.relative_to(ROOT)}: DR-{num} is cited and does not exist")
    return problems


CHECKS = (
    ("duplicate keys", lambda i, r: duplicate_keys()),
    ("unresolved references", lambda i, r: unresolved_references(i, r)),
    ("composed_of cycles", lambda i, r: composed_of_cycles(i)),
    ("collaboration membership", lambda i, r: collaboration_membership(i)),
    ("audit invariants", lambda i, r: audit_invariants(i)),
    ("served goals", lambda i, r: served_goals(i)),
    ("one context per portfolio", lambda i, r: one_context_per_portfolio(i)),
    ("decision options", lambda i, r: decision_options(i)),
    ("decision supersession", lambda i, r: decision_supersession(i)),
    ("decision numbering", lambda i, r: decision_numbering(i)),
    ("cited decisions", lambda i, r: cited_decisions(i)),
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
    pages = render.rendered()
    stale = render.unrendered()
    stale += [name for name, text in pages.items()
              if not (META / name).exists()
              or (META / name).read_text() != text.rstrip("\n") + "\n"]
    stale += [f"{p.relative_to(META)} is generated and nothing renders it"
              for p in render.orphans(pages)]
    print(("x  " if stale else "ok ") + "rendered prose" + (f": {', '.join(stale)}" if stale else ""))
    failed |= bool(stale)

    print(f"\n{len(index)} identified objects, {len(refs)} references")
    sys.exit(1 if failed else 0)
