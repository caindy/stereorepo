"""The gate: every Discipline this Project inherits, as a command that can fail.

`uv run gate` runs every step and `uv run gate <step>` runs one. The steps,
what they hold, and the four Articles they answer to are in `README.md`
beside this package's manifest, which names it as the readme.

Each step is a function from the workspace root to an :data:`Outcome`, and
the pure ones — those that read the tree and run no tool — are the ones a
probe can hand a tree built to fail them.
"""

from __future__ import annotations

import ast
import dataclasses
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path

#: Directories that are tool output, not the tree. Skipped everywhere a step
#: walks: the seed's own gate must not read the virtual environment it runs in,
#: and mutmut writes its mutated copy of the source beside the source.
SKIPPED = frozenset(
    {
        ".venv",
        ".git",
        "__pycache__",
        "mutants",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)


@dataclasses.dataclass(frozen=True)
class CouldNotRun:
    """The step did not run. Loud, unmarked, and not a failure: a missing tool
    is an absence of evidence, and exiting non-zero for it would train the
    reflex of installing nothing and skipping the step."""

    why: str


@dataclasses.dataclass(frozen=True)
class Passed:
    """The step ran and found nothing. Carries what it checked, so the mark is
    a claim about scope and not a bare tick."""

    scope: str


@dataclasses.dataclass(frozen=True)
class Found:
    """The step found something. One line per problem, each naming where."""

    problems: tuple[str, ...]


#: What one gate step reports. Three outcomes, never two.
type Outcome = CouldNotRun | Passed | Found

#: A gate step: a label somebody types after `uv run gate`, and what it runs.
type Step = tuple[str, Callable[[Path], Outcome]]


def failed(outcome: Outcome) -> bool:
    """Whether this outcome fails the gate."""
    return isinstance(outcome, Found)


def rendered(outcome: Outcome, label: str) -> str:
    """The report in the one shape every gate prints (A21): `?` unmarked,
    `ok` with its scope, `x` with a count and one indented line per problem.

    >>> rendered(Passed("3 files"), "step")
    'ok step — 3 files\\n'
    >>> rendered(Found(("a", "b")), "step")
    'x  step (2)\\n     a\\n     b\\n'
    >>> rendered(CouldNotRun("no tool"), "step")
    '?  step: no tool\\n'
    """
    if isinstance(outcome, CouldNotRun):
        return f"?  {label}: {outcome.why}\n"
    if isinstance(outcome, Passed):
        return f"ok {label} — {outcome.scope}\n"
    return f"x  {label} ({len(outcome.problems)})\n" + "".join(
        f"     {problem}\n" for problem in outcome.problems
    )


# --- the tree -------------------------------------------------------------


def packages(root: Path) -> list[Path]:
    """Every workspace member: a directory under the root with a manifest,
    not counting the root's own."""
    return sorted(
        path.parent for path in files(root, "pyproject.toml") if path.parent != root
    )


def files(root: Path, suffix: str) -> list[Path]:
    """Every file under `root` whose name ends in `suffix`, skipping tool
    output. `suffix` is a whole name when it has no leading dot."""
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not (SKIPPED & set(path.relative_to(root).parts))
        and (
            path.name == suffix
            if not suffix.startswith(".")
            else path.name.endswith(suffix)
        )
    )


def relative(root: Path, path: Path) -> str:
    """`path` under `root`, with forward slashes, for a report line."""
    return path.relative_to(root).as_posix()


# --- steps that run a tool ---------------------------------------------------


def tool(cwd: Path, module: str, args: list[str], scope: str) -> Outcome:
    """Runs one tool as `python -m <module>` from the interpreter the gate runs
    under, in `cwd`. Output streams through, so what the tool found is on the
    screen above the line that says it found something."""
    argv = [sys.executable, "-m", module, *args]
    try:
        status = subprocess.run(argv, cwd=cwd, check=False)  # noqa: S603  # reason: fixed argv from STEPS, no shell, no input
    except OSError as error:
        return CouldNotRun(f"{module} did not start: {error}")
    if status.returncode == 0:
        return Passed(scope)
    return Found((f"`{module} {' '.join(args)}` exited with {status.returncode}",))


def each_package(root: Path, step: Callable[[Path], Outcome], scope: str) -> Outcome:
    """Runs a step in every package, stopping at the first that does not pass.
    A workspace member is where its tests, its doctests and its mutants live,
    and the tools that run them read the member's own manifest."""
    members = packages(root)
    for package in members:
        outcome = step(package)
        if not isinstance(outcome, Passed):
            return outcome
    return Passed(f"{scope} over {len(members)} packages")


