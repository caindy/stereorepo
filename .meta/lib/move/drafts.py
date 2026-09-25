"""The final transition from work-in-progress draft to merge-ready pull request."""
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
