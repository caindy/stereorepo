"""`on coder`, the coder's door before and after its session, over a fake for each pass.

One module for one verb's probes, so a history log's Evidence names the file
holding them (solorepo's DR-209); the reviewer's verb is probed in `on.py`
(solorepo's DR-264).
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

CODER = "o-r-coder"
"""The login the door speaks as, from the `o/r` the fake answers `repo view` with."""

RUN = "https://github.com/o/r/actions/runs/99"
"""This run's page, as the environment names it."""


@check("coder door probes", pre=True)
def coder_door_probes() -> list[str]:
    """`on coder` at each phase of each pass, with what the workflow hands the phase as flags.

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
    threads are counted and a failed checkout is tolerated. Before the take
    pass's second harness step the Challenge's loop branch is read again: a
    pull request open on it is emitted as `resume` for that step's prompt and
    said, no pull request is an empty `resume` and its own line, the listing
    is asked with an empty fallback so a refused read is no pull request
    rather than a red job, and any other pass is refused. After the
    session: a take that failed or was cancelled is handed back, review
    requested where the pull request it left is green and clean and the
    Challenge given to the solo otherwise, with why, every read that failed
    among the whys and nothing owed where the run turns out to have
    finished; a rebase that succeeded redelivers the review pass and a
    refusal is said; and a pass neither harness finished ends the run red,
    a cancelled one not being a failed one.

    A take pass cut by its turn cap is the last of these and reports none of
    them, its step ending `success`: the transcript is read for the cap and
    the turns, every shape that cannot say the cap was hit reading as a pass
    that was not cut, and a cap on a green pull request hands over an account
    naming the cap rather than the step's conclusion. The second cap on the
    same pull request goes to the solo instead (solorepo's DR-277).
    """
    channel, _, programs = load_channel()
    on = programs["on"]
    return (_take_cases(channel, on) + _between_cases(on) + _pull_cases(channel, on)
            + _rebase_promote_cases(channel, on) + _after_cases(channel, on)
            + _cap_cases(channel, on))


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
        ended = outcome(lambda: on.coder("before", number, on.Delivery(*delivery),
                                         on.Ended("skipped", "skipped", None, "")))
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
                        ("take", "workflow_dispatch", "gemini"), ISSUE)
    if out.get("harness") != "gemini":
        problems.append(f"take: an unlabelled Challenge under a dispatch asking for "
                        f"Antigravity CLI decided {out!r}")

    ended, out, _ = _before(channel, on, _fakes(_GitHub(["challenge", "hard"]),
                                               _Take(by="held", why="labelled hard", level="")),
                            ("take", "issues", ""), ISSUE)
    if ended.code is not None or out.get("by") != "held" or out.get("why") != "labelled hard":
        problems.append(f"take: a held Challenge decided {out!r} with exit {ended.code!r}")
    return problems


class _Branch:
    """A stand-in for `loop_pull`, answering what is open on the Challenge's branch.

    Every call is recorded whole, the `default` included, since the door asks
    with an empty listing so that a read GitHub refuses is no pull request
    rather than a red job.
    """

    def __init__(self, pull: dict[str, Any] | None) -> None:
        self.pull = pull
        self.asked: list[tuple[str, str, Any]] = []

    def __call__(self, issue: str | int, fields: str, default: Any = None) -> Any:
        self.asked.append((str(issue), fields, default))
        return dict(self.pull) if self.pull else None


def _between(on: Any, branch: _Branch, task: str = "take") -> tuple[Any, dict[str, str]]:
    """`on coder between` against the stand-in: how it ended, and the outputs by key."""
    with _workspace() as root, stood_in(on.check_pr.sweep, loop_pull=branch):
        ended = outcome(lambda: on.coder("between", ISSUE, on.Delivery(task, "issues", ""),
                                         on.Ended("failure", "skipped", None, "claude")))
        out = dict(line.split("=", 1) for line in (root / "output").read_text().splitlines()
                   if "=" in line)
    return ended, out


