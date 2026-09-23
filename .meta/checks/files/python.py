"""The Python under `.meta/`, held to its linters — a ruleset at its floor, no configuration ignore, ruff clean, `mypy --strict` clean, a line limit that ratchets, a docstring on every public item — and the whole worktree held to the interpreter that Python is written for, since a `uvx` invocation is as often a shebang, a recipe or a workflow line as it is a `.py` file (solorepo's DR-177, solorepo's DR-210, solorepo's #540, solorepo's #760).

The line limit runs across two steps rather than one because it arrived over a
tree that had never been held to one, and the debt it found is diffuse: `meta
ruff` runs the declared ruleset flat, and `meta lines` ratchets `E501` alone
against `.meta/checks/lines.baseline.yaml`. That is the Ratchet Discipline's
answer for a checker that cannot be clean at once; a flat step would have had to
land the whole backlog in a single diff, which is how a limit gets adopted and
then quietly exempted. What the tree measured before the limit is in
`.meta/checks/files.history.md`.
"""
import ast
import pathlib
import re
import shutil
import subprocess
import sys
import tokenize
import tomllib
from collections.abc import Sequence
from typing import NamedTuple

from checks.collect import (
    META,
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    against_baseline,
    check,
    recorded_baseline,
)
from checks.files import sources

# `target-version` in `.meta/ruff.toml`, which is the syntax the tree is
# entitled to write: `py313` names Python 3.13.
TARGET_VERSION = re.compile(r"^py(?P<major>\d)(?P<minor>\d+)$")


# What wraps a command word where one is quoted, listed, fenced or tabulated,
# stripped from both ends so that `` `uvx` ``, `(uvx`, `uvx,` and `uvx:` are all
# read as the word `uvx`.
EDGES = "\"'`,[]()<>;:"


# The backslash a shell writes at the end of a wrapped command line. Dropped
# with every word that strips to nothing, a `>` blockquote marker being one, so
# that what the walk reads is the command's own words and no others.
CONTINUATION = "\\"


# The `uv tool run` options that take the following word as their value, read
# off `uv tool run --help` at 0.6.14, the version `.meta/arc/Dockerfile` bakes.
# A word after one of these is that value, not the command `uvx` was asked to
# run.
UVX_VALUED = frozenset({
    "--allow-insecure-host", "--cache-dir", "--color", "--config-file",
    "--config-setting", "-C", "--constraints", "-c", "--default-index",
    "--directory", "--env-file", "--exclude-newer", "--extra-index-url",
    "--find-links", "-f", "--fork-strategy", "--from", "--index",
    "--index-strategy", "--index-url", "-i", "--keyring-provider",
    "--link-mode", "--no-binary-package", "--no-build-isolation-package",
    "--no-build-package", "--overrides", "--prerelease", "--project",
    "--python", "-p", "--refresh-package", "--reinstall-package",
    "--resolution", "--upgrade-package", "-P", "--with", "--with-editable",
    "--with-requirements",
})


# The `uv tool run` options that stand alone, from the same reading. An option
# in neither set is one this walk has not heard of, and is reported rather than
# guessed at: guessing it valueless reads its value as the command, and the
# invocation passes unexamined.
UVX_FLAGS = frozenset({
    "--compile-bytecode", "--help", "-h", "--isolated", "--managed-python",
    "--native-tls", "--no-binary", "--no-build", "--no-build-isolation",
    "--no-cache", "-n", "--no-config", "--no-env-file", "--no-index",
    "--no-managed-python", "--no-progress", "--no-python-downloads",
    "--no-sources", "--offline", "--quiet", "-q", "--refresh", "--reinstall",
    "--upgrade", "-U", "--verbose", "-v", "--version", "-V",
})


# The commands that are a bare interpreter, whose version is therefore whatever
# `uvx` resolved rather than anything the invocation asked for.
INTERPRETERS = frozenset({"python", "python3"})


