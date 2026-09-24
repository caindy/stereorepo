"""Trunk's own HEAD check rollup, read on every reconciler pass (solorepo's #913).

One module per subject under test, so a history log's Evidence names the file
holding it (solorepo's DR-209).
"""
from typing import Any

from checks.collect import check
from checks.probes.harness import load_channel, outcome, stood_in

REFUSED = "gh: refused the query"
"""What a GraphQL read GitHub refuses exits with, in the shape the channel exits with."""

GREEN = [{"name": "gate", "conclusion": "SUCCESS"},
         {"name": "sweep", "conclusion": "SKIPPED"}]
"""A rollup every check of which passed; a skipped check is green, as every reader here reads it."""

RED = [{"name": "gate", "conclusion": "SUCCESS"},
       {"name": "python seed", "conclusion": "FAILURE"}]
"""A rollup with one failed check, which is the break solorepo's #910 was."""

RUNNING = [{"name": "gate", "status": "IN_PROGRESS"}]
"""A rollup whose only check has yet to conclude."""

STALE = [{"name": "gate", "conclusion": "FAILURE", "startedAt": "2026-09-01T00:00:00Z"},
         {"name": "gate", "conclusion": "SUCCESS", "startedAt": "2026-09-02T00:00:00Z"}]
"""Two runs of one check, the later one green: a re-run that healed the commit."""


@check("trunk probes", pre=True)
def trunk_probes() -> list[str]:
    """`trunk_health` over each rollup, and the line `reconcile` prints for each.

    `trunk_health`, against a GitHub answered from a dict: a rollup with a
    failed check reads red and names it; one every check of which passed, a
    skipped check among them, reads green; one still running reads neither red
    nor green and says it is pending; a commit nothing has reported on reads
    pending too, with no checks at all, which is what tells the two apart; two
    runs of one check are read at the later one, as every other rollup here is
    deduplicated; a repository GitHub will not read, one it names no default
    branch for, a branch it names no commit on, a rollup holding something that
    is not a check, and a query it refuses each answer no reading and say why,
    the last four being what pins the fail-closed contract.

    `report_trunk`, which is what the reconciler calls: one line per shape,
    naming the branch, the abbreviated commit and its subject, and the failing
    checks where there are any; and the reading handed back for solorepo's #984
    and solorepo's #985 to read.
    """
    channel, _, programs = load_channel()
    actions = programs["move"].cli.reconcile.actions
    return _reading_cases(channel, actions) + _log_cases(channel, actions)


def _answering(checks: Any, ref: str | None = "main", oid: str | None = "0123456789abcdef") -> Any:
    """A GraphQL that answers the trunk query from what a case holds.

    `ref` None is a repository GitHub names no default branch for, and `oid`
    None a branch it names no commit on. `checks` None is a commit with no
    rollup, which is what GitHub answers before anything has reported.
    """
    def graphql(query: str, **variables: Any) -> Any:
        if ref is None:
            return {"data": {"repository": {"defaultBranchRef": None}}}
        target: dict[str, Any] = {} if oid is None else {
            "oid": oid, "messageHeadline": "the commit that landed",
            "statusCheckRollup": None if checks is None else {"contexts": {"nodes": checks}}}
        return {"data": {"repository": {"defaultBranchRef": {"name": ref, "target": target}}}}
    return graphql


def _refusing(query: str, **variables: Any) -> Any:
    """A GraphQL read GitHub refuses, in the shape the channel exits with."""
    raise SystemExit(REFUSED)


def _unreadable(query: str, **variables: Any) -> Any:
    """A repository the token cannot see: GitHub answers `repository` null, not no key."""
    return {"data": {"repository": None}}


def _malformed(query: str, **variables: Any) -> Any:
    """A rollup holding something that is not a check, which nothing in the query admits."""
    return _answering(["gate"])(query, **variables)


def _reading_cases(channel: Any, actions: Any) -> list[str]:
    """`trunk_health` over each rollup and each way the read can answer nothing."""
    cases: list[tuple[str, Any, tuple[bool, bool, list[str]]]] = [
        ("a failed check", _answering(RED), (True, False, ["python seed"])),
        ("every check passed, one skipped", _answering(GREEN), (False, False, [])),
        ("a check still running", _answering(RUNNING), (False, True, [])),
        ("nothing reported yet", _answering(None), (False, True, [])),
        ("a re-run that healed the commit", _answering(STALE), (False, False, [])),
    ]
    problems = []
    for name, graphql, expected in cases:
        with stood_in(channel, graphql=graphql):
            found, why = actions.trunk_health("o", "r")
        if found is None:
            problems.append(f"trunk_health: {name} read nothing — {why}")
            continue
        got = (found.red, found.pending, found.failing)
        if got != expected:
            problems.append(f"trunk_health: {name} read {got}, not {expected}")
        if found.ref != "main" or found.oid != "0123456789abcdef":
            problems.append(f"trunk_health: {name} named {found.ref} at {found.oid}, not the "
                            "branch and commit GitHub answered with")
    if (checks := _reading(channel, actions, _answering(STALE))[0]) and len(checks.checks) != 1:
        problems.append(f"trunk_health: two runs of one check read as {checks.checks}, where "
                        "the rollup is deduplicated to the later run, as every other is")

    for name, graphql, expect in [("no default branch", _answering(GREEN, ref=None),
                                   "no default branch"),
                                  ("no commit on the branch", _answering(GREEN, oid=None),
                                   "no commit on main"),
                                  ("a repository it would not read", _unreadable,
                                   "named no repository o/r"),
                                  ("a rollup that is not checks", _malformed,
                                   "did not ask for"),
                                  ("a refused query", _refusing, REFUSED)]:
        found, why = _reading(channel, actions, graphql)
        if found is not None or expect not in why:
            problems.append(f"trunk_health: {name} read {found!r} saying {why!r}, where nothing "
                            f"is read and the reason names {expect!r}")
    return problems


def _reading(channel: Any, actions: Any, graphql: Any) -> tuple[Any, str]:
    """One `trunk_health` with the channel's GraphQL stood in."""
    with stood_in(channel, graphql=graphql):
        found, why = actions.trunk_health("o", "r")
    return found, str(why)


def _log_cases(channel: Any, actions: Any) -> list[str]:
    """`report_trunk`: one line per shape, and the reading handed back."""
    cases: list[tuple[str, Any, str]] = [
        ("a failed check", _answering(RED), "trunk is red — main at 0123456 (the commit that "
                                            "landed) fails python seed"),
        ("every check passed", _answering(GREEN), "trunk is green"),
        ("a check still running", _answering(RUNNING), "trunk is still running its checks"),
        ("nothing reported yet", _answering(None), "trunk has no checks reported"),
        ("a refused query", _refusing, "could not read trunk's check rollup"),
    ]
    problems = []
    for name, graphql, said in cases:
        with stood_in(channel, graphql=graphql):
            ended = outcome(lambda: actions.report_trunk("o", "r"))
        if said not in ended.out:
            problems.append(f"report_trunk: {name} said {ended.out!r}, where the log reads "
                            f"{said!r}")
    with stood_in(channel, graphql=_answering(RED)):
        handed = actions.report_trunk("o", "r")
    if handed is None or not handed.red:
        problems.append(f"report_trunk: a red trunk handed back {handed!r}, where the reading "
                        "is what solorepo's #984 and solorepo's #985 read")
    return problems
