"""A rung's prompt, rendered from its pass's form under `.meta/templates/` (solorepo's DR-281).

A prompt is one form per Role and pass under `.meta/templates/prompts/`,
filled by the door the way `constraints.md` is: `<number>`, `<repository>`
and the rest of the fields the door knows replace their angle brackets, and
an angle bracket the door does not fill, such as the `<path>` in a command
the prompt shows, is the session's to read as written. What differs by
harness is a block the template marks with `<!-- claude -->` and
`<!-- /claude -->`, or `gemini`, and the rendering keeps the block whose
name is the rung's harness and drops the others. The budget sentence is
filled from the rung, since the Antigravity CLI binds no turn cap and a
prompt naming one would teach that session to discount the cap that does
bind.

The rendered prompt is written under `.review/`, where the workflow's
attempt step reads it as a file: a prompt inlined in a workflow is copied
once per harness step, which is the duplication solorepo's DR-281 ends.
"""

import pathlib
import re
from collections.abc import Mapping

from lib.on import routing

TEMPLATES = pathlib.Path(__file__).resolve().parents[2] / "templates" / "prompts"
"""Where the prompt forms are, one per Role and pass, and one more where a harness takes a
form of its own."""

BLOCK = re.compile(r"^<!-- (?P<harness>\w+) -->\n(?P<body>.*?)^<!-- /(?P=harness) -->\n",
                   re.S | re.M)
"""A harness-conditional block: kept whole where its name is the rung's harness, else dropped."""

CAPPED = ("This run has <turns> turns and <minutes> minutes. Spend the last tenth of either "
          "on the hand-off, not on more work:")
"""The budget sentence on a harness that binds the turn cap."""

CLOCKED = ("This run has <minutes> minutes and no turn cap: the <name> is bounded by "
           "the clock alone. Spend the last tenth on the hand-off, not on more work:")
"""The budget sentence on a harness that binds no turn cap, named as the session knows itself."""

CAPPING = ("claude",)
"""The harnesses that bind a turn cap: Claude Code takes `--max-turns`, and `.meta/run_agy.py`
builds the Antigravity CLI's argument vector with `--print-timeout` alone, so a turn number
told to any other session binds nothing (solorepo's DR-277)."""

NAMES = {"gemini": "Antigravity CLI", "jules": "Jules session"}
"""What a clocked harness's budget sentence calls the session."""


def template(role: str, task: str, harness: str) -> pathlib.Path:
    """The form for a Role's pass: the harness's own where one exists, the pass's otherwise."""
    own = TEMPLATES / f"{role}-{task}-{harness}.md"
    return own if own.is_file() else TEMPLATES / f"{role}-{task}.md"


def budget(rung: routing.Tier) -> str:
    """The budget sentence for a rung, naming the caps its harness binds and no others."""
    if rung.harness in CAPPING:
        return CAPPED.replace("<turns>", rung.turns).replace("<minutes>", rung.minutes)
    return CLOCKED.replace("<name>", NAMES.get(rung.harness, rung.harness)) \
        .replace("<minutes>", rung.minutes)


def render(role: str, task: str, rung: routing.Tier, fields: Mapping[str, str]) -> str:
    """The prompt for a rung: the form with its blocks resolved and its fields filled.

    Parameters:
        role (str): `coder` or `reviewer`.
        task (str): The pass, which names the form.
        rung (routing.Tier): The harness and its caps.
        fields (Mapping[str, str]): What the door knows, by the name its angle bracket carries.
    """
    text = template(role, task, rung.harness).read_text(encoding="utf-8")
    text = BLOCK.sub(lambda found: found["body"] if found["harness"] == rung.harness else "",
                     text)
    filled = {**fields, "budget": budget(rung), "turns": rung.turns, "minutes": rung.minutes,
              "effort": rung.effort}
    for name, value in filled.items():
        text = text.replace(f"<{name}>", value)
    return text


def write(path: pathlib.Path, role: str, task: str, rung: routing.Tier,
          fields: Mapping[str, str]) -> pathlib.Path:
    """Renders the prompt for a rung and writes it to `path`, where the attempt step reads it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(role, task, rung, fields), encoding="utf-8")
    return path
