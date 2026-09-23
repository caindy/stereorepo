"""The reconciler: every open Issue and pull request read on the clock and what each is
owed (solorepo's DR-264)."""
import datetime
import sys
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

import channel
import check_pr
from lib.move import advance, challenges, common, manager, pull_requests
from lib.timing.github import NOT_RUN

RECONCILE_FIELDS = manager.MERGE_MANAGER_FIELDS + ",updatedAt"
"""The reconciler's read of each open pull request: the merge manager's fields, plus `updatedAt`.

It carries no `reviewThreads`, which `pr list` cannot return: the threads of a
pull request whose classification turns on them are read one at a time, by
`_threads_read`."""


RECONCILE_MINUTES = 30.0
"""How long a pull request or Issue must have sat idle before an act is owed on it.

The sweep's bound, for the sweep's reason: a pass merely still running is not
mistaken for one that stopped."""


UNREAD_MINUTES = 60.0
"""How long an unread Challenge must have sat since it last moved before its door is re-delivered.

The hour is the one `just next --check` reports an unread Challenge after
(solorepo's DR-230). Counting it from `updatedAt` rather than from the filing
is this verb's own choice: a re-delivery moves it, so a Challenge re-delivered
once is not re-delivered every period."""


IN_FLIGHT = ("queued", "in_progress")
"""The statuses a run has before it concludes, each listed by name so volume does not bound it."""


RUN_FIELDS = "displayTitle,status,conclusion,headBranch"
"""What `runs_of` reads off each run: its name, its status, its conclusion, and its branch.

The loop workflows write the name with the number they run for, which is how a
run for one Issue or pull request is told from the rest."""


ISSUE_FIELDS = "number,title,labels,assignees,blockedBy,updatedAt,createdAt"
"""What the reconciler reads off each open Issue, the blockers among it (solorepo's DR-213)."""


class Owed(NamedTuple):
    """One act the reconciler owes: its kind, the number it is owed on, and why.

    Attributes:
        kind: `rebase` or `review`, a coder pass dispatched on a pull request;
            `request`, a review requested again; `take`, the coder's take pass
            dispatched for a Challenge; `reread`, the reviewer's door
            re-delivered; `release`, a dead run's claim released; or `hold`,
            which is reported and never performed, since what it names is the
            solo's.
        number: The pull request or Issue the act is owed on.
        why: The reading that owes it, in the words the log gets.
        lower: The lower layer's number where `kind` is a stack hold, or None.
    """

    kind: str
    number: int
    why: str
    lower: int | None = None


class Runs(NamedTuple):
    """What GitHub lists of a workflow's runs, or that it would not.

    Attributes:
        flying: The runs queued or running, listed by status so that the
            hundred newest do not bound them.
        recent: The hundred newest runs, for a completed run's conclusion; None
            where GitHub would not list them.
    """

    flying: list[dict[str, Any]]
    recent: list[dict[str, Any]] | None

    @property
    def listed(self) -> bool:
        """Whether GitHub answered every listing; unlistable runs hold every guarded act."""
        return self.recent is not None


def runs_of(workflow: str) -> Runs:
    """The runs of a workflow, or that GitHub would not list them, said out loud.

    A listing refused is not nothing in flight: the guard that keeps two coder
    runs off one branch is what the listing is for, and a token without
    `actions: read` would otherwise disable it in silence. So a refusal is
    printed and answered as `Runs` with `recent` None, which holds every act
    the guard qualifies. A call that hangs exits the channel without asking
    for a fallback, and is caught here for the same reason.

    Parameters:
        workflow (str): The workflow file's name, as `gh run list` takes it.

    Returns:
        Runs: What was listed.
    """
    def listing(*args: str) -> list[dict[str, Any]] | None:
        try:
            found = channel.gh("run", "list", "--workflow", workflow, *args,
                               "--json", RUN_FIELDS, default=None)
        except SystemExit as exc:
            found, why = None, str(exc.code)
        else:
            why = "GitHub refused the listing"
        if found is None:
            print(f"reconcile: could not list {workflow} runs — {why}")
            return None
        return list(found)

    flying: list[dict[str, Any]] = []
    for status in IN_FLIGHT:
        got = listing("--status", status, "--limit", "100")
        if got is None:
            return Runs([], None)
        flying += got
    return Runs(flying, listing("--limit", "100"))


