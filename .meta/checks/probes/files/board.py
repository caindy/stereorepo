"""`files.board.board_front_matter` against a board holding one Issue per mistake it reports
and one per shape it accepts.

The step is run by the gate over the repository's own board, which holds no
mistakes, so a step that reported nothing at all would pass there. Here it is
given a board written to a temporary directory: each file either must be
reported, once and under the key it gets wrong, or must not be reported at
all, and a failure names the file.
"""
import pathlib
import tempfile
from collections.abc import Sequence
from typing import Any

from checks.collect import CouldNotRun, Found, check
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
