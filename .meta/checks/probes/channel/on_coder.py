"""`on coder`, the coder's door before its session, over a fake for each pass (solorepo's DR-264).

One module for one verb's probes, so a history log's Evidence names the file
holding them (solorepo's DR-209); the reviewer's verb is probed in `on.py`.
"""
import contextlib
import os
import pathlib
import tempfile
from collections.abc import Iterator, Sequence
from typing import Any, NamedTuple

from checks.collect import check
from checks.probes.harness import environment, load_channel, outcome, stood_in, unanswered

ISSUE = "7"
"""The Challenge the loop's branch names."""

PULL = "12"
"""The pull request a second pass answers."""

RUN = "https://github.com/o/r/actions/runs/99"
"""This run's page, as the environment names it."""


@check("coder door probes", pre=True)
def coder_door_probes() -> list[str]:
    """`on coder before` over each pass, with what the workflow hands it as flags.

    A take reads the Challenge's label for the harness, the label winning
    over a dispatch's input and the input over silence, asks the take door
    on the label's event, and takes the depth from the level the door read.
    The other passes read the pull request: a merged or closed one is `by`
    `merged` and nothing else is done; a rebase of a branch that is not the
    loop's shape is refused; otherwise the branch is checked out, the
    Challenge read off it, the harness taken from the input before the pull
    request's label, and the take door asked on the delivery's event, except
    for a dispatched answer, which is the solo's own word. Where a verdict's
    delivery finds the loop stood down, the sign is posted on the pull
    request, signed. The depth follows the pass; on approval the unresolved
    threads are counted and a failed checkout is tolerated. `after` is
    refused, being the workflow's own shell still.
    """
    channel, _, programs = load_channel()
    on = programs["on"]
    return (_take_cases(channel, on) + _pull_cases(channel, on)
            + _rebase_promote_cases(channel, on) + _after_cases(channel, on))


class _GitHub:
    """As much of GitHub as the coder's door asks about: labels, a pull request, and a sign."""

    def __init__(self, labels: Sequence[str] = (), state: str = "OPEN",
                 branch: str = f"claude/issue-{ISSUE}", base: str = "main") -> None:
        self.labels, self.state, self.branch, self.base = list(labels), state, branch, base
        self.posted: list[str] = []

    def __call__(self, *args: str, **kwargs: Any) -> Any:
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("issue", "view"):
            return {"labels": [{"name": name} for name in self.labels]}
        if args[:2] == ("pr", "view"):
            return {"state": self.state, "headRefName": self.branch, "baseRefName": self.base,
                    "labels": [{"name": name} for name in self.labels]}
        if args[:1] == ("api",) and args[1].endswith("/comments"):
            self.posted.append(args[-1].removeprefix("body="))
            return {"html_url": "https://github.com/o/r/pull/12#issuecomment-1"}
        raise unanswered(args, "the coder door fake")


class _Take:
    """A stand-in for the take door, answering one decision and recording what it was asked."""

    def __init__(self, by: str = "", why: str = "", level: str = "medium",
                 resume: str = "") -> None:
        self.decision = {"by": by, "why": why, "resume": resume, "level": level, "state": "",
                         "said": f"decided {by or 'the run continues'}"}
        self.asked: list[tuple[str, str]] = []

    def __call__(self, issue: str, door: str) -> dict[str, Any]:
        self.asked.append((issue, door))
        return dict(self.decision)


REFUSED = "::error::`{command}` failed: refused by the fake"
"""How the stand-in for `command` refuses a call it was told to."""


class _Commands:
    """A stand-in for `command`, recording each call and refusing the ones told to."""

    def __init__(self, refuse: str = "") -> None:
        self.calls: list[tuple[str, ...]] = []
        self.refuse = refuse

    def __call__(self, argv: Sequence[str], stdin: bytes | None = None) -> bytes:
        self.calls.append(tuple(argv))
        if self.refuse and self.refuse in argv:
            raise SystemExit(REFUSED.format(command=" ".join(argv)))
        return b""


@contextlib.contextmanager
def _workspace() -> Iterator[pathlib.Path]:
    """A temporary working directory with `GITHUB_OUTPUT` and `GITHUB_ENV` files, as a run has."""
    held = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory() as where:
        root = pathlib.Path(where)
        (root / "output").touch()
        (root / "env").touch()
        os.chdir(root)
        try:
            with environment(GITHUB_OUTPUT=str(root / "output"), GITHUB_ENV=str(root / "env"),
                             GITHUB_SERVER_URL="https://github.com", GITHUB_REPOSITORY="o/r",
                             GITHUB_RUN_ID="99", ACTOR_SESSION="gha-99", ACTOR_AGENT=None):
                yield root
        finally:
            os.chdir(held)


class _Fakes(NamedTuple):
    """What stands in for the door's reads and acts on one case."""

    gh: _GitHub
    take: _Take
    commands: _Commands
    threads: Sequence[dict[str, Any]] = ()


