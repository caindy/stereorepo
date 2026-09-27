"""What every module of the package shares: the levels, the pull request shape, the
failures a call through the channel raises short of exiting, and the `**Waits on.**`
line both lifecycles write (solorepo's DR-264).

The blocker line lives here because both lifecycles reach it and neither may
import the other to do so: `challenges` rewrites it as the relationship moves,
and `pull_requests` holds a revised body to it.
"""
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from typing import Any

import channel

# The paragraph both Issue forms open with, and an Issue reference in either of
# the two spellings GitHub renders: bare, and qualified by `owner/repo`. The
# match runs to the blank line, the next bold heading or the end of the body
# rather than to the first newline, because an editor wraps the paragraph and a
# rewrite anchored on one line leaves the wrapped remainder standing beside its
# replacement. Every terminator admits a carriage return, because a paragraph
# whose own terminator is not recognised is one this pattern runs past, and the
# span it would then rewrite is the rest of the body.
WAITS_LINE = re.compile(
    r"^\*\*Waits on\.\*\*(?P<text>.*?)(?=\r?\n[ \t]*\r?\n|\r?\n\*\*|\r?\n?\Z)", re.M | re.S)


ISSUE_REF = re.compile(r"(?:[\w.-]+/[\w.-]+)?#(\d+)")


# What a `**Waits on.**` line may hold besides its references and still be one
# this program can rewrite: the words that join references, and the words for
# none of them.
WAITS_FILLER = frozenset(("and", "nothing", "none", ""))


NO_WAITS_LINE = "no `**Waits on.**` line"
"""What rewriting a blocker line raises where the Issue body holds none."""


Pull = dict[str, Any]
"""One pull request as GitHub answers for it, whichever fields were asked for."""


UNREACHED = (OSError, subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError)
"""What a call through `channel` raises short of exiting: `gh` would not start, it
failed where the caller passed `tolerate_fail`, or GitHub answered with something
other than the JSON the caller reads. A verb that degrades rather than exits names
this tuple, so a defect in the code it guards is not reported as a GitHub failure."""


DIFFICULTIES = ("easy", "medium", "hard", "human")


HARNESSES = ("claude", "codex", "copilot", "gemini")


# The two levels a loop takes on the label's own event (solorepo's DR-112), which is what
# makes a Challenge at either one a run's rather than a session's.
LOOP_LEVELS = ("easy", "medium")


# The one level a run lands itself (solorepo's DR-235). The other three say which kind of
# Job takes the Challenge, which is the reviewer's verdict to give; this one says
# the next step is not a Job's at all, which is the fact a run is the first to
# hold and nobody else can see.
RUN_LEVEL = "human"


def refuse_a_level_and_a_mandate_apart(level: str | None, mandate: str | None,
                                       instead: str | None = None) -> None:
    """Refuse `--difficulty` and `--mandate` given apart from each other (solorepo's DR-278).

    A session may have the solo beside it, which is why the run refusal reads
    the run mark and stops there (solorepo's DR-235); may is not does, so a
    level typed from a session stands only where `mandate` carries the solo's
    own words asking for it. A mandate that is empty or whitespace is no
    mandate, since a caller that reaches for the flag and puts nothing in it has
    said no more than one that omitted it.

    The pair is read in both directions. A mandate with no level to stand behind
    is a flag that parses and does nothing, which includes the mandate given
    beside a flag that excludes `--difficulty`; the channel refuses what is
    typeable and inert everywhere else, and the words the caller was asked to
    quote are worth more than a silent discard. `instead` is what names that
    flag, so the refusal reads on the verb it was typed on and never mentions a
    flag the caller does not have — the two verbs that read this pair hold
    different surfaces around it, and only `move file` has `--roadmap`.

    `RUN_LEVEL` is exempt from the first direction for the reason it is exempt
    from the run refusal. It starts no Job and asks for the solo, so a Job saying
    the next step is not its own is not asked to quote a mandate whose absence is
    the thing it is reporting. It is not exempt from the second: a mandate quoted
    beside it is still a mandate that stands behind a level.

    Parameters:
        level (str | None): The level `--difficulty` names, or None where it names none.
        mandate (str | None): The solo's own words asking for `level`, or None;
            blank or whitespace counts as None.
        instead (str | None): The flag the caller gave that excludes `--difficulty`,
            written as it is typed, or None where none was given.

    Raises:
        SystemExit: If a level that is a verdict is given with no mandate behind
            it, or if a mandate is given with no level to stand behind.
    """
    quoted = bool((mandate or "").strip())
    if not level:
        if quoted:
            if instead:
                excluded = f"`{instead}` lands none"
                route = (f"Drop `--mandate`: `{instead}` and `--difficulty` exclude each other, "
                         "so there is no level here for his words to stand behind.")
            else:
                excluded = "none was given"
                route = ("Name the level he asked for: `--difficulty <level>`. Where he asked "
                         "for none, drop `--mandate` and let the reviewer read it.")
            sys.exit(f"say: `--mandate` quotes the solo asking for a level, and {excluded} "
                     "(solorepo's DR-278).\n"
                     "     Nothing was filed. `--mandate` is read only beside `--difficulty`, "
                     f"so his words reach nobody here.\n     {route}")
        return
    if level == RUN_LEVEL or quoted:
        return
    sys.exit(f"say: `{level}` skips the reviewer, and nothing here says the solo asked for it "
             "(solorepo's DR-230, solorepo's DR-278).\n"
             "     Nothing was filed. Without `--difficulty` it lands `challenge` alone, which "
             "is the reviewer's queue, and a level you inferred belongs in the body under "
             "`**Difficulty.**`, where it is a proposal the reader answers.\n"
             "     Where the solo did ask for this level, quote what he typed: "
             "`--mandate \"<his words>\"`.")


