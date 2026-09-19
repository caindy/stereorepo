"""`move waits` over the refusals it exists for, and the two records it keeps (solorepo's DR-213).
"""
import functools
import subprocess
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    load_channel,
    run_verb,
)


class FakeBlockers:
    """As much of GitHub as `move waits` and `file_issue` ask about, over `owner/repo`."""

    def __init__(self, issues: dict[int, Any],
                 blockers: dict[int, list[int]] | None = None,
                 deaf_body: bool = False,
                 deaf_relationship: bool = False) -> None:
        self.issues = issues
        self.blockers = {n: list(b) for n, b in (blockers or {}).items()}
        self.bodies: dict[int, str] = {n: str(data.get("body", "")) for n, data in issues.items()}
        self.labels: dict[int, list[str]] = {n: list(data.get("labels", ["challenge"])) for n, data in issues.items()}
        self.edits = 0
        self.deaf_body = deaf_body
        self.deaf_relationship = deaf_relationship

    def gh(self, *args: str, parse: bool = True, tolerate_fail: bool = False) -> Any:
        """One `gh` call: `repo view`, `api` (issue view), `issue view`, `issue edit`, or `issue create`."""
        head = args[:2]
        if head == ("repo", "view"):
            return {"nameWithOwner": "owner/repo"}
        if args[0] == "api":
            number = int(str(args[1]).rsplit("/", 1)[-1])
            if number not in self.issues:
                raise subprocess.CalledProcessError(1, ["gh", *list(args)], stderr="HTTP 404")
            return self.issues[number]
        if head == ("issue", "view"):
            number = int(args[2])
            nodes = [{"number": b} for b in self.blockers.get(number, [])]
            lbls = [{"name": lbl} for lbl in self.labels.get(number, ["challenge"])]
            return {"body": self.bodies.get(number, ""), "blockedBy": {"nodes": nodes}, "labels": lbls}
        if head == ("issue", "edit"):
            self.edits += 1
            number, flags = int(args[2]), list(args[3:])
            for flag, value in zip(flags[::2], flags[1::2], strict=True):
                if flag == "--add-blocked-by" and not self.deaf_relationship:
                    self.blockers.setdefault(number, []).append(int(value))
                elif flag == "--remove-blocked-by" and not self.deaf_relationship:
                    self.blockers[number] = [b for b in self.blockers.get(number, []) if b != int(value)]
                elif flag == "--body" and not self.deaf_body:
                    self.bodies[number] = value
            return ""
        if head == ("issue", "create"):
            self.edits += 1
            flags = list(args[2:])
            body = flags[flags.index("--body") + 1] if "--body" in flags else ""
            blocked = []
            if "--blocked-by" in flags:
                blocked = [int(n.strip()) for n in flags[flags.index("--blocked-by") + 1].split(",") if n.strip()]
            new_num = 901
            self.issues[new_num] = {"state": "open", "body": body}
            self.bodies[new_num] = body
            self.blockers[new_num] = blocked
            self.labels[new_num] = ["challenge"]
            return f"https://github.com/owner/repo/issues/{new_num}"
        return {}


def _said(channel: Any, fake: FakeBlockers, call: Any) -> str:
    """The text `call` answered with, or empty string on silent success."""
    res = run_verb(channel, fake.gh, call)
    return "" if res is None else res


