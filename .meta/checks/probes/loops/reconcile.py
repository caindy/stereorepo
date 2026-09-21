"""`reconcile`: one act per owed state, none under a run, none unless live (solorepo's DR-264).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import datetime
from typing import Any

from checks.collect import check
from checks.probes.harness import load_channel, outcome, stood_in, unanswered

REFUSED = "gh: refused the dispatch"
"""What a dispatch stood in for to fail exits with, in the words the channel exits with."""

FAILED_MERGE = f"say: #{9} is open after the merge call"
"""What a merge manager whose candidate did not land exits with."""

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
CHANGES = [{"author": {"login": REVIEWER}, "state": "CHANGES_REQUESTED"}]
ASKED = [{"login": REVIEWER}]

MINUTES = 30.0
"""The bound every pass here is run under, passed rather than read off the verb's default."""


@check("reconcile probes", pre=True)
def reconcile_probes() -> list[str]:
    """The reconciler's two readers and its one pass (solorepo's DR-264).

    `owed_by_pull`, over the classifiers' states: a conflicting branch under
    a verdict owes a rebase pass and one under nothing owes none; changes
    requested with no request owes a review pass; a failed gate under an
    approval owes one, and under a request whose reviewer check is the one
    that failed owes the request again; a green pull request with no verdict,
    request, or arming owes its first request, and armed owes nothing; a
    Challenge in any state but resumable is held, the claim read as nobody's
    so that `hard` under a claim is not swallowed by `TAKEN`; not free owes
    nothing.

    `owed_by_issue`, one case per state, ten in all: unread and quiet owes the
    door again and read or within the hour does not; offered and free owes
    the take, and blocked, under a run, or too soon does not; claimed past
    the longest run owes the release and within it does not; the rest owe
    nothing.

    `reconcile`, against a GitHub answered from a dict with timestamps read
    off the clock: the merge manager runs first and its exit is held to the
    end; one act is performed per owed state and none where a run is in
    flight; a Challenge whose pull request is in draft is counted as having
    one and not re-taken; a blocked one is not taken; a Challenge a triage
    run read is not re-delivered; without `--live` every act is reported and
    none performed; a conflict the listing answers `UNKNOWN` for is settled
    before it is read and owes the rebase pass, not the review pass; runs
    GitHub will not list hold every act and say so; and a refused act is
    printed and the next is performed.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    return _pull_cases(move) + _issue_cases(move) + _pass_cases(channel, move)


def _ago(minutes: float) -> str:
    """A timestamp `minutes` before now, as GitHub writes one."""
    when = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=minutes)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pull(number: int, **fields: Any) -> dict[str, Any]:
    """A loop branch's pull request as `RECONCILE_FIELDS` lists it, over shared defaults."""
    base = {"number": number, "title": f"pull {number}", "headRefName": f"claude/issue-{number}",
            "baseRefName": "main", "isDraft": False, "mergeable": "MERGEABLE",
            "statusCheckRollup": GREEN, "latestReviews": [], "reviews": [], "reviewRequests": [],
            "autoMergeRequest": None, "updatedAt": _ago(120)}
    return {**base, **fields}


