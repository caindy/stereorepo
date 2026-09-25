"""What the loops ask of GitHub's run and check machinery, which neither listing
answers.

`pr list` and `issue list` say what is open and what stands on it. Two readings
here say what they do not. `runs_of` lists a loop workflow's runs, which is how
a pass tells a dispatch already flying from one it owes, and it is made once per
loop workflow — three times a reconciler pass, for `coder.yml`, `review.yml` and
`triage.yml`, and each of those three costs a `gh run list` per status in
`IN_FLIGHT` and one more for the newest hundred, so nine listings a pass.
`trunk_health` reads the check rollup of trunk's own HEAD commit, which belongs
to no pull request and so appears in no rollup the loops read, and it is made
once a pass. Neither is re-read inside the verb that consumes it: both are read
where the pass begins and shared by every decision in it.

They sit in a module of the package rather than in `reconcile`, which is their
one caller, because that is where a script's body goes and `reconcile.py` stood
past the module ceiling (solorepo's DR-217).
"""
from typing import Any, NamedTuple

import channel
import check_pr
from lib.timing.github import NOT_RUN

IN_FLIGHT = ("queued", "in_progress")
"""The statuses a run has before it concludes, each listed by name so volume does not bound it."""


RUN_FIELDS = "displayTitle,status,conclusion,headBranch"
"""What `runs_of` reads off each run: its name, its status, its conclusion, and its branch.

The loop workflows write the name with the number they run for, which is how a
run for one Issue or pull request is told from the rest."""


TRUNK_ROLLUP = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      name
      target {
        ... on Commit {
          oid
          messageHeadline
          statusCheckRollup {
            contexts(first: 100) {
              nodes {
                ... on CheckRun { name status conclusion completedAt startedAt detailsUrl }
                ... on StatusContext { context state createdAt targetUrl }
              }
            }
          }
        }
      }
    }
  }
}
"""
"""The check rollup of the default branch's HEAD commit, asked for by name.

`check_pr.github.ROLLUP`'s fields against a commit reached through
`defaultBranchRef` rather than through a pull request's `commits(last: 1)`,
which is the only ref the loops read today. The fields are written out for that
file's reason (solorepo's DR-153): `gh`'s own query for `statusCheckRollup`
traverses `checkSuite.workflowRun`, an Actions resource, and a token without the
`actions` scope fails the whole query rather than returning the field null.

The branch is asked for rather than assumed, so a Portfolio whose trunk is not
called `main` is read correctly. `messageHeadline` is carried for the log: a red
trunk is reported with the commit that is red, and the subject is what a reader
recognises."""


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


class Trunk(NamedTuple):
    """The check rollup of trunk's own HEAD commit, as one reconciler pass read it.

    Attributes:
        ref: The default branch's name, as GitHub reports it.
        oid: The HEAD commit of that branch.
        headline: That commit's subject line.
        checks: Its check contexts, deduplicated by name to the latest run of
            each, the names in the order their earliest run started, which is
            the order `deduplicate_checks` leaves them in.
        failing: The names of the checks that concluded in anything but a pass,
            in the order `checks` holds them.
        pending: Whether the commit is unsettled — a check has yet to conclude,
            or nothing has reported on it at all, which is the sense
            `checks_summary` gives an empty rollup. With `red` this is the pair
            a caller reads, and green is `not red and not pending`; `checks`
            being empty is what tells an unreported commit from a running one.
    """

    ref: str
    oid: str
    headline: str
    checks: list[Any]
    failing: list[str]
    pending: bool

    @property
    def red(self) -> bool:
        """Whether a check on trunk's HEAD failed, which is the break there is anything to heal."""
        return bool(self.failing)


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


def _failing(checks: list[Any]) -> list[str]:
    """The names of the checks that concluded in anything but a pass.

    Read against the same two sets `checks_summary` reads a pull request's head
    against, so trunk is judged green or red on the terms every other rollup
    here is judged on.
    """
    states = check_pr.state
    failed = []
    for check in checks:
        value = str(check.get("conclusion") or check.get("state")
                    or check.get("status") or "PENDING").upper()
        if value not in states.GREEN and value not in states.UNCONCLUDED:
            failed.append(str(check.get("name") or check.get("context") or "check"))
    return failed


