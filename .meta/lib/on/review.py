"""Reviewer door lifecycle for `.meta/say/on` (solorepo's DR-217, DR-264)."""

import json
import os
import shutil
import sys
from collections.abc import Sequence

import agents
import channel
import check_pr
import depth
from lib.on import common


def trunk_paths() -> tuple[str, ...]:
    """The control plane less the workflows' own directory: what the run restored from trunk.

    `depth.CONTROL_PLANE` is the one statement of what the control plane is
    (solorepo's DR-217, solorepo's DR-219); the workflow that runs is the pull
    request's own by GitHub's rule, so its directory is not restored.
    """
    return tuple(p for p in depth.CONTROL_PLANE if not p.startswith(".github/workflows"))


def tracked_scratch() -> str:
    """What git tracks under `.review/`, one path per line; empty where nothing is."""
    return common.command(["git", "ls-files", "--", str(common.REVIEW)]).decode("utf-8", "replace")


def refuse_tracked_scratch() -> None:
    """Ends the run where `.review/` is tracked, before anything is written there.

    `.gitignore` silences an untracked `.review/`; it does not stop a branch
    committing one, and the checkout materialises whatever the merge ref
    tracks there before the door runs. A committed `.review/diff.patch`
    symlink turns the write into one onto its target, and a committed
    `.review/head` symlink lands the head's own channel and hooks on top of
    trunk's, after the restore. Nothing legitimate is ever tracked there, so
    the run refuses rather than guessing which shape it is looking at.

    Raises:
        SystemExit: Where anything under `.review/` is tracked.
    """
    if tracked_scratch().strip():
        sys.exit(
            "::error::.review/ is tracked in this tree, and the review door writes the "
            "reviewer's scratch there"
        )


def write_head(head: str, paths: Sequence[str]) -> list[str]:
    """The head's copies of `paths` under `.review/head/`, to be read there and never run.

    The reviewer reads the pull request's own channel and hooks there while
    what runs is still trunk's, because the reading hook's grammar admits a
    program spelled `.meta/say/<name>` and nothing under `.review/` is spelled
    that way. `git ls-tree -z` names what the head holds under the paths, so
    a name holding a space or a quote arrives whole, and `git archive` writes
    the head's tree rather than trunk's. A path the pull request deletes is
    simply absent, and the diff says so.

    Parameters:
        head (str): The pull request's head commit.
        paths (Sequence[str]): The trunk paths, without trailing slashes.

    Returns:
        list[str]: Every path written.

    Raises:
        SystemExit: Where the head holds none of the paths, which is this door
            failing and not a review.
    """
    listed = common.command(["git", "ls-tree", "-r", "-z", "--name-only", head, "--", *paths])
    names = [name.decode("utf-8", "surrogateescape") for name in listed.split(b"\0") if name]
    if not names:
        sys.exit(
            f"::error::no trunk path is in {head}, so there is nothing for the reviewer to "
            "read there"
        )
    archive = common.command(["git", "archive", head, "--", *names])
    common.command(["tar", "-x", "-C", str(common.REVIEW / "head")], stdin=archive)
    return names


def constraints(number: str, head: str, paths: Sequence[str]) -> str:
    """The constraints every agent on the review reads, the form filled for this pull request.

    Parameters:
        number (str): The pull request.
        head (str): Its head commit.
        paths (Sequence[str]): The trunk paths, enumerated and counted in the text.
    """
    quoted = [f"`{path}`" for path in paths]
    enumerated = ", ".join(quoted[:-1]) + " and " + quoted[-1] if len(quoted) > 1 else quoted[0]
    count = (
        common.NUMBER_WORDS[len(paths)]
        if len(paths) < len(common.NUMBER_WORDS)
        else str(len(paths))
    )
    return (
        common.CONSTRAINTS.read_text(encoding="utf-8")
        .replace("<number>", number)
        .replace("<repository>", channel.repo())
        .replace("<head>", head)
        .replace("<count>", count.capitalize())
        .replace("<paths>", enumerated)
    )


def depth_of(number: str) -> depth.DepthConfig:
    """The review's depth by what changed, evaluated as the Role reads (solorepo's DR-188).

    `depth.py` reaches GitHub with the token in its environment, so the Role's
    credential is lent to it for the evaluation and taken back after.

    Parameters:
        number (str): The pull request.
    """
    held = os.environ.get("GH_TOKEN")
    os.environ.update(channel.role_credential())
    try:
        files, meta, patch = depth.resolve_files_for_pr(number)
        return depth.evaluate(files, pr_meta=meta, diff_patch=patch)
    finally:
        if held is None:
            os.environ.pop("GH_TOKEN", None)
        else:
            os.environ["GH_TOKEN"] = held


def verdicts_of(number: str) -> int:
    """How many verdicts the reviewer's account has given on the pull request, on any head.

    Every page of the review list is read: an argued pull request holds a
    review per raise and per reply, bodiless and dropped by the count, and
    one page of a hundred loses the verdicts among them. Each review comes
    back as one line the state module reads in the shape `pr view` gives.
    """
    lines = channel.gh(
        "api",
        f"repos/{channel.repo()}/pulls/{number}/reviews?per_page=100",
        "--paginate",
        "--jq",
        ".[] | {author: {login: .user.login}, state, body}",
        parse=False,
    )
    reviews = [json.loads(line) for line in lines.splitlines() if line.strip()]
    return check_pr.state.verdicts_given({"reviews": reviews}, channel.role_login("reviewer"))


