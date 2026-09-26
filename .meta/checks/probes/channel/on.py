"""`on reviewer`, the reading and review doors, before and after a session (solorepo's DR-264).

One module for one program's probes, so a history log's Evidence names the file
holding them (solorepo's DR-209).
"""
import contextlib
import json
import pathlib
from collections.abc import Iterator, Sequence
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    environment,
    load_channel,
    outcome,
    stood_in,
    unanswered,
    workspace,
)

OPEN_ISSUES = [{"number": 3, "title": "another Challenge", "labels": [{"name": "challenge"}]}]
"""What `issue list` answers: one other open Issue."""

OPEN_PULLS = [{"number": 4, "title": "a pull request", "headRefName": "claude/issue-3"}]
"""What `pr list` answers: one open pull request."""

REVIEWER = "o-r-reviewer"
"""The reviewer's login in the fake's repository, `o/r`."""

DIFF = "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-a\n+b"
"""What `pr diff` answers."""

HEAD = "0123456789abcdef0123456789abcdef01234567"
"""The pull request's head, as `pr view` answers it."""

ASKED = "feedfacefeedfacefeedfacefeedfacefeedface"
"""The head the run was asked about, as `SOLOREPO_REVIEW_HEAD` names it."""

PULL = "9"
"""The pull request the review door is run for."""

PLACEHOLDERS = ("<number>", "<repository>", "<head>", "<count>", "<paths>")
"""What the constraints form leaves for the door to fill."""

