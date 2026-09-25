"""The handoff: the review request that names the Role a Challenge passes to (solorepo's DR-264)."""
import sys
from collections.abc import Mapping

import channel
import check_pr
from lib.move import common, pull_requests


class RequestRefused(SystemExit):
    """GitHub's refusal of the `pr edit` write that `request_review` makes.

    Raised for a refused `pr edit` that wrote nothing — the remove, or an add
    that followed no remove — so a caller re-requesting across a list of pull
    requests tells the refusals that reach every one of them (the credential
    without the repository write, the Role account that is not a collaborator)
    from the ones a single pull request causes (the remove took and the add did
    not, leaving the pull request with nobody requested). Subclasses `SystemExit`,
    so a caller that does not catch it exits with GitHub's message unchanged.
    """


REVIEW_WORKFLOW = "review.yml"
"""The workflow a review request starts, whose runs say whether one already stands on a head."""

RUN_STATE = "headSha,status"
"""The run fields `runs_at_head` asks for: which commit a run took, and whether it has finished.

What a completed run concluded is not among them, because no branch turns on
it: a run that skipped, that was cancelled and one that failed each posted no
verdict, which is the condition `reviewing` already reads, and a run that
posted one before failing left a verdict that stands.
"""


def runs_at_head(pull: common.Pull) -> list[Mapping[str, object]] | None:
    """The `review.yml` runs GitHub lists for a pull request's current head.

    Parameters:
        pull (dict): The pull request, carrying `headRefName` and `headRefOid`.

    Returns:
        list[Mapping] | None: The runs whose head is the commit the pull request
            is on, newest first, or None where GitHub would not list them at
            all — a credential without `actions: read`, or a call that hung,
            each printed rather than passed over, since a guard that is off
            reads exactly like one that found nothing.
    """
    try:
        runs = channel.gh("run", "list", "--workflow", REVIEW_WORKFLOW,
                          "--branch", str(pull.get("headRefName") or ""), "--limit", "50",
                          "--json", RUN_STATE, default=None)
    except SystemExit as exc:
        runs, why = None, str(exc.code)
    else:
        why = "GitHub refused the listing"
    if runs is None:
        print(f"say: could not list {REVIEW_WORKFLOW} runs on "
              f"{pull.get('headRefName')} — {why}")
        return None
    return [run for run in runs
            if str(run.get("headSha") or "") == str(pull.get("headRefOid") or "")]


def spoke_at(pr: str | int, head: str, login: str) -> bool:
    """Whether a Role's verdict on a pull request names the commit it is now on.

    `pr view --json reviews` carries no commit, so the reviews endpoint is read
    for the `commit_id` GitHub records each verdict against. A verdict is what
    `check_pr.state.is_verdict` admits and GitHub has not dismissed: the
    bodiless review GitHub wraps every raise and every reply in carries the
    head's commit and answers nothing (solorepo's DR-118), and a dismissal is
    how a fresh review is summoned at a head that has not moved. Every page is
    asked for a hundred, as the endpoint's other readers do, since an argued
    pull request holds a review per raise and per reply and thirty at a time
    loses the verdicts among them.

    Parameters:
        pr (str | int): Pull request number.
        head (str): The commit the pull request is on.
        login (str): The Role account whose verdicts count.

    Returns:
        bool: True where that login has a verdict at `head`. False where
            GitHub would not answer the listing, so that nothing is taken to
            answer the request.
    """
    try:
        reviews = channel.gh("api",
                             f"repos/{channel.repo()}/pulls/{pr}/reviews?per_page=100",
                             "--paginate", default=None)
    except SystemExit as exc:
        reviews, why = None, str(exc.code)
    else:
        why = "GitHub refused the listing"
    if reviews is None:
        print(f"say: could not list the verdicts on #{pr} — {why}")
        return False
    return any(str(review.get("commit_id") or "") == head
               and ((review.get("user") or {}).get("login")) == login
               and check_pr.state.is_verdict(review)
               and str(review.get("state") or "").upper() != "DISMISSED"
               for review in reviews)


