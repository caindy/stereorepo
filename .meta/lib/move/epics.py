"""Epic decomposition and completion using GitHub's native Issue relationships."""
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

import channel
from lib.move import challenges

EPIC_LABEL = "epic"
"""The visible marker for a parent Challenge awaiting its child Challenges."""
SUBISSUES_UNREADABLE = "say: GitHub did not return the sub-issues of #{issue}"
"""The failure when GitHub does not return a parent's native child Issues."""


def children_of(issue: int | str) -> list[dict[str, Any]]:
    """Return the direct GitHub sub-issues of an Issue."""
    found = channel.gh("api", "--paginate",
                       f"repos/{channel.repo()}/issues/{issue}/sub_issues")
    if not isinstance(found, list):
        raise SystemExit(SUBISSUES_UNREADABLE.format(issue=issue))
    return found


def link_child(parent: int | str, child: int | str) -> None:
    """Record a child as a native sub-issue of its parent."""
    repo = channel.repo()
    child_id = channel.gh("api", f"repos/{repo}/issues/{child}")["id"]
    existing = {int(item["number"]) for item in children_of(parent)}
    if int(child) in existing:
        return
    channel.gh("api", f"repos/{repo}/issues/{parent}/sub_issues", "-X", "POST",
               "-F", f"sub_issue_id={child_id}", parse=False)
    current = {int(item["number"]) for item in children_of(parent)}
    if int(child) not in current:
        sys.exit(f"say: GitHub did not link child Challenge #{child} to Epic #{parent}")


def approved_plan(parent: int | str) -> dict[str, Any] | None:
    """Read the coder's plan only when the next Issue comment is owner approval."""
    comments = channel.gh("api", "--paginate",
                          f"repos/{channel.repo()}/issues/{parent}/comments")
    coder = channel.role_login("coder")
    for index in range(len(comments) - 1, 0, -1):
        approval, proposal = comments[index], comments[index - 1]
        if (approval.get("body", "").strip() != "Approve decomposition"
                or approval.get("author_association") != "OWNER"
                or proposal.get("user", {}).get("login") != coder
                or "## Decomposition plan" not in proposal.get("body", "")):
            continue
        fence = chr(96) * 3
        match = re.search(fence + r"json\s*(\{.*?\})\s*" + fence,
                          proposal.get("body", ""), re.S)
        if not match:
            return None
        try:
            plan = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
        return plan if isinstance(plan, dict) and isinstance(plan.get("children"), list) else None
    return None


def approved(parent: int | str) -> bool:
    """Whether a repository owner approved the coder's immediately preceding valid plan."""
    return approved_plan(parent) is not None


def decompose(parent: int | str, source: str) -> None:
    """Create reviewer-triaged child Challenges from an approved JSON plan.

    The input is a JSON object with a children array. Each child has a
    title, body, and optional blocked_by array of earlier child indexes.
    """
    _require_hard_parent(parent)
    approved = approved_plan(parent)
    if approved is None:
        sys.exit("say: the solo has not approved this decomposition; comment "
                 "Approve decomposition as the repository owner first")
    validated = _validated_children(source, approved)
    _ensure_epic_label(parent)
    linked = {str(child["title"]): str(child["number"]) for child in children_of(parent)}
    created = _create_children(parent, validated, linked)
    print(f"Epic #{parent}: linked child Challenges {', '.join('#' + n for n in created)}")


def _require_hard_parent(parent: int | str) -> None:
    """Refuse decomposition unless the parent remains open, hard, and a Challenge."""
    view = channel.gh("issue", "view", str(parent), "--json", "state,labels")
    labels = {item["name"] for item in view.get("labels", [])}
    if view.get("state") != "OPEN" or "hard" not in labels or "challenge" not in labels:
        sys.exit(f"say: #{parent} must be an open, hard Challenge before decomposition")


def _validated_children(source: str, approved: dict[str, Any]) -> list[tuple[str, str, list[int]]]:
    """Parse the exact approved plan and validate each child and dependency index."""
    try:
        plan = json.loads(source)
        entries = plan["children"] if isinstance(plan, dict) else None
    except json.JSONDecodeError:
        sys.exit("say: decomposition input must be JSON with a children array")
    if plan != approved:
        sys.exit("say: decomposition input does not match the approved plan")
    if not isinstance(entries, list) or len(entries) < 2:
        sys.exit("say: a hard Challenge decomposition needs at least two child Challenges")
    validated: list[tuple[str, str, list[int]]] = []
    titles: set[str] = set()
    for index, item in enumerate(entries):
        child = _validated_child(index, item)
        if child[0] in titles:
            sys.exit(f"say: child title {child[0]!r} appears more than once")
        titles.add(child[0])
        validated.append(child)
    return validated