UNREAD = (None, None, None, "")
"""A `Session` before any session, as `before` and the reading door are handed one."""


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
    closed meanwhile, or lost `challenge` meanwhile.
    """
    channel, _, programs = load_channel()
    on = programs["on"]
    return _before_cases(channel, on) + _after_cases(channel, on)


@check("review door probes", pre=True)
def review_door_probes() -> list[str]:
    """`on reviewer before` and `after` over a pull request, with what the workflow hands `after`.

    Before: the harness by the pull request's label, Claude Code by default
    and Gemini or Jules by theirs, named as the reading door names
    it; every field of the depth a step output; the diff, the head's copies
    of the trunk paths, and the constraints written under `.review/`, the
    constraints counting and enumerating `depth.CONTROL_PLANE` less the
    workflows' directory and naming the pull request, the repository and the
    head; the head the run was asked about where `SOLOREPO_REVIEW_HEAD` is
    set; the verdicts the reviewer's login has given over every page, a
    bodiless `COMMENTED` and another login's verdict both left out; and a
    tracked `.review/` refused before anything is written. After: a verdict
    landed, the hook's evidence, and the fan-out ceiling each pass or end
    the step red with the finding the run log shows, the hook read for the
    harness that ran and the ceiling held for Claude Code alone; a session
    no harness step ran is a finding; and a flag the workflow did not hand
    over is a refusal rather than a pass.
    """
    channel, _, programs = load_channel()
    on = programs["on"]
    return _review_before_cases(channel, on) + _review_after_cases(channel, on)


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


class _Pull:
    """As much of GitHub as the review door asks about: a pull request's labels, head, reviews.

    The reviews are answered as the paginated REST read gives them, one JSON
    line each in the shape the door asks `--jq` for.
    """

    def __init__(self, labels: Sequence[str] = (), reviews: Sequence[dict[str, Any]] = ()) -> None:
        self.labels, self.reviews = list(labels), list(reviews)

    def __call__(self, *args: str, **kwargs: Any) -> Any:
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:1] == ("api",) and "/issues/" in args[1]:
            return {"pull_request": {"url": "x"}}
        if args[:1] == ("api",) and "/pulls/" in args[1] and "--paginate" in args:
            return "\n".join(json.dumps({"author": {"login": r["author"]["login"]},
                                         "state": r["state"], "body": r["body"]})
                             for r in self.reviews)
        if args[:2] == ("pr", "view"):
            return {"labels": [{"name": name} for name in self.labels], "headRefOid": HEAD}
        if args[:2] == ("pr", "diff"):
            return DIFF
        raise unanswered(args, "the review door fake")


def _review(login: str, state: str, body: str = "") -> dict[str, Any]:
    """A review as `pr view --json reviews` lists one."""
    return {"author": {"login": login}, "state": state, "body": body}


def _issue(labels: list[str], state: str = "OPEN") -> dict[str, Any]:
    """A Challenge as `CHALLENGE_FIELDS` reads it."""
    return {"number": 7, "title": "A Challenge to read", "url": "https://github.com/o/r/issues/7",
            "labels": [{"name": name} for name in labels], "body": "**Waits on.** Nothing.",
            "createdAt": "2026-09-22T00:00:00Z", "author": {"login": "solo"}, "state": state,
            "assignees": []}


@contextlib.contextmanager
def _workspace() -> Iterator[tuple[pathlib.Path, pathlib.Path, pathlib.Path]]:
    """A run's workspace and the two files it writes, with the head asked about unset.

    The head is the one variable a case here sets for itself; the toggles
    `workspace` stands down hold for every case.
    """
    with workspace(SOLOREPO_REVIEW_HEAD=None) as root:
        yield root, root / "output", root / "env"


def _before(channel: Any, on: Any,
            fake: _GitHub) -> tuple[Any, str, str, pathlib.Path | tuple[str, str]]:
    """`on reviewer before 7` against `fake`: how it ended, the two files, and the two pages."""
    with _workspace() as (root, output, env), stood_in(channel, gh=fake), \
            stood_in(on.common, tracked_scratch=lambda: ""):
        ended = outcome(lambda: on.reviewer("before", "7", on.Session(*UNREAD)))
        challenge = root / ".review" / "challenge.md"
        opened = root / ".review" / "open.md"
        pages = (challenge.read_text() if challenge.exists() else "",
                 opened.read_text() if opened.exists() else "")
        return ended, output.read_text(), env.read_text(), root if pages == ("", "") else pages


def _before_cases(channel: Any, on: Any) -> list[str]:
    """Before the session: unread, labelled for Gemini, at a level, closed."""
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

    ended, out, _, _ = _before(channel, on, _GitHub(_issue(["challenge", "harness:agy"])))
    if "harness=agy" not in out or "agent=antigravity-cli" not in out:
        problems.append(f"before: a Challenge labelled for Antigravity decided {out!r}")

    for name, fake in (("at a level", _GitHub(_issue(["challenge", "medium"]))),
                       ("closed", _GitHub(_issue(["challenge"], state="CLOSED")))):
        ended, out, env, pages = _before(channel, on, fake)
        if ended.code is not None or out.strip() != "read=false" or env.strip():
            problems.append(f"before: a Challenge {name} decided {out!r} and {env!r} with exit "
                            f"{ended.code!r}, not `read=false` alone")
        if not isinstance(pages, pathlib.Path):
            problems.append(f"before: a Challenge {name} still had its pages written")
    return problems


def _after_cases(channel: Any, on: Any) -> list[str]:
    """The reading door after the session: a level landed, and none landed."""
    problems = []
    unread = on.Session(*UNREAD)
    with _workspace(), stood_in(channel, gh=_GitHub(_issue(["challenge", "medium"]))):
        ended = outcome(lambda: on.reviewer("after", "7", unread))
    if ended.code is not None or "landed at medium" not in ended.out:
        problems.append(f"after: a level landed ended with {ended.code!r} and said {ended.out!r}")
    for name, fake in (("no level landed", _GitHub(_issue(["challenge"]))),
                       ("the Challenge closed meanwhile",
                        _GitHub(_issue(["challenge"], state="CLOSED"))),
                       ("challenge taken off meanwhile", _GitHub(_issue([])))):
        with _workspace(), stood_in(channel, gh=fake):
            ended = outcome(lambda: on.reviewer("after", "7", unread))
        red = ended.code is not None and "::error::" in ended.out
        if not red or "carries no level" not in ended.out:
            problems.append(f"after: {name} ended with {ended.code!r} and said {ended.out!r}, "
                            "where the step must end red and say why")
        if "landed at" in ended.out:
            problems.append(f"after: {name} was reported as read: {ended.out!r}")
    return problems


class _Archived:
    """A stand-in for `write_head`, recording the head and the paths it was asked for."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def __call__(self, head: str, paths: Sequence[str]) -> list[str]:
        self.calls.append((head, tuple(paths)))
        return list(paths)


def _review_before(channel: Any, on: Any, fake: _Pull,
                   tracked: str = "") -> tuple[Any, str, str, dict[str, str], _Archived]:
    """`on reviewer before` against `fake`: how it ended, the two files, and what was written.

    `tracked` is what `git ls-files` answers for `.review/`, nothing unless a
    case says otherwise, since the workspace is outside any repository.
    """
    archived = _Archived()
    review = on.review
    with _workspace() as (root, output, env), stood_in(channel, gh=fake), \
            stood_in(review, depth_of=lambda number: on.depth.STANDARD_CONFIG,
                     write_head=archived, tracked_scratch=lambda: tracked):
        ended = outcome(lambda: on.reviewer("before", PULL, UNREAD))
        written = {path.name: path.read_text() for path in (root / ".review").rglob("*")
                   if path.is_file()} if (root / ".review").is_dir() else {}
        return ended, output.read_text(), env.read_text(), written, archived


