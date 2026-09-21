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
import io
import re
import shutil
import subprocess
import sys
import tokenize
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
    """Represents a gate step that could not execute due to missing prerequisites."""

    why: str


@dataclasses.dataclass(frozen=True)
class Passed:
    """Represents a successfully executed gate step with its verified scope."""

    scope: str


@dataclasses.dataclass(frozen=True)
class Found:
    """Represents a gate step execution that detected one or more defects."""

    problems: tuple[str, ...]


#: What one gate step reports. Three outcomes, never two.
type Outcome = CouldNotRun | Passed | Found

#: A gate step: a label somebody types after `uv run gate`, and what it runs.
type Step = tuple[str, Callable[[Path], Outcome]]


def failed(outcome: Outcome) -> bool:
    """Checks whether an outcome represents a failing gate result.

    Args:
        outcome: Outcome instance to evaluate.

    Returns:
        bool: True if outcome indicates findings that fail the gate, False otherwise.
    """
    return isinstance(outcome, Found)


def rendered(outcome: Outcome, label: str) -> str:
    """Formats an outcome into a standardized gate report line adhering to Article 21.

    Args:
        outcome: Outcome instance to format.
        label: Name of the gate step.

    Returns:
        str: Formatted report line string with trailing newline.

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
    """Finds all member packages declared under the workspace root.

    Args:
        root: Workspace root directory path.

    Returns:
        list[Path]: Sorted list of package root paths excluding the workspace root.
    """
    return sorted(
        path.parent for path in files(root, "pyproject.toml") if path.parent != root
    )


def files(root: Path, suffix: str) -> list[Path]:
    """Finds all non-skipped files under a root matching a suffix or exact name.

    Args:
        root: Root directory path to search.
        suffix: File name suffix starting with a dot, or exact file name.

    Returns:
        list[Path]: Sorted list of matching file paths outside skipped tool directories.
    """
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
    """Formats a path relative to root using forward slashes.

    Args:
        root: Base directory path.
        path: Path to make relative.

    Returns:
        str: POSIX-style relative path string.
    """
    return path.relative_to(root).as_posix()


# --- steps that run a tool ---------------------------------------------------


def tool(cwd: Path, module: str, args: list[str], scope: str) -> Outcome:
    """Executes a Python module as a subprocess tool within the active interpreter.

    Args:
        cwd: Working directory for tool execution.
        module: Python module name to run via `-m`.
        args: Command-line arguments passed to the module.
        scope: Description of the check scope reported on success.

    Returns:
        Outcome: Passed on zero exit, Found on non-zero exit, or CouldNotRun on
            invocation failure.
    """
    argv = [sys.executable, "-m", module, *args]
    try:
        status = subprocess.run(argv, cwd=cwd, check=False)  # noqa: S603  # reason: fixed argv from STEPS, no shell, no input
    except OSError as error:
        return CouldNotRun(f"{module} did not start: {error}")
    if status.returncode == 0:
        return Passed(scope)
    return Found((f"`{module} {' '.join(args)}` exited with {status.returncode}",))


def each_package(root: Path, step: Callable[[Path], Outcome], scope: str) -> Outcome:
    """Executes a step callable across all workspace member packages.

    Args:
        root: Workspace root directory path.
        step: Step function taking a package directory path and returning an Outcome.
        scope: Prefix description for the reported scope on success.

    Returns:
        Outcome: Passed if all packages succeed, or the first non-Passed outcome
            encountered.
    """
    members = packages(root)
    for package in members:
        outcome = step(package)
        if not isinstance(outcome, Passed):
            return outcome
    return Passed(f"{scope} over {len(members)} packages")


def ruff(root: Path) -> Outcome:
    """Runs ruff check across the workspace directory.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome representing ruff linter execution results.
    """
    return tool(root, "ruff", ["check", "."], "ruff check over the workspace")


def types(root: Path) -> Outcome:
    """Runs mypy type checking across member packages in strict mode.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome representing type verification results across packages.
    """

    def one(package: Path) -> Outcome:
        targets = [
            relative(root, package / part)
            for part in ("src", "tests")
            if (package / part).is_dir()
        ]
        return tool(root, "mypy", targets, "")

    return each_package(root, one, "mypy --strict, source and tests,")


def test(root: Path) -> Outcome:
    """Runs pytest across member packages including documentation tests.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome representing test suite execution results.
    """
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
    """Runs mutation testing via mutmut across packages under packages/.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome representing mutation execution and survivor results.
    """
    mutmut = shutil.which("mutmut")
    if mutmut is None:
        return CouldNotRun("mutmut is not installed; `uv sync` installs it")
    problems: list[str] = []
    members = [pkg for pkg in packages(root) if pkg.parent.name == "packages"]
    for package in members:
        run_ = subprocess.run(  # noqa: S603  # reason: mutmut run fixed argv, no shell, no input
            [mutmut, "run"], cwd=package, check=False
        )
        if run_.returncode != 0:
            problems.append(
                f"`mutmut run` in {package.name} exited with {run_.returncode}"
            )
            continue
        results = subprocess.run(  # noqa: S603  # reason: mutmut results fixed argv, no shell, no input
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

NOQA = re.compile(
    r"#\s*noqa(?P<codes>:\s*[A-Z]+[0-9]*(?:\s*,\s*[A-Z]+[0-9]*)*)?(?P<rest>.*)$"
)
TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore(?P<codes>\[[^\]]*\])?(?P<rest>.*)$")
REASON = re.compile(r"#\s*reason:\s*\S")


def lints(root: Path) -> Outcome:
    """Verifies that manifests disable no lint rules and all suppressions state reasons.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome reporting unreasoned suppressions or disabled linter rules.
    """
    problems: list[str] = []
    manifests = files(root, "pyproject.toml")
    for manifest in manifests:
        problems += manifest_ignores(root, manifest)
    sources = files(root, ".py")
    suppression_count = 0
    for source in sources:
        for number, line in enumerate(
            source.read_text(encoding="utf-8").splitlines(), 1
        ):
            for pattern, what in ((NOQA, "noqa"), (TYPE_IGNORE, "type: ignore")):
                match = pattern.search(line)
                if match is None:
                    continue
                suppression_count += 1
                if not REASON.search(match.group("rest")):
                    problems.append(
                        f"{relative(root, source)}:{number}: `{what}` gives no reason"
                    )
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{suppression_count} suppressions across {len(sources)} source files, each "
        f"with a reason; {len(manifests)} manifests, none switching a rule off"
    )


def manifest_ignores(root: Path, manifest: Path) -> list[str]:
    """Inspects a pyproject.toml manifest for disabled lint rules or unreasoned ignores.

    Args:
        root: Workspace root directory path.
        manifest: Path to the pyproject.toml file.

    Returns:
        list[str]: Formatted error messages for each configuration suppression found.
    """
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
    """Checks whether a line number falls within a specified TOML table header block.

    Args:
        text: Full TOML document string.
        number: Target 1-indexed line number.
        table: Table substring to match in bracketed headers.

    Returns:
        bool: True if the line falls under a matching table header, False otherwise.
    """
    header = None
    for current, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("["):
            header = line.strip()
        if current == number:
            return header is not None and table in header
    return False


@dataclasses.dataclass(frozen=True)
class Comment:
    """A comment token in a Python source file.

    Attributes:
        line: 1-based line number where the comment appears.
        text: Comment text with leading `#` and whitespace stripped.
        inline: Whether the comment appears within a function body.
        own: Whether the comment occupies its own line.
    """

    line: int
    text: str
    inline: bool
    own: bool


@dataclasses.dataclass(frozen=True)
class Block:
    """A contiguous group of own-line comments, or a single trailing comment.

    Attributes:
        line: 1-based line number of the first comment in the block.
        text: Combined comment text joined with single spaces.
        inline: Whether the block appears within a function body.
    """

    line: int
    text: str
    inline: bool


DIRECTIVE = re.compile(
    r"^(noqa\b|type:\s*ignore\b|fmt:\s*\w+|pragma:|ruff:|mypy:|isort:|pylint:|pyright:"
    r"|nosec\b|coding[:=]|reason:|prettier-ignore|rustfmt::)"
)
NOTICE = re.compile(r"(copyright|SPDX-License-Identifier|licen[cs]e)", re.IGNORECASE)
CITATION = re.compile(r"(DR-\d{3}|Article\s+\d+|#\d+|RFC\s*\d+|https?://|\[\[[^\]]+\]\])")

STATEMENTS = (
    ast.Assign,
    ast.AugAssign,
    ast.Import,
    ast.ImportFrom,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Return,
    ast.If,
    ast.For,
    ast.While,
    ast.With,
    ast.Try,
    ast.Raise,
    ast.Assert,
    ast.Delete,
    ast.Global,
    ast.Nonlocal,
)


def python_comments(source: str) -> list[Comment]:
    """The `#` comments of a Python source, marked for function body placement.

    Args:
        source: Python source code string.

    Returns:
        list[Comment]: Parsed Comment records with lines, text, and placement.
    """
    spans = [
        (node.body[0].lineno, node.end_lineno)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and node.end_lineno is not None
    ]
    found = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        line = token.start[0]
        found.append(
            Comment(
                line=line,
                text=token.string.lstrip("#").strip(),
                inline=any(start <= line <= end for start, end in spans),
                own=not token.line[: token.start[1]].strip(),
            )
        )
    return found


def blocks(comments: list[Comment]) -> list[Block]:
    """Groups consecutive own-line comments into unified blocks.

    Args:
        comments: List of Comment records in source order.

    Returns:
        list[Block]: List of consolidated Block records.
    """
    grouped: list[list[Comment]] = []
    for comment in comments:
        joins = (
            grouped
            and comment.own
            and grouped[-1][-1].own
            and comment.line == grouped[-1][-1].line + 1
        )
        if joins:
            grouped[-1].append(comment)
        else:
            grouped.append([comment])
    return [
        Block(
            line=run[0].line,
            text=" ".join(c.text for c in run),
            inline=run[0].inline,
        )
        for run in grouped
    ]


def keep_exception(text: str) -> str | None:
    """Identifies which keep-exception a comment satisfies, or None.

    Args:
        text: Comment text to inspect.

    Returns:
        str | None: Exception kind ('directive', 'notice', 'citation') or None.
    """
    if DIRECTIVE.match(text):
        return "directive"
    if NOTICE.search(text):
        return "notice"
    if CITATION.search(text):
        return "citation"
    return None


def python_code(text: str) -> bool:
    """Whether a comment's text is a Python statement rather than prose.

    Args:
        text: Comment text to evaluate.

    Returns:
        bool: True if text parses as executable Python statements, False otherwise.
    """
    body = text.strip()
    if not body or keep_exception(body) == "directive":
        return False
    if body.endswith(":"):
        body += "\n    pass"
    try:
        parsed = ast.parse(body)
    except (SyntaxError, ValueError):
        return False
    if len(parsed.body) != 1:
        return bool(parsed.body)
    node = parsed.body[0]
    if isinstance(node, STATEMENTS):
        return True
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)


def suppressions(source: str) -> list[tuple[int, str]]:
    """The suppressions in a Python source that name no rule, as (line, what) pairs.

    Args:
        source: Python source code string.

    Returns:
        list[tuple[int, str]]: List of (line_number, error_description) tuples.
    """
    found: list[tuple[int, str]] = []
    for comment in python_comments(source):
        for pattern, what in ((NOQA, "noqa"), (TYPE_IGNORE, "type: ignore")):
            match = pattern.search(f"#{comment.text}")
            if match and not match.group("codes"):
                found.append((comment.line, f"bare `{what}` names no rule"))
    return found


def comments(root: Path) -> Outcome:
    """Verifies that source comments follow permissible exceptions.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome reporting comment violations across workspace Python sources.
    """
    problems: list[str] = []
    sources = files(root, ".py")
    counted = 0
    for source in sources:
        relative_path = relative(root, source)
        text = source.read_text(encoding="utf-8")
        try:
            source_comments = python_comments(text)
        except (SyntaxError, tokenize.TokenError) as error:
            problems.append(f"{relative_path}: does not parse — {error}")
            continue
        counted += len(source_comments)
        for comment in source_comments:
            if python_code(comment.text):
                text_prefix = comment.text[:60]
                problems.append(
                    f"{relative_path}:{comment.line}: "
                    f"commented-out code — `{text_prefix}`"
                )
        for number, what in suppressions(text):
            problems.append(f"{relative_path}:{number}: {what}")
        for block in blocks(source_comments):
            if block.inline and keep_exception(block.text) is None:
                text_prefix = block.text[:60]
                problems.append(
                    f"{relative_path}:{block.line}: inline commentary — `{text_prefix}`"
                )
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{counted} comments across {len(sources)} source files, clean of commented "
        "code, bare suppressions, and inline commentary"
    )


def doc(root: Path) -> Outcome:
    """Verifies that all modules and public items have docstrings.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome reporting undocumented public code symbols.
    """
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
    """Yields public top-level functions, classes, and public methods from an AST.

    Args:
        tree: Parsed AST module node.

    Yields:
        tuple[str, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef]:
            Pairs of symbol names and their corresponding AST definition nodes.
    """
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
    """Verifies that every markdown document is referenced by code or manifests.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome reporting unreferenced markdown documentation files.
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