def _between_cases(on: Any) -> list[str]:
    """Before the take pass's second harness step: the branch read again, any other pass refused."""
    problems = []
    branch = _Branch({"number": int(PULL)})
    ended, out = _between(on, branch)
    if ended.code is not None or out.get("resume") != PULL \
            or f"pull request #{PULL} is already open" not in ended.out:
        problems.append(f"between: a branch holding #{PULL} decided {out!r} with exit "
                        f"{ended.code!r} saying {ended.out!r}, where the prompt below takes "
                        "that number as its resume clause")
    if branch.asked != [(ISSUE, "number", [])]:
        problems.append(f"between: the branch was read as {branch.asked!r}, where the Challenge "
                        "is asked for its pull request's number under an empty listing, so that "
                        "a read GitHub refuses is no pull request and not a red job")
    ended, out = _between(on, _Branch(None))
    if ended.code is not None or out.get("resume") != "" \
            or "no pull request is open" not in ended.out:
        problems.append(f"between: a branch holding nothing decided {out!r} with exit "
                        f"{ended.code!r} saying {ended.out!r}, where the step below opens the "
                        "pull request itself")
    for task in ("rebase", "answer", "promote"):
        ended, _ = _between(on, _Branch({"number": int(PULL)}), task)
        if ended.code is None or "only the take pass" not in str(ended.code):
            problems.append(f"between: the {task} pass ended {ended.code!r}, where a pass whose "
                            "prompt carries no resume clause is refused")
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

    for label, asked, harness in (("harness:gemini", "", "gemini"),
                                  ("harness:gemini", "claude", "claude")):
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


NOTHING_TO_REDELIVER = "say: nothing to redeliver"
"""How the stand-in for `dispatch_pass` refuses."""

READ_FAILED = "gh: `{command}` failed"
"""How a stand-in refuses a read that was given no fallback."""

SIGNED = ("Actor: gha-99", "Agent: anthropics/claude-code-action@v1")
"""The Trailer every account the hand-back posts must carry."""


class _Loop:
    """A stand-in for the channel's verbs the hand-back acts through, recording each act."""

    def __init__(self, refuse_dispatch: bool = False) -> None:
        self.stopped: list[tuple[str, str]] = []
        self.requested: list[tuple[str, str]] = []
        self.dispatched: list[tuple[str, str | None]] = []
        self.refuse_dispatch = refuse_dispatch

    def stop(self, issue: str, body: str) -> None:
        self.stopped.append((str(issue), body))

    def request_review(self, pr: str, to: str) -> None:
        self.requested.append((str(pr), to))

    def dispatch_pass(self, pr: str, task: str | None) -> None:
        self.dispatched.append((str(pr), task))
        if self.refuse_dispatch:
            raise SystemExit(NOTHING_TO_REDELIVER)


class _Left:
    """A stand-in for `hand_back`, answering what the run left or refusing to read it."""

    def __init__(self, left: dict[str, Any] | None) -> None:
        self.left = left

    def __call__(self, issue: str) -> dict[str, Any]:
        if self.left is None:
            raise SystemExit(READ_FAILED.format(command="hand-back"))
        return dict(self.left)