def _fakes(gh: _GitHub | None = None, take: _Take | None = None,
           commands: _Commands | None = None, threads: Sequence[dict[str, Any]] = ()) -> _Fakes:
    """The fakes for one case, each defaulting to one that answers the ordinary way."""
    return _Fakes(gh or _GitHub(), take or _Take(), commands or _Commands(), threads)


def _before(channel: Any, on: Any, fakes: _Fakes, delivery: tuple[str, str, str],
            number: str) -> tuple[Any, dict[str, str], str]:
    """`on coder before` against the fakes: how it ended, the outputs by key, the environment."""
    with _workspace() as root, stood_in(channel, gh=fakes.gh), \
            stood_in(on, command=fakes.commands), stood_in(on.check_pr.sweep, take=fakes.take), \
            stood_in(on.check_pr.github, threads=lambda number: list(fakes.threads)):
        ended = outcome(lambda: on.coder("before", number, on.Delivery(*delivery)))
        out = dict(line.split("=", 1) for line in (root / "output").read_text().splitlines()
                   if "=" in line)
        return ended, out, (root / "env").read_text()


def _take_cases(channel: Any, on: Any) -> list[str]:
    """The take pass: the harness, the take door on the label's event, and the depth."""
    problems = []
    take = _Take(level="medium")
    ended, out, env = _before(channel, on, _fakes(_GitHub(["challenge", "medium"]), take),
                              ("take", "issues", ""), ISSUE)
    expected = {"pass": "take", "harness": "claude", "branch_prefix": "claude",
                "agent": "anthropics/claude-code-action@v1", "by": "", "level": "medium",
                "model": "claude-opus-5", "effort": "high", "turns": "120", "minutes": "60"}
    if ended.code is not None or any(out.get(k) != v for k, v in expected.items()):
        problems.append(f"take: a medium Challenge decided {out!r} with exit {ended.code!r}, "
                        f"not {expected!r}")
    if take.asked != [(ISSUE, "issues")]:
        problems.append(f"take: the take door was asked {take.asked!r}, not on the label's event")
    if "ACTOR_AGENT=anthropics/claude-code-action@v1" not in env:
        problems.append(f"take: the harness was named in the environment as {env!r}")

    take = _Take(level="easy", resume="9")
    _, out, _ = _before(channel, on, _fakes(_GitHub(["challenge", "easy", "harness:gemini"]),
                                           take),
                        ("take", "workflow_dispatch", "claude"), ISSUE)
    if out.get("harness") != "gemini" or out.get("model") != "claude-sonnet-5" \
            or out.get("minutes") != "30" or out.get("resume") != "9" \
            or out.get("gemini_model") != on.GEMINI_MODEL:
        problems.append(f"take: a Gemini-labelled easy Challenge under a dispatch asking for "
                        f"Claude Code decided {out!r}, where the label wins, easy is the "
                        "smaller model, and the hand-back left is named")
    if take.asked != [(ISSUE, "issues")]:
        problems.append(f"take: a dispatched take asked the take door {take.asked!r}, where "
                        "the door is the label's whatever the event")
    _, out, _ = _before(channel, on, _fakes(_GitHub(["challenge", "easy"]), _Take(level="easy")),
                        ("take", "workflow_dispatch", "codex"), ISSUE)
    if out.get("harness") != "codex":
        problems.append(f"take: an unlabelled Challenge under a dispatch asking for Codex "
                        f"decided {out!r}")

    ended, out, _ = _before(channel, on, _fakes(_GitHub(["challenge", "hard"]),
                                               _Take(by="held", why="labelled hard", level="")),
                            ("take", "issues", ""), ISSUE)
    if ended.code is not None or out.get("by") != "held" or out.get("why") != "labelled hard":
        problems.append(f"take: a held Challenge decided {out!r} with exit {ended.code!r}")
    return problems


