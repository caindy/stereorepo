"""What a `run:` step owes the root verb surface: where a recipe already wraps a
tool under `.meta/`, the step types the recipe rather than the tool
(solorepo's DR-252, solorepo's DR-275).

The scope is this repository's own CI — every `run:` step under
`.github/workflows/` and under `.meta/actions/`. `template/.github/workflows/`
is outside it: those files are seeded into a portfolio rather than run here, and
`workflows.gate_workflows_agree` is what reads them.

The channel is outside it too. `.meta/say/` is the Attested Mutation Plane
(solorepo's DR-252), addressed directly by every workflow that changes shared
state, and a recipe wrapping one of its verbs is an operator's convenience
rather than the one statement of how CI runs it.
"""

import pathlib
import re
from typing import Any

import yaml

from checks.collect import META, ROOT, CouldNotRun, Found, Passed, StepOutcome, check
from checks.files.justfile import JUSTFILE

WORKFLOWS = ROOT / ".github" / "workflows"
"""This repository's own workflows, which run here rather than in a portfolio."""

ACTIONS = META / "actions"
"""The composite actions those workflows reach through `uses:`, which travel
with `.meta/` into a portfolio (solorepo's DR-120)."""

CHANNEL = ".meta/say/"
"""The Attested Mutation Plane's prefix, whose verbs a workflow addresses
directly (solorepo's DR-252)."""

SCRIPT_RUNNERS = ("python", "python3", "uv", "uvx")
"""Command heads that run a script named further along the same command."""

PASS_THROUGH = ("sudo", "exec", "time")
"""Command heads that run whatever follows them unchanged."""

ENVIRONMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
"""Matches a leading `NAME=value`, which sets the environment of the command after it."""

SEPARATORS = re.compile(r"[\n;|&()]+")
"""Splits a shell script into commands: a newline, or any of the operators that end one."""

TOOL = re.compile(r"\.meta/[\w.@/-]+")
"""Matches a path under `.meta/`, which is how a recipe body names the tool it wraps."""


def _wrapped(justfile: pathlib.Path) -> dict[str, str]:
    """Reads the root verb surface for the tool each recipe wraps.

    Args:
        justfile: The rendered root verb surface.

    Returns:
        dict[str, str]: Each tool path under `.meta/` that a recipe body names, against
        the recipe naming it; the channel's own verbs excluded. Where two recipes wrap
        one tool — `pr`, `watch`, `sweep` and `pr-all` all wrap `.meta/check_pr.py` —
        the first in file order is the one named, since any of them is an answer to a
        step that types the script instead.
    """
    recipes: dict[str, str] = {}
    name = ""
    for line in justfile.read_text(encoding="utf-8").splitlines():
        if line[:1].strip() and not line.startswith("#"):
            name = line.split(":")[0].split()[0].lstrip("@")
        elif name and line.strip() and not line.strip().startswith("#"):
            for tool in TOOL.findall(line):
                if not tool.startswith(CHANNEL):
                    recipes.setdefault(tool, name)
    return recipes


def _invoked(command: str) -> str | None:
    """The tool one command runs, where it runs a tool under `.meta/`.

    Leading environment assignments and pass-through heads are dropped. A command an
    interpreter heads is read for the script it names, so `uvx --python 3.13 --with pyyaml
    python .meta/render.py` answers `.meta/render.py`; any other command answers only its own
    head, so `git checkout main .meta/check_pr.py` answers nothing.

    Args:
        command: One command, as the shell would run it.

    Returns:
        str | None: The path the command invokes, or None where it invokes nothing under `.meta/`.
    """
    tokens = command.split()
    while tokens and (ENVIRONMENT.match(tokens[0]) or tokens[0] in PASS_THROUGH):
        tokens.pop(0)
    if not tokens:
        return None
    if tokens[0] in SCRIPT_RUNNERS:
        return next((token for token in tokens[1:] if token.startswith(".meta/")), None)
    return tokens[0] if tokens[0].startswith(".meta/") else None


