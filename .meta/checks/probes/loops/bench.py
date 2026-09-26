"""Loop test doubles and fixture bench for loop probe test suites (solorepo's DR-217).

Provides simulated GitHub interactions, workflow runs, pull request states,
and verb recorders for loop probes.
"""
import contextlib
import datetime
from typing import Any

from checks.probes.harness import outcome, stood_in, unanswered

REFUSED = "gh: refused the dispatch"
"""What a dispatch stood in for to fail exits with, in the words the channel exits with."""

REVIEWER = "o-r-reviewer"
"""The reviewer Role's login over `o/r`."""

CODER = "o-r-coder"
"""The coder Role's login over `o/r`."""

GREEN = [{"name": "gate", "conclusion": "SUCCESS"}]
"""A rollup every check of which passed."""

RED = [{"name": "gate", "conclusion": "FAILURE"}]
"""A rollup with a failed check."""

REVIEWER_FAILED = [{"name": "gate", "conclusion": "SUCCESS"},
                   {"name": "reviewer", "conclusion": "FAILURE"}]
"""A rollup whose reviewer check failed."""

APPROVED = [{"author": {"login": REVIEWER}, "state": "APPROVED"}]
"""An approval verdict from the reviewer Role."""

CHANGES = [{"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"}]
"""A changes-requested verdict from the reviewer Role."""

COMMENT = [{"author": {"login": REVIEWER}, "state": "COMMENTED",
            "body": "withholding approval on the two open threads"}]
"""A comment verdict: approval withheld in prose rather than in GitHub's state for it."""

REPLY = [{"author": {"login": REVIEWER}, "state": "COMMENTED", "body": ""}]
"""A bodiless comment review, which is what GitHub records around a reply on a thread."""

PASSER_BY = [{"author": {"login": CODER}, "state": "COMMENTED",
              "body": "a remark from an account that is not the reviewer Role's"}]
"""A comment verdict from somebody the classifier is not asked about."""

OWED = [{"isResolved": False,
         "comments": {"nodes": [{"body": "the point, and nobody has answered it"}]}}]
"""A review thread owed an answer."""

ANSWERED = [{"isResolved": True,
             "comments": {"nodes": [{"body": "the point"}, {"body": "the answer to it"}]}}]
"""A review thread answered and resolved."""

PARKED = [{"isResolved": False,
           "comments": {"nodes": [{"body": "**Noticed and not done.** the item, held for the "
                                           "solo"}]}}]
"""A review thread parked as noticed and not done, which is held open until merge."""

CONVERSATIONS = {24: OWED, 25: ANSWERED, 26: OWED, 27: ANSWERED, 28: PARKED,
                 30: ANSWERED, 31: ANSWERED}
"""What GraphQL holds for the fixtures the listing cannot answer for, by pull request.

`RECONCILE_FIELDS` carries no `reviewThreads`, so a pull request whose
classification turns on them is read through GraphQL and the rest are not:
24 and 26 owe an answer, 25, 27, 30 and 31 owe none, and 28 holds a parked
notice.
"""

ASKED = [{"login": REVIEWER}]
"""A review request naming the reviewer Role."""

MINUTES = 30.0
"""The bound every pass here is run under, passed rather than read off the verb's default."""


def _ago(minutes: float) -> str:
    """A timestamp `minutes` before now, as GitHub writes one."""
    when = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=minutes)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _notice(move: Any, number: int, tagged: bool = True) -> list[dict[str, Any]]:
    """The sweep's standing advance notice on a pull request (solorepo's DR-255).

    Tagged `replay-refused head:<oid>` against the pull request's own head,
    which is the finding `advance.stalled_behind` admits, or untagged, which
    is every other problem a sweep reports under the same marker.
    """
    tag = f" {move.REPLAY_REFUSED_TAG} head:head{number}" if tagged else ""
    return [{"id": 1, "body": f"{move.ADVANCE_NOTICE_MARKER}{tag}\n"
                              "> the sweep could not advance this branch"}]