def _pull_cases(move: Any) -> list[str]:
    """`owed_by_pull` over each shape the classifiers name, a held Challenge, and not free."""
    issues = move.check_pr.state.IssueState
    cases: list[tuple[str, dict[str, Any], Any, bool, str | None]] = [
        ("conflicting under a verdict", _pull(1, mergeable="CONFLICTING", latestReviews=CHANGES),
         issues.RESUMABLE, True, "rebase"),
        ("conflicting under nothing", _pull(1, mergeable="CONFLICTING"), issues.RESUMABLE, True,
         None),
        ("changes requested, unanswered", _pull(1, latestReviews=CHANGES), issues.RESUMABLE,
         True, "review"),
        ("changes requested, review requested", _pull(1, latestReviews=CHANGES,
                                                       reviewRequests=ASKED),
         issues.RESUMABLE, True, None),
        ("approved with failing checks", _pull(1, latestReviews=APPROVED, statusCheckRollup=RED),
         issues.RESUMABLE, True, "review"),
        ("requested, reviewer check failed", _pull(1, reviewRequests=ASKED,
                                                    statusCheckRollup=REVIEWER_FAILED),
         issues.RESUMABLE, True, "request"),
        ("requested, checks pending", _pull(1, reviewRequests=ASKED,
                                             statusCheckRollup=[{"name": "gate",
                                                                 "status": "IN_PROGRESS"}]),
         issues.RESUMABLE, True, None),
        ("green and nobody holds it", _pull(1), issues.RESUMABLE, True, "request"),
        ("green and armed", _pull(1, autoMergeRequest={"enabledAt": "x"}), issues.RESUMABLE,
         True, None),
        ("held", _pull(1), issues.HELD, True, "hold"),
        ("held and not free", _pull(1), issues.HELD, False, "hold"),
        ("read as the coder's, which a claim at hard would be", _pull(1), issues.TAKEN, True,
         "hold"),
        ("unread", _pull(1), issues.UNREAD, True, "hold"),
        ("no open Challenge", _pull(1), None, True, None),
        ("not free", _pull(1, latestReviews=CHANGES), issues.RESUMABLE, False, None),
    ]
    problems = []
    for name, pull, found, free, expected in cases:
        state = move.check_pr.classify_pr(pull, move.deduplicate_checks(pull["statusCheckRollup"]),
                                          None, REVIEWER)
        act = move.owed_by_pull(pull, found, state, REVIEWER, free)
        kind = act.kind if act else None
        if kind != expected:
            problems.append(f"owed_by_pull: {name} owed {kind!r}, not {expected!r}")
    return problems


def _issue_cases(move: Any) -> list[str]:
    """`owed_by_issue` over all ten states, each bound within and past, blocked, and under a run."""
    states = move.check_pr.state.IssueState
    quiet = move.Quiet(True, True, True, False, 600.0)
    cases: list[tuple[str, Any, Any, str | None]] = [
        ("unread and quiet", states.UNREAD, quiet, "reread"),
        ("unread, read or within the hour", states.UNREAD,
         move.Quiet(True, False, True, False, 600.0), None),
        ("offered and free", states.OFFERED, quiet, "take"),
        ("offered under a run, or too soon", states.OFFERED,
         move.Quiet(False, True, True, False, 5.0), None),
        ("offered and blocked", states.OFFERED, move.Quiet(True, True, True, True, 600.0), None),
        ("claimed past the longest run", states.CLAIMED, quiet, "release"),
        ("claimed within the longest run", states.CLAIMED,
         move.Quiet(True, True, False, False, 40.0), None),
        ("held", states.HELD, quiet, None),
        ("handed back", states.HANDED_BACK, quiet, None),
        ("taken", states.TAKEN, quiet, None),
        ("resumable", states.RESUMABLE, quiet, None),
        ("roadmap", states.ROADMAP, quiet, None),
        ("unlabelled", states.UNLABELLED, quiet, None),
        ("closed", states.CLOSED, quiet, None),
    ]
    problems = []
    for name, found, when, expected in cases:
        act = move.owed_by_issue({"number": 5}, found, when)
        kind = act.kind if act else None
        if kind != expected:
            problems.append(f"owed_by_issue: {name} owed {kind!r}, not {expected!r}")
    return problems