def evidence(root: Path) -> Outcome:
    """Verifies that every history log entry names a test collected by pytest.

    Args:
        root: Workspace root directory path.

    Returns:
        Outcome: Outcome reporting history entries with missing or non-existent tests.
    """
    tests: list[str] = []
    argv = [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header"]
    for package in packages(root):
        try:
            out = subprocess.run(  # noqa: S603  # reason: pytest collect fixed argv, no shell, no input
                argv, cwd=package, capture_output=True, text=True, check=False
            )
        except OSError as error:
            return CouldNotRun(f"pytest did not start: {error}")
        if out.returncode not in (0, 5):
            return CouldNotRun(
                f"pytest --collect-only in {package.name} exited with {out.returncode}"
            )
        tests += [line.strip() for line in out.stdout.splitlines() if "::" in line]
    return evidence_against(root, tests)


@dataclasses.dataclass(frozen=True)
class Entry:
    """Represents an individual entry in a companion history log.

    Attributes:
        title: Problem or defect summary heading.
        evidence: Test symbol in backticks that verifies the resolution.
    """

    title: str
    evidence: str | None


def evidence_against(root: Path, tests: list[str]) -> Outcome:
    """Verifies history log evidence entries against valid test names.

    Args:
        root: Workspace root directory path.
        tests: List of test names collected from pytest.

    Returns:
        Outcome: Outcome reporting invalid or uncollected test evidence references.
    """
    problems: list[str] = []
    logs = 0
    entries = 0
    for package in packages(root):
        for log in files(package, ".history.md"):
            logs += 1
            name = relative(root, log)
            for entry in entries_of(log.read_text(encoding="utf-8")):
                entries += 1
                if entry.evidence is None:
                    problems.append(f"{name}: '{entry.title}' names no evidence")
                elif entry.evidence not in tests:
                    problems.append(
                        f"{name}: '{entry.title}' names `{entry.evidence}`, "
                        "which no test reports"
                    )
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{entries} entries across {logs} history logs, each naming a test that exists"
    )


