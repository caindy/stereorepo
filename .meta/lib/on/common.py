"""Shared values and reading-door helpers for `.meta/say/on` (solorepo's DR-217, DR-264)."""
import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Sequence
from typing import Any, NamedTuple

import channel
import check_pr

REVIEW = pathlib.Path(".review")
"""Where the session's reading material is written, in the workspace the run checked out."""

CONSTRAINTS = pathlib.Path(__file__).resolve().parents[2] / "templates" / "constraints.md"
"""The form of what bounds every agent on a review, which the review door fills."""

HARNESSES = {"gemini": "antigravity-cli", "jules": "google-labs-jules",
             "claude": "anthropics/claude-code-action@v1"}
"""Each harness a door can choose, and the Agent the Trailer names it by."""

READING_HARNESSES = ("gemini", "claude")
"""The harnesses the reading door chooses among, by a `harness:` label, in the order asked."""

REVIEW_HARNESSES = ("gemini", "jules", "claude")
"""The harnesses the review door chooses among, in the order asked: Antigravity CLI
(solorepo's DR-245), Google Labs Jules (solorepo's DR-246), and Claude Code by default."""

EVIDENCE = {"claude": (REVIEW / "hook-claude.evidence", "Claude Code"),
            "gemini": (REVIEW / "hook-agy.evidence", "Antigravity CLI")}
"""Where each harness's session leaves the reading hook's decisions, and the harness's name."""

NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen")
"""The words the constraints spell a count with."""

CHALLENGE_FIELDS = "number,title,url,labels,body,createdAt,author,state,assignees"
"""What the reading door reads off the Challenge: the classifier's fields, and the page's."""

NO_VERDICT = ("no verdict landed on #{n} (before={before} after={after}): either the reviewer's "
              "turn ended without reviewing, or its verdict was refused because the head moved "
              "under the run (solorepo's #566). The request stands either way, and the run that "
              "reads the new head answers it")
"""The review door's finding where the session left no verdict (solorepo's DR-122)."""

NO_HOOK = ("the hook decided no call on #{n}: either the reviewer session did not start, or "
           "{harness} never invoked the registered hook. Inspect the harness hook configuration. "
           "The request stands either way; the next review reads this unchanged head")
"""The review door's finding where the session's reading hook left no evidence."""


class Session(NamedTuple):
    """What the workflow knows about the review session that the door's `after` is handed.

    Attributes:
        verdicts: How many verdicts the Role had given before the session, as `before` emitted.
        agents: The fan-out ceiling `before` chose.
        ran: Which harness step ran the session: `claude`, `gemini`, `jules` or `none`.
        transcript: Where Claude Code's execution transcript is, or the empty string.

    The first three are `None` where the workflow did not say, which the
    review door's `after` refuses.
    """

    verdicts: int | None
    agents: int | None
    ran: str | None
    transcript: str


NOT_SAID = ("the review door's `after` takes what the workflow knows, --verdicts, --agents and "
            "--ran, and was handed verdicts={verdicts!r} agents={agents!r} ran={ran!r}: a number "
            "that did not arrive is a red run, not a green one it did not earn")
"""The refusal where `after` on a pull request is missing what it judges by."""

NO_HARNESS = ("no harness step ran the session on #{n}: the review was never started, and the "
              "request stands")
"""The review door's finding where the workflow reports that no harness step ran."""


def emit(target: str, **pairs: str) -> None:
    """`key=value` lines, appended to the file `target` names in the environment and printed.

    `GITHUB_OUTPUT` is where a step's outputs go and `GITHUB_ENV` where the
    job's environment does; where neither is set, which is a session running
    the door by hand, the lines are only printed.

    Parameters:
        target (str): `GITHUB_OUTPUT` or `GITHUB_ENV`.
        **pairs (str): The keys and values.
    """
    lines = [f"{key}={value}" for key, value in pairs.items()]
    path = os.environ.get(target)
    if path:
        with pathlib.Path(path).open("a", encoding="utf-8") as out:
            out.write("".join(f"{line}\n" for line in lines))
    for line in lines:
        print(f"{target}: {line}")


def harness_of(labels: Sequence[str], among: Sequence[str] = READING_HARNESSES) -> str:
    """Which harness runs the session, by a `harness:` label; Claude Code where there is none.

    Parameters:
        labels (Sequence[str]): The Issue's or pull request's labels.
        among (Sequence[str]): The harnesses this door chooses among, first match taken.
    """
    for name in among:
        if f"harness:{name}" in labels:
            return name
    return "claude"


def name_harness(harness: str) -> None:
    """The harness as a step output, and under both environment names the channel signs by.

    `ACTOR_AGENT` is the name the channel reads in a run, written beside the
    `AI_AGENT` the harness overwrites with its own build string
    (solorepo's DR-233).

    `GITHUB_ENV` reaches the steps after this one; the door's own process
    is given the name too, so that what it posts before the session ends is
    signed as the harness it has just chosen and not as the step.
    """
    emit("GITHUB_OUTPUT", harness=harness, agent=HARNESSES[harness])
    emit("GITHUB_ENV", AI_AGENT=HARNESSES[harness], ACTOR_AGENT=HARNESSES[harness])
    os.environ[channel.ENV_RUN_AGENT] = HARNESSES[harness]