class _GitHub:
    """As much of GitHub as `reconcile` asks about, answered from what a case holds.

    The open pull requests and Issues, the runs of each workflow answered by
    status where one is asked for, `pr view` answered from `views` where a
    case holds a settled read, and the takes it dispatches, recorded in
    `dispatched`. `unlistable` refuses every run listing.
    """

    def __init__(self, pulls: list[dict[str, Any]], issues: list[dict[str, Any]],
                 runs: dict[str, list[dict[str, Any]]],
                 views: dict[int, dict[str, Any]] | None = None) -> None:
        self.pulls, self.issues, self.runs = pulls, issues, runs
        self.views = views or {}
        self.dispatched: list[tuple[str, ...]] = []
        self.unlistable = False

    def __call__(self, *args: str, **kwargs: Any) -> Any:
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("pr", "list"):
            return list(self.pulls)
        if args[:2] == ("pr", "view"):
            number = int(args[2])
            return dict(self.views.get(number)
                        or next(p for p in self.pulls if int(p["number"]) == number))
        if args[:2] == ("issue", "list"):
            return list(self.issues)
        if args[:2] == ("issue", "view"):
            return {"state": "OPEN", "labels": [{"name": "challenge"}, {"name": "medium"}],
                    "assignees": []}
        if args[:2] == ("run", "list"):
            if self.unlistable:
                return kwargs.get("default")
            runs = list(self.runs.get(args[args.index("--workflow") + 1], []))
            if "--status" in args:
                wanted = args[args.index("--status") + 1]
                runs = [r for r in runs if r.get("status") == wanted]
            return runs
        if args[:2] == ("workflow", "run"):
            self.dispatched.append(args)
            return ""
        raise unanswered(args, "the reconcile fake")


class _Bench:
    """The verbs `reconcile` performs stood in by recorders, and the fixtures every pass reads.

    `acted` records each act as `(kind, number)`, the merge manager as
    `("merge_manager", None)`; `pulls` and `issues` are the fixtures, with
    their timestamps read off the clock: a pull request with changes
    requested, one conflicting under an approval, one green and unheld, and
    one in draft, and one under a claimed Challenge at `hard`; a Challenge
    behind each of the first three, an unread one, an offered one, one
    claimed with no pull request, one offered but blocked, one behind the
    draft, one offered with no `updatedAt`, and the claimed one at `hard`.
    """

    def __init__(self, channel: Any, move: Any) -> None:
        self.channel, self.move = channel, move
        self.acted: list[tuple[str, Any]] = []
        acted = self.acted
        self.stood = {"merge_manager": lambda **_: acted.append(("merge_manager", None)),
                      "run_coder": lambda pr, task: acted.append((task, int(pr))),
                      "request_review": lambda pr, to: acted.append(("request", int(pr))),
                      "release": lambda n: acted.append(("release", int(n))),
                      "relabel": lambda n, **kw: acted.append(("relabel", (int(n), tuple(kw)))),
                      "stacked": lambda n: None}
        self.pulls = [_pull(1, latestReviews=CHANGES),
                      _pull(2, mergeable="CONFLICTING", latestReviews=APPROVED),
                      _pull(3),
                      _pull(8, isDraft=True),
                      _pull(12, latestReviews=CHANGES)]
        self.issues = [self.issue(1, "medium"), self.issue(4, None), self.issue(5, "easy"),
                       self.issue(6, "easy", claimed=True),
                       self.issue(10, "easy", blocked_by=[4]),
                       self.issue(8, "easy"),
                       self.issue(11, "easy", moved=False),
                       self.issue(12, "hard", claimed=True)]

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
        """One `reconcile` with GitHub and the verbs stood in, `stood` over the recorders."""
        self.acted.clear()
        fake.dispatched.clear()
        flags.setdefault("minutes", MINUTES)
        with stood_in(self.channel, gh=fake), \
             stood_in(self.move, **{**self.stood, **(stood or {})}):
            return outcome(lambda: self.move.reconcile(**flags))