class Invocation(NamedTuple):
    """One `uvx` invocation this step has something to say about: an interpreter call, or a call whose command could not be read.

    Attributes:
        line: The one-based line the invocation starts on.
        pinned: The version `--python` names, or `None` where it names none.
        unread: `None` where the command word was read and is an interpreter;
            the option that stopped the walk, or the empty string where the
            file ended before any command word, otherwise.
    """

    line: int
    pinned: str | None
    unread: str | None


def declared_interpreter(config: str) -> str | None:
    """The Python version a `.meta/ruff.toml` declares, as `uvx --python` spells it.

    Args:
        config: The contents of `.meta/ruff.toml`.

    Returns:
        str | None: The dotted version, such as `3.13`, or `None` where the file
        declares no `target-version`.

    Raises:
        tomllib.TOMLDecodeError: Where `config` is not TOML. Left to the caller,
            which reports an unparseable configuration file as a defect in the
            tree rather than as a step that could not run.
    """
    data = tomllib.loads(config)
    declared = TARGET_VERSION.match(str(data.get("target-version", "")))
    if declared is None:
        return None
    return f"{declared['major']}.{declared['minor']}"


def _invocation_options(words: Sequence[str], start: int) -> int | None:
    """Where the options begin for a word that starts a `uvx` invocation, and `None` for a word that starts none.

    `uvx`, its long form `uv tool run`, and either qualified by a path are one
    invocation: `.meta/arc/Dockerfile` installs the binary at
    `/usr/local/bin/uvx`, and `tool_command()` builds its command from
    `shutil.which("uvx")`, so a path-qualified spelling is the ordinary runtime
    shape rather than an exotic one.
    """
    command = words[start].rsplit("/", 1)[-1]
    if command == "uvx":
        return start + 1
    if command == "uv" and list(words[start + 1:start + 3]) == ["tool", "run"]:
        return start + 3
    return None


def uvx_interpreter_calls(text: str) -> list[Invocation]:
    """Every `uvx` invocation in `text` that runs a bare interpreter, and every one whose command could not be read.

    Read as one stream of words rather than line by line, so a shebang, a
    workflow `run:`, a `just` recipe, a Markdown fence, a Python argument list
    and a YAML folded scalar are all read by one rule, and a call wrapped across
    two lines is read to its command instead of being dropped at the break. A
    rewrap is otherwise how a call site leaves this scan with nothing saying so,
    and one wrap away is one edit away: `.github/workflows/gate.yml` and
    `.meta/assertions/structure.yaml` each carry the command on a line of about
    140 columns.

    What cannot be read that way is reported rather than passed over. An option
    named in neither `UVX_VALUED` nor `UVX_FLAGS` stops the walk, because
    guessing it valueless would read its value as the command and pass the
    invocation unexamined.

    Args:
        text: The contents of one file.

    Returns:
        list[Invocation]: One entry per interpreter call or unreadable
        invocation, each against the line its `uvx` stands on.
    """
    stream = [(number, stripped)
              for number, line in enumerate(text.splitlines(), start=1)
              for stripped in (word.strip(EDGES) for word in line.split())
              if stripped and stripped != CONTINUATION]
    words = [word for _, word in stream]
    calls: list[Invocation] = []
    for start in range(len(words)):
        options = _invocation_options(words, start)
        if options is None:
            continue
        at = options
        pinned: str | None = None
        unread: str | None = None
        while at < len(words) and words[at].startswith("-"):
            option = words[at]
            if option.startswith("--python="):
                pinned = option.split("=", 1)[1]
                at += 1
            elif option in ("--python", "-p") and at + 1 < len(words):
                pinned = words[at + 1]
                at += 2
            elif option in UVX_VALUED:
                at += 2
            elif option in UVX_FLAGS or "=" in option:
                at += 1
            else:
                unread = option
                break
        number = stream[start][0]
        if unread is not None:
            calls.append(Invocation(number, pinned, unread))
        elif at >= len(words):
            if at > options:
                calls.append(Invocation(number, pinned, ""))
        elif words[at].rsplit("/", 1)[-1] in INTERPRETERS:
            calls.append(Invocation(number, pinned, None))
    return calls