def in_flight(runs: Runs, title: str = "", branch: str = "") -> bool:
    """Whether a run named `title`, or running on `branch`, is queued or running.

    Unlistable runs answer True: where nothing says whether a run is
    answering, nothing is dispatched beside it.

    Parameters:
        runs (Runs): A workflow's runs, as `runs_of` lists them.
        title (str): A run's whole display title, as the loop workflows write
            it: `coder-issue-#<n>`, `triage-issue-#<n>`.
        branch (str): A head branch, which is how a review run is found.

    Returns:
        bool: True where a run matching either has not concluded, or where
            the runs could not be listed.
    """
    if not runs.listed:
        return True
    for run in runs.flying:
        if title and str(run.get("displayTitle") or "") == title:
            return True
        if branch and run.get("headBranch") == branch:
            return True
    return False


def read_by(runs: Runs, title: str) -> bool:
    """Whether the newest run named `title` whose job ran concluded `success`, as `next` reads it.

    A run the job declined or one displaced before it started concludes in
    `NOT_RUN` and is passed over, so the run read is one that owed a reading.
    Unlistable runs answer True, since a re-delivery nothing can check against
    is one too many.

    Parameters:
        runs (Runs): The triage runs, as `runs_of` lists them.
        title (str): The run name `triage.yml` writes for the Issue.

    Returns:
        bool: True where a reader read it and finished, or where nothing can say.
    """
    if not runs.listed:
        return True
    for run in runs.recent or []:
        if str(run.get("displayTitle") or "") != title:
            continue
        if run.get("status") == "completed" and str(run.get("conclusion") or "") in NOT_RUN:
            continue
        return run.get("status") == "completed" and run.get("conclusion") == "success"
    return False


def idle_minutes(obj: Mapping[str, Any], now: datetime.datetime) -> float:
    """Minutes since an Issue or pull request last moved, by `updatedAt`; forever without one."""
    moved = obj.get("updatedAt")
    if not moved:
        return float("inf")
    since = datetime.datetime.fromisoformat(str(moved).replace("Z", "+00:00"))
    return (now - since).total_seconds() / 60


def _challenge_reads(number: int, reading: Any = None) -> Any:
    """What `classify_issue` reads of the Challenge a loop branch names, or None if unreadable.

    The pull request is counted open and the claim read as nobody's, as the
    doors a run arrives at with its own pull request read it.
    """
    challenge: Mapping[str, Any] | None = None
    if reading is not None and hasattr(reading, "by_number"):
        challenge = reading.by_number.get(number)
    if challenge is None:
        try:
            challenge = channel.gh("issue", "view", str(number), "--json", "state,labels,assignees",
                                   default=None)
        except SystemExit:
            challenge = None
    if challenge is None:
        return None
    return check_pr.state.classify_issue({"state": "OPEN", **challenge}, None, True)


def _held_above(number: int, lower: common.Pull, reading: Any = None) -> Owed:
    """The hold on a layer whose lower layer conflicts, saying who moves the lower layer.

    A lower layer the reconciler will rebase, a loop branch not in draft whose
    Challenge reads `RESUMABLE`, is rebased first and the hold clears on a
    later pass. One it will not, the solo's own branch, a draft, or a
    Challenge in a state that is the solo's, leaves the stack to the solo,
    and the hold says so rather than naming a mover that will not move
    (solorepo's DR-133).
    """
    lower_num = int(lower["number"])
    match = pull_requests.LOOPS_BRANCH.match(lower.get("headRefName") or "")
    where = f"a layer above #{lower_num}, which conflicts with its own base"
    if not match:
        return Owed("hold", number, f"{where} and is not the loop's branch: the stack is the "
                                    "solo's to resolve from the bottom", lower=lower_num)
    if lower.get("isDraft"):
        return Owed("hold", number, f"{where} and is in draft, which the reconciler does not "
                                    "rebase: the stack is the solo's to resolve from the bottom",
                    lower=lower_num)
    found = _challenge_reads(int(match.group(1)), reading)
    if found is check_pr.state.IssueState.RESUMABLE:
        return Owed("hold", number, f"{where} and is rebased first: a stack is resolved from "
                                    "the bottom", lower=lower_num)
    reads = found.value if found is not None else "no Challenge the loop can read"
    return Owed("hold", number, f"{where} and its Challenge reads {reads}, which is the "
                                "solo's: the stack is the solo's to resolve from the bottom",
                lower=lower_num)