def ruff(root: Path) -> Outcome:
    """`ruff check`, with the rule set the workspace manifest selects."""
    return tool(root, "ruff", ["check", "."], "ruff check over the workspace")


def types(root: Path) -> Outcome:
    """`mypy --strict` over each package's source and tests, one package at a
    time so two packages' test modules cannot collide by name. Run from the
    root, because mypy reads its configuration from the directory it runs in
    and the workspace manifest holds it."""

    def one(package: Path) -> Outcome:
        targets = [
            relative(root, package / part)
            for part in ("src", "tests")
            if (package / part).is_dir()
        ]
        return tool(root, "mypy", targets, "")

    return each_package(root, one, "mypy --strict, source and tests,")


def test(root: Path) -> Outcome:
    """`pytest`, doctests included: the examples in the prose are executed
    rather than asserted, the package readme's among them. Run in each
    package, whose manifest holds its pytest configuration, so the run is the
    same one mutmut repeats."""
    return each_package(
        root,
        lambda package: tool(
            package,
            "pytest",
            [
                "--doctest-modules",
                "--doctest-glob=README.md",
                "src",
                "tests",
                "README.md",
            ],
            "",
        ),
        "pytest, doctests included,",
    )


def mutants(root: Path) -> Outcome:
    """`mutmut run` in each package under `packages/`, the signal behind the
    tests (A3). A mutant that survives is a line the tests execute without
    checking, and one no test reaches is a line they do not execute; both are
    findings. Could not run when mutmut is not installed, so a missing tool is
    reported and not passed.

    mutmut mutates a package's `src/` into `mutants/` beside it and puts that
    copy first on the path, which is why it runs in the package rather than the
    workspace: it knows `src/`, and nothing else. The gate is not mutated: its
    steps are watched failing by the probes, which is the claim mutation would
    make, and its surface is mostly the text of its reports.

    The run's exit code says nothing about survivors, so `mutmut results` is
    read afterwards: it prints one line per mutant that was not killed."""
    mutmut = shutil.which("mutmut")
    if mutmut is None:
        return CouldNotRun("mutmut is not installed; `uv sync` installs it")
    problems: list[str] = []
    members = [pkg for pkg in packages(root) if pkg.parent.name == "packages"]
    for package in members:
        run_ = subprocess.run(  # noqa: S603  # reason: fixed argv, no shell, no input
            [mutmut, "run"], cwd=package, check=False
        )
        if run_.returncode != 0:
            problems.append(
                f"`mutmut run` in {package.name} exited with {run_.returncode}"
            )
            continue
        results = subprocess.run(  # noqa: S603  # reason: fixed argv, no shell, no input
            [mutmut, "results"],
            cwd=package,
            capture_output=True,
            text=True,
            check=False,
        )
        problems += [
            f"{package.name}: {line.strip()}"
            for line in results.stdout.splitlines()
            if line.strip()
        ]
    if problems:
        return Found(tuple(problems))
    return Passed(f"mutmut over {len(members)} packages, every mutant killed")


# --- pure steps: functions over a path, watched failing by the probes --------

NOQA = re.compile(r"#\s*noqa(?::\s*[A-Z]+[0-9]+(?:\s*,\s*[A-Z]+[0-9]+)*)?(?P<rest>.*)$")
TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore(?:\[[^\]]*\])?(?P<rest>.*)$")
REASON = re.compile(r"#\s*reason:\s*\S")


def lints(root: Path) -> Outcome:
    """No rule is switched off in configuration, and every suppression at a
    site carries a reason (A2).

    An `ignore` in a ruff table is a rule deleted where nobody reads. A
    `per-file-ignores` entry is configuration too, and is allowed only with a
    reason on its line, because the alternative — a `noqa` on every assert in
    every test — is a rule nobody would keep. At a site, a `noqa` and a
    `type: ignore` each carry a `reason:`, or they are a configuration
    ignore with extra steps.
    """
    problems: list[str] = []
    manifests = files(root, "pyproject.toml")
    for manifest in manifests:
        problems += manifest_ignores(root, manifest)
    sources = files(root, ".py")
    suppressions = 0
    for source in sources:
        for number, line in enumerate(
            source.read_text(encoding="utf-8").splitlines(), 1
        ):
            for pattern, what in ((NOQA, "noqa"), (TYPE_IGNORE, "type: ignore")):
                match = pattern.search(line)
                if match is None:
                    continue
                suppressions += 1
                if not REASON.search(match.group("rest")):
                    problems.append(
                        f"{relative(root, source)}:{number}: `{what}` gives no reason"
                    )
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{suppressions} suppressions across {len(sources)} source files, each "
        f"with a reason; {len(manifests)} manifests, none switching a rule off"
    )