def reviewing(pull: common.Pull, login: str) -> str:
    """What answers a standing request on this head, or the empty string where nothing does.

    Parameters:
        pull (dict): The pull request, carrying `number`, `headRefName` and
            `headRefOid`.
        login (str): The Role account the review is requested of.

    Returns:
        str: What was found, for the caller to print — a `review.yml` run
            listed on this head that has not completed, or `login`'s own
            verdict standing at it. The empty string where neither does: a run
            on this head that finished without that verdict, a run only on the
            head a push moved off, no run at all, and a listing GitHub would
            not answer, which is read as nothing rather than as something
            (solorepo's #950).
    """
    runs = runs_at_head(pull)
    if not runs:
        return ""
    head = str(pull.get("headRefOid") or "")
    short = head[:7]
    flying = [run for run in runs if str(run.get("status") or "") != "completed"]
    if flying:
        return (f"a {REVIEW_WORKFLOW} run on {short} is "
                f"{str(flying[0].get('status') or 'queued').replace('_', ' ')}")
    if spoke_at(pull["number"], head, login):
        return f"{REVIEW_WORKFLOW} has run on {short} and {login}'s verdict on it stands"
    return ""


def request_review(pr: str | int, to: str) -> None:
    """Request pull request review from a designated Role account.

    Signals a role handoff by requesting review on GitHub. If a review request
    is already pending for the designated login, it is withdrawn and re-requested
    to trigger notification events — but only where the request is stale, since
    a run already standing on this head would be duplicated by one that fires
    again, and `reviewing` says which of the two this is (solorepo's #950).
    Polls branch mergeability and refuses review
    requests if the branch is conflicting (solorepo's DR-145). Draft status
    remains unchanged: it is the work-in-progress semaphore until final
    reviewer approval (solorepo's DR-287). Reads back requested reviewers to verify
    the assignment took effect.

    Parameters:
        pr (int or str): Pull request number.
        to (str): Target Role name (e.g., 'reviewer').

    Raises:
        RequestRefused: For a refused `pr edit` that wrote nothing — the remove,
            or an add that followed no remove.
        SystemExit: If the pull request is not open, if its branch conflicts
            with its base, if the reviewer was removed but could not be added
            back, or if GitHub does not show the reviewer requested after the write.
    """
    login = channel.role_login(to)
    pull = channel.gh("pr", "view", str(pr), "--json", pull_requests.ADVANCE)
    if pull.get("state") != "OPEN":
        sys.exit(f"say: #{pr} is {pull.get('state', '').lower()}, not open")
    if pull_requests.mergeability(pull) == "CONFLICTING":
        sys.exit(f"say: #{pr}'s branch {pull['headRefName']} conflicts with its base, "
                 f"{pull['baseRefName']}. GitHub builds no merge ref for one that does, "
                 "review.yml runs on pull_request, and so a review requested on it would "
                 f"create no run and be answered by nobody. Rebase {pull['headRefName']} "
                 f"onto {pull['baseRefName']}, push, and the request can be made")
    def asked() -> list[str]:
        return [r.get("login") for r
                in channel.gh("pr", "view", str(pr), "--json", "reviewRequests")["reviewRequests"]]

    again = login in asked()
    if again and (answered := reviewing(pull, login)):
        print(f"review of #{pr} stands requested of {login}, and {answered}; nothing was "
              "asked again, which would have started a second run on the same head")
        return

    def request() -> None:
        """The request, withdrawn first where one already stands so that GitHub delivers it again."""
        if again:
            try:
                channel.gh("pr", "edit", str(pr), "--remove-reviewer", login, parse=False)
            except SystemExit as exc:
                raise RequestRefused(exc.code) from exc
        try:
            channel.gh("pr", "edit", str(pr), "--add-reviewer", login, parse=False)
        except SystemExit as exc:
            if again:
                sys.exit(f"say: removed {login} from #{pr} but could not add them back — {exc.code}")
            raise RequestRefused(exc.code) from exc

    channel.act(request, asked, lambda who: login in who,
                lambda who: f"say: GitHub shows {who or 'nobody'} requested on #{pr} after the "
                            f"call, not {login}")
    print(f"{'requested again' if again else 'requested'} review of #{pr} from {login}")