def _refusal_probes(channel: Any, move: Any, open_issue: dict[str, Any]) -> list[str]:
    """Problems found running `move waits` over refused invocations."""
    problems: list[str] = []
    refusals = (
        ("a blocker GitHub has no number for", f"no #{'99'}",
         {1: open_issue}, None, lambda m: m.waits(1, on=[99])),
        ("a blocker that is a pull request", "pull request",
         {1: open_issue, 2: {"state": "open", "pull_request": {}}}, None,
         lambda m: m.waits(1, on=[2])),
        ("a blocker that is closed", "closed",
         {1: open_issue, 2: {"state": "closed", "body": ""}}, None,
         lambda m: m.waits(1, on=[2])),
        ("an Issue naming itself", "cannot wait on itself",
         {1: open_issue}, None, lambda m: m.waits(1, on=[1])),
        ("an Issue that already blocks its candidate", "cycle",
         {1: open_issue, 2: {"state": "open", "body": ""}, 3: {"state": "open", "body": ""}},
         {2: [3], 3: [1]}, lambda m: m.waits(1, on=[2])),
        ("a target that is closed", "closed",
         {1: {"state": "closed", "body": "**Waits on.** Nothing."}}, None,
         lambda m: m.waits(1, clear=True)),
        ("an Issue with no such line", "has no `**Waits on.**` line",
         {1: {"state": "open", "body": "filed some other way"},
          2: {"state": "open", "body": ""}}, None, lambda m: m.waits(1, on=[2])),
        ("removing a blocker with an attached explanatory clause", "says",
         {1: {"state": "open", "body": f"**Waits on.** #{'2'}, which settles who may put a decision in force.\n\n**What was noticed.** Detail.\n"},
          2: {"state": "open", "body": ""}}, {1: [2]}, lambda m: m.waits(1, off=[2])),
    )
    for case, phrase, issues, blockers, call in refusals:
        fake = FakeBlockers(issues, blockers)
        answer = _said(channel, fake, functools.partial(call, move))
        if not answer or phrase not in answer:
            problems.append(f"waits: {case} was told {answer!r}, which does not say {phrase!r}")
        if fake.edits:
            problems.append(f"waits: {case} made {fake.edits} edits having refused")
    return problems


def _mutation_probes(channel: Any, move: Any, open_issue: dict[str, Any]) -> list[str]:
    """Problems found running `move waits` over valid mutations and verify checks."""
    problems: list[str] = []

    fake = FakeBlockers({1: open_issue, 2: {"state": "open", "body": ""}})
    answer = _said(channel, fake, lambda: move.waits(1, on=[2]))
    if answer or fake.blockers.get(1) != [2]:
        problems.append(f"waits: setting a blocker said {answer!r} and left GitHub holding {fake.blockers}")
    if f"**Waits on.** #{'2'}" not in fake.bodies.get(1, ""):
        problems.append(f"waits: setting a blocker left the line as {fake.bodies.get(1)!r}")
    if "**What was noticed.**" not in fake.bodies.get(1, ""):
        problems.append("waits: setting a blocker lost the body below the line")

    prose_body = {"state": "open", "body": f"**Waits on.** Decision DR-{'041'}.\n\n**What was noticed.** Text.\n"}
    fake = FakeBlockers({1: prose_body, 2: {"state": "open", "body": ""}})
    answer = _said(channel, fake, lambda: move.waits(1, on=[2]))
    if answer or fake.blockers.get(1) != [2]:
        problems.append(f"waits: setting a blocker with prose said {answer!r} and left {fake.blockers}")
    if f"**Waits on.** Decision DR-{'041'}, #{'2'}" not in fake.bodies.get(1, ""):
        problems.append(f"waits: setting a blocker did not preserve prose: {fake.bodies.get(1)!r}")

    joined = {"state": "open", "body": f"**Waits on.** #{'2'}, #{'3'}\n\n**What was noticed.** Text.\n"}
    fake = FakeBlockers({1: joined, 2: {"state": "open", "body": ""}, 3: {"state": "open", "body": ""}},
                        {1: [2, 3]})
    answer = _said(channel, fake, lambda: move.waits(1, off=[2]))
    if answer or fake.blockers.get(1) != [3]:
        problems.append(f"waits: dropping one blocker said {answer!r} and left {fake.blockers}")
    if f"**Waits on.** #{'3'}" not in fake.bodies.get(1, ""):
        problems.append(f"waits: dropping one blocker left the line as {fake.bodies.get(1)!r}")

    fake = FakeBlockers({1: {"state": "open", "body": f"**Waits on.** #{'2'}\n\n**What was noticed.** Text.\n"},
                         2: {"state": "open", "body": ""}}, {1: [2]})
    answer = _said(channel, fake, lambda: move.waits(1, clear=True))
    if answer or fake.blockers.get(1) != []:
        problems.append(f"waits: clearing said {answer!r} and left GitHub holding {fake.blockers}")
    if "**Waits on.** Nothing." not in fake.bodies.get(1, ""):
        problems.append(f"waits: clearing left the line as {fake.bodies.get(1)!r}")

    fake = FakeBlockers({1: {"state": "open", "body": f"**Waits on.** #{'2'}\n\n**What was noticed.** Text.\n"},
                         2: {"state": "open", "body": ""}}, {1: [2]})
    answer = _said(channel, fake, lambda: move.waits(1, on=[2]))
    if fake.edits:
        problems.append(f"waits: idempotent call made {fake.edits} edits")

    return problems