def manifest_ignores(root: Path, manifest: Path) -> list[str]:
    """The lines of one manifest that switch a rule off in configuration."""
    text = manifest.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return [f"{relative(root, manifest)}: does not parse — {error}"]
    name = relative(root, manifest)
    lint = data.get("tool", {}).get("ruff", {}).get("lint", {})
    problems = [
        f"{name}: `{key}` switches {len(lint[key])} rules off in configuration"
        for key in ("ignore", "extend-ignore")
        if lint.get(key)
    ]
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if (
            stripped.startswith('"')
            and "= [" in stripped
            and "#" not in stripped
            and in_table(text, number, "per-file-ignores")
        ):
            problems.append(
                f"{name}:{number}: `{stripped}` ignores rules for a path and "
                "gives no reason"
            )
    mypy = data.get("tool", {}).get("mypy", {})
    for override in [mypy, *mypy.get("overrides", [])]:
        for key in ("ignore_errors", "ignore_missing_imports"):
            if override.get(key):
                problems.append(
                    f"{name}: mypy `{key}` switches checking off in configuration"
                )
    return problems


def in_table(text: str, number: int, table: str) -> bool:
    """Whether line `number` of a TOML text sits under a `[…table]` header."""
    header = None
    for current, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("["):
            header = line.strip()
        if current == number:
            return header is not None and table in header
    return False


def doc(root: Path) -> Outcome:
    """Every module, and every public function, class and method, has a
    docstring — the Python `missing_docs`. Tests are not documentation and are
    not held to it; a package's `src/` is."""
    problems: list[str] = []
    counted = 0
    modules = 0
    for package in packages(root):
        for source in (
            files(package / "src", ".py") if (package / "src").is_dir() else []
        ):
            modules += 1
            try:
                tree = ast.parse(source.read_text(encoding="utf-8"))
            except SyntaxError as error:
                problems.append(f"{relative(root, source)}: does not parse — {error}")
                continue
            for name, node in public_items(tree):
                counted += 1
                if ast.get_docstring(node) is None:
                    where = (
                        f"{relative(root, source)}:{node.lineno}"
                        if isinstance(node, ast.AST) and hasattr(node, "lineno")
                        else relative(root, source)
                    )
                    problems.append(f"{where}: `{name}` has no docstring")
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{counted} public items across {modules} modules, each with a docstring"
    )


def public_items(
    tree: ast.Module,
) -> Iterator[
    tuple[str, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef]
]:
    """The module, then every public def and class at the top level and every
    public method of a public class."""
    yield "module", tree
    for node in tree.body:
        if isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ) and not node.name.startswith("_"):
            yield node.name, node
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if isinstance(
                        member, ast.FunctionDef | ast.AsyncFunctionDef
                    ) and not member.name.startswith("_"):
                        yield f"{node.name}.{member.name}", member


def orphans(root: Path) -> Outcome:
    """Every markdown file under a package is named by a source file or the
    manifest in it.

    Python has no `include_str!`, so naming is the consumer: a docstring that
    says which log sits beside the module, or a manifest that names its readme.
    Prose beside code that nothing names is a copy waiting to drift, or a first
    copy nobody reads, which is debris. Either way it is an orphan.
    """
    problems: list[str] = []
    counted = 0
    members = packages(root)
    for package in members:
        naming = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [*files(package, ".py"), *files(package, "pyproject.toml")]
        )
        for markdown in files(package, ".md"):
            counted += 1
            if markdown.name not in naming:
                problems.append(f"{relative(root, markdown)}: named by nothing")
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{counted} markdown files under {len(members)} packages, "
        "each named by a source file"
    )