def review_before(number: str) -> None:
    """The review door before the session: which harness, how deep, what it reads, and the count.

    The harness is chosen by the pull request's own label (solorepo's DR-242)
    and named as the reading door names it. The depth is `depth.py`'s
    (solorepo's DR-188), every field of it a step output. What the session
    reads is written as files, since a diff and the head's copies of the
    trunk paths both exceed what a shell result carries whole
    (solorepo's #196): the diff, the head's copies under `.review/head/`, and
    the constraints every agent reads. The head is the one the run was asked
    about, `SOLOREPO_REVIEW_HEAD`, or the pull request's where a session runs
    the door by hand. The verdicts the Role has already given are counted
    last, so that only a verdict the session itself posts satisfies `after`
    (solorepo's DR-122).

    Parameters:
        number (str): The pull request.
    """
    view = channel.gh("pr", "view", number, "--json", "labels,headRefOid")
    harness = common.harness_of(check_pr.state.issue_labels(view), common.REVIEW_HARNESSES)
    common.name_harness(harness)
    found = depth_of(number)
    common.emit("GITHUB_OUTPUT", **{key: str(value) for key, value in found._asdict().items()})
    head = os.environ.get("SOLOREPO_REVIEW_HEAD") or str(view.get("headRefOid") or "HEAD")
    refuse_tracked_scratch()
    shutil.rmtree(common.REVIEW, ignore_errors=True)
    (common.REVIEW / "head").mkdir(parents=True)
    diff = channel.gh("pr", "diff", number, parse=False)
    (common.REVIEW / "diff.patch").write_text(f"{diff}\n", encoding="utf-8")
    paths = trunk_paths()
    write_head(head, [path.rstrip("/") for path in paths])
    (common.REVIEW / "constraints.md").write_text(
        constraints(number, head, paths), encoding="utf-8"
    )
    common.emit("GITHUB_OUTPUT", verdicts=str(verdicts_of(number)))
    for written in sorted(path for path in common.REVIEW.rglob("*") if path.is_file()):
        print(written)


def spawned(transcript: str) -> int:
    """How many agents Claude Code's execution transcript shows the session spawned."""
    content = agents.read_content(transcript, quiet=True) if transcript else ""
    return len(agents.parse_agents(content))


def review_after(number: str, session: common.Session) -> None:
    """The review door after the session: a verdict landed, the hook fired, the ceiling was kept.

    The verdict is counted rather than the transcript believed, because the
    harness reports success when the model's turn ends and a turn ends
    without a verdict as readily as with one (solorepo's DR-122). The hook's
    evidence file says the session's reads went through the reading hook,
    where Claude Code or Antigravity CLI ran it; Jules leaves none. The
    fan-out ceiling is held against Claude Code's transcript alone
    (solorepo's DR-191), since Antigravity CLI writes none. A session no
    harness step ran is a finding of its own. Every finding is printed, and
    one is enough to end the run red.

    Parameters:
        number (str): The pull request.
        session (common.Session): What the workflow knows about the session.

    Raises:
        SystemExit: Where any finding stands, or the workflow did not say what
            the door judges by.
    """
    if session.verdicts is None or session.agents is None or session.ran is None:
        sys.exit("::error::" + common.NOT_SAID.format(**session._asdict()))
    problems = []
    after = verdicts_of(number)
    if after > session.verdicts:
        print(f"a verdict landed on #{number}")
    else:
        problems.append(common.NO_VERDICT.format(n=number, before=session.verdicts, after=after))
    if session.ran == "none":
        problems.append(common.NO_HARNESS.format(n=number))
    if session.ran in common.EVIDENCE:
        evidence, harness = common.EVIDENCE[session.ran]
        calls = evidence.read_text(encoding="utf-8").splitlines() if evidence.is_file() else []
        if calls:
            print(f"the hook decided {len(calls)} calls on #{number} ({harness})")
        else:
            problems.append(common.NO_HOOK.format(n=number, harness=harness))
    if session.ran == "claude":
        kept, said = agents.evaluate_ceiling(spawned(session.transcript), session.agents)
        if kept:
            print(said)
        else:
            problems.append(said.removeprefix("::error::"))
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        sys.exit(1)


def reviewer(phase: str, number: str, session: common.Session) -> None:
    """The reviewer's door, `before` or `after` the session, for what `number` names.

    Parameters:
        phase (str): `before` or `after`.
        number (str): A Challenge, which is the reading door, or a pull
            request, which is the review door.
        session (common.Session): What the workflow knows after a review session;
            unread on the reading door and before any session, and refused
            absent after a review session.
    """
    if channel.sibling("move").kind(number) == "pull request":
        if phase == "before":
            review_before(number)
        else:
            review_after(number, session)
    elif phase == "before":
        common.reading_before(number)
    else:
        common.reading_after(number)