def _pass_cases(channel: Any, move: Any) -> list[str]:
    """`reconcile` end to end: each act once live, reported otherwise, none under a run."""
    bench = _Bench(channel, move)
    problems = _edge_cases(bench)
    fake = _GitHub(bench.pulls, bench.issues, {})
    ended = bench.run(fake, live=True)
    expected = {("merge_manager", None), ("review", 1), ("rebase", 2), ("request", 3),
                ("relabel", (4, ("remove",))), ("relabel", (4, ("add",))), ("release", 6)}
    acted = bench.acted
    if ended.code is not None or set(acted) != expected or len(acted) != len(expected):
        problems.append(f"reconcile: live over the fixtures performed {acted} with exit "
                        f"{ended.code!r}, not one act per owed state {sorted(expected)}")
    if f"holding #{12}" not in ended.out:
        problems.append(f"reconcile: a claimed Challenge at hard behind an open pull request was "
                        f"not held: {ended.out!r}")
    taken = sorted(a[a.index("-f") + 1] for a in fake.dispatched)
    if taken != ["issue=11", "issue=5"]:
        problems.append(f"reconcile: the takes dispatched were {taken}, where the offered "
                        "Challenge and the one that never moved are owed one each, and the "
                        "blocked one and the one behind a draft none")

    ended = bench.run(fake, live=False)
    if ended.code is not None or acted != [("merge_manager", None)] or fake.dispatched:
        problems.append(f"reconcile: not live performed {acted} and dispatched "
                        f"{fake.dispatched}, where every act should have been reported")
    if f"would dispatch a review pass for #{1}" not in ended.out:
        problems.append(f"reconcile: not live did not say what it would do: {ended.out!r}")

    busy = {"coder.yml": [{"displayTitle": f"coder-issue-#{1}", "status": "in_progress",
                           "headBranch": "claude/issue-1"},
                          {"displayTitle": f"coder-issue-#{5}", "status": "queued",
                           "headBranch": "main"}],
            "review.yml": [{"displayTitle": "review", "status": "in_progress",
                            "headBranch": "claude/issue-3"}],
            "triage.yml": [{"displayTitle": f"triage-issue-#{4}", "status": "completed",
                            "conclusion": "success", "headBranch": "main"}]}
    ended = bench.run(_GitHub(bench.pulls, bench.issues, busy), live=True)
    left = {a for a in acted if a[0] != "merge_manager"}
    if left != {("rebase", 2), ("release", 6)}:
        problems.append(f"reconcile: with runs in flight, and a triage run that read, it "
                        f"performed {sorted(left)}, where only the rebase and the release were "
                        "owed")
    return problems


def _refusing(pr: Any, task: str) -> None:
    """A dispatch GitHub refuses, in the words the channel exits with."""
    raise SystemExit(REFUSED)


def _failing(**_: Any) -> None:
    """A merge manager whose candidate failed to land."""
    raise SystemExit(FAILED_MERGE)


def _edge_cases(bench: _Bench) -> list[str]:
    """An `UNKNOWN` off the listing, unlistable runs, a refused dispatch, and a failed merge."""
    problems = []
    unknown = _pull(7, mergeable="UNKNOWN", latestReviews=CHANGES)
    settling = _GitHub([unknown], [], {}, views={7: {**unknown, "mergeable": "CONFLICTING"}})
    with stood_in(bench.channel, MERGEABILITY=(2, 0)):
        bench.run(settling, live=True)
    if ("rebase", 7) not in bench.acted or ("review", 7) in bench.acted:
        problems.append(f"reconcile: a conflict the listing answered UNKNOWN for was owed "
                        f"{[a for a in bench.acted if a[1] == 7]}, not the rebase pass the "
                        "settled read shows")

    unlistable = _GitHub(bench.pulls, bench.issues, {})
    unlistable.unlistable = True
    ended = bench.run(unlistable, live=True)
    held = [a for a in bench.acted if a[0] != "merge_manager"]
    if held or unlistable.dispatched or "could not be listed" not in ended.out:
        problems.append(f"reconcile: with runs GitHub would not list it performed {held} and "
                        f"dispatched {unlistable.dispatched}, and said {ended.out!r}, where "
                        "every act is held and the log says why")

    ended = bench.run(_GitHub(bench.pulls, bench.issues, {}), {"run_coder": _refusing}, live=True)
    if ended.code is not None or ("request", 3) not in bench.acted or "could not" not in ended.out:
        problems.append(f"reconcile: a refused dispatch ended the pass with {ended.code!r} and "
                        f"{bench.acted}, where the refusal is printed and the next act performed")

    ended = bench.run(_GitHub(bench.pulls, bench.issues, {}), {"merge_manager": _failing},
                      live=True)
    if ended.code != FAILED_MERGE or ("review", 1) not in bench.acted:
        problems.append(f"reconcile: a failed merge ended with {ended.code!r} after "
                        f"{bench.acted}, where the reading goes on and the merge's code is "
                        "the exit")
    return problems
