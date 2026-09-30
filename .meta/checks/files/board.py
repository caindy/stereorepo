"""The board: every Issue file's front matter holds to the ontology's `Issue` class.

An Issue is a Markdown file under `issues/<stage>/`, and its front matter holds
only the slots `work/purpose.yaml` declares on the class: a `difficulty` the
`Difficulty` enum holds, and a `waits_on` and a `parent` that name Issues by
slug. The pair loop reads these keys and nothing else, so a misspelt key or an
unknown difficulty used to leave the Issue looking ungroomed, with nothing to
say why. The slots and the values are read off the schema rather than listed
here, so this step moves when the class does.
"""
import pathlib
from collections.abc import Sequence
from typing import Any

import yaml

from checks.collect import ROOT, CouldNotRun, Found, Passed, StepOutcome, check
from checks.files import sources
from checks.files.wiki import FRONTMATTER

BOARD = ROOT / "issues"
"""The board, whose subdirectories are the stages an Issue sits in."""

ELSEWHERE = ":"
"""What separates the repository from the slug in a `waits_on` entry naming another
repository's Issue."""


def _rel(path: pathlib.Path) -> pathlib.Path:
    """`path` relative to the repository root, or as given where it is not under it."""
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def _is_issue(path: pathlib.Path) -> bool:
    """Whether `path` is an Issue file on the repository's board: `issues/<stage>/<slug>.md`.

    `sources.tree()` lists a tracked file the working tree has deleted, so the
    file has to be there as well as listed."""
    return path.suffix == ".md" and path.parent.parent == BOARD and path.is_file()


def _as_list(value: Any) -> list[Any]:
    """A slot that may be written as a scalar or as a list, as a list."""
    return value if isinstance(value, list) else [value]


def _problems(path: pathlib.Path, slots: set[str], difficulties: set[str],
              board: set[str]) -> list[str]:
    """What is wrong with one Issue file's front matter, one line per key."""
    where = _rel(path)
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        return []
    try:
        front = yaml.safe_load(match["block"])
    except yaml.YAMLError as e:
        return [f"{where}: front matter: does not parse as YAML: {str(e).splitlines()[0]}"]
    if front is None:
        return []
    if not isinstance(front, dict):
        return [f"{where}: front matter: is a {type(front).__name__}, not a mapping"]
    problems = [f"{where}: {key}: is not a slot of the Issue class ({', '.join(sorted(slots))})"
                for key in front if key not in slots]
    if "difficulty" in front and str(front["difficulty"]) not in difficulties:
        problems.append(f"{where}: difficulty: {front['difficulty']!r} is not one of "
                        f"{', '.join(sorted(difficulties))}")
    if "waits_on" in front:
        problems.extend(f"{where}: waits_on: {entry!r} names no Issue on the board"
                        for entry in _as_list(front["waits_on"])
                        if ELSEWHERE not in str(entry) and str(entry) not in board)
    if "parent" in front and str(front["parent"]) not in board:
        problems.append(f"{where}: parent: {front['parent']!r} names no Issue on the board")
    return problems


@check("board front matter")
def board_front_matter(views: Sequence[Any],
                       md_files: Sequence[pathlib.Path] | None = None) -> StepOutcome:
    """Every Issue's front matter holds only the `Issue` class's slots, with values that resolve.

    Reports a key the class does not declare, a `difficulty` outside the
    `Difficulty` enum, a `waits_on` entry or a `parent` naming no Issue in any
    stage, and front matter that is not a YAML mapping. A `waits_on` entry
    written `<repository>:<slug>` names another repository's Issue and is not
    looked up. A `README.md` says what a stage holds and is not an Issue, so it
    is skipped whether it comes from the tree or from `md_files`, which is the
    seam a probe passes its own board through.
    """
    sv = next((sv for sv in views if "Issue" in sv.all_classes()), None)
    if sv is None:
        return CouldNotRun("no schema declares the Issue class")
    slots = set(sv.class_slots("Issue"))
    difficulties = set(sv.get_enum("Difficulty").permissible_values)
    files = md_files if md_files is not None else [p for p in sources.tree() if _is_issue(p)]
    issues = [path for path in files if path.name != "README.md"]
    board = {path.stem for path in issues}
    problems = [line for path in issues for line in _problems(path, slots, difficulties, board)]
    if problems:
        return Found(problems)
    return Passed(f"{len(issues)} Issues")


ORDER = "backlog/ORDER"
"""The backlog's running order, relative to the board: one slug per line, `#` lines aside."""

ORDERABLE = ("backlog", "todo", "in-progress", "desk-check")
"""The stages a slug in `ORDER` may name an Issue in: the backlog, or on its way from it.

An Issue underway keeps its line on its own branch until the squash that lands
it removes the line, so its own gate must still find it."""


@check("board order")
def board_order(root: pathlib.Path | None = None) -> StepOutcome:
    """Every slug `issues/backlog/ORDER` names is an Issue in the backlog or underway.

    A line naming an Issue that landed, or no Issue at all, would sit in the
    running order unread, so each is reported with its line number. Blank lines
    and `#` lines name nothing. A board with no `ORDER` runs in filename order
    and passes. `root` is the seam a probe passes its own board through.
    """
    board = root if root is not None else BOARD
    path = board / ORDER
    if not path.is_file():
        return Passed("no ORDER")
    lines = path.read_text(encoding="utf-8").splitlines()
    named = [(n, line.strip()) for n, line in enumerate(lines, 1)
             if line.strip() and not line.strip().startswith("#")]
    problems = [f"{_rel(path)}:{n}: {slug!r} names no Issue in {', '.join(ORDERABLE)}"
                for n, slug in named
                if not any((board / stage / f"{slug}.md").is_file() for stage in ORDERABLE)]
    if problems:
        return Found(problems)
    return Passed(f"{len(named)} slugs")