def _review_chain(on: Any, out: str, written: dict[str, str]) -> list[str]:
    """The chain among the outputs, and the first rung's prompt written (solorepo's DR-281)."""
    problems = []
    for line in ("tiers=1", "tier_1_harness=claude",
                 f"tier_1_model={on.depth.STANDARD_CONFIG.model}"):
        if line not in out.splitlines():
            problems.append(f"review before: the chain's {line} is not among the outputs {out!r}")
    prompt = written.get("prompt.md", "")
    if "Review pull request" in prompt or f"#{PULL}" not in prompt:
        problems.append("review before: the first rung's prompt was not written for Claude Code "
                        f"on #{PULL}: {prompt[:80]!r}")
    return problems


def _review_before_cases(channel: Any, on: Any) -> list[str]:
    """The review door before the session: the harness, the depth, the files, and the count."""
    problems = []
    reviews = [_review(REVIEWER, "COMMENTED"), _review(REVIEWER, "APPROVED"),
               _review("somebody", "CHANGES_REQUESTED", "no")]
    ended, out, env, written, archived = _review_before(channel, on, _Pull(reviews=reviews))
    if ended.code is not None or "harness=claude" not in out \
            or "agent=anthropics/claude-code-action@v1" not in out:
        problems.append(f"review before: an unlabelled pull request decided {out!r} with exit "
                        f"{ended.code!r}, not reviewed by Claude Code")
    if "ACTOR_AGENT=anthropics/claude-code-action@v1" not in env:
        problems.append(f"review before: the harness was named in the environment as {env!r}")
    for line in (f"agents={on.depth.STANDARD_CONFIG.agents}",
                 f"reason={on.depth.STANDARD_CONFIG.reason}"):
        if line not in out.splitlines():
            problems.append(f"review before: the depth's {line} is not among the outputs {out!r}")
    problems += _review_chain(on, out, written)
    if "verdicts=1" not in out:
        problems.append(f"review before: the verdicts given were counted as {out!r}, where one "
                        "approval stands beside a bodiless comment and another login's verdict")
    problems += _review_pages(on, written, archived)

    for label, harness, agent in (("harness:agy", "agy", "antigravity-cli"),
                                  ("harness:jules", "jules", "google-labs-jules")):
        ended, out, _, _, _ = _review_before(channel, on, _Pull(labels=[label]))
        if f"harness={harness}" not in out or f"agent={agent}" not in out:
            problems.append(f"review before: a pull request labelled {label} decided {out!r}")

    archived = _Archived()
    review = on.review
    with _workspace(), environment(SOLOREPO_REVIEW_HEAD=ASKED), stood_in(channel, gh=_Pull()), \
            stood_in(review, depth_of=lambda number: on.depth.STANDARD_CONFIG,
                     write_head=archived, tracked_scratch=lambda: ""):
        ended = outcome(lambda: on.reviewer("before", PULL, UNREAD))
    if ended.code is not None or not archived.calls or archived.calls[0][0] != ASKED:
        problems.append(f"review before: the head the run was asked about was not the one "
                        f"archived: {archived.calls!r}, exit {ended.code!r}")

    ended, _, _, written, archived = _review_before(channel, on, _Pull(), tracked=".review/head\n")
    if ended.code is None or "tracked" not in str(ended.code) or written or archived.calls:
        problems.append(f"review before: a tracked .review/ ended {ended.code!r} with "
                        f"{sorted(written)} written and {archived.calls!r} archived, where the "
                        "run must refuse before anything is written")
    return problems


def _review_pages(on: Any, written: dict[str, str], archived: _Archived) -> list[str]:
    """What the review door wrote under `.review/`: the diff, the head's paths, the constraints."""
    problems = []
    paths = tuple(p.rstrip("/") for p in on.depth.CONTROL_PLANE
                  if not p.startswith(".github/workflows"))
    if written.get("diff.patch", "").rstrip("\n") != DIFF:
        problems.append(f"review before: the diff was written as {written.get('diff.patch')!r}")
    if archived.calls != [(HEAD, paths)]:
        problems.append(f"review before: the head's copies were archived as {archived.calls!r}, "
                        f"not {HEAD} over {paths}")
    constraints = written.get("constraints.md", "")
    count = on.NUMBER_WORDS[len(paths)].capitalize()
    for expected in (f"#{PULL}", "of o/r", HEAD, f"**{count} paths",
                     *(f"`{p}`" for p in on.depth.CONTROL_PLANE
                       if not p.startswith(".github/workflows"))):
        if expected not in constraints:
            problems.append(f"review before: the constraints do not say {expected!r}")
    for placeholder in PLACEHOLDERS:
        if placeholder in constraints:
            problems.append(f"review before: {placeholder} survives in the constraints")
    return problems