class Constraints(NamedTuple):
    """Caller constraints parameterizing what an act is owed (solorepo's DR-264).

    Attributes:
        free: Whether the branch is free of in-flight runs and past its idle bound.
        pulls: All open pull requests across the repository for stack ordering, or
            None to skip the stack evaluation.
        held_only: When True, restricts rebase dispatches to branches held by a
            request, an arming, or a verdict.
        reading: Shared pass context of the reconciler providing cached issue and
            run state (Reading), or None outside a reconcile pass.
    """

    free: bool = True
    pulls: Sequence[common.Pull] | None = None
    held_only: bool = False
    reading: Any = None


def _owed_rebase(pull: common.Pull, reviewer_login: str,
                 constraints: Constraints) -> Owed | None:
    """What a conflicting pull request is owed under its constraints."""
    number = int(pull["number"])
    if constraints.pulls is not None:
        lower = pull_requests.conflicting_below(pull, constraints.pulls)
        if lower is not None:
            return _held_above(number, lower, constraints.reading)
    asked = check_pr.is_review_requested(pull, reviewer_login)
    verdict = check_pr.latest_verdict(pull, reviewer_login)
    armed = bool(pull.get("autoMergeRequest"))
    if asked or armed or verdict in advance.VERDICTS:
        return Owed("rebase", number, "conflicting under a request, an arming, or a verdict")
    if not constraints.held_only:
        return Owed("rebase", number, "conflicting, and nobody holds it: no request stands, no "
                                      "merge is armed, and no verdict was given")
    return None


def _owed_gate_failed(pull: common.Pull, reviewer_login: str) -> Owed | None:
    """What a pull request with failed checks is owed.

    A gate that failed owes a review pass where the reviewer had approved and
    nobody is asked, and owes the request again where the check that failed is
    the reviewer's own and a request stands (solorepo's DR-178).
    """
    number = int(pull["number"])
    asked = check_pr.is_review_requested(pull, reviewer_login)
    verdict = check_pr.latest_verdict(pull, reviewer_login)
    checks = manager.deduplicate_checks(pull.get("statusCheckRollup") or [])
    reviewer_check = next((c for c in checks if c.get("name") == "reviewer"), None)
    reviewer_failed = str((reviewer_check or {}).get("conclusion") or "").upper() == "FAILURE"
    if asked and reviewer_failed:
        return Owed("request", number, "review requested, and the reviewer check failed "
                                       "without a verdict")
    if verdict == "APPROVED" and not asked:
        return Owed("review", number, "approved, with failing checks")
    return None


