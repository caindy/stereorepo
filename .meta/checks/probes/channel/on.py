"""`on reviewer`, the reading door before and after its session, over a fake (solorepo's DR-264).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import contextlib
import os
import pathlib
import tempfile
from collections.abc import Iterator
from typing import Any

from checks.collect import check
from checks.probes.harness import environment, load_channel, outcome, stood_in, unanswered

OPEN_ISSUES = [{"number": 3, "title": "another Challenge", "labels": [{"name": "challenge"}]}]
"""What `issue list` answers: one other open Issue."""

OPEN_PULLS = [{"number": 4, "title": "a pull request", "headRefName": "claude/issue-3"}]
"""What `pr list` answers: one open pull request."""


@check("reading door probes", pre=True)
def reading_door_probes() -> list[str]:
    """`on reviewer before` and `after` over a Challenge in each state the door decides on.

    Before: an unread Challenge is read, Claude Code by default and Gemini by
    its label, the harness named in `GITHUB_OUTPUT` and under both variables
    in `GITHUB_ENV`, and the Challenge and what is open written under
    `.review/` with the title, the body, and every open Issue and pull
    request; a Challenge at a level, or closed, is a stale delivery, `read`
    false, nothing else written, and nothing under `.review/`. After: a level
    landed is read as read, and none as not, which ends the step with the
    error the run log shows, whether the Challenge is still unread, was
    closed meanwhile, or lost `challenge` meanwhile. A number naming a pull
    request is refused on both phases, since that door is not this seam's.
    """
    channel, _, programs = load_channel()
    on = programs["on"]
    return _before_cases(channel, on) + _after_cases(channel, on)


class _GitHub:
    """As much of GitHub as the reading door asks about: a number's kind, an Issue, what is open."""

    def __init__(self, issue: dict[str, Any], kind: str = "issue") -> None:
        self.issue, self.kind = issue, kind

    def __call__(self, *args: str, **kwargs: Any) -> Any:
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:1] == ("api",) and "/issues/" in args[1]:
            return {"pull_request": {"url": "x"}} if self.kind == "pull request" else {}
        if args[:2] == ("issue", "view"):
            return dict(self.issue)
        if args[:2] == ("issue", "list"):
            return list(OPEN_ISSUES)
        if args[:2] == ("pr", "list"):
            return list(OPEN_PULLS)
        raise unanswered(args, "the reading door fake")


def _issue(labels: list[str], state: str = "OPEN") -> dict[str, Any]:
    """A Challenge as `CHALLENGE_FIELDS` reads it."""
    return {"number": 7, "title": "A Challenge to read", "url": "https://github.com/o/r/issues/7",
            "labels": [{"name": name} for name in labels], "body": "**Waits on.** Nothing.",
            "createdAt": "2026-09-22T00:00:00Z", "author": {"login": "solo"}, "state": state,
            "assignees": []}


@contextlib.contextmanager
def _workspace() -> Iterator[tuple[pathlib.Path, pathlib.Path, pathlib.Path]]:
    """A temporary working directory with `GITHUB_OUTPUT` and `GITHUB_ENV` files, as a run has."""
    held = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory() as where:
        root = pathlib.Path(where)
        output, env = root / "output", root / "env"
        output.touch()
        env.touch()
        os.chdir(root)
        try:
            with environment(GITHUB_OUTPUT=str(output), GITHUB_ENV=str(env)):
                yield root, output, env
        finally:
            os.chdir(held)


def _before(channel: Any, on: Any,
            fake: _GitHub) -> tuple[Any, str, str, pathlib.Path | tuple[str, str]]:
    """`on reviewer before 7` against `fake`: how it ended, the two files, and the two pages."""
    with _workspace() as (root, output, env), stood_in(channel, gh=fake):
        ended = outcome(lambda: on.reviewer("before", "7"))
        challenge = root / ".review" / "challenge.md"
        opened = root / ".review" / "open.md"
        pages = (challenge.read_text() if challenge.exists() else "",
                 opened.read_text() if opened.exists() else "")
        return ended, output.read_text(), env.read_text(), root if pages == ("", "") else pages