def _readback_probes(channel: Any, move: Any, open_issue: dict[str, Any]) -> list[str]:
    """Problems found running `move waits` against a GitHub that drops one of the two writes.

    Each case makes `waits_verify` the only thing standing between a dropped
    edit and a silent success, which is what the read-back of both records
    exists for (solorepo's DR-213).
    """
    problems: list[str] = []

    fake = FakeBlockers({1: open_issue, 2: {"state": "open", "body": ""}}, deaf_body=True)
    answer = _said(channel, fake, lambda: move.waits(1, on=[2]))
    if not answer or "line not citing" not in answer:
        problems.append(f"waits: deaf body edit was told {answer!r}")

    fake = FakeBlockers({1: open_issue, 2: {"state": "open", "body": ""}}, deaf_relationship=True)
    answer = _said(channel, fake, lambda: move.waits(1, on=[2]))
    if not answer or "blockedBy" not in answer or "not" not in answer:
        problems.append(f"waits: deaf relationship edit was told {answer!r}")

    return problems


def _filing_probes(channel: Any, move: Any) -> list[str]:
    """Problems found running `file_issue` with `--blocked-by`."""
    problems: list[str] = []
    fake = FakeBlockers({2: {"state": "open", "body": ""}, 3: {"state": "closed", "body": ""}})

    answer = _said(channel, fake, lambda: move.file_issue("Title", f"**Waits on.** #{'2'}.\n\nWhat was noticed.\n",
                                                          blocked_by=[2]))
    if answer or fake.blockers.get(901) != [2]:
        problems.append(f"file_issue: filing with --blocked-by said {answer!r} and left {fake.blockers}")

    answer = _said(channel, fake, lambda: move.file_issue("Title", f"**Waits on.** #{'2'}.\n\nWhat was noticed.\n"))
    if not answer or "--blocked-by" not in answer:
        problems.append(f"file_issue: omitted --blocked-by was told {answer!r}")

    answer = _said(channel, fake, lambda: move.file_issue("Title", f"**Waits on.** #{'3'}.\n\nWhat was noticed.\n",
                                                          blocked_by=[3]))
    if not answer or "closed" not in answer:
        problems.append(f"file_issue: closed blocker in --blocked-by was told {answer!r}")

    fake = FakeBlockers({2: {"state": "open", "body": ""}})
    answer = _said(channel, fake, lambda: move.file_issue("Title", "**Waits on.** Nothing.\n\nWhat was noticed.\n",
                                                          blocked_by=[2]))
    if answer or fake.blockers.get(901) != [2]:
        problems.append(f"file_issue: a flag the line does not name said {answer!r} and left {fake.blockers}")
    if f"**Waits on.** #{'2'}" not in fake.bodies.get(901, ""):
        problems.append(f"file_issue: the line was left as {fake.bodies.get(901)!r}, not rendered from the flag")

    fake = FakeBlockers({2: {"state": "open", "body": ""}})
    answer = _said(channel, fake, lambda: move.file_issue(
        "Title", f"**Waits on.** Decision DR-{'041'}.\n\nWhat was noticed.\n", blocked_by=[2]))
    if f"DR-{'041'}" not in fake.bodies.get(901, "") or f"#{'2'}" not in fake.bodies.get(901, ""):
        problems.append(f"file_issue: rendering over a prose blocker left the line as {fake.bodies.get(901)!r}")

    return problems


@check("waits probes", pre=True)
def waits_probes() -> list[str]:
    """`move waits` and `file_issue` over the refusals they exist for, and the two records they keep (solorepo's DR-213)."""
    channel, _, programs = load_channel()
    move = programs["move"]
    open_issue = {"state": "open", "body": "**Waits on.** Nothing.\n\n**What was noticed.** Test details.\n"}
    problems: list[str] = []
    problems += _refusal_probes(channel, move, open_issue)
    problems += _mutation_probes(channel, move, open_issue)
    problems += _readback_probes(channel, move, open_issue)
    problems += _filing_probes(channel, move)
    return problems
