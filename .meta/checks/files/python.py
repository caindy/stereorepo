"""The Python under `.meta/`, held to its linters: no configuration ignore, ruff clean, `mypy --strict` clean, and a docstring on every public item (solorepo's DR-177, solorepo's DR-210, solorepo's #540).
"""
import ast
import re
import shutil
import subprocess
import sys
import tokenize
import tomllib
from collections.abc import Sequence

from checks.collect import (
    META,
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)
from checks.files import sources


@check("meta lints")
def meta_lints() -> StepOutcome:
    """No linter rule is switched off in configuration, and every site suppression carries a reason (A2, solorepo's DR-177).

    An `ignore` in `.meta/ruff.toml` switches a rule off where nobody reads it.
    At a site, a `noqa` or `type: ignore` comment without an explanatory
    `reason:` is a configuration ignore with extra steps. This holds .meta/
    tooling to the same discipline the Python bootstrap enforces on portfolio
    code.

    Read from comment tokens, so a suppression quoted in a string or a docstring
    is the text of one rather than one: `comments.py` states every pattern here
    and passes each to a probe as a literal, and a line scan reports both. The
    patterns are `comments.py`'s too, so that the rule a suppression names and
    the reason it gives are read off one parse (solorepo's DR-150).
    """
    from checks import comments
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
    py_files = sources.meta_sources()
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
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{suppressions} suppressions across {len(py_files)} files, each with a reason; "
        ".meta/ruff.toml switches no rule off"
    )


RUFF = "ruff==0.14.0"


MYPY = "mypy==2.3.1"


TYPES_BASELINE = META / "checks" / "types.baseline.yaml"


# A mypy diagnostic, which is `<path>:<line>: error: <message>  [<rule>]`. Only
# `error` is counted: `note` lines elaborate the error above them and would
# count one diagnostic twice (solorepo's DR-210).
MYPY_ERROR = re.compile(r"^(?P<path>[^\s:][^:]*):(?P<line>\d+):(?:\d+:)? error: (?P<message>.*)$")


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
    """Ruff check over .meta/ against the ruleset declared in .meta/ruff.toml (solorepo's DR-177).

    Runs `ruff check` on the repository staging directory using the configured
    ruleset. A violation fails the gate with the offending rule and location.
    """
    config = META / "ruff.toml"
    if not config.is_file():
        return CouldNotRun(".meta/ruff.toml is missing")
    scripts = [str(p) for p in sources.meta_sources() if p.suffix != ".py"]
    cmd = tool_command("ruff", RUFF, ["check", "--config", str(config), str(META), *scripts])
    if not cmd:
        return CouldNotRun("neither ruff nor uvx is installed")
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if out.returncode == 0:
        return Passed("ruff check passed over .meta/")
    lines = [line.strip() for line in (out.stdout + "\n" + out.stderr).splitlines() if line.strip()]
    return Found(tuple(lines))


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