def _before_cases(channel: Any, on: Any) -> list[str]:
    """Before the session: unread, labelled for Gemini, at a level, closed, and a pull request."""
    problems = []
    ended, out, env, pages = _before(channel, on, _GitHub(_issue(["challenge"])))
    if ended.code is not None or "read=true" not in out or "harness=claude" not in out \
            or "agent=anthropics/claude-code-action@v1" not in out:
        problems.append(f"before: an unread Challenge decided {out!r} with exit {ended.code!r}, "
                        "not read by Claude Code")
    if "AI_AGENT=anthropics/claude-code-action@v1" not in env \
            or "ACTOR_AGENT=anthropics/claude-code-action@v1" not in env:
        problems.append(f"before: the harness was named in the environment as {env!r}, not under "
                        "ACTOR_AGENT, which the channel reads, beside the AI_AGENT the harness "
                        "overwrites")
    if isinstance(pages, pathlib.Path):
        problems.append("before: an unread Challenge left nothing under .review/")
    else:
        challenge, opened = pages
        if "A Challenge to read" not in challenge or "**Waits on.** Nothing." not in challenge:
            problems.append(f"before: the Challenge page {challenge!r} carries neither the title "
                            "nor the body")
        if "#3" not in opened or "#4" not in opened or "claude/issue-3" not in opened:
            problems.append(f"before: the open page {opened!r} does not list what is open")

    ended, out, _, _ = _before(channel, on, _GitHub(_issue(["challenge", "harness:gemini"])))
    if "harness=gemini" not in out or "agent=antigravity-cli" not in out:
        problems.append(f"before: a Challenge labelled for Gemini decided {out!r}")

    for name, fake in (("at a level", _GitHub(_issue(["challenge", "medium"]))),
                       ("closed", _GitHub(_issue(["challenge"], state="CLOSED")))):
        ended, out, env, pages = _before(channel, on, fake)
        if ended.code is not None or out.strip() != "read=false" or env.strip():
            problems.append(f"before: a Challenge {name} decided {out!r} and {env!r} with exit "
                            f"{ended.code!r}, not `read=false` alone")
        if not isinstance(pages, pathlib.Path):
            problems.append(f"before: a Challenge {name} still had its pages written")

    ended, out, _, _ = _before(channel, on, _GitHub(_issue(["challenge"]), kind="pull request"))
    if ended.code is None or "pull request door" not in str(ended.code) or out.strip():
        problems.append(f"before: a pull request was answered {out!r} with exit {ended.code!r}, "
                        "not refused as the other door's")
    return problems


def _after_cases(channel: Any, on: Any) -> list[str]:
    """The reading door after the session: a level landed, none landed, and a pull request."""
    problems = []
    with _workspace(), stood_in(channel, gh=_GitHub(_issue(["challenge", "medium"]))):
        ended = outcome(lambda: on.reviewer("after", "7"))
    if ended.code is not None or "landed at medium" not in ended.out:
        problems.append(f"after: a level landed ended with {ended.code!r} and said {ended.out!r}")
    for name, fake in (("no level landed", _GitHub(_issue(["challenge"]))),
                       ("the Challenge closed meanwhile",
                        _GitHub(_issue(["challenge"], state="CLOSED"))),
                       ("challenge taken off meanwhile", _GitHub(_issue([])))):
        with _workspace(), stood_in(channel, gh=fake):
            ended = outcome(lambda: on.reviewer("after", "7"))
        red = ended.code is not None and "::error::" in ended.out
        if not red or "carries no level" not in ended.out:
            problems.append(f"after: {name} ended with {ended.code!r} and said {ended.out!r}, "
                            "where the step must end red and say why")
        if "landed at" in ended.out:
            problems.append(f"after: {name} was reported as read: {ended.out!r}")
    with _workspace(), stood_in(channel, gh=_GitHub(_issue(["challenge"]), kind="pull request")):
        ended = outcome(lambda: on.reviewer("after", "7"))
    if ended.code is None or "pull request door" not in str(ended.code):
        problems.append(f"after: a pull request was answered with exit {ended.code!r}, not "
                        "refused as the other door's")
    return problems