def owed_by_pull(pull: common.Pull, found: Any, state: Any, reviewer_login: str,
                 constraints: Constraints | bool | None = None) -> Owed | None:
    """What a loop branch's pull request is owed, read off the two classifiers' states, or None.

    `state` is `classify_pr`'s and `found` is `classify_issue`'s, and the act
    is decided on those (solorepo's DR-264); what the states do not carry, who
    is asked and whether the merge is armed, is read off the pull request.
    The shapes are the ones the sweep's `unheld` names, each qualified by
    `free`, which the caller reads as the bound's silence with no run
    answering. A branch conflicting under a request, an arming, or a verdict
    owes a rebase pass, which is the sweep's own dispatch, the verdict the
    coder has not answered being the case solorepo's DR-237 added to it; so
    does one conflicting that nobody holds, since a review that ended
    without a verdict consumed the request the branch was waiting on, and a
    branch no review can run on waits on nothing else. Stacks are resolved from
    the bottom (solorepo's DR-133), leaving layers above a conflicting root
    held.

    A request for changes nobody is answering owes a review pass, since the
    review event was dropped or a run ended without answering.

    A green pull request with no verdict, no request, and no arming owes its
    first request, since a run ended without handing it over. A Challenge in
    any state but `RESUMABLE`, the one a loop-level Challenge with an open pull
    request reads when the claim is read as nobody's, is held and reported,
    free or not, since what stands on it is the solo's: a claim read as the
    coder's would read `TAKEN` before `hard`, and a branch the solo took over at
    `hard` would be acted on, which is what the take door's second reading
    exists to prevent (solorepo's DR-142).

    Parameters:
        pull (dict): The pull request, carrying `RECONCILE_FIELDS`, its
            `mergeable` settled by `mergeability` where `free`: the bulk
            listing answers `UNKNOWN` for a branch GitHub has not recomputed,
            and a conflict read as anything else dispatches the wrong pass.
        found (IssueState | None): What `classify_issue` read of the Challenge
            the branch names, with the pull request counted open and the claim
            read as nobody's, as the doors a run arrives at with its own pull
            request read it; None where the branch names no open Challenge.
        state (PullRequestState): What `classify_pr` reads of the pull request.
        reviewer_login (str): The reviewer Role's login.
        constraints (Constraints | bool | None): Caller constraints parameterizing
            the reading, a bare boolean for `free`, or None for defaults.

    Returns:
        Owed | None: The one act owed, or None.
    """
    if isinstance(constraints, bool):
        c = Constraints(free=constraints)
    elif constraints is None:
        c = Constraints()
    else:
        c = constraints
    number = int(pull["number"])

    if found is None:
        return None
    if found is not check_pr.state.IssueState.RESUMABLE:
        return Owed("hold", number, f"its Challenge reads {found.value}, which is the solo's")
    if not c.free:
        return None

    pulls_ = check_pr.PullRequestState
    if state is pulls_.NEEDS_REBASE:
        return _owed_rebase(pull, reviewer_login, c)
    if state is pulls_.CHANGES_REQUESTED and not check_pr.is_review_requested(pull, reviewer_login):
        return Owed("review", number, "changes requested, and no run answering them")
    if state is pulls_.GATE_FAILED:
        return _owed_gate_failed(pull, reviewer_login)
    if (state is pulls_.AWAITING_REVIEW
            and not check_pr.is_review_requested(pull, reviewer_login)
            and not check_pr.latest_verdict(pull, reviewer_login)
            and not pull.get("autoMergeRequest")):
        return Owed("request", number, "green, and nobody holds it")
    return None


class Quiet(NamedTuple):
    """How long an Issue has sat, read against each bound, and what stands beside it.

    Attributes:
        free: Idle past the reconciler's bound with no coder run for it.
        unread: Idle past `UNREAD_MINUTES` with no triage run for it in flight
            and none that read it and finished.
        expired: Idle past the coder workflow's job timeout with no coder run
            for it, which is a claim its run died holding.
        blocked: Waiting on an open Issue (solorepo's DR-213), which `just
            next` keeps out of the ripe list and a take pass must not start.
        idle: The minutes it has sat, for the log.
    """

    free: bool
    unread: bool
    expired: bool
    blocked: bool
    idle: float


def owed_by_issue(issue: Mapping[str, Any], found: Any, quiet: Quiet) -> Owed | None:
    """What an Issue is owed off its `IssueState`, or None.

    An unread Challenge past the hour with no reader running and none that
    read it owes the reviewer's door again; an offered one free of any run
    and waiting on nothing owes the take pass; a claimed one with no pull
    request whose claim has expired owes its release, which is the lease
    solorepo's #781 asked for.

    Parameters:
        issue (dict): The Issue, carrying `ISSUE_FIELDS`.
        found (IssueState): What `classify_issue` read.
        quiet (Quiet): How long it has sat against each bound, and what
            stands beside it.

    Returns:
        Owed | None: The one act owed, or None.
    """
    number = int(issue["number"])
    states = check_pr.state.IssueState
    if found is states.UNREAD and quiet.unread:
        return Owed("reread", number, "unread for an hour, and no reader read it")
    if found is states.OFFERED and quiet.free and not quiet.blocked:
        return Owed("take", number, "offered, and no run took it")
    if found is states.CLAIMED and quiet.expired:
        return Owed("release", number, f"claimed with no pull request and no run for "
                                       f"{int(quiet.idle)} minutes, past the longest coder run")
    return None


PERFORMED = {"rebase": ("dispatch a rebase pass for", "dispatched a rebase pass for"),
             "review": ("dispatch a review pass for", "dispatched a review pass for"),
             "request": ("request review of", "requested review of"),
             "take": ("dispatch the take pass for", "dispatched the take pass for"),
             "reread": ("re-deliver to the reviewer", "re-delivered to the reviewer"),
             "release": ("release the claim on", "released the claim on")}
"""Each act's verb, to say and to have done, for the log."""