def _declared_version() -> str | StepOutcome:
    """The version `.meta/ruff.toml` declares, or the outcome the step reports in place of one.

    The ways there is no version are separated, because under solorepo's DR-261
    an unrunnable step fails under CI, which makes this string the whole
    diagnostic of a red required check rather than a note beside a green one. A
    missing file is an environment the step cannot run in; a file that is
    present and either unparseable or silent on `target-version` is a defect in
    the tree, which is how `meta_lints` reads the same file below.
    """
    config = META / "ruff.toml"
    if not config.is_file():
        return CouldNotRun(".meta/ruff.toml is missing")
    try:
        declared = config.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return CouldNotRun(f".meta/ruff.toml cannot be read — {error}")
    try:
        version = declared_interpreter(declared)
    except tomllib.TOMLDecodeError as error:
        return Found((f".meta/ruff.toml: does not parse — {error}",))
    if version is None:
        return Found((".meta/ruff.toml: declares no `target-version`, so there is no version "
                      "to hold an invocation to",))
    return version


def _scannable(source: pathlib.Path) -> tuple[str | None, str | None]:
    """The text of `source` for the walk to read, and why it could not be read.

    A file holding a NUL byte is binary, as git decides it, and is neither text
    nor a problem. Anything else that will not decode is a problem and not a
    silence: one such file removes every call site it holds from the scan.
    """
    try:
        raw = source.read_bytes()
    except OSError as error:
        return None, f"cannot be read, so it was not scanned — {error}"
    if b"\0" in raw:
        return None, None
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError as error:
        return None, f"is not UTF-8, so it was not scanned — {error}"


def _call_problem(call: Invocation, where: str, version: str) -> str | None:
    """What is wrong with one invocation, or `None` where nothing is."""
    if call.unread == "":
        return f"{where}: a `uvx` invocation runs past the end of the file, so the command " \
               f"it names cannot be read"
    if call.unread is not None:
        return f"{where}: a `uvx` invocation carries `{call.unread}`, which this step does " \
               f"not know, so the command it names cannot be read"
    if call.pinned is None:
        return f"{where}: `uvx` runs an interpreter it does not pin — add `--python {version}`"
    if call.pinned != version:
        return f"{where}: `uvx` pins Python {call.pinned}, and .meta/ruff.toml declares {version}"
    return None


@check("meta interpreter")
def meta_interpreter() -> StepOutcome:
    """Every invocation that asks `uvx` to run an interpreter names the version `.meta/ruff.toml` declares (solorepo's #760).

    Reads the whole worktree — every file git tracks or does not ignore, so
    `justfile`, `.github/workflows/`, `template/`, `bootstraps/`, Markdown and
    YAML as much as `.py` — because that is where the invocations are. It is the
    one step in this module that is not scoped to `.meta/`.

    `uvx` given no `--python` resolves whatever default the machine has, so the
    tooling runs on an interpreter that need not parse the syntax the tree is
    entitled to write. `threading.Lock | None` is a `TypeError` at import before
    Python 3.13, which kills `.meta/gate` before its first step reports: no step
    name, no verdict, only a traceback from inside the runner.

    The version is stated in each invocation and reconciled here rather than
    derived, because a shebang has no way to read a file.

    The count this step passes with is a report and not an assertion. What keeps
    it a ratchet is that no call site leaves the scan quietly: a wrapped call is
    read across the break, a file that cannot be read or decoded is reported,
    and an option neither `UVX_VALUED` nor `UVX_FLAGS` names stops the walk with
    a line rather than a shrug. A stated count would be the other shape, and it
    cannot be this one: a portfolio inherits this step and its own tree holds a
    different number.
    """
    version = _declared_version()
    if not isinstance(version, str):
        return version
    problems = []
    declared_floor = tuple(int(x) for x in version.split("."))
    if sys.version_info[:2] < declared_floor:
        problems.append(
            f"running interpreter is {sys.version.split()[0]}, which is below "
            f".meta/ruff.toml's declared floor of Python {version} (solorepo's DR-268)"
        )
    calls = 0
    for source in sources.tree():
        if not source.is_file():
            continue
        relative = source.relative_to(ROOT)
        text, unscanned = _scannable(source)
        if unscanned is not None:
            problems.append(f"{relative}: {unscanned}")
        if text is None:
            continue
        for call in uvx_interpreter_calls(text):
            if call.unread is None:
                calls += 1
            problem = _call_problem(call, f"{relative}:{call.line}", version)
            if problem is not None:
                problems.append(problem)
    if problems:
        return Found(tuple(problems))
    return Passed(f"{calls} uvx invocations across the worktree, each pinned to Python {version}")