def kind(number: str | int) -> str:
    """Pull request or Issue, asked of GitHub. The numbers are one sequence and
    the verbs that take either — `comment`, `revise` — should not make a
    caller say which."""
    found = channel.gh("api", f"repos/{channel.repo()}/issues/{number}")
    return "pull request" if found.get("pull_request") else "issue"


def native_blockers(issue: int | str) -> list[int]:
    """The Issue numbers GitHub records as blocking `issue`.

    Parameters:
        issue (int | str): Issue number to read.

    Returns:
        list[int]: Blocker Issue numbers, in GitHub's order.
    """
    view = channel.gh("issue", "view", str(issue), "--json", "blockedBy")
    return [n["number"] for n in (view.get("blockedBy") or {}).get("nodes", []) if "number" in n]


def waits_line(blockers: Sequence[int], prose: Sequence[str] = ()) -> str:
    """The `**Waits on.**` line describing `blockers` and any surviving `prose` items.

    Parameters:
        blockers (Sequence[int]): Blocker Issue numbers.
        prose (Sequence[str]): Non-Issue prose items (Decisions, accounts).

    Returns:
        str: The line, naming each blocker/prose, or `Nothing.` for an empty sequence.
    """
    items = list(prose) + [f"#{n}" for n in blockers]
    return "**Waits on.** " + (", ".join(items) if items else "Nothing.")


def prose_segment(item: str) -> bool:
    """Whether a `**Waits on.**` comma segment says anything besides its citations.

    A segment is prose where what remains of it once its citations and
    punctuation are struck out is not filler, which is what distinguishes a
    blocker the rewrite must carry forward from the words that join citations.

    Parameters:
        item (str): One comma segment of the line, stripped.

    Returns:
        bool: True where the segment says something besides its citations.
    """
    cleaned = re.sub(r"[^\w\s]+", " ", ISSUE_REF.sub(" ", item)).lower().split()
    return not set(cleaned) <= WAITS_FILLER


def waits_items(text: str) -> tuple[list[str], list[str]]:
    """The comma segments of a `**Waits on.**` paragraph: all of them, then the prose.

    Parameters:
        text (str): The paragraph's text, as `WAITS_LINE` groups it.

    Returns:
        tuple[list[str], list[str]]: Every segment, and the ones `prose_segment`
            calls prose.
    """
    line_text = " ".join(text.split())
    raw_items = [p.strip().rstrip(".") for p in line_text.split(",") if p.strip()]
    return raw_items, [item for item in raw_items if prose_segment(item)]


def severed_clause(item: str, after_citation: bool) -> bool:
    """Whether a `**Waits on.**` comma segment continues the sentence before it.

    The reading is where the segment stands rather than what word it opens with.
    `waits_line` renders prose ahead of the citations however the source line
    ordered them, so a segment standing after a citation is a continuation of
    the sentence that citation began, whatever its first word. A segment citing
    an Issue of its own reads that way too: the rewrite renders the citation a
    second time from the relationship, leaving the prose around it beside a
    number the line already carries.

    Parameters:
        item (str): One comma segment of the line, stripped.
        after_citation (bool): Whether a segment before this one cites an Issue.

    Returns:
        bool: True where the segment reads as part of a citation's sentence.
    """
    return after_citation or bool(ISSUE_REF.search(item))


def severed_clauses(body: str) -> list[str]:
    """The prose segments a rewrite of this `**Waits on.**` paragraph would strand.

    A rewrite emits the surviving prose ahead of the citations, so a segment
    that only reads beside its neighbours is one the rewrite would move away
    from what it explains — as surely when a blocker is added as when one is
    taken off. `severed_clause` says which segments read that way, each read
    against what stands before it.

    A paragraph citing no Issue at all has none, whatever its words: no segment
    stands after a citation and none carries one, so the free-standing prose
    blocker solorepo's DR-170 preserves — `All three seed repositories being
    migrated` — is admitted by the rule rather than by an exception to it.

    Parameters:
        body (str): The Issue's body Markdown text.

    Returns:
        list[str]: The segments that read as part of a citation's sentence, in
            the order the paragraph holds them; empty where there is no
            paragraph, no citation in it, or no such segment.
    """
    found = WAITS_LINE.search(body or "")
    if not found:
        return []
    raw_items, _ = waits_items(found.group("text"))
    severed, after_citation = [], False
    for item in raw_items:
        if prose_segment(item) and severed_clause(item, after_citation):
            severed.append(item)
        after_citation = after_citation or bool(ISSUE_REF.search(item))
    return severed