class _After(_GitHub):
    """The coder door fake after a session: an Issue's state and level, and the merged listing."""

    def __init__(self, state: str = "OPEN", labels: Sequence[str] = ("challenge", "medium"),
                 merged: list[dict[str, Any]] | None = None, unreadable: str = "",
                 comments: Sequence[str | tuple[str, str]] = ()) -> None:
        super().__init__(labels=labels, state=state)
        self.merged, self.unreadable, self.comments = merged, unreadable, list(comments)

    def __call__(self, *args: str, **kwargs: Any) -> Any:
        if args[:2] == ("issue", "view"):
            if self.unreadable == "issue":
                return self.refuse(args, kwargs)
            return {"state": self.state, "labels": [{"name": name} for name in self.labels]}
        if args[:2] == ("pr", "list"):
            if self.unreadable == "merged":
                return self.refuse(args, kwargs)
            return list(self.merged or [])
        if args[:2] == ("pr", "view") and "comments" in args:
            if self.unreadable == "comments":
                return self.refuse(args, kwargs)
            return {"comments": [self.commented(comment) for comment in self.comments]}
        return super().__call__(*args, **kwargs)

    @staticmethod
    def commented(comment: str | tuple[str, str]) -> dict[str, Any]:
        """One conversation comment as GitHub lists it: a bare body is the coder's own."""
        login, body = comment if isinstance(comment, tuple) else (CODER, comment)
        return {"body": body, "author": {"login": login}}

    @staticmethod
    def refuse(args: tuple[str, ...], kwargs: dict[str, Any]) -> Any:
        """Refuses as `channel.gh` does: the fallback where one was given, else an exit."""
        if "default" in kwargs:
            return kwargs["default"]
        raise SystemExit(READ_FAILED.format(command=" ".join(args)))


class _Session(NamedTuple):
    """One `after` case: what the workflow reports, and what stands in for the reads and acts."""

    delivery: tuple[str, str, str]
    ended: tuple[str | None, str | None, int | None, str] \
        | tuple[str | None, str | None, int | None, str, str]
    fake: _GitHub
    left: _Left
    loop: _Loop


def _session(delivery: tuple[str, str, str],
             ended: tuple[str | None, str | None, int | None, str]
             | tuple[str | None, str | None, int | None, str, str],
             fake: _GitHub | None = None, left: _Left | None = None,
             loop: _Loop | None = None) -> _Session:
    """An `after` case, each stand-in defaulting to one that answers the ordinary way."""
    return _Session(delivery, ended, fake or _After(), left or _Left(None), loop or _Loop())


def _after(channel: Any, on: Any, case: _Session) -> tuple[Any, _Loop]:
    """`on coder after` against the case's fakes: how it ended and what the loop's verbs saw.

    `ACTOR_AGENT` is set as the run has it by then, `before` having written
    it to `GITHUB_ENV` for every step after its own.
    """
    delivery, ended, fake, left, loop = case
    move = channel.sibling("move")
    number = ISSUE if delivery[0] == "take" else PULL
    with _workspace(), environment(ACTOR_AGENT="anthropics/claude-code-action@v1"), \
            stood_in(channel, gh=fake), stood_in(on.check_pr.sweep, hand_back=left), \
            stood_in(move, stop=loop.stop, request_review=loop.request_review,
                     dispatch_pass=loop.dispatch_pass):
        ended_as = outcome(lambda: on.coder("after", number, on.Delivery(*delivery),
                                            on.Ended(*ended)))
    return ended_as, loop


