"""`files.board.board_front_matter` against a board holding one Issue per mistake it reports
and one per shape it accepts, and `files.board.board_order` against an `ORDER` naming one
slug per stage it must or must not accept.

The steps are run by the gate over the repository's own board, which holds no
mistakes, so a step that reported nothing at all would pass there. Here each is
given a board written to a temporary directory: each file or line either must be
reported, once and under the key or line it gets wrong, or must not be reported
at all, and a failure names it.
"""
import pathlib
import tempfile
from collections.abc import Sequence
from typing import Any

from checks.collect import CouldNotRun, Found, Passed, check
from checks.files import board

WELL_FORMED = {
    "full": "---\ndifficulty: medium\nwaits_on: [scalar]\nparent: bare\n---\n# Full\n",
    "scalar": "---\nwaits_on: bare\n---\n# Scalar\n",
    "elsewhere": "---\nwaits_on: [other-repository:some-slug]\n---\n# Elsewhere\n",
    "bare": "# No front matter\n",
    "empty": "---\n---\n# Empty front matter\n",
}
"""Issues whose front matter holds to the class, by slug; none may be reported."""

MISTAKES = {
    "misspelt": ("dificulty", "---\ndificulty: easy\n---\n# Misspelt\n"),
    "unknown": ("difficulty", "---\ndifficulty: trivial\n---\n# Unknown\n"),
    "waiting": ("waits_on", "---\nwaits_on: [bare, missing]\n---\n# Waiting\n"),
    "orphan": ("parent", "---\nparent: missing\n---\n# Orphan\n"),
    "listed": ("front matter", "---\n- difficulty\n---\n# Listed\n"),
    "unparsed": ("front matter", "---\ndifficulty: [easy\n---\n# Unparsed\n"),
}
"""Issues with one mistake each, by slug, against the key the report must name."""

README = "---\ndificulty: trivial\n---\n# What this stage holds\n"
"""A stage's README, whose front matter would fail were it read as an Issue."""


@check("board front matter probes")
def board_front_matter_probes(views: Sequence[Any]) -> list[str]:
    """Each mistake is reported once under its file and key; no well-formed Issue or README is."""
    with tempfile.TemporaryDirectory() as tmp:
        stage = pathlib.Path(tmp) / "backlog"
        stage.mkdir()
        texts = {**WELL_FORMED, **{slug: text for slug, (_, text) in MISTAKES.items()},
                 "README": README}
        for slug, text in texts.items():
            (stage / f"{slug}.md").write_text(text, encoding="utf-8")
        outcome = board.board_front_matter(views, sorted(stage.iterdir()))
    if isinstance(outcome, CouldNotRun):
        return [f"board front matter: could not run: {outcome.why}"]
    lines = list(outcome.problems) if isinstance(outcome, Found) else []
    problems = []
    for slug, (key, _) in MISTAKES.items():
        found = [line for line in lines if f"/{slug}.md: {key}: " in line]
        if len(found) != 1:
            problems.append(f"board front matter: {slug}.md is reported {len(found)} times "
                            f"under {key}, not once")
    for slug in [*WELL_FORMED, "README"]:
        if any(f"/{slug}.md: " in line for line in lines):
            problems.append(f"board front matter: {slug}.md is reported, and holds no mistake")
    return problems


ORDER = "# the developer's\nkept\n\nflight\n# groomed below\nlanded\nnowhere\n"
"""An `ORDER` naming one backlog Issue, one in flight, one landed and one nowhere,
with a comment, a blank line and the marker between them."""

ORDER_STAGES = {"kept": "backlog", "flight": "in-progress", "landed": "done"}
"""Where each slug `ORDER` names has its Issue file, by slug; `nowhere` has none."""

ORDER_REPORTED = {"landed": 6, "nowhere": 7}
"""The slugs `board order` must report, against the line each sits on."""


@check("board order probes")
def board_order_probes() -> list[str]:
    """A landed slug and a missing slug are each reported once at their line; nothing else is."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        bare = board.board_order(root)
        for slug, stage in ORDER_STAGES.items():
            (root / stage).mkdir(exist_ok=True)
            (root / stage / f"{slug}.md").write_text(f"# {slug}\n", encoding="utf-8")
        (root / "backlog" / "ORDER").write_text(ORDER, encoding="utf-8")
        outcome = board.board_order(root)
    problems = [] if isinstance(bare, Passed) else ["board order: a board with no ORDER fails"]
    if isinstance(outcome, CouldNotRun):
        return [*problems, f"board order: could not run: {outcome.why}"]
    lines = list(outcome.problems) if isinstance(outcome, Found) else []
    for slug, n in ORDER_REPORTED.items():
        found = [line for line in lines if f"ORDER:{n}: {slug!r} " in line]
        if len(found) != 1:
            problems.append(f"board order: {slug} on line {n} is reported {len(found)} times")
    if len(lines) != len(ORDER_REPORTED):
        problems.append(f"board order: {len(lines)} lines reported, not {len(ORDER_REPORTED)}")
    return problems