SELECT_FLOOR = {
    "E4": "E", "E7": "E", "E9": "E", "W": "W", "F": "F", "I": "I", "N": "N",
    "UP": "UP", "B": "B", "BLE": "BLE", "C4": "C", "C90": "C", "DTZ": "DTZ",
    "PLR0912": "PL", "PLR0913": "PL", "PLR0915": "PL", "PLW1510": "PL",
    "RET": "RET", "SIM": "SIM", "TRY003": "TRY", "RUF": "RUF", "PTH": "PTH",
}
"""What `.meta/ruff.toml` must select, each entry against the ruff linter that owns it.

Stated here rather than read from the file it audits, and each entry paired with
its linter rather than left as bare text, for the reasons recorded in
solorepo's DR-263.
"""


WIDEST = "ALL"
"""Ruff's selector for every rule it implements, which reaches every entry of the floor."""


def _reaches(selector: str, rule: str, linter: str) -> bool:
    """Whether one `select` entry selects the rules a floor entry names.

    A ruff selector is a linter's prefix followed by as much of a code as the
    author wrote, and a prefix widens only inside the linter that owns it:
    `TRY` selects `TRY003` because both are tryceratops, while `T` is
    flake8-debugger and selects none of it. Reaching the linter's own prefix is
    what tells the two apart.

    Args:
        selector: One entry of `select` or `extend-select`.
        rule: The floor entry it is read against.
        linter: The prefix of the ruff linter that owns `rule`.

    Returns:
        bool: True where the selector is ruff's widest, or is a prefix of the
        rule that reaches at least the linter's own prefix.
    """
    if selector == WIDEST:
        return True
    return rule.startswith(selector) and selector.startswith(linter)


def unselected(lint: dict[str, object]) -> list[str]:
    """The entries of `SELECT_FLOOR` a `[lint]` table does not reach.

    Args:
        lint: The `[lint]` table of `.meta/ruff.toml`, as `tomllib` read it.

    Returns:
        list[str]: The floor entries no selector under `select` or
        `extend-select` reaches, in the floor's own order.
    """
    selectors: list[str] = []
    for key in ("select", "extend-select"):
        named = lint.get(key)
        if isinstance(named, list):
            selectors += [str(entry) for entry in named]
    return [rule for rule, linter in SELECT_FLOOR.items()
            if not any(_reaches(selector, rule, linter) for selector in selectors)]


def unreasoned(py_files: Sequence[pathlib.Path]) -> tuple[list[str], int]:
    """Every site suppression under `.meta/` that gives no reason, and how many were read.

    Args:
        py_files: The Python sources to read, as `sources.meta_sources` lists them.

    Returns:
        tuple[list[str], int]: One problem per suppression without a `reason:`
        and one per file that will not parse, in path order; and the number of
        suppressions read, reasoned or not.
    """
    from checks import comments
    problems: list[str] = []
    suppressions = 0
    for source in sorted(py_files):
        relative = source.relative_to(ROOT).as_posix()
        try:
            found = comments.python_comments(source.read_text(encoding="utf-8"))
        except (SyntaxError, tokenize.TokenError) as error:
            problems.append(f"{relative}: does not parse — {error}")
            continue
        for comment in found:
            for pattern, what in ((comments.NOQA, "noqa"), (comments.TYPE_IGNORE, "type: ignore")):
                match = pattern.search(f"#{comment.text}")
                if match is None:
                    continue
                suppressions += 1
                if not comments.REASON.search(match.group("rest")):
                    problems.append(f"{relative}:{comment.line}: `{what}` gives no reason")
    return problems, suppressions