def challenge_page(view: dict[str, Any]) -> str:
    """The Challenge as the session reads it: its number, title, link, labels, filing, and body."""
    labels = ", ".join(check_pr.state.issue_labels(view))
    filed = f"{view.get('createdAt', '')} by {(view.get('author') or {}).get('login', '')}"
    return (f"# #{view['number']} {view.get('title', '')}\n\n{view.get('url', '')}\n"
            f"labels: {labels}\nfiled: {filed}\n\n---\n\n{view.get('body') or ''}")


def open_page() -> str:
    """What is open beside the Challenge: every open Issue and pull request, one line each."""
    issues = channel.gh("issue", "list", "--state", "open", "--limit", "200",
                        "--json", "number,title,labels")
    pulls = channel.gh("pr", "list", "--state", "open", "--limit", "100",
                       "--json", "number,title,headRefName")
    lines = ["# Open Issues", ""]
    lines += [f"- #{i['number']} [{', '.join(check_pr.state.issue_labels(i))}] {i['title']}"
              for i in issues]
    lines += ["", "# Open pull requests", ""]
    lines += [f"- #{p['number']} ({p.get('headRefName', '')}) {p['title']}" for p in pulls]
    return "\n".join(lines) + "\n"


def reading_before(number: str) -> None:
    """The reading door before the session: still unread, which harness reads, and what it reads.

    A Challenge that reads anything but `UNREAD` through the Issue classifier
    is a stale delivery: a level landed while this run waited, and a level is
    the reviewer's verdict already given (solorepo's DR-230), so the session
    is not started. Otherwise the harness is chosen by the Challenge's own
    label, named under `ACTOR_AGENT`, which the channel reads in a run,
    beside the `AI_AGENT` the harness overwrites (solorepo's DR-233), and
    the Challenge and what is open are written under `.review/`, since
    the session's reading hook runs only the programs
    `.meta/lib/worktree_only/grammar.py` lists, and `gh issue` is not among
    them.

    Parameters:
        number (str): The Challenge.
    """
    view = channel.gh("issue", "view", number, "--json", CHALLENGE_FIELDS)
    labels = check_pr.state.issue_labels(view)
    found = check_pr.state.classify_issue(view, None, False)
    if found is not check_pr.state.IssueState.UNREAD:
        emit("GITHUB_OUTPUT", read="false")
        print(f"#{number} is labelled '{', '.join(labels)}' now and reads {found.value}: "
              "this delivery is stale")
        return
    harness = harness_of(labels)
    emit("GITHUB_OUTPUT", read="true")
    name_harness(harness)
    shutil.rmtree(REVIEW, ignore_errors=True)
    REVIEW.mkdir()
    (REVIEW / "challenge.md").write_text(challenge_page(view), encoding="utf-8")
    (REVIEW / "open.md").write_text(open_page(), encoding="utf-8")
    print(f"#{number} is labelled '{', '.join(labels)}': unread, and {harness} reads it")


def reading_after(number: str) -> None:
    """The reading door after the session: whether it was read, which is a level landed.

    The level is read rather than the transcript believed, because GitHub
    holds the one and the transcript only claims the other
    (solorepo's DR-122). A session that ended without landing one has not
    read, whatever else happened to the Challenge meanwhile: one closed, or
    stripped of `challenge`, while the session ran carries no level either,
    and is reported as what it reads rather than as read.

    Parameters:
        number (str): The Challenge.

    Raises:
        SystemExit: Where no level stands, so the run is red and the Challenge
            still waits.
    """
    view = channel.gh("issue", "view", number, "--json", "labels,state")
    labels = check_pr.state.issue_labels(view)
    level = next((d for d in channel.sibling("move").DIFFICULTIES if d in labels), None)
    if level is None:
        found = check_pr.state.classify_issue(view, None, False)
        print(f"::error::the session ended and #{number} carries no level, reading "
              f"{found.value}: nothing was read, and the Challenge still waits")
        sys.exit(1)
    print(f"#{number} was read and landed at {level}")


def command(argv: Sequence[str], stdin: bytes | None = None) -> bytes:
    """Runs a command and answers its output, or ends the run saying what failed and why.

    A command that fails leaves through the same `::error::` line every other
    failure here does, with its own words, so the run log says why the door
    failed rather than which exit status it saw.

    Parameters:
        argv (Sequence[str]): The command and its arguments.
        stdin (bytes | None): What the command reads, where it reads anything.

    Raises:
        SystemExit: Where the command is missing or ends with a status.
    """
    try:
        return subprocess.run(list(argv), check=True, capture_output=True, input=stdin).stdout
    except FileNotFoundError:
        sys.exit(f"::error::`{argv[0]}` is not on this runner, and the review door runs it")
    except subprocess.CalledProcessError as failed:
        why = failed.stderr.decode("utf-8", "replace").strip() if failed.stderr else ""
        sys.exit(f"::error::`{' '.join(argv)}` failed: {why or f'status {failed.returncode}'}")
