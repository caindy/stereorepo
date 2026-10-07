"""What the citation steps read from: the patterns a Decision citation takes, the files a
portfolio inherits, and an Issue file without the quoted lines of its `Pair notes`.
"""
import pathlib
import re
from collections.abc import Iterator

from checks.collect import META, ROOT, TEMPLATE
from checks.files import inherited, tree

DR = re.compile(r"\bDR-(\d{3})\b")


# A citation of stereorepo's record, in the form the material a portfolio
# inherits writes one: the possessive, then a run. `Stereorepo's DR-085` names
# one at the head of a sentence, and `stereorepo's DR-085, DR-104` names two.
FOREIGN = re.compile(r"[Ss]tereorepo's DR-\d{3}\b(?:(?:,| and|, and) DR-\d{3}\b)*")
SCAFFOLD = "work:portfolio/stereorepo"

OUTMODED_BELOW = 297
"""The first number the scaffold's record issued after it was pruned
(stereorepo's DR-297). In the scaffold, a missing number below it is an
outmoded entry."""

NOTES = "Pair notes"
"""The section of an Issue file where the pair loop keeps each turn's note: a
copy of `PAIR_NOTES` in `pair/board.py`, which `.meta/` cannot import."""

NOTE_STOPS = ("Needs elaboration", "The plan", "Desk-check brief", "Desk-check notes",
              "Desk-check children")
"""The headings and bold leads that end a `Pair notes` section: a copy of
`NOTE_STOPS` in `pair/loop.py`. A test in `pair/test_pair.py` reads this
literal and compares it with the original."""

HEADING = re.compile(r"^(?:#{1,6}\s*|\*\*)(?P<name>[^*\n]+?)\.?(?:\*\*)?\s*$")
"""A Markdown heading or a bold lead, matched on a stripped line: a copy of
`_HEADING` in `pair/board.py`."""


def copied_files() -> set[pathlib.Path]:
    """Determine the absolute paths of all files copied into a specialized portfolio.

    Returns:
        set[pathlib.Path]: File paths copied into a new portfolio via specialization.
    """
    copied = {ROOT / "justfile"}
    for token in inherited():
        base = ROOT / token if (ROOT / token).exists() else META / token
        copied.update([base] if base.is_file() else base.rglob("*") if base.is_dir() else [])
    return copied


def durable(copied: set[pathlib.Path]) -> Iterator[pathlib.Path]:
    """Yield all durable repository files subject to citation validation.

    Covers documentation pages, inherited portfolio files, template files,
    and assertion files under `.meta/assertions/`.

    Parameters:
        copied (set[pathlib.Path]): Set of file paths copied into specialized portfolios.

    Yields:
        pathlib.Path: Next durable file path to inspect for citations.
    """
    for path in tree():
        if path.is_symlink() or not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix == ".md" or path in copied or TEMPLATE in path.parents or (
                path.suffix in (".yaml", ".yml") and (META / "assertions") in path.parents) or (
                path == META / "jules" / "client.py"):
            yield path


def without_notes(text: str) -> str:
    """`text`, an Issue file, with each quoted line of its `Pair notes` sections blanked.

    The pair loop quotes each turn's note under `Pair notes`. A note records
    a turn and makes no claim a reader should follow, and the gate the seat
    ran never saw it, so a note that explains a fix by quoting the citation
    it fixed must not fail the next turn. Skipping the notes here, where the
    citation steps read, covers every step, including one added later,
    where rewriting each refused form in the note would have to track the
    steps one by one.

    A section opens at a heading or bold lead named `Pair notes`, and ends
    at the next heading of its level or above, at any heading if a bold lead
    opened it, or at a heading or bold lead named in `NOTE_STOPS` or
    `Pair notes`, as `_note_spans` in `pair/board.py` reads it. Only lines
    that start with `>` once indentation is stripped are blanked: a line the
    seat wrote unquoted is still read. Blanking keeps the line count.
    """
    lines = text.splitlines(keepends=True)
    notes, ends = NOTES.lower(), {stop.lower() for stop in NOTE_STOPS} | {NOTES.lower()}
    inside, opened = False, 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if head := HEADING.match(stripped):
            name = head["name"].strip().lower()
            level = len(stripped) - len(stripped.lstrip("#"))
            if inside and (name in ends or (level and (not opened or level <= opened))):
                inside = False
            if name == notes:
                inside, opened = True, level
        elif inside and stripped.startswith(">"):
            lines[i] = "\n" if line.endswith("\n") else ""
    return "".join(lines)


def is_issue(path: pathlib.Path) -> bool:
    """Whether `path`, absolute under `ROOT`, is an Issue file: `issues/<stage>/<slug>.md`."""
    return path.suffix == ".md" and path.parent.parent == ROOT / "issues"


def read(path: pathlib.Path) -> str:
    """The text of `path` as the citation steps read it.

    An Issue file (`is_issue`) is read without the quoted lines of its
    `Pair notes` (`without_notes`); every other file is read whole. Raises
    what `pathlib.Path.read_text` raises.
    """
    text = path.read_text()
    return without_notes(text) if is_issue(path) else text
