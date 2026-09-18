"""The `delegate` verb: which loop is dispatched for which intent.

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import subprocess
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    environment,
    load_channel,
    outcome,
    stood_in,
)


class FakeDelegate:
    """As much of GitHub as `delegate` asks about: one Issue's labels and assignees, the pull request it names, and the open pull requests on it.

    `labels` and `assignees` are as the calls leave them; `edits` records every
    `issue edit` and `dispatched` every `workflow run` as `(pull_request, task)`.
    `pr view` answers `pr_data` where `is_pr`, and otherwise raises
    `subprocess.CalledProcessError`, which is what a number that is an Issue
    looks like to the channel. `repo view` answers `o/r` and `api user` answers
    `o-r-coder`, the coder Role's login for that repository.
    """

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
        """One `gh` call, answered by the handler for its first two words."""
        handlers = {
            ("pr", "view"): self.view_pull,
            ("pr", "list"): lambda cmd: self.open_prs,
            ("issue", "view"): self.view_issue,
            ("issue", "edit"): self.edit_issue,
            ("workflow", "run"): self.run_workflow,
            ("api", "user"): lambda cmd: "o-r-coder",
            ("repo", "view"): lambda cmd: {"nameWithOwner": "o/r"},
        }
        handler = handlers.get(args[:2])
        if handler is None:
            raise AssertionError(f"mock asked unknown: {args}")
        return handler(args)

    def view_pull(self, cmd: tuple[Any, ...]) -> Any:
        """`pr_data` where the number is a pull request, and the CLI's error otherwise."""
        if self.is_pr:
            return self.pr_data
        raise subprocess.CalledProcessError(1, ["gh", "pr", "view"], output="", stderr="mock API error")

    def view_issue(self, cmd: tuple[Any, ...]) -> dict[str, Any]:
        """The Issue as its labels and assignees stand."""
        return {
            "number": int(cmd[2]),
            "state": "OPEN",
            "labels": [{"name": lbl} for lbl in self.labels],
            "assignees": [{"login": a} for a in self.assignees],
        }

    def edit_issue(self, cmd: tuple[Any, ...]) -> str:
        """Apply `--add-assignee`, `--add-label` and `--remove-label` to the Issue, recording the call in `edits`."""
        self.edits.append(cmd)
        for idx, arg in enumerate(cmd):
            if arg == "--add-assignee":
                self.assignees.append(cmd[idx + 1])
            elif arg == "--add-label" and cmd[idx + 1] not in self.labels:
                self.labels.append(cmd[idx + 1])
            elif arg == "--remove-label" and cmd[idx + 1] in self.labels:
                self.labels.remove(cmd[idx + 1])
        return ""

    def run_workflow(self, cmd: tuple[Any, ...]) -> str:
        """Record the `(pull_request, task)` a dispatch names."""
        fields = dict(arg.split("=", 1) for arg in cmd if "=" in arg and not arg.startswith("-"))
        self.dispatched.append((fields.get("pull_request"), fields.get("task")))
        return ""


def _unestimated_issue_is_labelled_medium_and_assigned(channel, move) -> list[str]:
    problems: list[str] = []
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
    return problems


def _medium_issue_has_its_label_re_added(channel, move) -> list[str]:
    problems: list[str] = []
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
    return problems


def _hard_issue_refused_without_level(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeDelegate(["challenge", "hard"])
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("5"))
    if not ran.code or "pass --level to explicitly delegate" not in ran.code:
        problems.append(f"delegate: hard issue without --level was not refused:\n{ran.code}")
    if fake.assignees or fake.edits:
        problems.append("delegate: refused hard issue modified issue state")
    return problems


def _hard_issue_delegated_with_an_explicit_level(channel, move) -> list[str]:
    problems: list[str] = []
    fake = FakeDelegate(["challenge", "hard"])
    with stood_in(channel, gh=fake):
        ran = outcome(lambda: move.delegate("5", level="medium"))
    if ran.code:
        problems.append(f"delegate: hard issue with explicit --level medium failed: {ran.code}")
    if "o-r-coder" not in fake.assignees:
        problems.append(f"delegate: explicit --level did not assign coder (assignees: {fake.assignees})")
    if "medium" not in fake.labels or "hard" in fake.labels:
        problems.append(f"delegate: explicit --level did not update labels (labels: {fake.labels})")
    return problems


def _conflicting_pull_request_dispatches_rebase_first(channel, move) -> list[str]:
    problems: list[str] = []
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
    return problems


def _changes_requested_pull_request_dispatches_review(channel, move) -> list[str]:
    problems: list[str] = []
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
    return problems


def _clean_pull_request_refused(channel, move) -> list[str]:
    problems: list[str] = []
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
    return problems


def _pull_request_off_the_loops_branch_refused(channel, move) -> list[str]:
    problems: list[str] = []
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


@check("delegate probes", pre=True)
def delegate_probes():
    """`move delegate` on either a Challenge or pull request, verifying difficulty level enforcement and pass dispatches.

    `delegate` is the solo's, and a run is refused the level it lands
    (solorepo's DR-235), so `ACTOR_SESSION` is unset around every case rather
    than left as the environment has it: the gate runs inside the coder loop's
    container as well as on a laptop, and the same case would otherwise be a
    delegation in one place and a refused level in the other. The run's own case
    is stated where the refusal is, in `probes/channel/level.py`.
    """
    channel, _, programs = load_channel()
    move = programs["move"]
    with environment(ACTOR_SESSION=None):
        return [problem for problems in (
            _unestimated_issue_is_labelled_medium_and_assigned(channel, move),
            _medium_issue_has_its_label_re_added(channel, move),
            _hard_issue_refused_without_level(channel, move),
            _hard_issue_delegated_with_an_explicit_level(channel, move),
            _conflicting_pull_request_dispatches_rebase_first(channel, move),
            _changes_requested_pull_request_dispatches_review(channel, move),
            _clean_pull_request_refused(channel, move),
            _pull_request_off_the_loops_branch_refused(channel, move)
        ) for problem in problems]

