"""What a composite action's guard and the runner image owe each other: a tool
an action under `.meta/actions/` guards with `type -p` or `command -v` is a tool
`.meta/arc/Dockerfile` installs (solorepo's DR-156).
"""
import pathlib
import re
import shlex

import yaml

from checks.collect import (
    META,
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)

ACTIONS = META / "actions"
"""The directory of composite actions the gate and loop workflows call."""

DOCKERFILE = META / "arc" / "Dockerfile"
"""The single-source runner image this repository's scale set runs on (solorepo's DR-156)."""

GUARD = re.compile(r"(?:type\s+-p|command\s+-v)\s+([A-Za-z0-9_.+-]+)")
"""A step script guarding an installation on the tool already being there: the
two spellings the actions use, capturing the command they look for."""

BIN_DIRS = ("/usr/local/bin", "/usr/bin", "/bin", "/usr/local/sbin", "/usr/sbin")
"""The directories on a runner's `PATH` that an install form puts a command into."""

SEPARATORS = ("&&", "||", "|", ";", ";;")
"""The shell operators a `RUN` chain is one command each side of."""


def _logical_lines(text: str) -> list[str]:
    """A Dockerfile's instructions with backslash continuations joined and comments dropped.

    Args:
        text: The Dockerfile as read off disk.

    Returns:
        list[str]: One entry per instruction, each a single line.
    """
    joined = re.sub(r"\\\n\s*", " ", text)
    return [line.strip() for line in joined.splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def _words(line: str) -> list[str]:
    """One instruction's words, shell-split, or whitespace-split where quoting defeats `shlex`."""
    try:
        return shlex.split(line, comments=True)
    except ValueError:
        return line.split()


def _commands(words: list[str]) -> list[list[str]]:
    """One instruction's words cut into the commands its shell operators separate.

    A `RUN` keyword is dropped so that the first command of a chain reads like
    the rest of it; `COPY` is kept, being a form of its own rather than a shell.
    """
    commands: list[list[str]] = [[]]
    for word in words[1:] if words[:1] == ["RUN"] else words:
        if word in SEPARATORS:
            commands.append([])
        else:
            commands[-1].append(word)
    return [command for command in commands if command]


def _in_bin_dir(path: str) -> bool:
    """Whether a path names a directory on `PATH` or something directly inside one."""
    trimmed = path.rstrip("/")
    return trimmed in BIN_DIRS or any(trimmed.startswith(d + "/") for d in BIN_DIRS)


def _installs(command: list[str]) -> list[str]:
    """The command names one command of a Dockerfile puts on a runner's `PATH`.

    Four forms, which together are every install `.meta/arc/Dockerfile` makes: an
    `apt-get install` package list; a `COPY` whose destination is a `bin`
    directory, which lands each source under its own basename; an `ln -s` whose
    destination is under one, which lands that basename; and a `tar -C` into one,
    which lands the members the operands name.

    Args:
        command: One command's words, the shell operators already cut out.

    Returns:
        list[str]: Every command name this one installs.
    """
    operands = [word for word in command if not word.startswith("-")]
    if len(command) >= 2 and command[0].endswith("apt-get") and command[1] == "install":
        return operands[2:]
    if command[0] == "COPY" and len(operands) >= 3 and _in_bin_dir(operands[-1]):
        return [pathlib.PurePosixPath(source).name for source in operands[1:-1]]
    if command[0] == "ln" and len(operands) >= 3 and _in_bin_dir(operands[-1]):
        return [pathlib.PurePosixPath(operands[-1]).name]
    if command[0] == "tar" and "-C" in command:
        destination = command.index("-C") + 1
        if destination < len(command) and _in_bin_dir(command[destination]):
            return [pathlib.PurePosixPath(member).name
                    for member in command[destination + 1:] if not member.startswith("-")]
    return []


def installed_commands(text: str) -> set[str]:
    """The commands a Dockerfile puts on a runner's `PATH`.

    Reads the closed set of install forms `_installs` names rather than parsing
    the shell. A tool installed by a form outside that set reads as absent, which
    is the direction a drift check should fail in: the answer is to install the
    tool or to teach `_installs` the form, and neither is silent.

    Args:
        text: The Dockerfile as read off disk.

    Returns:
        set[str]: Every command name the file installs.
    """
    commands: set[str] = set()
    for line in _logical_lines(text):
        for command in _commands(_words(line)):
            commands.update(_installs(command))
    return commands


def guarded_tools() -> dict[str, list[str]]:
    """The tools the composite actions guard an installation on.

    Reads the `run:` scripts rather than the file text, so that the prose in an
    action's YAML comments — which is where every other `type -p` under
    `.meta/actions/` appears — is not mistaken for a guard. Shell comments inside
    a script are dropped for the same reason.

    Returns:
        dict[str, list[str]]: Each guarded command, against the sorted
        repository-relative paths of the actions that guard it.
    """
    found: dict[str, set[str]] = {}
    for path in sorted(ACTIONS.rglob("*")):
        if path.suffix not in (".yml", ".yaml") or not path.is_file():
            continue
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        for step in (document.get("runs") or {}).get("steps") or []:
            if not isinstance(step, dict) or not isinstance(step.get("run"), str):
                continue
            script = "\n".join(line for line in step["run"].splitlines()
                               if not line.lstrip().startswith("#"))
            for tool in GUARD.findall(script):
                found.setdefault(tool, set()).add(path.relative_to(ROOT).as_posix())
    return {tool: sorted(paths) for tool, paths in sorted(found.items())}


@check("guarded tools installed")
def guarded_tools_installed() -> StepOutcome:
    """Every tool a composite action guards is a tool the runner image installs.

    A guard is a no-op on the image that carries the tool and an installation on
    the image that does not, so dropping the tool from `.meta/arc/Dockerfile`
    breaks nothing at once and leaves the guard's account of the image wrong
    (solorepo's #916). solorepo's DR-156 names that drift as its own falsifier;
    this step is what makes it fail rather than wait to be read.

    Returns:
        Passed | Found | CouldNotRun: One entry per guarded tool the Dockerfile
        does not install, naming the actions that guard it; `CouldNotRun` where
        no action guards a tool or the Dockerfile is absent, which is a portfolio
        that runs its jobs on hosted runners.
    """
    if not DOCKERFILE.is_file():
        return CouldNotRun(f"no {DOCKERFILE.relative_to(ROOT)} to read")
    guards = guarded_tools()
    if not guards:
        return CouldNotRun("no composite action guards a tool")

    installed = installed_commands(DOCKERFILE.read_text(encoding="utf-8"))
    problems = [f"{DOCKERFILE.relative_to(ROOT)} installs no '{tool}', "
                f"which {', '.join(paths)} guards on"
                for tool, paths in guards.items() if tool not in installed]
    if problems:
        return Found(problems)
    return Passed(f"{len(guards)} guarded tool{'s' if len(guards) != 1 else ''}")
