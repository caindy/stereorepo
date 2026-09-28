"""Prose as the citation steps read it: the scalars of an assertion, the text of a page with its code stripped, and the Charter entry a citation points at.
"""
import pathlib
import re
from collections.abc import Iterator
from typing import Any

import yaml

from checks.collect import META

# A12 asks three things of a citation and `cited decisions` resolves one of them:
# the number. What follows resolves the rest — the claim the citation goes on to
# make about the thing it names (stereorepo's DR-130, solorepo's #147). Four shapes, chosen
# because each is a string search rather than a reading: an Article number that
# resolves, a quotation that appears where it is attributed, a relation that is
# the slot it claims to be, and a line that reads what it is cited for. A
# paraphrase is none of these and is nobody's check.
BLOCK = re.compile(r"```.*?```", re.S)
SPAN = re.compile(r"`[^`\n]*`")


ARTICLE = re.compile(r"\bA(\d{1,2})\b")


CITE = r"(?:DR-\d{3}|A\d{1,2})"


# Punctuation and markup boundaries that delimit citation scopes (sentence punctuation,
# markdown link brackets, and table cell pipes).
GAP = r"[^.;:|\[\]()\n]{0,30}?"


# Bounded non-citation span ensuring relation verbs bind to the nearest adjacent citation
# anchor in either direction without spanning intervening citations (stereorepo's DR-175).
NEAREST = rf"(?:(?!{CITE})[^.;:|\[\]()\n]){{0,30}}?"


# Attribution: the words that turn a quotation into a claim about the entry
# beside it. Deliberately not `is` or `was`, which put a quotation next to a
# citation in sentences that are not attributing it to anything.
SAYS = r"says|say|said|reads|read|states|state|stated|calls it|names it|puts it|has it|quotes"


# What is not a claim: a relation denied, or one entertained and not made.
HEDGED = re.compile(r"\b(not|never|no longer|would|could|should|might|may|cannot|"
                    r"rather than|instead of|if)\b", re.I)


def scalars(node: object) -> Iterator[str]:
    """Recursively traverse a YAML document node and yield all leaf scalar string values.

    Parameters:
        node (object): Parsed YAML object (dict, list, or scalar).

    Yields:
        str: Next scalar string found within the node.
    """
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from scalars(value)
    elif isinstance(node, list):
        for value in node:
            yield from scalars(value)


def comments(text: str) -> list[str]:
    """Extract comment blocks from YAML or source text as normalized prose spans.

    Parameters:
        text (str): Source text containing comments.

    Returns:
        list[str]: Normalized prose spans for contiguous comment blocks.
    """
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            content = stripped.lstrip("#").strip()
            if content:
                current.append(content)
            elif current:
                blocks.append(flat(" ".join(current)))
                current = []
        else:
            if current:
                blocks.append(flat(" ".join(current)))
                current = []
    if current:
        blocks.append(flat(" ".join(current)))
    return blocks


def prose(path: pathlib.Path) -> list[str]:
    """Extract an assertion's leaf scalars or a page flattened to a single span.

    For YAML, yields each parsed scalar string as its own span. For Markdown, strips
    fenced code blocks and flattens the remaining page into a single span. Comments
    are not prose here: the YAML parser ignores them and Markdown retains them in the
    flattened page; callers that need comment blocks call `comments()` beside this.

    Parameters:
        path (pathlib.Path): Path of file to extract prose from.

    Returns:
        list[str]: An assertion's leaf scalars (one span each for YAML), or a single
        flattened page span with fenced code blocks removed (for Markdown).
    """
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return []
    if path.suffix in (".yaml", ".yml"):
        try:
            return [flat(s) for s in scalars(yaml.safe_load(text))]
        except yaml.YAMLError:
            return []
    return [flat(BLOCK.sub(" ", text))]


def flat(text: str) -> str:
    """Normalizes arbitrary sequences of whitespace in text into a single space."""
    return re.sub(r"\s+", " ", text)


def normalise(text: str) -> str:
    """Normalize text for quotation matching by folding case, quotes, and typography.

    Parameters:
        text (str): Raw quotation or source text.

    Returns:
        str: Normalized lowercase text with typography and formatting stripped.
    """
    text = flat(text.replace("’", "'").replace("‘", "'")  # noqa: RUF001  # reason: normalising unicode smart quotes to ascii quotes
                .replace("“", '"').replace("”", '"'))
    return re.sub(r"[`*_]", "", text).lower()


def entry_text(cite: str, charter: dict[int, dict[str, Any]]) -> str | None:
    """Retrieve the complete normalized text of a Decision Record or Article entry.

    Parameters:
        cite (str): Citation identifier (`DR-nnn` or `An`).
        charter (dict[int, dict]): Charter article definitions indexed by article number.

    Returns:
        str | None: Normalized concatenated text of all entry scalars, or None if not found.
    """
    if cite.startswith("DR-"):
        path = META / "assertions" / "decisions" / f"{cite}.yaml"
        if not path.is_file():
            return None
        try:
            return normalise(" ".join(scalars(yaml.safe_load(path.read_text()))))
        except yaml.YAMLError:
            return None
    article = charter.get(int(cite[1:]))
    if article is None:
        return None
    return normalise(" ".join(scalars(article)))