@check("meta lints")
def meta_lints() -> StepOutcome:
    """The ruleset is at its floor, nothing is switched off, and a suppression gives a reason.

    What is held here is A2 and solorepo's DR-177. An `ignore` in
    `.meta/ruff.toml` switches a rule off where nobody reads it.
    At a site, a `noqa` or `type: ignore` comment without an explanatory
    `reason:` is a configuration ignore with extra steps. This holds .meta/
    tooling to the same discipline the Python bootstrap enforces on portfolio
    code.

    `select` admits the same evasion: declining to select a rule costs no
    suppression, no `reason:` and no argument, while switching the same rule off
    after selecting it costs all three. `SELECT_FLOOR` is the ruleset this
    repository must select at a minimum, and a `.meta/ruff.toml` whose `select`
    and `extend-select` do not reach every entry of it is a problem this step
    reports (solorepo's DR-263).

    Read from comment tokens, so a suppression quoted in a string or a docstring
    is the text of one rather than one: `comments.py` states every pattern here
    and passes each to a probe as a literal, and a line scan reports both. The
    patterns are `comments.py`'s too, so that the rule a suppression names and
    the reason it gives are read off one parse (solorepo's DR-150).
    """
    config = META / "ruff.toml"
    if not config.is_file():
        return CouldNotRun(".meta/ruff.toml is missing")
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        return Found((f".meta/ruff.toml: does not parse — {error}",))
    problems = []
    lint = data.get("lint", {})
    for key in ("ignore", "extend-ignore"):
        if lint.get(key):
            problems.append(f".meta/ruff.toml: `{key}` switches {len(lint[key])} rules off in configuration")
    missing = unselected(lint)
    if missing:
        problems.append(f".meta/ruff.toml: `select` does not reach {', '.join(missing)}, "
                        "which the floor in checks/files/python.py names")
    py_files = sources.meta_sources()
    unreasoned_problems, suppressions = unreasoned(py_files)
    problems += unreasoned_problems
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{suppressions} suppressions across {len(py_files)} files, each with a reason; "
        f".meta/ruff.toml reaches all {len(SELECT_FLOOR)} entries of the floor "
        "and switches none off"
    )


RUFF = "ruff==0.14.0"


MYPY = "mypy==2.3.1"


TYPES_BASELINE = META / "checks" / "types.baseline.yaml"


LINES_BASELINE = META / "checks" / "lines.baseline.yaml"


FILE_SIZES_BASELINE = META / "checks" / "file_sizes.baseline.yaml"


# How long a module under `.meta/` may run before its body belongs in a package
# of its own: solorepo's DR-217's number, which that decision's last consequence
# holds the remaining scripts to.
MODULE_CEILING = 500


# How long a file in the entry layer may run. Tighter than `MODULE_CEILING`
# because solorepo's DR-217 leaves an entry point its docstring, its re-exports
# and its `__main__` guard and puts the body in `.meta/lib/<script>/`: a file on
# the invocation surface that runs past this is carrying logic the package
# beneath it should hold.
ENTRY_CEILING = 350


# The two directories whose Python is the invocation surface — the paths the
# justfile, the workflows and the Role accounts type. Written as the parent of a
# repository-relative path, which is what `ceiling` reads.
ENTRY_LAYER = (".meta", ".meta/say")


# The line-length rule, named once because two steps divide it between them:
# `meta ruff` passes over it and `meta lines` ratchets it, so the ruleset
# `.meta/ruff.toml` declares is run whole and no rule is switched off.
LINE_LENGTH_RULE = "E501"


# A mypy diagnostic, which is `<path>:<line>: error: <message>  [<rule>]`. Only
# `error` is counted: `note` lines elaborate the error above them and would
# count one diagnostic twice (solorepo's DR-210).
MYPY_ERROR = re.compile(r"^(?P<path>[^\s:][^:]*):(?P<line>\d+):(?:\d+:)? error: (?P<message>.*)$")


# A ruff finding in `concise` output, which is `<path>:<line>:<column>: <rule> <message>`.
RUFF_FINDING = re.compile(
    r"^(?P<path>[^\s:][^:]*):(?P<line>\d+):\d+: (?P<rule>[A-Z]+\d+) (?P<message>.*)$")