def receipts(root: Path) -> Outcome:
    """Every entry in a history log names a test that exists.

    An entry's receipt is the test that would fail if the change were undone,
    as pytest names it from the package: `tests/test_x.py::test_y`. That makes
    relevance mechanical: if the test is gone, the entry is stale. The tests
    are read from `pytest --collect-only`, so what is checked is what would
    actually run.
    """
    tests: list[str] = []
    argv = [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header"]
    for package in packages(root):
        try:
            out = subprocess.run(  # noqa: S603  # reason: fixed argv, no shell, no input
                argv, cwd=package, capture_output=True, text=True, check=False
            )
        except OSError as error:
            return CouldNotRun(f"pytest did not start: {error}")
        if out.returncode not in (0, 5):
            return CouldNotRun(
                f"pytest --collect-only in {package.name} exited with {out.returncode}"
            )
        tests += [line.strip() for line in out.stdout.splitlines() if "::" in line]
    return receipts_against(root, tests)


@dataclasses.dataclass(frozen=True)
class Entry:
    """One history entry: its heading, and the test it names, if any."""

    title: str
    receipt: str | None


def receipts_against(root: Path, tests: list[str]) -> Outcome:
    """:func:`receipts`, given the tests. Separated so a probe can hand it a list."""
    problems: list[str] = []
    logs = 0
    entries = 0
    for package in packages(root):
        for log in files(package, ".history.md"):
            logs += 1
            name = relative(root, log)
            for entry in entries_of(log.read_text(encoding="utf-8")):
                entries += 1
                if entry.receipt is None:
                    problems.append(f"{name}: '{entry.title}' names no receipt")
                elif entry.receipt not in tests:
                    problems.append(
                        f"{name}: '{entry.title}' names `{entry.receipt}`, "
                        "which no test reports"
                    )
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{entries} entries across {logs} history logs, each naming a test that exists"
    )


def entries_of(text: str) -> list[Entry]:
    """The entries of a history log. An entry starts at a `###` heading; its
    receipt is a line starting `Receipt:` naming a test in backticks. HTML
    comments are not entries, which is how a log can carry the form of one.

    >>> entries_of("### Broke\\n\\nReceipt: `tests/test_x.py::test_y`\\n<!-- ### F -->")
    [Entry(title='Broke', receipt='tests/test_x.py::test_y')]
    """
    entries: list[Entry] = []
    for line in without_comments(text).splitlines():
        if line.startswith("### "):
            entries.append(Entry(line[4:].strip(), None))
        elif line.strip().startswith("Receipt:") and entries:
            parts = line.split("`")
            entries[-1] = Entry(entries[-1].title, parts[1] if len(parts) > 1 else None)
    return entries


def without_comments(text: str) -> str:
    """The text with every `<!-- … -->` removed. A comment never closed runs to
    the end, as it does in HTML.

    >>> without_comments("a <!-- b --> c <!-- d")
    'a  c '
    """
    first, *rest = text.split("<!--")
    return first + "".join(piece.split("-->", 1)[1] for piece in rest if "-->" in piece)


# --- the gate -----------------------------------------------------------------

#: Every step, in the order the gate runs them. Cheap and pure first, so a
#: manifest or syntax slip is reported before a type check is paid for.
STEPS: tuple[Step, ...] = (
    ("lints", lints),
    ("ruff", ruff),
    ("types", types),
    ("doc", doc),
    ("test", test),
    ("orphans", orphans),
    ("receipts", receipts),
    ("mutants", mutants),
)


def select(wanted: str) -> list[Step]:
    """The steps a word selects: every step for `gate`, the one step with that
    label otherwise, and nothing for a word that is neither. One word selects
    one step at most, so a test that runs the gate with a word can never be
    made to run the whole gate — whose `test` step runs the tests.

    >>> [label for label, _ in select("gate")] == [label for label, _ in STEPS]
    True
    >>> [label for label, _ in select("doc")]
    ['doc']
    >>> select("nothing")
    []
    """
    if wanted == "gate":
        return list(STEPS)
    return [step for step in STEPS if step[0] == wanted][:1]


def run(root: Path, steps: list[Step]) -> int:
    """Runs the steps and reports each. No steps is a usage error, exit 2."""
    if not steps:
        known = " | ".join(label for label, _ in STEPS)
        print(f"usage: uv run gate [gate | {known}]", file=sys.stderr)
        return 2
    exit_code = 0
    for label, step in steps:
        outcome = step(root)
        sys.stdout.write(rendered(outcome, label))
        sys.stdout.flush()
        if failed(outcome):
            exit_code = 1
    return exit_code


def workspace_root() -> Path:
    """The workspace: the nearest ancestor of this file with a manifest that
    declares one."""
    for candidate in Path(__file__).resolve().parents:
        manifest = candidate / "pyproject.toml"
        if manifest.is_file() and "[tool.uv.workspace]" in manifest.read_text(
            encoding="utf-8"
        ):
            return candidate
    msg = "gate: no workspace manifest above this package"
    raise SystemExit(msg)


def main() -> int:
    """`uv run gate [step]`."""
    wanted = sys.argv[1] if len(sys.argv) > 1 else "gate"
    return run(workspace_root(), select(wanted))