def redeliver(number: int) -> None:
    """Re-deliver a Challenge to the reviewer's door: `challenge` taken off and put back, retried.

    The door fires on `challenge` landing (solorepo's DR-230), so the label is
    taken off and put back. The put-back is the half that must not fail, since
    a Challenge left without `challenge` reads `UNLABELLED` and nothing here
    owes it anything again; so where the settled write refuses, the label is
    put back through `gh_with_retry` before the refusal is reported.

    Parameters:
        number (int): The Challenge.

    Raises:
        SystemExit: Where either half refused; the label was put back before
            the second half's refusal is raised, or the exit says it was not.
    """
    challenges.relabel(number, remove=["challenge"])
    try:
        challenges.relabel(number, add=["challenge"])
    except SystemExit as refused:
        try:
            channel.gh_with_retry("issue", "edit", str(number), "--add-label", "challenge",
                                  parse=False, tolerate_fail=True)
        except common.UNREACHED as again:
            sys.exit(f"{refused.code}; and putting `challenge` back on #{number} was refused "
                     f"too — {again} — so it is unlabelled, and `just next` is what reports it")
        raise


def perform(owed: Sequence[Owed], live: bool) -> None:
    """Perform each act owed, or say what would be performed, each isolated from the rest.

    A refusal on one act is printed and the next is performed, as the merge
    manager isolates a candidate's failure (solorepo's #776). The
    take pass is dispatched without a harness, so the door reads the
    Challenge's own `harness:` label as the label's delivery would.

    Parameters:
        owed (list[Owed]): The acts, as `reconcile` read them.
        live (bool): Whether to perform them; otherwise each is reported.
    """
    for act in owed:
        if act.kind == "hold":
            print(f"reconcile: holding #{act.number} — {act.why}")
            continue
        saying, done = PERFORMED[act.kind]
        if not live:
            print(f"reconcile: would {saying} #{act.number} — {act.why}")
            continue
        try:
            if act.kind == "rebase":
                advance.run_coder(act.number, "rebase")
            elif act.kind == "review":
                advance.run_coder(act.number, "review")
            elif act.kind == "request":
                pull_requests.request_review(act.number, "reviewer")
            elif act.kind == "take":
                channel.gh("workflow", "run", "coder.yml", "-f", f"issue={act.number}",
                           parse=False)
            elif act.kind == "reread":
                redeliver(act.number)
            elif act.kind == "release":
                challenges.release(act.number)
        except SystemExit as exc:
            print(f"reconcile: could not {saying} #{act.number} — {exc.code}")
            continue
        print(f"reconcile: {done} #{act.number} — {act.why}")


def reconcile(live: bool = False, dry_run: bool = False, minutes: float | None = None) -> None:
    """Run the merge manager, then perform what every open Issue and pull request is owed.

    The primary loop, of which the webhook doors are the accelerator
    (solorepo's DR-264): a dropped edge costs one period of the clock rather
    than a freeze. The merge manager runs first, as it did on the clock before
    this, and its exit is held until the reading is done so that a failed
    candidate paints the run red without starving the acts beside it. That
    manager declines the lock rather than waiting on it, which is what lets the
    reading go on regardless (solorepo's DR-267); that this pass was not
    cancelled behind merge traffic before reaching the reading at all is what
    the two workflows' separate concurrency groups bought. Every act is
    qualified twice: by `minutes` of silence, and by no run for it queued or
    running, read off the run names the loop workflows write; runs GitHub will
    not list hold every act that needs the guard, and the log says so. A pull
    request that is free has its mergeability settled before it is read, as
    every other dispatch here settles it, so an `UNKNOWN` pays in a wait and not
    in the wrong pass, and the threads its classification turns on are read with
    it (solorepo's DR-265). Whether a Challenge has a pull request open counts a
    draft, as the take door counts one, since the merge manager this has just
    run is what parks a stalled loop branch in draft (solorepo's DR-258). With
    `live`, each act is performed; without it, each is reported and none
    performed.

    Parameters:
        live (bool): Whether to perform the acts, or only report them.
        dry_run (bool): The merge manager's own dry run: name its winner and
            merge nothing; with it, nothing here is performed either.
        minutes (float | None): The silence an act waits for, `RECONCILE_MINUTES`
            by default.

    Raises:
        SystemExit: With the merge manager's code, after the reading, where a
            candidate failed to land.
    """
    bound = RECONCILE_MINUTES if minutes is None else minutes
    ended: str | int | None = None
    try:
        manager.merge_manager(dry_run=dry_run)
    except SystemExit as exc:
        ended = exc.code
        print(f"reconcile: the merge manager ended with {ended}; reading on")
    owner, name, reviewer_login = manager.repo_context()
    coder = channel.role_login("coder")
    pulls = channel.gh("pr", "list", "--state", "open", "--limit", "100",
                       "--json", RECONCILE_FIELDS)
    issues = channel.gh("issue", "list", "--state", "open", "--limit", "200",
                        "--json", ISSUE_FIELDS)
    coder_runs, review_runs, triage_runs = (runs_of("coder.yml"), runs_of("review.yml"),
                                            runs_of("triage.yml"))
    if not (coder_runs.listed and review_runs.listed and triage_runs.listed):
        print("reconcile: holding every act a run could be answering, since the runs could "
              "not be listed and nothing says whether one is")
    reading = Reading(now=datetime.datetime.now(datetime.UTC), bound=bound,
                      longest=float(check_pr.longest_run() or 75), coder=coder,
                      reviewer_login=reviewer_login, owner=owner, name=name,
                      by_number={int(i["number"]): i for i in issues},
                      named={int(m.group(1)) for pull in pulls
                             if (m := pull_requests.LOOPS_BRANCH.match(
                                 pull.get("headRefName") or ""))},
                      coder_runs=coder_runs, review_runs=review_runs, triage_runs=triage_runs)
    owed = owed_by_pulls(pulls, reading) + owed_by_issues(issues, reading)
    if not owed:
        print("reconcile: nothing owed")
    perform(owed, live and not dry_run)
    if ended is not None:
        sys.exit(ended)