def tool_command(name: str, pin: str, args: Sequence[str],
                 deps: Sequence[str] = ()) -> list[str] | None:
    """The command that runs a pinned Python tool, by whichever of three routes this machine has.

    An executable on `PATH` first, because the gate's own `uvx` environment puts
    one there; then the module in this interpreter; then `uvx`, which fetches
    the pin. A portfolio's contributor has one of the three and should not have
    to know which.

    Args:
        name: The executable and module name, which are the same for both tools here.
        pin: The requirement passed to `uvx --from` when falling back to the `uvx`
            route, exact so that a release cannot move a ratcheted count under the
            baseline that recorded it.
        args: The arguments after the tool's own name.
        deps: Further requirements the `uvx` route needs in the environment.

    Returns:
        list[str] | None: The command to run, or `None` where none of the three
        routes is available.
    """
    found = shutil.which(name)
    if found:
        return [found, *args]
    try:
        res = subprocess.run([sys.executable, "-m", name, "--version"],
                             capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return [sys.executable, "-m", name, *args]
    except OSError:
        pass
    uvx = shutil.which("uvx")
    if uvx:
        supplied = [word for dep in deps for word in ("--with", dep)]
        return [uvx, "--from", pin, *supplied, name, *args]
    return None


@check("meta ruff")
def meta_ruff() -> StepOutcome:
    """Ruff check over .meta/, less the line limit `meta lines` ratchets (solorepo's DR-177).

    Runs `ruff check` on the repository staging directory using the ruleset
    `.meta/ruff.toml` declares. A violation fails the gate with the offending
    rule and location.

    `E501` is passed over here and ratcheted by `meta lines` instead. The
    command-line `--ignore` is what carries that split rather than an `ignore`
    in the configuration, which `meta lints` refuses and which would switch the
    rule off for every reader of the file.
    """
    config = META / "ruff.toml"
    if not config.is_file():
        return CouldNotRun(".meta/ruff.toml is missing")
    scripts = [str(p) for p in sources.meta_sources() if p.suffix != ".py"]
    cmd = tool_command("ruff", RUFF, ["check", "--config", str(config),
                                      "--ignore", LINE_LENGTH_RULE, str(META), *scripts])
    if not cmd:
        return CouldNotRun("neither ruff nor uvx is installed")
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if out.returncode == 0:
        return Passed("ruff check passed over .meta/")
    lines = [line.strip() for line in (out.stdout + "\n" + out.stderr).splitlines() if line.strip()]
    return Found(tuple(lines))


def ruff_findings(output: str) -> tuple[dict[str, int], dict[str, list[str]]]:
    """The findings a concise ruff run reported, by repository-relative path.

    Args:
        output: The tool's standard output, in ruff's `concise` format. Paths
            are relative to the directory the run was made from, which is the
            repository root.

    Returns:
        tuple[dict[str, int], dict[str, list[str]]]: How many findings each file
        holds, and the diagnostic lines behind each count, in the order ruff
        reported them.
    """
    counts: dict[str, int] = {}
    sites: dict[str, list[str]] = {}
    for line in output.splitlines():
        match = RUFF_FINDING.match(line.strip())
        if match is None:
            continue
        relative = match.group("path")
        counts[relative] = counts.get(relative, 0) + 1
        sites.setdefault(relative, []).append(
            f"{relative}:{match.group('line')}: {match.group('rule')} {match.group('message')}")
    return counts, sites


@check("meta lines")
def meta_lines() -> StepOutcome:
    """Every file under .meta/ sits at its baseline of lines over the limit (solorepo's DR-177).

    The limit is 100, declared in `.meta/ruff.toml`. `lines.baseline.yaml`
    records how many lines over it each file may still hold, and a file fails on
    either side of its number — over, because the debt grew; under, because a
    baseline nobody lowers has stopped being one. New code is held to the limit
    from the moment it lands, and the backlog drains as files are touched.

    The scope and the configuration are `meta ruff`'s, so the limit is declared
    once; `--select` narrows the run to the one rule that step passes over.
    """
    if not LINES_BASELINE.is_file():
        return CouldNotRun(f"{LINES_BASELINE.relative_to(ROOT).as_posix()} is missing")
    config = META / "ruff.toml"
    if not config.is_file():
        return CouldNotRun(".meta/ruff.toml is missing")
    scripts = [str(p) for p in sources.meta_sources() if p.suffix != ".py"]
    cmd = tool_command("ruff", RUFF, ["check", "--config", str(config),
                                      "--select", LINE_LENGTH_RULE, "--output-format", "concise",
                                      str(META), *scripts])
    if not cmd:
        return CouldNotRun("neither ruff nor uvx is installed")
    out = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(ROOT))
    if out.returncode not in (0, 1):
        return CouldNotRun(f"ruff could not run — {(out.stderr or out.stdout).strip()}")
    counts, sites = ruff_findings(out.stdout)
    problems = against_baseline(counts, sites, recorded_baseline(LINES_BASELINE),
                                "lines over the limit", LINES_BASELINE)
    if problems:
        return Found(tuple(problems))
    return Passed(f"{sum(counts.values())} lines over the limit across {len(counts)} files, "
                  "each file at its baseline")