def _pull(number: int, **fields: Any) -> dict[str, Any]:
    """A loop branch's pull request as `RECONCILE_FIELDS` lists it, over shared defaults."""
    base = {"number": number, "title": f"pull {number}", "headRefName": f"claude/issue-{number}",
            "headRefOid": f"head{number}",
            "baseRefName": "main", "isDraft": False, "mergeable": "MERGEABLE",
            "statusCheckRollup": GREEN, "latestReviews": [], "reviews": [], "reviewRequests": [],
            "autoMergeRequest": None, "updatedAt": _ago(120)}
    return {**base, **fields}


class _GitHub:
    """As much of GitHub as `reconcile` asks about, answered from what a case holds.

    The open pull requests and Issues, the runs of each workflow answered by
    status where one is asked for, `pr view` answered from `views` where a
    case holds a settled read, the review threads of each pull request
    answered over GraphQL from `threads` with the numbers asked for recorded
    in `queried`, repository check inquiries answered from `trunk_checks`,
    and the takes it dispatches, recorded in `dispatched`.
    `unlistable` refuses every run listing.
    """

    def __init__(self, pulls: list[dict[str, Any]], issues: list[dict[str, Any]],
                 runs: dict[str, list[dict[str, Any]]],
                 views: dict[int, dict[str, Any]] | None = None,
                 threads: dict[int, list[dict[str, Any]]] | None = None) -> None:
        """Initialize the simulated GitHub state for loop reconciliation test cases."""
        self.pulls = [dict(p) for p in pulls]
        self.issues, self.runs = issues, runs
        self.views = views or {}
        self.threads = CONVERSATIONS if threads is None else threads
        self.trunk_checks: list[dict[str, Any]] | None = GREEN
        self.trunk_ref: str | None = "main"
        self.trunk_oid: str | None = "0123456789abcdef"
        self.trunk_headline = "the commit that landed"
        self.dispatched: list[tuple[str, ...]] = []
        self.queried: list[int] = []
        self.unlistable = False
        self.unreadable = False

    @staticmethod
    def asked_for(pull: dict[str, Any], asked: list[str]) -> dict[str, Any]:
        """A pull request as `--json` asked for it, which is all of it where nothing was asked.

        GitHub answers the fields named and no others, so a field dropped from
        `RECONCILE_FIELDS` is one no reader here can still read: the arm that
        turns on it fails rather than staying green off a payload the fake
        hands back regardless.
        """
        return {k: v for k, v in pull.items() if k in asked} if asked else dict(pull)

    def graphql(self, query: str, **variables: Any) -> dict[str, Any]:
        """The review threads or trunk checks asked for, and the ask recorded.

        Inspects parameter signatures to discriminate between PR thread queries
        and repository check inquiries (solorepo's #1059). `unreadable` refuses
        the query in the words the channel exits with.
        """
        if self.unreadable:
            raise SystemExit(REFUSED)
        if "number" in variables:
            number = int(variables["number"])
            self.queried.append(number)
            return {"data": {"repository": {"pullRequest": {
                "reviewThreads": {"nodes": self.threads.get(number, [])}}}}}
        if "owner" in variables and "name" in variables:
            target: dict[str, Any] = {}
            if self.trunk_oid is not None:
                rollup = (None if self.trunk_checks is None
                          else {"contexts": {"nodes": self.trunk_checks}})
                target = {"oid": self.trunk_oid, "messageHeadline": self.trunk_headline,
                          "statusCheckRollup": rollup}
            ref = (None if self.trunk_ref is None
                   else {"name": self.trunk_ref, "target": target})
            return {"data": {"repository": {"defaultBranchRef": ref}}}
        raise unanswered(variables, "the bench graphql fake")

    def __call__(self, *args: str, **kwargs: Any) -> Any:
        """Simulate a gh CLI invocation matching the provided command arguments."""
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        asked = args[args.index("--json") + 1].split(",") if "--json" in args else []
        if args[:2] == ("pr", "list"):
            return [self.asked_for(pull, asked) for pull in self.pulls]
        if args[:2] == ("pr", "view"):
            number = int(args[2])
            return self.asked_for(self.views.get(number)
                                  or next(p for p in self.pulls if int(p["number"]) == number),
                                  asked)
        if args[:2] == ("issue", "list"):
            return list(self.issues)
        if args[:2] == ("issue", "view"):
            return {"state": "OPEN", "labels": [{"name": "challenge"}, {"name": "medium"}],
                    "assignees": []}
        if args[:2] == ("run", "list"):
            if self.unlistable:
                return kwargs.get("default")
            workflow = args[args.index("--workflow") + 1] if "--workflow" in args else "all"
            runs = list(self.runs.get(workflow, []))
            if "--status" in args:
                wanted = args[args.index("--status") + 1]
                runs = [r for r in runs if r.get("status") == wanted]
            return runs
        if args[:2] == ("workflow", "run"):
            self.dispatched.append(args)
            return ""
        if args[:2] == ("pr", "ready"):
            number = int(args[2])
            pull = next((p for p in self.pulls if int(p["number"]) == number), None)
            if pull is not None:
                pull["isDraft"] = "--undo" in args
            return ""
        raise unanswered(args, "the reconcile fake")


