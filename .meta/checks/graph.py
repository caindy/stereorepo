"""Invariants over the assertion graph, and the Decision record's arithmetic.

What the schemas state and LinkML cannot check: a reference that resolves to
nothing, a cycle a path cannot traverse, a membership that crosses a file
boundary, and the three counts over the Decision record that a rule cannot make
(solorepo's DR-150). History in graph.history.md.
"""
import re
import subprocess

import yaml

from citations import FOREIGN
from collect import META, ROOT, check


@check("unresolved references")
def unresolved_references(index, refs):
    """Every URI referenced in an assertion slot exists as an identified object in the index."""
    return [f"{site} -> {target} '{ref}' does not exist"
            for ref, target, site in refs if ref not in index]


@check("composed_of cycles")
def composed_of_cycles(index):
    """A skill composes tools and may compose skills. It may not compose itself."""
    graph = {i: o.get("composed_of", []) for i, (c, o, _) in index.items() if c == "Capability"}
    problems, state = [], {}

    def visit(node, trail):
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


@check("collaboration membership")
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


@check("audit invariants")
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


@check("served goals")
def served_goals(index):
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
def one_context_per_portfolio(index):
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


OPTIONS_REQUIRED_FROM = 60
"""The first number issued after the model existed.

A ratchet, and a number rather than a date because the entries recording the
conversion were written the same day it landed. Everything below this line was
converted from prose that never named an alternative, and backfilling one would
be inventing a rejection, which solorepo's DR-050 forbids. Everything at or above it was
written against a class that says what a Decision is, so an accepted entry
naming no alternative is a non-decision and fails.

Never lowered. Raising it would be the loosening the Ratchet Discipline is about,
justified at the moment it is made and paid for afterwards.
"""