def _after_cases(channel: Any, on: Any) -> list[str]:
    """`after` on each pass: the take handed back, the rebase redelivered, the rest verified."""
    problems = _hand_back_cases(channel, on)
    take = ("take", "issues", "")
    ended, loop = _after(channel, on, _session(take, ("success", "skipped", None, "claude")))
    if ended.code is not None or loop.stopped or loop.requested or "nothing to hand back" \
            not in ended.out:
        problems.append(f"after: a take that succeeded ended {ended.code!r} saying {ended.out!r}")

    rebase = ("rebase", "workflow_dispatch", "claude")
    ended, loop = _after(channel, on, _session(rebase, ("failure", "success", None, "")))
    if ended.code is not None or loop.dispatched != [(PULL, "review")]:
        problems.append(f"after: a rebase the fallback finished ended {ended.code!r} and "
                        f"dispatched {loop.dispatched!r}, where the review pass is redelivered")
    ended, loop = _after(channel, on, _session(rebase, ("success", "skipped", None, ""),
                                          loop=_Loop(refuse_dispatch=True)))
    if ended.code is not None or "nothing to redeliver" not in ended.out:
        problems.append(f"after: a redelivery refused ended {ended.code!r} saying "
                        f"{ended.out!r}, where the refusal is said and not a failure")
    for task, delivery in (("rebase", rebase), ("answer", ("answer", "pull_request_review", "")),
                           ("promote", ("promote", "pull_request_review", ""))):
        ended, loop = _after(channel, on, _session(delivery, ("failure", "failure", 2, "")))
        if ended.code is None or f"Neither Claude nor Gemini {task} pass succeeded" \
                not in str(ended.code):
            problems.append(f"after: a {task} pass neither harness finished ended "
                            f"{ended.code!r}")
        ended, loop = _after(channel, on, _session(delivery, ("cancelled", "skipped", 2, "")))
        if ended.code is not None or loop.dispatched or loop.stopped or loop.requested:
            problems.append(f"after: a {task} pass cancelled ended {ended.code!r} and acted "
                            f"{loop.dispatched!r} {loop.stopped!r} {loop.requested!r}, where a "
                            "cancelled pass is not a failed one and nothing is owed")
    for name, ended_as in (("no outcomes", (None, None, 2, "")),
                           ("no Claude Code outcome", (None, "skipped", 2, ""))):
        ended, loop = _after(channel, on, _session(take, ended_as))
        if ended.code is None or "did not arrive" not in str(ended.code) or loop.stopped:
            problems.append(f"after: {name} ended {ended.code!r}, where an outcome that did not "
                            "arrive is a red run")
    empty = outcome(lambda: on.build_parser().parse_args(
        ["coder", "after", ISSUE, "--pass", "take", "--event", "issues", "--claude", "",
         "--gemini", "skipped"]))
    if empty.code is None or "did not arrive" not in empty.err:
        problems.append(f"after: an empty --claude was parsed as {empty.code!r} {empty.err!r}, "
                        "where an empty outcome is refused")
    ended, loop = _after(channel, on, _session(("promote", "pull_request_review", ""),
                                          ("skipped", "skipped", 0, "")))
    if ended.code is not None or "no threads were held" not in ended.out:
        problems.append(f"after: a promotion with no threads ended {ended.code!r} saying "
                        f"{ended.out!r}")
    return problems


