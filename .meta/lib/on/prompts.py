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

A form is read from the worktree where the checkout carries one and from
trunk where it carries none. The coder's door checks the pull request's
head branch out before it renders, so a branch cut before the commit that
added a form has no such file on disk by the time the rendering reads it,
and the door is running trunk's own code (solorepo's DR-219) against a
worktree that predates it. Trunk answers for what the branch does not
carry, the way `review.yml` restores the control plane under
solorepo's DR-217, and without writing into the worktree the coder is about
to commit from.
"""

import pathlib
import re
import subprocess
from collections.abc import Mapping

from lib.on import routing

ROOT = pathlib.Path(__file__).resolve().parents[3]
"""The repository root, which is where a form is read from trunk."""

TEMPLATES = ROOT / ".meta" / "templates" / "prompts"
"""Where the prompt forms are, one per Role and pass, and one more where a harness takes a
form of its own."""

TRUNK = "origin/main"
"""The revision a form is read from where the worktree carries none."""

WHERE = TEMPLATES.relative_to(ROOT).as_posix()
"""The forms' path from the repository root, which is how `git show` names a file."""

MISSING = ("no prompt form for the {role}'s {task} pass on {harness}: neither {names} is under "
           "{where}, in this worktree or on {trunk}")
"""The `FileNotFoundError` message where a pass has no form in the worktree and none on `TRUNK`,
formatted with `role`, `task`, `harness`, `names`, `where` and `trunk`."""

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

NAMES = {"gemini": "Antigravity CLI", "jules": "Jules session", "copilot": "Copilot CLI"}
"""What a clocked harness's budget sentence calls the session."""


def forms(role: str, task: str, harness: str) -> tuple[str, str]:
    """The forms a Role's pass may be read from: the harness's own first, the pass's after."""
    return f"{role}-{task}-{harness}.md", f"{role}-{task}.md"


def trunk(name: str) -> str | None:
    """The form `name` as `TRUNK` holds it, or `None` where that revision carries no such form."""
    found = subprocess.run(["git", "show", f"{TRUNK}:{WHERE}/{name}"],
                           capture_output=True, cwd=ROOT, check=False)
    return found.stdout.decode("utf-8") if found.returncode == 0 else None


def template(role: str, task: str, harness: str) -> str:
    """The text of the form for a Role's pass: the harness's own where one exists, the pass's
    otherwise.

    The worktree decides where it carries either form, so a branch that
    changes one is rendered from its own; trunk answers only where it
    carries neither, which is the checkout cut before the form landed.

    Parameters:
        role (str): `coder` or `reviewer`.
        task (str): The pass, which names the form.
        harness (str): The rung's harness, which may take a form of its own.

    Raises:
        FileNotFoundError: Where neither the worktree nor `TRUNK` carries a form for the pass.
    """
    wanted = forms(role, task, harness)
    for name in wanted:
        path = TEMPLATES / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
    for name in wanted:
        text = trunk(name)
        if text is not None:
            return text
    raise FileNotFoundError(MISSING.format(role=role, task=task, harness=harness,
                                           names=" nor ".join(wanted), where=WHERE, trunk=TRUNK))


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
    text = template(role, task, rung.harness)
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
