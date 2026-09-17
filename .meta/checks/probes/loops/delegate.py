"""The `delegate` verb: which loop is dispatched for which intent.

One module for one probe, so a history log's receipt names the file holding it (solorepo's DR-209).
"""
import subprocess
from typing import Any

from collect import check
from probes.harness import (
    load_channel,
    outcome,
    stood_in,
)


@check("delegate probes", pre=True)
def delegate_probes():
    """`move delegate` on either a Challenge or pull request, verifying difficulty level enforcement and pass dispatches."""
    channel, _, programs = load_channel()
    move = programs["move"]
    problems = []

    class FakeDelegate:
        def __init__(
            self,
            issue_labels: list[str],
            assignees: list[str] | None = None,
            is_pr: bool = False,
            pr_data: dict[str, Any] | None = None,
            open_prs: list[dict[str, Any]] | None = None,
        ) -> None:
            self.labels = list(issue_labels)
            self.assignees = list(assignees or [])
            self.is_pr = is_pr
            self.pr_data = pr_data or {}
            self.open_prs = open_prs or []
            self.dispatched: list[tuple[Any, Any]] = []
            self.edits: list[Any] = []

        def __call__(self, *args: Any, parse: bool = True, **kwargs: Any) -> Any:
            cmd = args
            if cmd[:2] == ("pr", "view"):
                if self.is_pr:
                    return self.pr_data
                raise subprocess.CalledProcessError(1, ["gh", "pr", "view"], output="", stderr="mock API error")
            if cmd[:2] == ("pr", "list"):
                return self.open_prs
            if cmd[:2] == ("issue", "view"):
                return {
                    "number": int(cmd[2]),
                    "state": "OPEN",
                    "labels": [{"name": lbl} for lbl in self.labels],
                    "assignees": [{"login": a} for a in self.assignees],
                }
            if cmd[:2] == ("issue", "edit"):
                self.edits.append(cmd)
                for idx, arg in enumerate(cmd):
                    if arg == "--add-assignee":
                        self.assignees.append(cmd[idx + 1])
                    elif arg == "--add-label":
                        lbl = cmd[idx + 1]
                        if lbl not in self.labels:
                            self.labels.append(lbl)
                    elif arg == "--remove-label":
                        lbl = cmd[idx + 1]
                        if lbl in self.labels:
                            self.labels.remove(lbl)
                return ""
            if cmd[:2] == ("workflow", "run"):
                pr = None
                task = None
                for arg in cmd:
                    if arg.startswith("pull_request="):
                        pr = arg.split("=")[1]
                    elif arg.startswith("task="):
                        task = arg.split("=")[1]
                self.dispatched.append((pr, task))
                return ""
            if cmd[:2] == ("api", "user"):
                return "o-r-coder"
            if cmd[:2] == ("repo", "view"):
                return {"nameWithOwner": "o/r"}
            raise AssertionError(f"mock asked unknown: {cmd}")

    fake = FakeDelegate(["challenge"])
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("5"))
    if ran.code:
        problems.append(f"delegate: unestimated issue failed with exit {ran.code!r}")
    if "o-r-coder" not in fake.assignees:
        problems.append(f"delegate: unestimated issue was not assigned to coder (assignees: {fake.assignees})")
    if "medium" not in fake.labels:
        problems.append(f"delegate: unestimated issue was not labelled with medium (labels: {fake.labels})")
    adds = [cmd for cmd in fake.edits if "--add-label" in cmd and "medium" in cmd]
    if not adds:
        problems.append("delegate: unestimated issue did not trigger labeled event via label addition")
    if "triggered coder loop via label change" not in ran.out:
        problems.append(f"delegate: unestimated issue did not state label change trigger:\n{ran.out}")

    fake = FakeDelegate(["challenge", "medium"])
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("5"))
    if ran.code:
        problems.append(f"delegate: medium issue failed with exit {ran.code!r}")
    removes = [cmd for cmd in fake.edits if "--remove-label" in cmd and "medium" in cmd]
    adds = [cmd for cmd in fake.edits if "--add-label" in cmd and "medium" in cmd]
    if not removes or not adds:
        problems.append("delegate: medium issue did not trigger labeled event by removing and re-adding label")
    if "triggered coder loop via label re-addition" not in ran.out:
        problems.append(f"delegate: medium issue did not state label re-addition trigger:\n{ran.out}")

    fake = FakeDelegate(["challenge", "hard"])
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("5"))
    if not ran.code or "pass --level to explicitly delegate" not in ran.code:
        problems.append(f"delegate: hard issue without --level was not refused:\n{ran.code}")
    if fake.assignees or fake.edits:
        problems.append("delegate: refused hard issue modified issue state")

    fake = FakeDelegate(["challenge", "hard"])
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("5", level="medium"))
    if ran.code:
        problems.append(f"delegate: hard issue with explicit --level medium failed: {ran.code}")
    if "o-r-coder" not in fake.assignees:
        problems.append(f"delegate: explicit --level did not assign coder (assignees: {fake.assignees})")
    if "medium" not in fake.labels or "hard" in fake.labels:
        problems.append(f"delegate: explicit --level did not update labels (labels: {fake.labels})")

    fake = FakeDelegate(["challenge", "medium"], open_prs=[
        {
            "number": 101,
            "headRefName": "claude/issue-5",
            "baseRefName": "main",
            "mergeable": "CONFLICTING",
            "reviews": [{"state": "CHANGES_REQUESTED", "author": {"login": "o-r-reviewer"}}],
        }
    ])
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("5"))
    if ran.code:
        problems.append(f"delegate: conflicting PR failed with exit {ran.code!r}")
    if fake.dispatched != [("101", "rebase")]:
        problems.append(f"delegate: conflicting PR with changes requested did not prioritize rebase (dispatched: {fake.dispatched})")
    if "dispatched rebase pass" not in ran.out:
        problems.append(f"delegate: conflicting PR did not print rebase dispatch message:\n{ran.out}")

    fake = FakeDelegate(["challenge", "medium"], is_pr=True, pr_data={
        "number": 101,
        "headRefName": "claude/issue-5",
        "baseRefName": "main",
        "mergeable": "MERGEABLE",
        "reviews": [{"state": "CHANGES_REQUESTED", "author": {"login": "o-r-reviewer"}}],
    })
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("101"))
    if ran.code:
        problems.append(f"delegate: changes requested PR failed with exit {ran.code!r}")
    if fake.dispatched != [("101", "review")]:
        problems.append(f"delegate: did not dispatch review to 101 (dispatched: {fake.dispatched})")
    if "dispatched review pass" not in ran.out:
        problems.append(f"delegate: changes requested PR did not print review dispatch message:\n{ran.out}")

    fake = FakeDelegate(["challenge", "medium"], is_pr=True, pr_data={
        "number": 101,
        "headRefName": "claude/issue-5",
        "baseRefName": "main",
        "mergeable": "MERGEABLE",
        "reviews": [],
    })
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("101"))
    if not ran.code or "is clean and has no standing changes requested" not in ran.code:
        problems.append(f"delegate: clean PR without changes requested was not refused:\n{ran.code}")
    if fake.dispatched:
        problems.append(f"delegate: clean PR unexpectedly dispatched passes: {fake.dispatched}")

    fake = FakeDelegate(["challenge", "medium"], is_pr=True, pr_data={
        "number": 102,
        "headRefName": "feature/not-a-loop",
        "baseRefName": "main",
        "mergeable": "MERGEABLE",
        "reviews": [],
    })
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("102"))
    if not ran.code or "is not a loop branch" not in ran.code:
        problems.append(f"delegate: non-loop branch PR was not refused:\n{ran.code}")
    if fake.dispatched:
        problems.append(f"delegate: non-loop branch PR unexpectedly dispatched passes: {fake.dispatched}")

    return problems