def _hand_back_cases(channel: Any, on: Any) -> list[str]:
    """A take that did not finish: every way the hand-back ends, in the order it reads."""
    problems = []
    take = ("take", "issues", "")
    green = {"number": 12, "branch": f"claude/issue-{ISSUE}", "handed": False, "green": True,
             "conflicting": False, "base": "main"}
    fake = _After()
    ended, loop = _after(channel, on, _session(take, ("failure", "skipped", None, "claude"), fake,
                                          _Left(green)))
    if ended.code is not None or loop.stopped or loop.requested != [(PULL, "reviewer")] \
            or len(fake.posted) != 1 or "where a run stopped" not in fake.posted[0] \
            or ".\n\nEvery check on this head is green" not in fake.posted[0] \
            or any(line not in fake.posted[0] for line in SIGNED):
        problems.append(f"hand-back: a green pull request ended {ended.code!r}, stopped "
                        f"{loop.stopped!r}, requested {loop.requested!r}, posted "
                        f"{fake.posted!r}, where review is requested after the signed account "
                        "is posted")
    ended, loop = _after(channel, on, _session(take, ("failure", "cancelled", None, "claude"),
                                          left=_Left({**green, "green": False})))
    account = loop.stopped[0][1] if loop.stopped else ""
    if ended.code is not None or loop.requested or len(loop.stopped) != 1 \
            or "ended cancelled" not in account or "red gate" not in account \
            or "again.\n\nNot requested of the reviewer:" not in account \
            or any(line not in account for line in SIGNED):
        problems.append(f"hand-back: a red pull request ended {ended.code!r} with "
                        f"{loop.stopped!r}, where the Challenge goes to the solo in a signed "
                        "account of two paragraphs naming the fallback's outcome")
    cases = (("what the run left unreadable", _Left(None), _After(), "could not read what"),
             ("no pull request", _Left({**green, "number": None, "branch": None}), _After(),
              "opened no pull request"),
             ("a conflicting branch", _Left({**green, "conflicting": True}), _After(),
              "conflicts with its base"),
             ("the Issue unreadable", _Left(green), _After(unreadable="issue"),
              "could not be read"),
             ("the merged listing unreadable", _Left(green), _After(unreadable="merged"),
              "has merged could not be read"))
    for name, left, fake, why in cases:
        ended, loop = _after(channel, on, _session(take, ("failure", "skipped", None, "gemini"),
                                                   fake, left))
        account = loop.stopped[0][1] if loop.stopped else ""
        if ended.code is not None or len(loop.stopped) != 1 or why not in account \
                or loop.requested or any(line not in account for line in SIGNED) \
                or f"/issue-{ISSUE}`" not in account:
            problems.append(f"hand-back: {name} ended {ended.code!r} with {loop.stopped!r}, "
                            f"where the Challenge goes to the solo in a signed account saying "
                            f"{why!r} and naming the branch")
        if (left.left is None or left.left.get("branch") is None) \
                and f"`gemini/issue-{ISSUE}`" not in account:
            problems.append(f"hand-back: {name} named the branch as {account!r}, where the "
                            "prefix the door was handed names it when nothing was left")
    quiet = (("handed already", _Left({**green, "handed": True}), _After()),
             ("the Issue closed", _Left(green), _After(state="CLOSED")),
             ("the Issue at human", _Left(green), _After(labels=["challenge", "human"])),
             ("the branch merged", _Left(green), _After(merged=[{"number": 12}])))
    for name, left, fake in quiet:
        ended, loop = _after(channel, on, _session(take, ("failure", "skipped", None, "claude"),
                                                   fake, left))
        if ended.code is not None or loop.stopped or loop.requested:
            problems.append(f"hand-back: {name} ended {ended.code!r} with {loop.stopped!r} and "
                            f"{loop.requested!r}, where the run finished and nothing is owed")
    return problems


CAPPED_TRANSCRIPT = ('[{"type": "assistant"}, {"type": "result", "subtype": "error_max_turns", '
                     '"num_turns": 120, "is_error": true}]')
"""A transcript of a session the turn cap cut, as `claude-code-action` publishes it."""

FINISHED_TRANSCRIPT = ('[{"type": "result", "subtype": "success", "num_turns": 40, '
                       '"is_error": false}]')
"""A transcript of a session that finished within its cap."""

INTERLEAVED_TRANSCRIPT = ('Running the session...\n'
                          '{"type": "assistant"}\n'
                          '{"type": "result", "subtype": "error_max_turns", "num_turns": 120}\n')
"""The same capped session as JSON Lines with a runner's status line through it: the shape
whole-document decoding has already lost on here (`agents.history.md`)."""


def _transcript(root: pathlib.Path, name: str, content: str) -> str:
    """Writes a transcript outside the case's workspace and answers where it is."""
    where = root / name
    where.write_text(content, encoding="utf-8")
    return str(where)


def _cut_by_cap_cases(on: Any, root: pathlib.Path) -> list[str]:
    """`cut_by_cap` over every shape the transcript arrives in: only the cap answers a number."""
    problems = []
    cases = ((CAPPED_TRANSCRIPT, 120, "a capped session"),
             (FINISHED_TRANSCRIPT, None, "a session that finished"),
             ('{"type": "result", "subtype": "error_max_turns"}', 0,
              "a capped session the transcript counted no turns for"),
             (INTERLEAVED_TRANSCRIPT, 120, "a capped session logged over as JSON Lines"),
             ('{"subtype": "error_max_turns", "num_turns": "many"}', 0,
              "a capped session whose turn count is not a number"),
             ("not json at all", None, "a transcript that is not JSON"),
             ("[]", None, "a transcript with no result entry"))
    for content, want, name in cases:
        got = on.cut_by_cap(_transcript(root, "one.json", content))
        if got != want:
            problems.append(f"cut_by_cap: {name} answered {got!r}, not {want!r}")
    for where, name in (("", "no path at all"),
                        (str(root / "absent.json"), "a path nothing wrote")):
        got = on.cut_by_cap(where)
        if got is not None:
            problems.append(f"cut_by_cap: {name} answered {got!r}, where a reading that "
                            "cannot say the cap was hit is not one that says it was")
    return problems