def entries_of(text: str) -> list[Entry]:
    """Parses history entries from markdown text outside HTML comments.

    Args:
        text: Markdown content from a history log file.

    Returns:
        list[Entry]: Parsed list of Entry records with titles and optional
            evidence citations.

    >>> log = "### Broke\\n\\nEvidence: `tests/test_x.py::test_y`\\n<!-- ### F -->"
    >>> entries_of(log)
    [Entry(title='Broke', evidence='tests/test_x.py::test_y')]
    """
    entries: list[Entry] = []
    for line in without_comments(text).splitlines():
        if line.startswith("### "):
            entries.append(Entry(line[4:].strip(), None))
        elif line.strip().startswith("Evidence:") and entries:
            parts = line.split("`")
            entries[-1] = Entry(entries[-1].title, parts[1] if len(parts) > 1 else None)
    return entries


def without_comments(text: str) -> str:
    """Strips HTML comment blocks from markdown text.

    Args:
        text: Input string potentially containing `<!-- ... -->` comment blocks.

    Returns:
        str: String with all HTML comments stripped.

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
    ("comments", comments),
    ("ruff", ruff),
    ("types", types),
    ("doc", doc),
    ("test", test),
    ("orphans", orphans),
    ("evidence", evidence),
    ("mutants", mutants),
)


def select(wanted: str) -> list[Step]:
    """Selects gate steps matching a command-line request string.

    Args:
        wanted: Step label, or 'gate' to select all configured steps.

    Returns:
        list[Step]: Matching step list, containing at most one step when not 'gate'.

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
    """Executes a list of gate steps and prints formatted outcome reports.

    Args:
        root: Workspace root directory path.
        steps: List of Step tuples to execute.

    Returns:
        int: Exit status code (0 for success, 1 for failures, 2 for empty step list).
    """
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
    """Locates the nearest ancestor directory containing a UV workspace configuration.

    Returns:
        Path: Absolute directory path of the enclosing workspace.

    Raises:
        SystemExit: If no workspace manifest exists in directory ancestors.
    """
    for candidate in Path(__file__).resolve().parents:
        manifest = candidate / "pyproject.toml"
        if manifest.is_file() and "[tool.uv.workspace]" in manifest.read_text(
            encoding="utf-8"
        ):
            return candidate
    msg = "gate: no workspace manifest above this package"
    raise SystemExit(msg)


def main() -> int:
    """CLI entry point for running workspace gate verification steps."""
    wanted = sys.argv[1] if len(sys.argv) > 1 else "gate"
    return run(workspace_root(), select(wanted))
