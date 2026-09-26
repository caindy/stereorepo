"""Epic children, completion, and leaf pull-request closing rules (solorepo's DR-292)."""
import json
from typing import Any

from checks import citations
from checks.collect import check
from checks.probes.harness import load_channel, stood_in

PARENT = 50
"""The parent Issue the fake holds open until its children close."""

PLAN = {"children": [
    {"title": "First child", "body": "**Waits on.** Nothing.\n\n**Difficulty.** medium"},
    {"title": "Second child", "body": "**Waits on.** Nothing.\n\n**Difficulty.** easy"},
]}
"""The approved decomposition the parent comment and GitHub links carry."""
UNANSWERED = "Epic probe received an unsupported GitHub call: {args!r}"
"""The assertion message when the fake receives an unsupported call."""


class EpicGitHub:
    """The comments, child Issues, and close operation needed by the Epic lifecycle."""

    def __init__(self, child_states: tuple[str, str]) -> None:
        self.state = "OPEN"
        self.children = [
            {"number": 51, "title": "First child", "state": child_states[0]},
            {"number": 52, "title": "Second child", "state": child_states[1]},
        ]
        self.comments = [
            {"user": {"login": "coder-login"}, "author_association": "OWNER",
             "body": "## Decomposition plan\n```json\n" + json.dumps(PLAN) + "\n```"},
            {"author_association": "OWNER", "body": "Approve decomposition"},
        ]
        self.closed: list[int] = []

    def __call__(self, *args: Any, parse: bool = True, **kwargs: Any) -> Any:
        """Answer only the Issue and API calls the Epic lifecycle is meant to make."""
        if args[:2] == ("issue", "list"):
            return ([{"number": PARENT, "labels": [{"name": "epic"}]}]
                    if self.state == "OPEN" else [])
        if args[:2] == ("issue", "view"):
            issue = str(args[2])
            if issue == str(PARENT):
                return {"state": self.state, "labels": [{"name": "epic"}]}
        if args[:2] == ("issue", "close"):
            self.state = "CLOSED"
            self.closed.append(int(args[2]))
            return ""
        if args and args[0] == "api":
            endpoint = str(args[2] if args[1] == "--paginate" else args[1])
            if endpoint.endswith("/comments"):
                return self.comments
            if endpoint.endswith("/sub_issues"):
                return self.children
        raise AssertionError(UNANSWERED.format(args=args))


@check("Epic lifecycle probes", pre=True)
def epic_lifecycle_probes() -> list[str]:
    """Only a complete, approved set of closed children closes its Epic; leaves cannot close it."""
    channel, _, programs = load_channel()
    epics = programs["move"].manager.epics
    problems: list[str] = []

    incomplete = EpicGitHub(("closed", "open"))
    with stood_in(channel, gh=incomplete, repo=lambda: "o/r",
                  role_login=lambda _role: "coder-login"):
        if epics.approved_plan(PARENT) != PLAN:
            problems.append("Epic: the owner approval did not authorize the immediately "
                            "preceding plan")
        epics.close_completed()
    if incomplete.state != "OPEN" or incomplete.closed:
        problems.append("Epic: a parent closed while one approved child remained open")

    complete = EpicGitHub(("closed", "closed"))
    with stood_in(channel, gh=complete, repo=lambda: "o/r",
                  role_login=lambda _role: "coder-login"):
        epics.close_completed()
    if complete.state != "CLOSED" or complete.closed != [PARENT]:
        problems.append("Epic: all closed children did not close their approved parent "
                        "exactly once")

    check_pr = citations.load_check_pr()
    epic = EpicGitHub(("OPEN", "OPEN"))
    body = f"**What it closes.**\n- Closes #{PARENT} — parent Epic\n"
    with stood_in(check_pr.github, gh=epic):
        refused = check_pr.form.check_closing_blockers(body)
    if not any("leaf pull request may close only child Challenges" in item for item in refused):
        problems.append(f"Epic: a leaf pull request could close its parent: {refused}")
    return problems