@check("decision alternatives")
def decision_alternatives(index):
    """One option is chosen, and it is stated at all from `DR-060` onward.

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
def decision_level(index):
    """A Decision is the Portfolio's, a Product's or a Project's, and not two of
    these (solorepo's DR-093).

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
def withdrawn_decisions(index):
    """A withdrawn Decision says why it is a hole (solorepo's DR-112).

    LinkML requires `withdrawn_because` when `status` is `WITHDRAWN`, but since
    nothing runs `linkml-validate` against these entries, we enforce this rule
    here.
    """
    problems = []
    for did, (cls, obj, _) in index.items():
        if cls != "Decision":
            continue
        if obj.get("status") == "WITHDRAWN" and not obj.get("withdrawn_because"):
            problems.append(f"{did}: status is WITHDRAWN but lacks 'withdrawn_because'")
    return problems


# One line of `git ls-remote`: the object, a tab, the ref. Anchored at the end
# because an annotated tag is advertised twice, `refs/tags/DR-nnn` and the
# `^{}` line that dereferences it to the commit, and counting both would say
# nothing wrong but would say it twice.
RESERVATION = re.compile(r"\trefs/tags/DR-(\d+)$", re.M)


def reserved_decision_numbers():
    """The numbers GitHub holds a tag for, or None when it will not say
    (solorepo's DR-128).

    Asked of the remote rather than of this clone. A tag another branch pushed
    is not here unless something fetched it, and CI checks out one commit with
    no tags at all, so a local answer would be "none reserved" on the one
    machine where the question is being asked in earnest.

    This is the only step of this gate that reaches the network, and it is
    reached only when the record has a hole the commits here did not explain. A
    run over a contiguous record, or one whose every hole a deletion accounts
    for, asks nothing of anyone.

    Not, therefore, only when the answer can turn a red into a pass. A clone
    with no history to read explains no hole, so every hole arrives here and
    both answers are red — which is the path where this call buys least and the
    one an old shallow portfolio takes on every red run (solorepo's #152). It is made
    anyway: skipping it would leave the caller with no answer, and no answer is
    the sentence saying the remote would not say, printed on a run that never
    asked it — the advice to take a number another branch is holding. Telling
    the two reds apart instead costs a fourth sentence, on a run that is red
    whichever of them it prints.
    """
    try:
        found = subprocess.run(["git", "-C", str(ROOT), "ls-remote", "--tags", "origin", "DR-*"],
                               capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if found.returncode:
        return None
    return {int(n) for n in RESERVATION.findall(found.stdout)}


# One path of `git log --diff-filter=D --name-only`: an entry a commit in this
# history removed. Written as a pattern rather than three digits, so that a file
# a portfolio copies carries no citation of a Decision it does not have
# (solorepo's DR-124).
DELETION = re.compile(r"^\.meta/assertions/decisions/DR-(\d+)\.yaml$", re.M)


def deleted_decision_numbers(numbers):
    """Which of these numbers the record here once held and a commit removed, or
    None when there is no history to read (solorepo's DR-128).

    The question the tag cannot answer. A tag outlives the entry, so from the
    first redemption on it is there whether the number is in flight or was
    written and then dropped; what tells those apart is whether an entry for the
    number was ever in this record, which is a fact about commits. Local, and
    needing no remote at all: a portfolio with no `origin` still has its own.

    `--no-renames`, because an entry renamed rather than deleted — a number
    retyped as its neighbour during a repair — leaves the record short by one
    just the same, and rename detection would call that no deletion at all. The
    pathspec is the holes and only the holes: a number the record still holds
    was not deleted whatever its path did on the way here.

    A shallow clone is not asked. `git log` over a truncated history answers
    "nothing was deleted" for every number older than the graft, which is the
    green this check exists to refuse; the workflows that run this check out
    with `fetch-depth: 0` for that reason.
    """
    if not numbers:
        return set()
    where = (META / "assertions" / "decisions").relative_to(ROOT)
    argv = ["git", "-C", str(ROOT)]
    try:
        shallow = subprocess.run([*argv, "rev-parse", "--is-shallow-repository"],
                                 capture_output=True, text=True, timeout=30)
        if shallow.returncode or shallow.stdout.strip() != "false":
            return None
        found = subprocess.run(argv + ["log", "--no-renames", "--diff-filter=D",
                                       "--name-only", "--format=", "--"]
                               + [f"{where}/DR-{n:03d}.yaml" for n in sorted(numbers)],
                               capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if found.returncode:
        return None
    return {int(m.group(1)) for m in DELETION.finditer(found.stdout)}


@check("decision numbering")
def decision_numbering(index, reserved=reserved_decision_numbers,
                       deleted=deleted_decision_numbers):
    """Numbers are stable identifiers, so the sequence is contiguous and unused,
    and a hole GitHub reserves is a number in flight rather than a deletion.

    A Decision is numbered rather than named because it is an occurrence: two
    entries with the same claim are two decisions, and the sequence says which
    came first (solorepo's DR-125). The contiguity checked here is part of what the
    identifier means, not a convention laid over it — a slug would name the
    claim and lose the order, and a deleted slug leaves no hole to find.

    A gap means an entry was deleted rather than withdrawn, which is the failure
    the WITHDRAWN status exists to prevent: a citation to a number that resolves
    to nothing is indistinguishable from a citation to a number that was never
    issued. Duplicates cannot be seen here — the index would have silently kept
    the last — so they are counted from the document instead.

    Since solorepo's DR-128 a number is issued by `.meta/say/move mint`, which
    reserves it as a tag before it is cited anywhere. So a branch that mints a
    number while another branch holds the one below it has a record with a hole
    in it, through no fault of its own, until the other lands — and that hole is
    a promise somebody is keeping, not an entry somebody dropped.

    Two reads tell those apart, and the tag on its own cannot. The tag is never
    deleted, so from the first redemption on it holds every number the record
    holds too, and a hole dropped for having one would be dropped forever: an
    entry deleted six weeks after it landed still has its tag. So a hole is a
    reservation only when a tag holds the number *and* no commit in this history
    removed its entry. The tag says the number was issued; the history says
    whether it was ever redeemed, and it is the second that catches a deletion.

    The history is read first, and the tags decide only the holes it leaves.
    That order is what makes the mechanism work where it is most needed: the
    commits are here in every install, the remote is not, so a portfolio with
    no `origin` — and a sandbox with no network — still gets the one sentence
    that says what to do, `the record held DR-nnn and a commit here removed
    it`, instead of being sent at a remote it was never going to have. It also
    means each remaining sentence speaks of holes no read has explained, and
    that the remote is not asked at all when the commits explain every hole.

    A reservation nobody redeems is closed the way every other hole is, by
    writing the number back into the record as WITHDRAWN; the tag stays, so the
    number is never issued twice. This is not where that closure is prompted: a
    number minted and never written has a tag and no commit, which is what a
    number in flight has, so it reads as a promise somebody is still keeping for
    as long as nobody looks at the tag. That hole is the one failure here that
    stays quiet, and solorepo's DR-128 says so. One case now has a prompt
    elsewhere — `move supersede` names the numbers the branch it closes minted
    and will never redeem, since closing a pull request is the moment somebody
    knows (solorepo's DR-164) — and a reservation whose branch simply stopped
    still has none.

    A hole neither read can explain stays a failure. Red on a hole that might
    have been reserved costs a session one message; green on a hole that was a
    deletion is the failure this check exists for, kept quiet by a network that
    was down or a clone with no history behind it.

    The commits decide the holes they can and the tags decide what is left,
    in that order, so a clone with no `origin` still names its local deletions.
    What neither read explains is reported as unexplained, and a read that
    could not be made is unknown rather than vacant: a remote nobody could
    reach never makes a number in flight look available.

    Both reads are parameters, defaulting to the two functions above, so that
    `reservation_probes` stands them in by passing arguments. It used to rebind
    them on the module and restore them in a `finally`, which a probe needs only
    because a check reaches for its sources by name: a probe that mutates the
    module it tests is one exception away from leaving the gate holding a fake,
    and it constrains the order probes may run in for no stated reason.
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
    missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
    if missing:
        def listed(numbers):
            """The numbers as `DR-nnn`, at most ten of them and then a count of the rest.

            Truncated because one mistyped number makes every number after it
            missing, and a check that answers with nine hundred lines is one
            nobody reads to the end of.
            """
            shown = ", ".join(f"DR-{n:03d}" for n in numbers[:10])
            return shown + (f" and {len(numbers) - 10} more" if len(numbers) > 10 else "")

        removed = deleted(missing)
        gone = [] if removed is None else [n for n in missing if n in removed]
        rest = [n for n in missing if n not in gone]
        if gone:
            problems.append(f"the record held {listed(gone)} and a commit here removed it, "
                            "tag or no tag; a number withdrawn stays in the record as a hole")
        if rest:
            held = reserved()
            if held is None and removed is None:
                problems.append(f"no entry for {listed(rest)}; the remote would not say which "
                                "numbers it reserves and this clone has no history to read, so "
                                "nothing here tells a number in flight from a deletion")
            elif held is None:
                problems.append(f"no entry for {listed(rest)}, and no commit here removed it; "
                                "the remote would not say which numbers it reserves, so a number "
                                "in flight cannot be told from one nobody has written")
            elif removed is None:
                problems.append(f"no entry for {listed(rest)}; this clone has no history to read, "
                                "so a deletion cannot be told from a number in flight here")
            elif unheld := [n for n in rest if n not in held]:
                problems.append(f"no entry for {listed(unheld)}, and no tag reserving it; "
                                "a number withdrawn stays in the record as a hole")
    return problems


# The record itself: naming it under `enacted_in` satisfies the letter of A20 and
# defeats the point, so it does not count. `.meta/work/decisions.yaml` is the
# schema and is a legitimate target, which is why this is a prefix and not a word.
RECORD = (".meta/assertions/decisions/", ".meta/decisions.md")


@check("artifact paths")
def artifact_paths(index):
    """Every Artifact is a file that exists.

    The reference to an Artifact is resolved by the references check, like any
    other; what no schema can know is whether the path on the far side still
    names something. One check per Artifact rather than one per citation, which
    is the whole reason for making it an entity.
    """
    return [f"{ident}: {obj['path']} does not exist"
            for ident, (cls, obj, _) in sorted(index.items())
            if cls == "Artifact" and not (ROOT / obj["path"]).is_file()]


@check("reserved article numbers")
def reserved_article_numbers(index):
    """A retired Article's number is never issued again.

    The reservation is the only thing a retirement leaves behind, and it exists
    so that a citation written years ago cannot silently come to mean something
    new. Nothing else defends it: the Charter is hand-numbered, and a hole is an
    absence, which nothing notices on its own.
    """
    charter = yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    holes = charter.get("retired_articles") or []
    retired = {r["number"] for r in holes}
    live = {int(a["id"].rsplit("/", 1)[-1]) for a in charter.get("articles") or []}
    problems = [f"A{n} is retired and issued again; a retired number is reserved forever"
                for n in sorted(retired & live)]
    # The pointer to the account is prose, `solorepo's DR-085`, since the entry
    # is solorepo's and the Charter goes to every portfolio (solorepo's DR-121). A string
    # slot is a slot nothing resolves, so the form is held here and the number
    # by `cited decisions`, which together are what the reference check was.
    problems += [f"A{r['number']}: retired_by is {r.get('retired_by')!r}, and the account "
                 "of a retirement is cited as solorepo's DR-nnn"
                 for r in holes if not FOREIGN.fullmatch(str(r.get("retired_by", "")))]
    return problems


@check("enacted decisions")
def enacted_decisions(index):
    """A20. An adopted decision names an Artifact that carries its rule (solorepo's DR-078).

    Whether the Artifact exists is a reference, resolved with every other. What
    is left here is the arithmetic no schema states: ADOPTED means in force, and
    in force with nowhere to be read from is in force over nobody.

    Naming the record itself would satisfy the letter and defeat the point, so
    it does not count.
    """
    record = {ident for ident, (cls, obj, _) in index.items()
              if cls == "Artifact" and obj["path"].startswith(RECORD)}
    return [f"DR-{ident.rsplit('/', 1)[-1]} is adopted and names no artifact "
            "carrying its rule"
            for ident, (cls, obj, _) in sorted(index.items())
            if cls == "Decision" and obj.get("status") == "ADOPTED"
            and not [a for a in (obj.get("enacted_in") or []) if a not in record]]