def retarget_waits(body: str, want: Sequence[int]) -> str:
    """`body` with its `**Waits on.**` paragraph rewritten to describe `want`.

    The paragraph is replaced by one line preserving non-Issue prose blockers
    (Decisions, accounts, the solo per solorepo's DR-170). Whether the paragraph
    is one a rewrite may touch at all is `severed_clauses`'s to answer and each
    caller's to refuse in its own words, since the two that reach here are a
    filing that has no Issue number yet and a verb that has one.

    Parameters:
        body (str): The Issue's body Markdown text.
        want (Sequence[int]): Blocker Issue numbers now recorded on GitHub.

    Returns:
        str: The rewritten body.

    Raises:
        LookupError: If `body` has no `**Waits on.**` line.
    """
    found = WAITS_LINE.search(body or "")
    if not found:
        raise LookupError(NO_WAITS_LINE)
    _, prose_items = waits_items(found.group("text"))
    new_line = waits_line(want, prose_items)
    return body[:found.start()] + new_line + body[found.end():]


def cited_waits(body: str) -> list[int]:
    """The Issue numbers a body's `**Waits on.**` paragraph cites, ascending.

    Every caller reading citations off the line reads the same span the rewrite
    replaces, so a citation on the paragraph's second physical line is one no
    guard can miss and the rewrite then drop.

    Parameters:
        body (str): The Issue's body Markdown text.

    Returns:
        list[int]: The cited numbers, ascending; empty where there is no paragraph.
    """
    found = WAITS_LINE.search(body or "")
    if not found:
        return []
    return sorted({int(n) for n in ISSUE_REF.findall(found.group("text"))})


def unbacked_waits(body: str, recorded: Sequence[int]) -> list[int]:
    """The Issues a body's `**Waits on.**` paragraph cites that `recorded` does not hold.

    Parameters:
        body (str): The Issue's body Markdown text.
        recorded (Sequence[int]): The blockers GitHub's relationship holds.

    Returns:
        list[int]: The cited numbers the relationship omits, ascending.
    """
    return sorted(set(cited_waits(body)) - {int(n) for n in recorded})


def refuse_unbacked_waits(issue: int | str, body: str) -> None:
    """Refuse a body whose `**Waits on.**` paragraph cites a blocker GitHub does not hold.

    The check `move file --blocked-by` makes at filing, made again wherever the
    line is rewritten afterwards (solorepo's DR-213).

    Parameters:
        issue (int | str): The Issue whose body is being replaced.
        body (str): The body about to be written.

    Raises:
        SystemExit: If the paragraph cites an Issue the relationship omits.
    """
    recorded = native_blockers(issue)
    unbacked = unbacked_waits(body, recorded)
    if not unbacked:
        return
    cited = ", ".join(f"#{n}" for n in unbacked)
    whole = sorted(set(recorded) | set(unbacked))
    sys.exit(f"say: the revised `**Waits on.**` line of #{issue} cites {cited}, which GitHub's "
             "blocked-by relationship does not hold: the line would say one thing and the "
             "relationship another, and the relationship is the record every classifier reads "
             "(solorepo's DR-213). So the sweep would call #" f"{issue} ripe and the run that "
             "took it would stand down on reading the line.\n"
             f"     Nothing was written. `move waits {issue} --on "
             f"{','.join(str(n) for n in whole)}` sets both records together — `--on` replaces "
             "the relationship, so it names every blocker and not only the new one — and this "
             "verb writes the rest of the body afterwards.")


def parse_waits_on(body: str | None) -> list[int]:
    """The blockers an Issue or pull request declares in prose.

    Either form is read: the `**Waits on.**` paragraph both Issue forms open
    with, and the `**What it waits on.**` heading a pull request body carries.

    Parameters:
        body (str | None): The body Markdown text, or None.

    Returns:
        list[int]: The numbers the line cites, in the order it holds them;
            empty for a body with no such line and for one saying nothing.
    """
    if not body:
        return []
    m = WAITS_LINE.search(body) or \
        re.search(r"\*\*What it waits on\.\*\*\s*(.*?)(?:\n\s*\n|\Z)", body, re.S)
    if not m:
        return []
    text = " ".join(m.group(1).split())
    if text.lower().rstrip(".") in ("nothing", "none", ""):
        return []
    return [int(n) for n in re.findall(r"#(\d+)", text)]