def _review_after(channel: Any, on: Any, session: Any, evidence: str | None = None,
                  spawned: int = 0) -> Any:
    """`on reviewer after` with the session as the workflow described it, and what it left.

    The pull request carries two verdicts of the reviewer's, so a session
    that counted one before has a verdict landed and one that counted two
    has none.
    """
    two = _Pull(reviews=[_review(REVIEWER, "CHANGES_REQUESTED", "no"),
                         _review(REVIEWER, "APPROVED")])
    with _workspace() as (root, _, _), stood_in(channel, gh=two), \
            stood_in(on.review, spawned=lambda transcript: spawned):
        (root / ".review").mkdir()
        if evidence is not None:
            (root / ".review" / evidence).write_text("Bash\nRead\nGrep\n")
        return outcome(lambda: on.reviewer("after", PULL, session))


def _review_after_cases(channel: Any, on: Any) -> list[str]:
    """The review door after the session: the verdict, the hook's evidence, the ceiling."""
    problems = []
    ended = _review_after(channel, on, on.Session(1, 3, "claude", "t.json"),
                          evidence="hook-claude.evidence", spawned=2)
    if ended.code is not None or f"a verdict landed on #{PULL}" not in ended.out \
            or f"the hook decided 3 calls on #{PULL} (Claude Code)" not in ended.out \
            or "within the fan-out ceiling of 3" not in ended.out:
        problems.append(f"review after: a session that did everything ended {ended.code!r} "
                        f"saying {ended.out!r}")

    ended = _review_after(channel, on, on.Session(2, 3, "claude", "t.json"),
                          evidence="hook-claude.evidence")
    none = f"::error::no verdict landed on #{PULL} (before=2 after=2)"
    if ended.code is None or none not in ended.out:
        problems.append(f"review after: no verdict landing ended {ended.code!r} saying "
                        f"{ended.out!r}")

    ended = _review_after(channel, on, on.Session(1, 3, "claude", "t.json"))
    if ended.code is None or f"::error::the hook decided no call on #{PULL}" not in ended.out \
            or "Claude Code never invoked" not in ended.out:
        problems.append(f"review after: no evidence ended {ended.code!r} saying {ended.out!r}")

    ended = _review_after(channel, on, on.Session(1, 3, "claude", "t.json"),
                          evidence="hook-claude.evidence", spawned=4)
    if ended.code is None or "breaching the fan-out ceiling of 3" not in ended.out:
        problems.append(f"review after: four agents under a ceiling of three ended {ended.code!r} "
                        f"saying {ended.out!r}")

    ended = _review_after(channel, on, on.Session(1, 1, "agy", ""),
                          evidence="hook-agy.evidence", spawned=4)
    if ended.code is not None or "(Antigravity CLI)" not in ended.out or "ceiling" in ended.out:
        problems.append(f"review after: an Antigravity session ended {ended.code!r} saying "
                        f"{ended.out!r}, where its hook is read and no ceiling is held")

    ended = _review_after(channel, on, on.Session(1, 1, "jules", ""), spawned=4)
    if ended.code is not None or "hook" in ended.out or "ceiling" in ended.out:
        problems.append(f"review after: a Jules session ended {ended.code!r} saying "
                        f"{ended.out!r}, where only the verdict is read")

    ended = _review_after(channel, on, on.Session(2, 3, "claude", "t.json"), spawned=4)
    if ended.out.count("::error::") != 3:
        problems.append(f"review after: three findings were reported as {ended.out!r}")

    ended = _review_after(channel, on, on.Session(1, 3, "none", ""))
    if ended.code is None or "::error::no harness step ran the session" not in ended.out:
        problems.append(f"review after: no harness step running ended {ended.code!r} saying "
                        f"{ended.out!r}, where that is the finding the door exists for")

    empty = on.build_parser().parse_args(
        ["reviewer", "after", PULL, "--verdicts", "", "--agents", "", "--ran", ""])
    if (empty.verdicts, empty.agents, empty.ran) != (None, None, None):
        problems.append(f"review after: empty flags were parsed as {empty!r}, where an output "
                        "that never arrived reaches the door as an empty string")

    for name, session in (("no flags", on.Session(*UNREAD)),
                          ("no --verdicts", on.Session(None, 3, "claude", "")),
                          ("no --agents", on.Session(1, None, "claude", "")),
                          ("no --ran", on.Session(1, 3, None, ""))):
        ended = _review_after(channel, on, session, evidence="hook-claude.evidence")
        if ended.code is None or "takes what the workflow knows" not in str(ended.code) \
                or "landed" in ended.out:
            problems.append(f"review after: {name} ended {ended.code!r} saying {ended.out!r}, "
                            "where a number that did not arrive is a red run")
    return problems
