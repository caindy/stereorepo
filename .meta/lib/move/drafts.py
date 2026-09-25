"""Draft to merge-ready pull request transitions (solorepo's DR-287)."""
import sys

import channel
from lib.check_pr import state

FIELDS = ("number,state,isDraft,headRefName,baseRefName,changedFiles,mergeable,latestReviews,"
          "reviews,reviewRequests,statusCheckRollup")
"""What `ready` reads to verify final reviewer approval before leaving draft."""


def holds_changes(pull: object) -> bool:
    """Return whether a pull request changes at least one file against its base."""
    return (
        isinstance(pull, dict)
        and isinstance(pull.get("changedFiles"), int)
        and pull["changedFiles"] > 0
    )


def draft(pr: str | int) -> None:
    """Return an undrafted pull request to draft (solorepo's DR-287).

    Parameters:
        pr: Pull request number.

    Raises:
        SystemExit: If the pull request is not open or remains undrafted after
            the mutation.
    """
    pull = channel.gh("pr", "view", str(pr), "--json", "state,isDraft")
    if pull.get("state") != "OPEN":
        sys.exit(f"say: #{pr} is {pull.get('state', '').lower()}, not open")
    if pull.get("isDraft"):
        print(f"#{pr} is draft already")
        return
    channel.act(
        lambda: channel.gh("pr", "ready", str(pr), "--undo", parse=False),
        lambda: bool(channel.gh("pr", "view", str(pr), "--json", "isDraft")["isDraft"]),
        lambda is_draft: is_draft,
        lambda _: f"say: GitHub shows #{pr} still not a draft after the call")
    print(f"#{pr} returned to draft")


def ready(pr: str | int) -> None:
    """Take an approved, green implementation pull request out of draft."""
    pull = channel.gh("pr", "view", str(pr), "--json", FIELDS)
    if pull.get("state") != "OPEN":
        sys.exit(f"say: #{pr} is {pull.get('state', '').lower()}, not open")
    if not pull.get("isDraft"):
        print(f"#{pr} is ready to merge already")
        return
    if not holds_changes(pull):
        sys.exit(f"say: #{pr}'s branch {pull['headRefName']} changes no file against "
                 f"{pull['baseRefName']}, so it stays a draft")
    reviewer = channel.role_login("reviewer")
    found = state.classify_pr(pull, reviewer_login=reviewer)
    if found is not state.PullRequestState.READY_TO_MERGE:
        sys.exit(f"say: #{pr} is {found.value}, not ready for the final draft transition")
    channel.act(
        lambda: channel.gh("pr", "ready", str(pr), parse=False),
        lambda: bool(channel.gh("pr", "view", str(pr), "--json", "isDraft")["isDraft"]),
        lambda draft: not draft,
        lambda _: f"say: GitHub shows #{pr} still a draft after the call")
    print(f"#{pr} is ready to merge")