class _Bench:
    """The verbs `reconcile` performs stood in by recorders, and the fixtures every pass reads.

    `acted` records each act as `(kind, number)`, the merge manager as
    `("merge_manager", None)`; `pulls` and `issues` are the fixtures, with
    their timestamps read off the clock. The pull requests, by number: 1
    with changes requested, 2 conflicting under an approval, 3 green and
    unheld, 8 in draft, 12 under a claimed Challenge at `hard`, and four
    stacks that hold the rule that a conflicting stack is resolved from the
    bottom: 13 a conflicting approved root with 14 a conflicting approved
    layer on it, 15 conflicting under no request and no verdict, 16 a clean
    root under a request with 17 a conflicting approved layer on it, 18 a
    conflicting draft root with 19 a conflicting approved layer on it, and
    20 a conflicting root on the solo's own branch with 21 a conflicting
    approved layer on it, and 22 a conflicting root under a claimed
    Challenge at `hard` with 23 a conflicting approved layer on it; two
    under a comment verdict whose threads only GraphQL can answer for,
    24 with one owed an answer and 25 with every one answered; four
    approved, 26 with a thread owed an answer, 27 with every one
    answered, 28 with a notice parked, and 29 with a failed gate, which
    is settled before its threads are reached; and two approved and
    `BEHIND` with a replay refused on their heads, 30 unstacked and 31 a
    layer above the conflicting root 13, which holds it. The Challenges: one
    behind each of the first three, an unread one, an offered one, one
    claimed with no pull request, one offered but blocked, one behind
    the draft, one offered with no `updatedAt`, and the claimed ones at
    `hard` behind 12 and 22.
    """

    def __init__(self, channel: Any, move: Any) -> None:
        """Initialize bench fixtures and stood-in move verb recorders."""
        self.channel, self.move = channel, move
        self.acted: list[tuple[str, Any]] = []
        self.filed: list[tuple[str, str]] = []
        self.stopped: list[tuple[int, str]] = []
        acted = self.acted

        def _file(title: str, body: str) -> None:
            acted.append(("file", 0))
            self.filed.append((title, body))

        def _stop(n: Any, body: str) -> None:
            acted.append(("escalate", int(n)))
            self.stopped.append((int(n), body))

        self.stood = {"merge_manager": lambda **_: acted.append(("merge_manager", None)),
                      "run_coder": lambda pr, task: acted.append((task, int(pr))),
                      "request_review": lambda pr, to: acted.append(("request", int(pr))),
                      "release": lambda n: acted.append(("release", int(n))),
                      "relabel": lambda n, **kw: acted.append(("relabel", (int(n), tuple(kw)))),
                      "file_issue": _file,
                      "stop": _stop,
                      "stacked": lambda n: None}
        self.pulls = [_pull(1, latestReviews=CHANGES),
                      _pull(2, mergeable="CONFLICTING", latestReviews=APPROVED),
                      _pull(3),
                      _pull(8, isDraft=True),
                      _pull(12, latestReviews=CHANGES),
                      _pull(13, mergeable="CONFLICTING", latestReviews=APPROVED),
                      _pull(14, baseRefName="claude/issue-13", mergeable="CONFLICTING",
                            latestReviews=APPROVED),
                      _pull(15, mergeable="CONFLICTING"),
                      _pull(16, reviewRequests=[{"login": REVIEWER}]),
                      _pull(17, baseRefName="claude/issue-16", mergeable="CONFLICTING",
                            latestReviews=APPROVED),
                      _pull(18, isDraft=True, mergeable="CONFLICTING"),
                      _pull(19, baseRefName="claude/issue-18", mergeable="CONFLICTING",
                            latestReviews=APPROVED),
                      _pull(20, headRefName="claude/stack-root", mergeable="CONFLICTING"),
                      _pull(21, baseRefName="claude/stack-root", mergeable="CONFLICTING",
                            latestReviews=APPROVED),
                      _pull(22, mergeable="CONFLICTING", latestReviews=APPROVED),
                      _pull(23, baseRefName="claude/issue-22", mergeable="CONFLICTING",
                            latestReviews=APPROVED),
                      _pull(24, latestReviews=COMMENT, reviews=COMMENT),
                      _pull(25, latestReviews=COMMENT, reviews=COMMENT),
                      _pull(26, latestReviews=APPROVED, reviews=APPROVED),
                      _pull(27, latestReviews=APPROVED, reviews=APPROVED),
                      _pull(28, latestReviews=APPROVED, reviews=APPROVED),
                      _pull(29, latestReviews=APPROVED, reviews=APPROVED,
                            statusCheckRollup=RED),
                      _pull(30, latestReviews=APPROVED, reviews=APPROVED,
                            mergeStateStatus="BEHIND", comments=_notice(move, 30)),
                      _pull(31, baseRefName="claude/issue-13", latestReviews=APPROVED,
                            reviews=APPROVED, mergeStateStatus="BEHIND",
                            comments=_notice(move, 31))]
        self.issues = [self.issue(1, "medium"), self.issue(4, None), self.issue(5, "easy"),
                       self.issue(6, "easy", claimed=True),
                       self.issue(10, "easy", blocked_by=[4]),
                       self.issue(8, "easy"),
                       self.issue(11, "easy", moved=False),
                       self.issue(12, "hard", claimed=True),
                       self.issue(22, "hard", claimed=True)]

    def issue(self, number: int, level: str | None, claimed: bool = False,
              blocked_by: list[int] | None = None, moved: bool = True) -> dict[str, Any]:
        """An open Challenge as `ISSUE_FIELDS` lists it, moved two hours ago unless never."""
        labels = ["challenge"] + ([level] if level else [])
        row = {"number": number, "labels": [{"name": name} for name in labels],
               "assignees": [{"login": CODER}] if claimed else [],
               "blockedBy": {"nodes": [{"number": n} for n in blocked_by or []]},
               "createdAt": _ago(180)}
        if moved:
            row["updatedAt"] = _ago(120)
        return row

    def run(self, fake: _GitHub, stood: dict[str, Any] | None = None, **flags: Any) -> Any:
        """One `reconcile` with GitHub and the verbs stood in, `stood` over the recorders.

        Each verb is stood in on the module of `lib.move` that defines it,
        which is where a caller in the package looks it up (solorepo's DR-217).
        """
        self.acted.clear()
        self.filed.clear()
        self.stopped.clear()
        fake.dispatched.clear()
        fake.queried.clear()
        flags.setdefault("minutes", MINUTES)
        by_module: dict[Any, dict[str, Any]] = {}
        for name, fake_verb in {**self.stood, **(stood or {})}.items():
            by_module.setdefault(_owner(self.move, name), {})[name] = fake_verb
        with contextlib.ExitStack() as stack:
            stack.enter_context(stood_in(self.channel, gh=fake, graphql=fake.graphql))
            for module, verbs in by_module.items():
                stack.enter_context(stood_in(module, **verbs))
            return outcome(lambda: self.move.reconcile(**flags))