def trunk_health(owner: str, name: str) -> tuple[Trunk | None, str]:
    """The check rollup of trunk's HEAD commit, or why it could not be read.

    Detection, and the first half of what solorepo's #913 asked for: every
    rollup the loops read belongs to an open pull request's own head, so a
    commit that landed on trunk with a failing job is noticed only when a branch
    rebased onto it goes red. Reading trunk's own HEAD names the break at its
    source, and names the commit that carries it.

    A trunk commit with no rollup at all — nothing has reported on it yet — is a
    reading with no checks rather than a refusal: it is neither red nor green,
    and `pending` is what says so, `checks` being what tells it from a commit
    whose checks are still running.

    Nothing the read can do fails the pass around it. A refusal, and an answer
    that is not the shape the query asked for, are each no reading and are
    handed back as one, in the same closed shape `manager.ranking.read_threads`
    fails in: detection sits beside the acts the reconciler performs and must
    never be able to stop them, and a pass that died reading trunk would leave
    every rebase, review and take it owed undispatched for the period. The guard
    reaches the shaping of the answer as well as the asking, since a rollup
    holding something that is not a check fails where it is read.

    Parameters:
        owner (str): The repository's owner.
        name (str): The repository's name.

    Returns:
        tuple[Trunk | None, str]: The reading and an empty reason, or None and
            why it could not be read, which is what the log says in its place.
    """
    try:
        answered = channel.graphql(TRUNK_ROLLUP, owner=owner, name=name)
        repository = ((answered or {}).get("data") or {}).get("repository")
        if repository is None:
            return None, (f"GitHub named no repository {owner}/{name}, which is what a token "
                          "without sight of one is answered with")
        ref = repository.get("defaultBranchRef")
        if not ref:
            return None, "GitHub named no default branch"
        head = ref.get("target") or {}
        if not head.get("oid"):
            return None, f"GitHub named no commit on {ref.get('name')}"
        contexts = ((head.get("statusCheckRollup") or {}).get("contexts") or {}).get("nodes") or []
        checks = check_pr.deduplicate_checks([c for c in contexts if c])
        _, _, unconcluded = check_pr.state.checks_summary(checks)
        return Trunk(ref=str(ref.get("name") or ""), oid=str(head["oid"]),
                     headline=str(head.get("messageHeadline") or ""), checks=list(checks),
                     failing=_failing(list(checks)), pending=unconcluded), ""
    except SystemExit as exc:
        return None, str(exc.code)
    except (LookupError, TypeError, AttributeError) as exc:
        return None, f"GitHub answered something the query did not ask for ({exc!r})"


def report_trunk(owner: str, name: str) -> Trunk | None:
    """Read trunk's HEAD rollup and say what it holds, in the reconciler's log.

    The reconciler is the one caller, and the line it prints carries that verb's
    prefix. Detection is the whole of this act: dispatching a pass at once to
    repair a red trunk is solorepo's #984, and re-dispatching the pull requests
    a red one stranded, once it is green again, is solorepo's #985. Both read
    what this hands back.

    Parameters:
        owner (str): The repository's owner.
        name (str): The repository's name.

    Returns:
        Trunk | None: The reading, or None where GitHub refused it.
    """
    found, why = trunk_health(owner, name)
    if found is None:
        print(f"reconcile: could not read trunk's check rollup — {why}")
        return None
    at = f"{found.ref} at {found.oid[:7]} ({found.headline})"
    if found.red:
        print(f"reconcile: trunk is red — {at} fails {', '.join(found.failing)}")
    elif not found.checks:
        print(f"reconcile: trunk has no checks reported — {at}")
    elif found.pending:
        print(f"reconcile: trunk is still running its checks — {at}")
    else:
        print(f"reconcile: trunk is green — {at}")
    return found