def ceiling(relative: str) -> int:
    """The line ceiling a Python source under `.meta/` is held to.

    Args:
        relative: The file's repository-relative path, in posix form.

    Returns:
        int: `ENTRY_CEILING` where the file sits directly in a directory of
        `ENTRY_LAYER`, and `MODULE_CEILING` anywhere else under `.meta/`.
    """
    parent = relative.rsplit("/", 1)[0] if "/" in relative else ""
    return ENTRY_CEILING if parent in ENTRY_LAYER else MODULE_CEILING


def line_counts(found: Sequence[pathlib.Path]) -> dict[str, int]:
    """How many lines each source holds, by repository-relative path.

    Args:
        found: The Python sources under `.meta/`, as absolute paths.

    Returns:
        dict[str, int]: One entry per source, in the order it was given.
    """
    return {source.relative_to(ROOT).as_posix(): len(source.read_text(
        encoding="utf-8").splitlines()) for source in found}


def past_ceilings(lengths: dict[str, int]) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Which sources run past the ceiling their path sets, and by how far.

    Args:
        lengths: Repository-relative path to how many lines the file holds.

    Returns:
        tuple[dict[str, int], dict[str, list[str]]]: How many lines past its
        ceiling each file runs, holding only the files that run past one, and
        the detail line behind each count, naming the length and the ceiling.
    """
    counts: dict[str, int] = {}
    sites: dict[str, list[str]] = {}
    for relative, length in lengths.items():
        limit = ceiling(relative)
        if length <= limit:
            continue
        counts[relative] = length - limit
        sites[relative] = [f"{relative}: {length} lines against a ceiling of {limit}"]
    return counts, sites


@check("meta file sizes")
def meta_file_sizes() -> StepOutcome:
    """Every file under .meta/ sits at its baseline of lines past its ceiling (solorepo's DR-217).

    A module may run to `MODULE_CEILING` lines and a file on the invocation
    surface to `ENTRY_CEILING`, past which the body belongs in
    `.meta/lib/<script>/`. `file_sizes.baseline.yaml` records how far past its
    ceiling each file may still run, and a file fails on either side of its
    number — over, because a session appended to a module already too long;
    under, because a baseline nobody lowers has stopped being one. A file the
    baseline does not name may run past no ceiling at all, so a new module
    lands under its ceiling or not at all, and a decomposition ratchets the
    baseline down.

    The scope is `meta lines`'s and `meta types`'s, so what counts as Python
    under `.meta/` is answered in one place.
    """
    if not FILE_SIZES_BASELINE.is_file():
        return CouldNotRun(f"{FILE_SIZES_BASELINE.relative_to(ROOT).as_posix()} is missing")
    lengths = line_counts(sources.meta_sources())
    counts, sites = past_ceilings(lengths)
    problems = against_baseline(counts, sites, recorded_baseline(FILE_SIZES_BASELINE),
                                "lines past its ceiling", FILE_SIZES_BASELINE)
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(lengths)} Python files under .meta/, {len(counts)} past a ceiling "
                  "and each at its baseline")


def mypy_errors(output: str) -> tuple[dict[str, int], dict[str, list[str]]]:
    """The strict-mode type errors a mypy run reported, by repository-relative path.

    Args:
        output: The tool's combined standard output and standard error.

    Returns:
        tuple[dict[str, int], dict[str, list[str]]]: How many errors each file
        holds, and the diagnostic lines behind each count, in the order mypy
        reported them.
    """
    counts: dict[str, int] = {}
    sites: dict[str, list[str]] = {}
    for line in output.splitlines():
        match = MYPY_ERROR.match(line.strip())
        if match is None:
            continue
        relative = match.group("path")
        counts[relative] = counts.get(relative, 0) + 1
        sites.setdefault(relative, []).append(
            f"{relative}:{match.group('line')}: {match.group('message')}")
    return counts, sites


@check("meta types")
def meta_types() -> StepOutcome:
    """`mypy --strict` over .meta/ (solorepo's DR-210, solorepo's #540).

    Product code instantiated from the Python bootstrap's seed is held to
    `mypy --strict` outright, and the tooling under `.meta/` that every
    portfolio inherits is held to the same standard: clean under `mypy --strict`
    with no baseline read.

    The pin is exact on the `uvx` route, matching the gate environment's own
    top-level requirements in `.meta/assertions/structure.yaml` and
    `.github/workflows/gate.yml`.

    The extension-less programs are named on the command line beside the
    directory, because mypy collects `*.py` from a directory and would
    otherwise skip the channel, the gate's own entry point and the arc — the
    programs that read the credential, compose the `Actor:` Trailer and decide
    which verb a Role may type. `--scripts-are-modules` is what lets more than
    one of them be named at once: a file with no suffix is a script, every
    script is the module `__main__`, and two `__main__` modules in one run is a
    duplicate-module error that stops the run before it checks anything.
    """
    config = META / "mypy.ini"
    if not config.is_file():
        return CouldNotRun(".meta/mypy.ini is missing")
    scripts = [str(p) for p in sources.meta_sources() if p.suffix != ".py"]
    cmd = tool_command("mypy", MYPY,
                       ["--config-file", str(config), "--strict",
                        "--ignore-missing-imports", "--scripts-are-modules",
                        str(META), *scripts],
                       deps=("types-pyyaml",))
    if not cmd:
        return CouldNotRun("neither mypy nor uvx is installed")
    out = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(ROOT))
    if out.returncode == 0:
        return Passed("mypy --strict passed over .meta/")
    lines = [line.strip() for line in (out.stdout + "\n" + out.stderr).splitlines() if line.strip()]
    return Found(tuple(lines) or ("mypy failed and reported nothing",))


@check("meta doc")
def meta_doc() -> StepOutcome:
    """Every module and script under .meta/, and every public function, class and method, has a docstring (A2, solorepo's DR-179).

    Extends the Python Bootstrap's missing_docs requirement to the repository's
    own tooling and scripts under .meta/. Holds inherited and scaffolding Python
    to the same literate programming standards enforced on product code.
    """
    problems: list[str] = []
    counted = 0
    modules = 0

    found = sources.meta_sources()
    for source in found:
        modules += 1
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except SyntaxError as error:
            problems.append(f"{source.relative_to(ROOT)}: does not parse — {error}")
            continue
        counted += 1
        if ast.get_docstring(tree) is None:
            problems.append(f"{source.relative_to(ROOT)}: module has no docstring")
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and not node.name.startswith("_")
            ):
                counted += 1
                if ast.get_docstring(node) is None:
                    problems.append(f"{source.relative_to(ROOT)}:{node.lineno}: `{node.name}` has no docstring")
                if isinstance(node, ast.ClassDef):
                    for member in node.body:
                        if (
                            isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and not member.name.startswith("_")
                        ):
                            counted += 1
                            if ast.get_docstring(member) is None:
                                problems.append(
                                    f"{source.relative_to(ROOT)}:{member.lineno}: `{node.name}.{member.name}` has no docstring"
                                )

    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} public items across {modules} files, each with a docstring")