UNDEFINED = "no module of lib.move defines {name!r}"
"""What standing in a name no module of the package defines raises."""


def _owner(move: Any, name: str) -> Any:
    """The module of `lib.move` that defines `name`, reached through the entry's exports.

    Four modules absent from the entry's `from lib.move import` line are reached through
    one that imports them (solorepo's DR-217); `lib/move/__init__.py` gives each its reason.
    """
    modules = (move.common, move.challenges, move.pull_requests, move.decisions,
               move.cli.handoff, move.manager.advance, move.manager, move.cli.reconcile,
               move.cli.reconcile.actions, move.cli)
    for module in modules:
        held = getattr(module, name, None)
        if held is not None and getattr(held, "__module__", None) == module.__name__:
            return module
    raise AssertionError(UNDEFINED.format(name=name))


FAILED_MERGE = f"say: #{9} is open after the merge call"
"""What a merge manager whose candidate did not land exits with."""


def _refusing(pr: Any, task: str) -> None:
    """A dispatch GitHub refuses, in the words the channel exits with."""
    raise SystemExit(REFUSED)


def _failing(**_: Any) -> None:
    """A merge manager whose candidate failed to land."""
    raise SystemExit(FAILED_MERGE)


def _reading(move: Any) -> Any:
    """A pass's shared reading with nothing standing in it, for the readers that take one."""
    empty = move.Runs([], [])
    return move.Reading(now=datetime.datetime.now(datetime.UTC), bound=MINUTES, longest=75.0,
                        coder=CODER, reviewer_login=REVIEWER, owner="o", name="r",
                        by_number={}, named=set(), coder_runs=empty, review_runs=empty,
                        triage_runs=empty, action_runs=empty)


