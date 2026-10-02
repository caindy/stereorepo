"""What the citation steps read from: the patterns a Decision citation takes, and the files a portfolio inherits.
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
