"""`reconcile`: one act per owed state, none under a run, none unless live (solorepo's DR-264).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import contextlib
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
notice."""

ASKED = [{"login": REVIEWER}]

MINUTES = 30.0
"""The bound every pass here is run under, passed rather than read off the verb's default."""


@check("reconcile probes", pre=True)
def reconcile_probes() -> list[str]:
    """The reconciler's two readers and its one pass (solorepo's DR-264).

    `classify_pr`, over the two arms that turn on the threads, since
    `owed_by_pull` reads the state and not the conditions under it: a
    comment verdict with a thread owed an answer and no request standing
    reads `CHANGES_REQUESTED`, and the same verdict with nothing owed, under
    a review request, bodiless, or left by an account that is not the
    reviewer's reads `AWAITING_REVIEW` (solorepo's DR-265); an approval with
    a notice parked reads `AWAITING_PROMOTION` and one with every thread
    answered `READY_TO_MERGE`, which is the pair no act tells apart
    (solorepo's DR-159).

    `owed_by_pull`, over the classifiers' states: a conflicting branch under
    a verdict owes a rebase pass and one under nothing owes none; changes
    requested with no request owes a review pass, and so does a comment
    verdict with a thread owed an answer and no request standing, which is the
    verdict that withholds approval in prose (solorepo's DR-265); an approval
    ready to merge but behind its base owes the rebase pass where the sweep's
    own advance notice stands on it and nothing where it does not, or where
    the branch is current with a notice the sweep has yet to clear — the same
    verdict owes nothing with nothing owed on it or with a request standing,
    and a bodiless comment review, which is what GitHub records around a reply
    on a thread, is no verdict and owes nothing either; an approval with a
    thread owed an answer owes a review pass, and one with a notice parked
    or every thread answered owes nothing; a failed gate under an approval
    owes one, and under a request whose reviewer check is the one that
    failed owes the request again; a green pull request with no verdict,
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
    before it is read and owes the rebase pass, not the review pass; a
    comment verdict and an approval are each read against the threads the
    listing cannot carry, so one with a thread owed an answer is dispatched
    a review pass and one with every thread answered or a notice parked is
    owed nothing, the read made for those pull requests and no others — a
    conflicting branch and a failed gate are settled before the threads are
    reached — and a read GitHub refuses owes nothing and says so; runs
    GitHub will not list hold every act and say so; and a refused act is
    printed and the next is performed.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    return (_classifier_cases(move) + _pull_cases(move) + _issue_cases(move)
            + _pass_cases(channel, move))


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


def _classifier_cases(move: Any) -> list[str]:
    """`classify_pr` over the two arms that turn on the threads, one condition per case.

    `owed_by_pull` cannot pin these: it answers `None` for a pull request under
    a review request whatever state it was handed, and `None` for
    `AWAITING_PROMOTION` and `READY_TO_MERGE` alike, so a case reading the act
    alone stays green with a condition deleted. Each shape here removes one
    condition of an arm and asserts the state the classifier every reader asks
    reports for it (solorepo's DR-265, solorepo's DR-159).
    """
    states = move.check_pr.PullRequestState
    cases: list[tuple[str, dict[str, Any], Any]] = [
        ("a comment verdict with a thread owed", _pull(1, latestReviews=COMMENT,
                                                       reviewThreads=OWED),
         states.CHANGES_REQUESTED),
        ("a comment verdict with nothing owed", _pull(1, latestReviews=COMMENT),
         states.AWAITING_REVIEW),
        ("a comment verdict under a review request", _pull(1, latestReviews=COMMENT,
                                                           reviewThreads=OWED,
                                                           reviewRequests=ASKED),
         states.AWAITING_REVIEW),
        ("a reply on a thread, which is no verdict", _pull(1, latestReviews=REPLY,
                                                           reviewThreads=OWED),
         states.AWAITING_REVIEW),
        ("a comment verdict from a passer-by", _pull(1, latestReviews=PASSER_BY,
                                                     reviewThreads=OWED),
         states.AWAITING_REVIEW),
        ("an approval with a notice parked", _pull(1, latestReviews=APPROVED,
                                                   reviewThreads=PARKED),
         states.AWAITING_PROMOTION),
        ("an approval with every thread answered", _pull(1, latestReviews=APPROVED,
                                                         reviewThreads=ANSWERED),
         states.READY_TO_MERGE),
    ]
    problems = []
    for name, pull, expected in cases:
        found = move.check_pr.classify_pr(pull, move.deduplicate_checks(pull["statusCheckRollup"]),
                                          None, REVIEWER)
        if found is not expected:
            problems.append(f"classify_pr: {name} read {found!r}, not {expected!r}")
    return problems


def _pull_cases(move: Any) -> list[str]:
    """`owed_by_pull` over each shape the classifiers name, a held Challenge, and not free."""
    issues = move.check_pr.state.IssueState
    notice = _notice(move, 1)
    untagged = _notice(move, 1, tagged=False)
    cases: list[tuple[str, dict[str, Any], Any, bool, str | None]] = [
        ("conflicting under a verdict", _pull(1, mergeable="CONFLICTING", latestReviews=CHANGES),
         issues.RESUMABLE, True, "rebase"),
        ("conflicting under nothing", _pull(1, mergeable="CONFLICTING"), issues.RESUMABLE, True,
         "rebase"),
        ("changes requested, unanswered", _pull(1, latestReviews=CHANGES), issues.RESUMABLE,
         True, "review"),
        ("changes requested, review requested", _pull(1, latestReviews=CHANGES,
                                                       reviewRequests=ASKED),
         issues.RESUMABLE, True, None),
        ("comment verdict with a thread owed", _pull(1, latestReviews=COMMENT,
                                                     reviewThreads=OWED),
         issues.RESUMABLE, True, "review"),
        ("comment verdict with nothing owed", _pull(1, latestReviews=COMMENT),
         issues.RESUMABLE, True, None),
        ("comment verdict under a review request", _pull(1, latestReviews=COMMENT,
                                                         reviewThreads=OWED,
                                                         reviewRequests=ASKED),
         issues.RESUMABLE, True, None),
        ("a reply on a thread, which is no verdict", _pull(1, latestReviews=REPLY,
                                                            reviewThreads=OWED),
         issues.RESUMABLE, True, None),
        ("approved with a thread owed", _pull(1, latestReviews=APPROVED, reviewThreads=OWED),
         issues.RESUMABLE, True, "review"),
        ("approved with a notice parked", _pull(1, latestReviews=APPROVED, reviewThreads=PARKED),
         issues.RESUMABLE, True, None),
        ("approved with every thread answered", _pull(1, latestReviews=APPROVED,
                                                      reviewThreads=ANSWERED),
         issues.RESUMABLE, True, None),
        ("approved and behind with a replay refused on this head",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="BEHIND", comments=notice),
         issues.RESUMABLE, True, "rebase"),
        ("approved and behind with no finding, which is the sweep's to bring current",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="BEHIND"),
         issues.RESUMABLE, True, None),
        ("approved and behind under a finding that is not a refused replay",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="BEHIND", comments=untagged),
         issues.RESUMABLE, True, None),
        ("approved and behind under a finding against a head it no longer has",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="BEHIND", comments=_notice(move, 99)),
         issues.RESUMABLE, True, None),
        ("approved and current with a finding the sweep has not cleared",
         _pull(1, latestReviews=APPROVED, reviewThreads=ANSWERED,
               mergeStateStatus="CLEAN", comments=notice),
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
    case holds a settled read, the review threads of each pull request
    answered over GraphQL from `threads` with the numbers asked for recorded
    in `queried`, and the takes it dispatches, recorded in `dispatched`.
    `unlistable` refuses every run listing.
    """

    def __init__(self, pulls: list[dict[str, Any]], issues: list[dict[str, Any]],
                 runs: dict[str, list[dict[str, Any]]],
                 views: dict[int, dict[str, Any]] | None = None,
                 threads: dict[int, list[dict[str, Any]]] | None = None) -> None:
        self.pulls, self.issues, self.runs = pulls, issues, runs
        self.views = views or {}
        self.threads = CONVERSATIONS if threads is None else threads
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
        """The review threads of the pull request asked for, and the ask recorded.

        `unreadable` refuses the query in the words the channel exits with.
        """
        number = int(variables["number"])
        self.queried.append(number)
        if self.unreadable:
            raise SystemExit(REFUSED)
        return {"data": {"repository": {"pullRequest": {
            "reviewThreads": {"nodes": self.threads.get(number, [])}}}}}

    def __call__(self, *args: str, **kwargs: Any) -> Any:
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

    `advance` and `reconcile` share a name with the verb they hold, so the
    entry exports the verb and the module is reached through one that
    imports it (solorepo's DR-217).
    """
    modules = (move.common, move.challenges, move.pull_requests, move.decisions,
               move.manager.advance, move.manager, move.cli.reconcile, move.cli)
    for module in modules:
        held = getattr(module, name, None)
        if held is not None and getattr(held, "__module__", None) == module.__name__:
            return module
    raise AssertionError(UNDEFINED.format(name=name))


def _pass_cases(channel: Any, move: Any) -> list[str]:
    """`reconcile` end to end: each act once live, reported otherwise, none under a run."""
    bench = _Bench(channel, move)
    problems = _edge_cases(bench)
    fake = _GitHub(bench.pulls, bench.issues, {})
    ended = bench.run(fake, live=True)
    expected = {("merge_manager", None), ("review", 1), ("rebase", 2), ("request", 3),
                ("relabel", (4, ("remove",))), ("relabel", (4, ("add",))), ("release", 6),
                ("rebase", 13), ("rebase", 15), ("rebase", 17), ("review", 24), ("review", 26),
                ("review", 29), ("rebase", 30)}
    acted = bench.acted
    if ended.code is not None or set(acted) != expected or len(acted) != len(expected):
        problems.append(f"reconcile: live over the fixtures performed {acted} with exit "
                        f"{ended.code!r}, not one act per owed state {sorted(expected)}: the "
                        "root of a conflicting stack, a conflicting branch nobody holds, and a "
                        "layer whose root is clean are each owed a rebase, the layer above "
                        "a conflicting root none, a comment verdict and an approval each with "
                        "a thread owed an answer a review pass, where one with every thread "
                        "answered and one with a notice parked owe nothing, an approval "
                        "with a failed gate the review pass its checks owe, and an approval "
                        "behind its base with a replay refused on its head the rebase pass, "
                        "where the layer of that shape above a conflicting root is held")
    if sorted(fake.queried) != [24, 25, 26, 27, 28, 30, 31]:
        problems.append(f"reconcile: the threads read were those of {sorted(fake.queried)}, "
                        "where the listing carries none and the read is owed to the pull "
                        "requests standing with no request under a comment verdict or an "
                        "approval, and to no other: a conflicting branch and a failed gate "
                        "are settled before the threads are reached")
    if f"holding #{12}" not in ended.out:
        problems.append(f"reconcile: a claimed Challenge at hard behind an open pull request was "
                        f"not held: {ended.out!r}")
    if f"holding #{14}" not in ended.out or "is rebased first" not in ended.out:
        problems.append(f"reconcile: the layer above a conflicting root was not held saying "
                        f"why: {ended.out!r}")
    if f"holding #{19}" not in ended.out or "in draft" not in ended.out \
            or "solo's to resolve" not in ended.out:
        problems.append(f"reconcile: the layer above a conflicting draft was not held naming "
                        f"the solo as the mover: {ended.out!r}")
    if f"holding #{21}" not in ended.out or "not the loop's branch" not in ended.out:
        problems.append(f"reconcile: the layer above a conflicting root on the solo's own "
                        f"branch was not held naming the solo as the mover: {ended.out!r}")
    if f"holding #{23}" not in ended.out or "its Challenge reads" not in ended.out:
        problems.append(f"reconcile: the layer above a conflicting root whose Challenge is "
                        f"claimed at hard was not held naming the solo as the mover: "
                        f"{ended.out!r}")
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
    if left != {("rebase", 2), ("release", 6), ("rebase", 13), ("rebase", 15), ("rebase", 17),
                ("review", 24), ("review", 26), ("review", 29), ("rebase", 30)}:
        problems.append(f"reconcile: with runs in flight, and a triage run that read, it "
                        f"performed {sorted(left)}, where only the rebases of the branches "
                        "no run answers, the release, and the review passes for the comment "
                        "verdict, the approval with a thread owed, and the approval with a "
                        "failed gate were owed")
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

    root = _pull(7, mergeable="UNKNOWN")
    layer = _pull(9, baseRefName="claude/issue-7", mergeable="CONFLICTING", latestReviews=APPROVED)
    with stood_in(bench.channel, MERGEABILITY=(2, 0)):
        ended = bench.run(_GitHub([root, layer], [], {}), live=True)
    if ("rebase", 9) not in bench.acted or f"holding #{9}" in ended.out:
        problems.append(f"reconcile: a layer above a root still UNKNOWN when the bound ran out "
                        f"was owed {[a for a in bench.acted if a[1] == 9]}, where only a "
                        "conflict below holds it and the next pass reads the root settled")

    talking = _pull(40, latestReviews=COMMENT, reviews=COMMENT)
    unreadable = _GitHub([talking], [], {}, threads={40: OWED})
    unreadable.unreadable = True
    ended = bench.run(unreadable, live=True)
    left = [a for a in bench.acted if a[0] != "merge_manager"]
    if left or "could not be read" not in ended.out:
        problems.append(f"reconcile: a comment verdict whose threads GitHub would not read was "
                        f"owed {left} and said {ended.out!r}, where nothing is owed on a read "
                        "that failed and the log says it failed")

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