def _validated_child(index: int, item: Any) -> tuple[str, str, list[int]]:
    """Validate one child entry's title, proposed difficulty, and earlier blockers."""
    if not isinstance(item, Mapping):
        sys.exit(f"say: child {index + 1} must be an object")
    title, body = item.get("title"), item.get("body")
    blockers = item.get("blocked_by", [])
    if not isinstance(title, str) or not title.strip() or not isinstance(body, str):
        sys.exit(f"say: child {index + 1} needs a title and body")
    if not body.startswith("**Waits on.**"):
        sys.exit(f"say: child {index + 1} body must begin with **Waits on.**")
    if not re.search(r"^\*\*Difficulty\.\*\*\s*`?(easy|medium)`?(?:\s|$)",
                     body, re.M | re.I):
        sys.exit(f"say: child {index + 1} must propose easy or medium under **Difficulty.**")
    if not isinstance(blockers, list) or any(
            not isinstance(ref, int) or ref < 0 or ref >= index for ref in blockers):
        sys.exit(f"say: child {index + 1} blockers must name earlier child indexes")
    return title.strip(), body, blockers


def _ensure_epic_label(parent: int | str) -> None:
    """Create the Epic label if necessary and mark the open parent Issue."""
    labels = channel.gh("label", "list", "--limit", "1000", "--json", "name")
    if EPIC_LABEL not in {label["name"] for label in labels}:
        channel.gh("label", "create", EPIC_LABEL, "--color", "5319e7",
                   "--description", "Parent Challenge with child Challenges", parse=False)
    channel.gh("issue", "edit", str(parent), "--add-label", EPIC_LABEL, parse=False)


def _create_children(parent: int | str, validated: list[tuple[str, str, list[int]]],
                     linked: dict[str, str]) -> list[str]:
    """Create missing child Issues, recover partial filings, and link each native sub-issue."""
    issue_queue = challenges.open_issue_queue()
    created: list[str] = []
    for title, body, blockers in validated:
        blocker_numbers = []
        for ref in blockers:
            blocker = created[ref]
            state = channel.gh("issue", "view", blocker, "--json", "state")["state"]
            if state == "OPEN":
                blocker_numbers.append(int(blocker))
        number = linked.get(title)
        if number is None:
            existing = challenges.open_with_title(title, issue_queue)
            if existing:
                candidate = channel.gh("issue", "view", existing[0], "--json", "body")
                marker = f"**Parent Epic.** #{parent}"
                if marker not in str(candidate.get("body") or ""):
                    sys.exit(f"say: open Issue #{existing[0]} already uses child title {title!r}; "
                             "nothing was linked to the Epic")
                number = existing[0]
            else:
                child_body = f"{body.rstrip()}\n\n**Parent Epic.** #{parent}\n"
                number, _ = challenges.file_issue(title, channel.signed(child_body),
                                                  blocked_by=blocker_numbers)
        created.append(number)
        link_child(parent, number)
    return created


def close_completed() -> None:
    """Close open Epics whose direct child Challenges have all closed."""
    epics = channel.gh("issue", "list", "--state", "open", "--label", EPIC_LABEL,
                       "--limit", "1000", "--json", "number,labels")
    for epic in epics:
        if EPIC_LABEL not in {item.get("name") for item in epic.get("labels", [])}:
            continue
        number = int(epic["number"])
        children = children_of(number)
        plan = approved_plan(number)
        expected = (plan or {}).get("children", [])
        complete = len(expected) > 0 and len(children) == len(expected) and all(
            child.get("state") == "closed" for child in children)
        if complete:
            channel.gh("issue", "close", str(number), parse=False)
            state = channel.gh("issue", "view", str(number), "--json", "state")["state"]
            if state != "CLOSED":
                sys.exit(f"say: GitHub still shows completed Epic #{number} as {state}")
            print(f"Epic #{number}: closed after all {len(children)} child Challenges closed")