def _pull_cases(channel: Any, on: Any) -> list[str]:
    """The answering pass: found, checked out, read for the Challenge, signed if owed, or done."""
    problems = []
    take, commands = _Take(), _Commands()
    ended, out, _ = _before(channel, on, _fakes(_GitHub(base="claude/issue-3"), take, commands),
                            ("answer", "pull_request_review", ""), PULL)
    expected = {"pass": "answer", "number": PULL, "branch": f"claude/issue-{ISSUE}",
                "base": "claude/issue-3", "issue": ISSUE, "by": "", "harness": "claude",
                "model": "claude-opus-5", "minutes": "60", "gemini_model": on.GEMINI_MODEL}
    if ended.code is not None or any(out.get(k) != v for k, v in expected.items()):
        problems.append(f"answer: a request for changes decided {out!r} with exit "
                        f"{ended.code!r}, not {expected!r}")
    if take.asked != [(ISSUE, "pull_request_review")]:
        problems.append(f"answer: the take door was asked {take.asked!r}, not on the verdict's "
                        "event")
    if ("git", "checkout", "--quiet", f"claude/issue-{ISSUE}") not in commands.calls:
        problems.append(f"answer: the branch was not checked out: {commands.calls!r}")

    fake = _GitHub()
    held = _Take(by="held", why="labelled hard", level="")
    ended, out, _ = _before(channel, on, _fakes(fake, held),
                            ("answer", "pull_request_review", ""), PULL)
    if ended.code is not None or out.get("by") != "held" or len(fake.posted) != 1 \
            or f"No run takes this up: #{ISSUE} is labelled hard" not in fake.posted[0] \
            or RUN not in fake.posted[0] or "Actor: gha-99" not in fake.posted[0] \
            or "Agent: anthropics/claude-code-action@v1" not in fake.posted[0]:
        problems.append(f"answer: a verdict with no Job decided {out!r} and posted "
                        f"{fake.posted!r}, where the sign is left on the pull request, signed "
                        "as the harness the door has just chosen")

    ended, out, _ = _before(channel, on, _fakes(commands=_Commands(refuse="checkout")),
                            ("answer", "pull_request_review", ""), PULL)
    if ended.code is None or "checkout" not in str(ended.code):
        problems.append(f"answer: a checkout that failed ended {ended.code!r}, where the "
                        "session must not run against whatever tree the runner holds")

    take, fake = _Take(), _GitHub()
    ended, out, _ = _before(channel, on, _fakes(fake, take), ("answer", "workflow_dispatch", ""),
                            PULL)
    if ended.code is not None or out.get("by") != "" or take.asked or fake.posted:
        problems.append(f"answer: a dispatched review pass decided {out!r} and asked "
                        f"{take.asked!r}, where the solo's own word is not read against")

    for label, asked, harness in (("harness:gemini", "", "gemini"), ("harness:gemini", "codex",
                                                                      "codex")):
        _, out, _ = _before(channel, on, _fakes(_GitHub([label])),
                            ("answer", "workflow_dispatch", asked), PULL)
        if out.get("harness") != harness:
            problems.append(f"answer: a pull request labelled {label} under a dispatch asking "
                            f"for {asked!r} decided {out!r}, not {harness}")

    for state in ("MERGED", "CLOSED"):
        take, commands = _Take(), _Commands()
        ended, out, _ = _before(channel, on, _fakes(_GitHub(state=state), take, commands),
                                ("answer", "pull_request_review", ""), PULL)
        if ended.code is not None or out.get("by") != "merged" or out.get("why") != "merged" \
                or take.asked or commands.calls or "harness" in out:
            problems.append(f"answer: a {state} pull request decided {out!r} with exit "
                            f"{ended.code!r}, asked {take.asked!r} and ran {commands.calls!r}, "
                            "where nothing is done")

    return problems


def _rebase_promote_cases(channel: Any, on: Any) -> list[str]:
    """The rebase and promotion passes: the shape refused, the depth, the count, the checkout."""
    problems = []
    ended, out, _ = _before(channel, on, _fakes(_GitHub(branch="feature/x")),
                            ("rebase", "workflow_dispatch", "claude"), PULL)
    if ended.code is None or "names no Challenge" not in str(ended.code):
        problems.append(f"rebase: a branch that is not the loop's shape ended {ended.code!r}")
    take = _Take()
    ended, out, _ = _before(channel, on, _fakes(take=take),
                            ("rebase", "workflow_dispatch", "claude"), PULL)
    if ended.code is not None or out.get("model") != "claude-opus-5" or out.get("minutes") != "30" \
            or out.get("turns") != "60" or take.asked != [(ISSUE, "workflow_dispatch")]:
        problems.append(f"rebase: decided {out!r} and asked {take.asked!r}, where the larger "
                        "model takes half the budget and the take door is asked")

    threads = [{"isResolved": False}, {"isResolved": True}, {"isResolved": False}]
    refusing = _Commands(refuse="checkout")
    ended, out, _ = _before(channel, on, _fakes(commands=refusing, threads=threads),
                            ("promote", "pull_request_review", ""), PULL)
    if ended.code is not None or out.get("count") != "2" or out.get("model") != "claude-sonnet-5" \
            or out.get("turns") != "30" or out.get("minutes") != "15" \
            or ("git", "checkout", "--quiet", f"claude/issue-{ISSUE}") not in refusing.calls:
        problems.append(f"promote: decided {out!r} with exit {ended.code!r} after "
                        f"{refusing.calls!r}, where two threads are held, the smaller model "
                        "takes a quarter of the budget, and a checkout attempted and failed "
                        "is tolerated")
    return problems


def _after_cases(channel: Any, on: Any) -> list[str]:
    """`after`, refused while the second phase is the workflow's own shell."""
    with _workspace(), stood_in(channel, gh=_GitHub()):
        ended = outcome(lambda: on.coder("after", PULL, on.Delivery("answer", "workflow_dispatch",
                                                                   "")))
    if ended.code is None or "still `coder.yml`'s own shell" not in str(ended.code):
        return [f"after: was answered with exit {ended.code!r}, not refused as the shell's still"]
    return []
