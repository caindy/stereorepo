"""What the citation steps read from: the patterns a Decision and an Issue citation take, and the files a portfolio inherits.
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

# A citation of solorepo's record, the repository stereorepo was seeded from.
# It names history this record does not hold, so nothing resolves it; it is
# taken out of the text before the bare scan, like a foreign citation
# (stereorepo's DR-297).
LEGACY = re.compile(r"[Ss]olorepo's DR-\d{3}\b(?:(?:,| and|, and) DR-\d{3}\b)*")


# An Issue number cited bare, as GitHub linked one. Not `#abc123`, which is a
# fragment or a colour, and not the tail of a longer number. Not a number in
# quotes either: `"#7"` in a probe is the string it greps its own output for.
ISSUE = re.compile(r"(?<![\w#&\"'])#(\d{1,4})(?!\d)")

# A citation of one of solorepo's GitHub Issues, which is how inherited prose
# cites the legacy repository's history: the possessive, then a run, so
# `solorepo's #11, #21` names two.
ISSUE_FOREIGN = re.compile(r"[Ss]olorepo's #\d{1,4}\b(?:(?:,| and|, and) #\d{1,4}\b)*")


def issue_citation() -> tuple[re.Pattern[str], re.Pattern[str]]:
    """The patterns for an Issue citation: a bare `#n`, and `solorepo's #n` (stereorepo's DR-132).

    Returns:
        tuple[re.Pattern, re.Pattern]: `(ISSUE, ISSUE_FOREIGN)`.
    """
    return ISSUE, ISSUE_FOREIGN


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
    and assertion files under `.meta/assertions/`. Not `WHY_FORK.md`, which is
    kept as written until its content is worked up into records.

    Parameters:
        copied (set[pathlib.Path]): Set of file paths copied into specialized portfolios.

    Yields:
        pathlib.Path: Next durable file path to inspect for citations.
    """
    for path in tree():
        if path.is_symlink() or not path.is_file() or ".git" in path.parts:
            continue
        if path == ROOT / "WHY_FORK.md":
            continue
        if path.suffix == ".md" or path in copied or TEMPLATE in path.parents or (
                path.suffix in (".yaml", ".yml") and (META / "assertions") in path.parents) or (
                path == META / "jules" / "client.py"):
            yield path