def _commands(script: str) -> list[str]:
    """Splits one `run:` step's script into the commands the shell would run.

    Backslash continuations are joined, and a comment line is dropped whole.

    Args:
        script: The step's script, as YAML read it.

    Returns:
        list[str]: One entry per command, in the order they appear, blanks removed.
    """
    joined = script.replace("\\\n", " ")
    lines = [line for line in joined.splitlines() if not line.strip().startswith("#")]
    return [command.strip() for command in SEPARATORS.split("\n".join(lines)) if command.strip()]


def _scripts(document: Any) -> list[str]:
    """Every `run:` step's script in one parsed workflow or composite action.

    Walks the document rather than the two shapes that hold steps, so a job's steps,
    a composite action's steps and anything else carrying a `run:` are all read.

    Args:
        document: A parsed YAML document, or any part of one.

    Returns:
        list[str]: One entry per `run:` whose value is a string.
    """
    if isinstance(document, dict):
        found = [document["run"]] if isinstance(document.get("run"), str) else []
        for value in document.values():
            found += _scripts(value)
        return found
    if isinstance(document, list):
        return [script for item in document for script in _scripts(item)]
    return []


def _line_of(text: str, command: str) -> int:
    """The line a command was written on, for the finding to name.

    Args:
        text: The file as it is on disk.
        command: One command, as `_commands` split it.

    Returns:
        int: The first line holding the command's first line, or 0 where the shell's
        own splitting left nothing to match — the finding then names the file alone.
    """
    head = command.splitlines()[0].strip()
    for number, line in enumerate(text.splitlines(), 1):
        if head and head in line:
            return number
    return 0


def _named(path: pathlib.Path) -> str:
    """How a finding names a file: its path from the repository root.

    Args:
        path: The file the finding is about.

    Returns:
        str: The path to print.
    """
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def _problems(path: pathlib.Path, recipes: dict[str, str]) -> list[str]:
    """Reads one workflow or composite action for a step typing a tool a recipe wraps.

    Args:
        path: The file to read.
        recipes: Each wrapped tool against the recipe wrapping it, as `_wrapped` read them.

    Returns:
        list[str]: One line per `run:` step invoking a wrapped tool directly, empty where none does.
    """
    text = path.read_text(encoding="utf-8")
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"{_named(path)}: is not readable as YAML — {exc}"]
    problems = []
    for script in _scripts(document):
        for command in _commands(script):
            tool = _invoked(command)
            if tool in recipes:
                where = f"{_named(path)}:{_line_of(text, command) or ''}".rstrip(":")
                problems.append(f"{where} runs {tool} directly, which `just {recipes[tool]}` "
                                "wraps — type the recipe, so the operator surface and CI "
                                "state the same line (solorepo's DR-252, solorepo's DR-275)")
    return problems


@check("operator boundary")
def operator_boundary(justfile: pathlib.Path = JUSTFILE,
                      roots: tuple[pathlib.Path, ...] = (WORKFLOWS, ACTIONS)) -> StepOutcome:
    """No `run:` step runs a tool a root `just` recipe wraps (solorepo's DR-275).

    The recipe is meant to be the one statement of how a check is run, so that the
    operator surface and CI cannot drift apart: a `run:` step naming the tool itself is
    a second statement, and the recipe may gain a flag, an interpreter pin or a
    dependency while CI keeps the old invocation with nothing reporting the divergence.
    The tools are read off the root `justfile` rather than listed here, so a recipe
    added tomorrow brings its own site under the rule.

    Args:
        justfile: The root verb surface to read the wrapped tools from.
        roots: The directories whose YAML files are read for `run:` steps.

    Returns:
        Passed | Found | CouldNotRun: Validation result listing each step that types the
        tool where a recipe wraps it.
    """
    if not justfile.is_file():
        return CouldNotRun("no root justfile to read the recipes from")
    recipes = _wrapped(justfile)
    if not recipes:
        return CouldNotRun("no recipe on the root verb surface wraps a tool under .meta/")
    paths = sorted(path for root in roots for path in root.rglob("*")
                   if path.suffix in (".yml", ".yaml") and path.is_file())
    if not paths:
        return CouldNotRun("no workflow or composite action to scan")
    problems = [problem for path in paths for problem in _problems(path, recipes)]
    if problems:
        return Found(problems)
    return Passed(f"{len(paths)} file{'s' if len(paths) != 1 else ''} against "
                  f"{len(recipes)} wrapped tool{'s' if len(recipes) != 1 else ''}")