def _cap_cases(channel: Any, on: Any) -> list[str]:
    """A take pass the turn cap cut: the transcript read, the account, and the second cap."""
    take = ("take", "issues", "")
    green = {"number": 12, "branch": f"claude/issue-{ISSUE}", "handed": False, "green": True,
             "conflicting": False, "base": "main"}
    with tempfile.TemporaryDirectory() as where:
        root = pathlib.Path(where)
        problems = _cut_by_cap_cases(on, root)
        capped = _transcript(root, "capped.json", CAPPED_TRANSCRIPT)
        whole = _transcript(root, "whole.json", FINISHED_TRANSCRIPT)

        fake = _After()
        ended, loop = _after(channel, on, _session(
            take, ("success", "skipped", None, "claude", capped), fake, _Left(green)))
        posted = fake.posted[0] if fake.posted else ""
        if ended.code is not None or loop.stopped or loop.requested != [(PULL, "reviewer")] \
                or "was cut by its turn cap, 120 turns in" not in posted \
                or "ended success" in posted or "Every check on this head is green" not in posted:
            problems.append(f"cap: a capped take pass on a green pull request ended "
                            f"{ended.code!r}, stopped {loop.stopped!r}, requested "
                            f"{loop.requested!r}, posted {fake.posted!r}, where the account "
                            "names the cap and review is requested")

        ended, loop = _after(channel, on, _session(
            take, ("success", "skipped", None, "claude", whole), _After(), _Left(green)))
        if ended.code is not None or loop.stopped or loop.requested \
                or "nothing to hand back" not in ended.out:
            problems.append(f"cap: a take pass that finished within its cap ended "
                            f"{ended.code!r} saying {ended.out!r} and acted {loop.requested!r}")

        fake = _After(comments=["This run was cut by its turn cap, 120 turns in."])
        ended, loop = _after(channel, on, _session(
            take, ("success", "skipped", None, "claude", capped), fake, _Left(green)))
        account = loop.stopped[0][1] if loop.stopped else ""
        if ended.code is not None or loop.requested or len(loop.stopped) != 1 \
                or "does not fit twice" not in account \
                or "was cut by its turn cap" not in account:
            problems.append(f"cap: a second capped take pass ended {ended.code!r}, stopped "
                            f"{loop.stopped!r} and requested {loop.requested!r}, where a "
                            "Challenge that does not fit twice goes to the solo")

        quoted = ("o-r-reviewer", "The account says the run was cut by its turn cap, so I am "
                                 "reading this as a draft.")
        for fake, name in ((_After(comments=[quoted]), "a comment quoting the cap account"),
                           (_After(unreadable="comments"), "a comment listing GitHub refuses")):
            ended, loop = _after(channel, on, _session(
                take, ("success", "skipped", None, "claude", capped), fake, _Left(green)))
            if ended.code is not None or loop.stopped \
                    or loop.requested != [(PULL, "reviewer")]:
                problems.append(f"cap: {name} ended {ended.code!r}, stopped {loop.stopped!r} "
                                f"and requested {loop.requested!r}, where only the door's own "
                                "account is a cap it posted and a read it cannot make is not one")

        ended, loop = _after(channel, on, _session(
            take, ("failure", "skipped", None, "claude", capped), _After(),
            _Left({**green, "green": False})))
        account = loop.stopped[0][1] if loop.stopped else ""
        if ended.code is not None or len(loop.stopped) != 1 or "ended failure" not in account:
            problems.append(f"cap: a take pass whose step failed ended {ended.code!r} with "
                            f"{loop.stopped!r}, where the step's own conclusion is the account "
                            "and the transcript is not read")
    return problems