def _trunk(move: Any, failing: list[str], oid: str = "abc1234def") -> Any:
    """Trunk's HEAD rollup as `report_trunk` answers with one, red where `failing` names a check."""
    return move.cli.reconcile.actions.Trunk(
        ref="main", oid=oid, headline="the commit that landed",
        checks=[{"name": name} for name in failing], failing=failing, pending=False)


def _check_reconcile_draft_demotions(fake: _GitHub) -> list[str]:
    """Verify that conflicting PRs were demoted to draft while maintenance rebases were not."""
    problems: list[str] = []
    p2 = next((p for p in fake.pulls if p["number"] == 2), None)
    p29 = next((p for p in fake.pulls if p["number"] == 29), None)
    p30 = next((p for p in fake.pulls if p["number"] == 30), None)
    if p2 and not p2.get("isDraft"):
        problems.append("reconcile: conflicting pull request 2 was not demoted to draft "
                        "before rebase dispatch")
    if p29 and not p29.get("isDraft"):
        problems.append("reconcile: approved pull request 29 with failing checks "
                        "was not demoted to draft before review dispatch")
    if p30 and p30.get("isDraft"):
        problems.append("reconcile: non-conflict maintenance rebase pull request 30 "
                        "was demoted to draft")
    return problems


def _check_trunk_outcomes(bench: _Bench) -> list[str]:
    """Verify reconciler action sequencing and workflow triggers under clean vs failing
    trunk checks.
    """
    problems: list[str] = []
    stranded = _pull(45, statusCheckRollup=RED, mergeStateStatus="BEHIND")
    clean_fake = _GitHub([stranded], [bench.issue(45, "medium")], {})
    dry_clean = bench.run(clean_fake, live=False)
    if ("rebase", 45) in [a for a in bench.acted if a[0] != "merge_manager"] \
            or f"would dispatch a rebase pass for #{45}" not in dry_clean.out:
        problems.append(f"reconcile: clean trunk did not report rebase for stranded PR: "
                        f"{dry_clean.out!r}")
    if "trunk is green" not in dry_clean.out or "would file the heal Challenge" in dry_clean.out:
        problems.append("reconcile: clean trunk check evaluation was misreported")

    bench.run(clean_fake, live=True)
    p45_clean = next((p for p in clean_fake.pulls if p["number"] == 45), None)
    if ("rebase", 45) not in bench.acted or (p45_clean and p45_clean.get("isDraft")) \
            or ("file", 0) in bench.acted:
        problems.append(f"reconcile: stranded PR behind green trunk was not rebased cleanly: "
                        f"{bench.acted}")

    red_stranded = _pull(45, statusCheckRollup=RED, mergeStateStatus="BEHIND")
    conflicting = _pull(2, mergeable="CONFLICTING", latestReviews=APPROVED)
    failing_app = _pull(29, latestReviews=APPROVED, reviews=APPROVED, statusCheckRollup=RED)
    red_pulls = [red_stranded, conflicting, failing_app]
    red_fake = _GitHub(red_pulls, [bench.issue(45, "medium"), bench.issue(2, "medium"),
                                   bench.issue(29, "medium")], {})
    red_fake.trunk_checks = RED
    dry_red = bench.run(red_fake, live=False)
    if "trunk is red" not in dry_red.out \
            or "would file the heal Challenge for a red trunk" not in dry_red.out \
            or f"would dispatch a rebase pass for #{45}" in dry_red.out:
        problems.append(f"reconcile: red trunk did not report heal filing or suppressed stranded "
                        f"rebase: {dry_red.out!r}")

    bench.run(red_fake, live=True)
    non_mm = [a for a in bench.acted if a[0] != "merge_manager"]
    if ("rebase", 45) in bench.acted or ("file", 0) not in bench.acted or not non_mm \
            or non_mm[0] != ("file", 0):
        problems.append(f"reconcile: red trunk did not sequence heal filing before PR acts: "
                        f"{bench.acted}")
    p2_red = next((p for p in red_fake.pulls if p["number"] == 2), None)
    p29_red = next((p for p in red_fake.pulls if p["number"] == 29), None)
    if ("rebase", 2) not in bench.acted or not (p2_red and p2_red.get("isDraft")) \
            or ("review", 29) not in bench.acted or not (p29_red and p29_red.get("isDraft")):
        problems.append("reconcile: draft demotions or maintenance dispatches failed under red "
                        f"trunk: {bench.acted}")

    heal = {"number": 50,
            "title": bench.move.cli.reconcile.actions.HEAL_TITLE.format(branch="main",
                                                                        commit="0123456"),
            "labels": [{"name": "challenge"}, {"name": "medium"}], "assignees": [],
            "createdAt": _ago(10), "updatedAt": _ago(10)}
    heal_fake = _GitHub([red_stranded], [heal, bench.issue(45, "medium")], {})
    heal_fake.trunk_checks = RED
    dry_heal = bench.run(heal_fake, live=False)
    if f"would dispatch the take pass for #{50}" not in dry_heal.out:
        problems.append(f"reconcile: red trunk did not report take pass for heal Challenge: "
                        f"{dry_heal.out!r}")
    bench.run(heal_fake, live=True)
    dispatched_heal = [a for a in heal_fake.dispatched if a[:3] == ("workflow", "run", "coder.yml")
                       and "-f" in a and "issue=50" in a]
    if not dispatched_heal or ("rebase", 45) in bench.acted:
        problems.append(f"reconcile: heal take pass was not dispatched under red trunk: "
                        f"{heal_fake.dispatched}")
    return problems


GitHub = _GitHub
"""Alias for `_GitHub` test double."""

Bench = _Bench
"""Alias for `_Bench` fixture bench."""
