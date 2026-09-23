"""Drafts: the one check before every way out of draft, and the verb that takes a pull request out.

A plan-only pull request is a draft while its plan is argued, and the merge
manager, `advance` and the reconciler all pass over a draft. What keeps its
empty commit from merging on the plan's approval is that nothing takes a
branch that changes no file out of draft, whatever the branch is named
(solorepo's DR-273). `move ready`, `request-review` and the merge manager's
restoration all ask `holds_changes` first.
"""
import sys
from collections.abc import Mapping

import channel
from lib.move import common

FIELDS = "number,state,isDraft,headRefName,baseRefName,changedFiles"
"""What `ready` reads of a pull request: whether it is open, a draft, and changes any file."""


def holds_changes(pull: Mapping[str, object]) -> bool:
    """Whether a pull request's branch changes any file against its base.

    A pull request read without `changedFiles` answers False, so a caller that
    forgot the field keeps the draft rather than lifting it.
    """
    changed = pull.get("changedFiles")
    return isinstance(changed, int) and changed > 0


def ready(pr: str | int) -> None:
    """Take a draft pull request out of draft, once its branch holds changes.

    Refused on a pull request that is not open, and on a branch that changes
    no file against its base, which is a plan and stays a draft.
    """
    pull = channel.gh("pr", "view", str(pr), "--json", FIELDS)
    if pull.get("state") != "OPEN":
        sys.exit(f"say: #{pr} is {pull.get('state', '').lower()}, not open")
    if not pull.get("isDraft"):
        print(f"#{pr} is ready for review already")
        return
    if not holds_changes(pull):
        sys.exit(f"say: #{pr}'s branch {pull['headRefName']} changes no file against "
                 f"{pull['baseRefName']}, so it is a plan and stays a draft. Push the "
                 "implementation first (solorepo's DR-273)")
    channel.act(
        lambda: channel.gh("pr", "ready", str(pr), parse=False),
        lambda: bool(channel.gh("pr", "view", str(pr), "--json", "isDraft")["isDraft"]),
        lambda draft: not draft,
        lambda _: f"say: GitHub shows #{pr} still a draft after the call")
    print(f"#{pr} is ready for review")


def restore(pr: str | int, pull: Mapping[str, object]) -> None:
    """Take a loop's draft out of draft on its way to review, unless it holds no changes.

    Loop drafts are restored on the request that hands them back to review
    (solorepo's DR-258); a failed call is warned about rather than raised, so
    the request itself still goes out.
    """
    if not holds_changes(pull):
        print(f"left #{pr} a draft: its branch changes no file (solorepo's DR-273)")
        return
    try:
        channel.gh("pr", "ready", str(pr), parse=False)
        print(f"restored #{pr} from draft to ready for review")
    except (SystemExit, *common.UNREACHED) as exc:
        print(f"warning: could not mark #{pr} ready for review: {exc}", file=sys.stderr)