class Reading(NamedTuple):
    """What one pass of the reconciler reads once and every decision shares.

    Attributes:
        now: The moment the pass is made.
        bound: The silence an act waits for, in minutes.
        longest: The coder workflow's job timeout, in minutes.
        coder: The coder Role's login, whose assignment is a claim.
        reviewer_login: The reviewer Role's login.
        owner: The repository's owner, for the thread read.
        name: The repository's name, for the thread read.
        by_number: Every open Issue by number.
        named: The Issues an open loop-branch pull request names, drafts
            included, which is what `classify_issue` counts as a pull request.
        coder_runs: `coder.yml`'s runs.
        review_runs: `review.yml`'s runs.
        triage_runs: `triage.yml`'s runs.
    """

    now: datetime.datetime
    bound: float
    longest: float
    coder: str
    reviewer_login: str
    owner: str
    name: str
    by_number: dict[int, Mapping[str, Any]]
    named: set[int]
    coder_runs: Runs
    review_runs: Runs
    triage_runs: Runs


def owed_by_pulls(pulls: Sequence[common.Pull], reading: Reading) -> list[Owed]:
    """What every open loop-branch pull request not in draft is owed, read through both classifiers.

    A rebase owed to a layer of a stack is held while a layer below it
    conflicts, since a stack is resolved from the bottom (solorepo's DR-133):
    the root's rebase pass runs first, and each layer above it is rebased onto
    its new base on a later pass, once the layers below it are clean.

    The threads a free pull request's classification turns on are read before
    it is classified, by `_threads_read`; one that is not free is classified
    without them, since `owed_by_pull` answers None for it whatever state it
    was handed.

    Parameters:
        pulls (list): The open pull requests, carrying `RECONCILE_FIELDS`.
        reading (Reading): What the pass reads once.

    Returns:
        list[Owed]: The acts owed, at most one per pull request.
    """
    owed: list[Owed] = []
    for pull in pulls:
        match = pull_requests.LOOPS_BRANCH.match(pull.get("headRefName") or "")
        if not match or pull.get("isDraft"):
            continue
        challenge_number = int(match.group(1))
        found = _challenge_reads(challenge_number, reading)
        head = str(pull.get("headRefName") or "")
        busy = (in_flight(reading.coder_runs, title=f"coder-issue-#{pull['number']}")
                or in_flight(reading.coder_runs, title=f"coder-issue-#{challenge_number}")
                or in_flight(reading.review_runs, branch=head))
        free = not busy and idle_minutes(pull, reading.now) >= reading.bound
        if free:
            pull_requests.mergeability(pull)
        checks = manager.deduplicate_checks(pull.get("statusCheckRollup") or [])
        state = check_pr.classify_pr(pull, checks,
                                     _threads_read(pull, checks, reading) if free else None,
                                     reading.reviewer_login)
        act = owed_by_pull(pull, found, state, reading.reviewer_login,
                           Constraints(free=free, pulls=pulls, reading=reading))
        if act:
            owed.append(act)
    return owed


def _threads_read(pull: common.Pull, checks: Sequence[Mapping[str, Any]],
                  reading: Reading) -> list[dict[str, Any]] | None:
    """The review threads of a pull request whose classification turns on them, or None.

    Two arms of `classify_pr` turn on the review threads, and both stand with
    no review requested. A standing verdict of `COMMENTED` reads
    `CHANGES_REQUESTED` where a thread is owed an answer and owes nothing
    where none is (solorepo's DR-265). An approval reads `CHANGES_REQUESTED`
    where a thread is owed, `AWAITING_PROMOTION` where a notice is parked, and
    `READY_TO_MERGE` where the gate is green and the threads show neither;
    where the gate is still running it reads `AWAITING_GATE`, which is a shape
    this read admits on purpose, a check merely unconcluded being no failure.
    Read without the threads, no approval reaches either of the first two, so
    a green one carrying an unanswered thread reads `READY_TO_MERGE` and is
    dispatched no review pass, and what stops it is the merge manager refusing
    an unresolved conversation rather than the coder being told to answer it.

    The listing answers neither arm, since `pr list` returns no
    `reviewThreads`, so the threads are read here, through the query the merge
    manager already makes: one query per pass for each pull request standing
    in one of those two shapes, and none for any other. A pull request
    `classify_pr` settles before it reaches the threads is not read either —
    a conflicting branch owes the rebase pass and a failed gate owes what its
    checks owe, whatever the threads hold — which is what holds the read to
    the approved pull requests awaiting merge rather than to every approved
    one.

    A read GitHub refuses answers None, which `classify_pr` reads as an empty
    thread list and which owes nothing; the log says so, as it does for a run
    GitHub will not list.

    Parameters:
        pull (dict): The pull request, carrying `RECONCILE_FIELDS`, its
            `mergeable` settled.
        checks (list): Its check rollup, deduplicated, as `classify_pr` is
            handed it.
        reading (Reading): What the pass reads once.

    Returns:
        list[dict] | None: The threads, or None where the classification does
            not turn on them or GitHub refused the read.
    """
    has_failures, _, _ = check_pr.state.checks_summary(checks)
    if (check_pr.is_review_requested(pull, reading.reviewer_login)
            or str(pull.get("mergeable") or "").upper() == "CONFLICTING"
            or has_failures):
        return None
    if (check_pr.state.standing_verdict(pull, reading.reviewer_login) != "COMMENTED"
            and check_pr.latest_verdict(pull, reading.reviewer_login) != "APPROVED"):
        return None
    threads, why = manager.read_threads(pull, reading.owner, reading.name)
    if threads is None:
        print(f"reconcile: #{pull['number']} is classified against its threads and they "
              f"could not be read — {why}")
    return threads


def owed_by_issues(issues: Sequence[Mapping[str, Any]], reading: Reading) -> list[Owed]:
    """What every open Issue is owed, each read through the Issue classifier against the bounds.

    Parameters:
        issues (list): The open Issues, carrying `ISSUE_FIELDS`.
        reading (Reading): What the pass reads once.

    Returns:
        list[Owed]: The acts owed, at most one per Issue.
    """
    owed: list[Owed] = []
    for issue in issues:
        number = int(issue["number"])
        found = check_pr.state.classify_issue({**issue, "state": "OPEN"}, reading.coder,
                                              number in reading.named)
        idle = idle_minutes(issue, reading.now)
        busy_coder = in_flight(reading.coder_runs, title=f"coder-issue-#{number}")
        busy_triage = in_flight(reading.triage_runs, title=f"triage-issue-#{number}")
        quiet = Quiet(free=not busy_coder and idle >= reading.bound,
                      unread=(not busy_triage and idle >= UNREAD_MINUTES
                              and not read_by(reading.triage_runs, f"triage-issue-#{number}")),
                      expired=not busy_coder and idle >= reading.longest,
                      blocked=any(n in reading.by_number
                                  for n in challenges.issue_blockers(dict(issue))),
                      idle=idle)
        act = owed_by_issue(issue, found, quiet)
        if act:
            owed.append(act)
    return owed
