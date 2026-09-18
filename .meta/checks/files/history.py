"""The history logs under `.meta/`: every entry names a receipt that exists, and no log is orphaned from its module (solorepo's DR-171).
"""
import ast

from collect import (
    META,
    ROOT,
    Found,
    Passed,
    StepOutcome,
    check,
)


def without_comments(text: str) -> str:
    """Text with every `<!-- ... -->` comment removed (solorepo's DR-171)."""
    first, *rest = text.split("<!--")
    return first + "".join(piece.split("-->", 1)[1] for piece in rest if "-->" in piece)


def history_entries_of(text: str) -> list[tuple[str, str | None]]:
    """The (title, receipt) pairs of a history log (solorepo's DR-171)."""
    entries: list[tuple[str, str | None]] = []
    for line in without_comments(text).splitlines():
        if line.startswith("### "):
            entries.append((line[4:].strip(), None))
        elif line.strip().startswith("Receipt:") and entries:
            parts = line.split("`")
            entries[-1] = (entries[-1][0], parts[1].strip() if len(parts) > 1 else None)
    return entries


@check("meta history orphans")  # type: ignore[untyped-decorator]  # reason: flat `collect` import makes this Any; see collect.check
def meta_history_orphans() -> StepOutcome:
    """Every .history.md under .meta/ has a companion module that names it in its docstring (solorepo's DR-171).

    The companion is the file of the same stem beside the log: `<stem>.py`, the
    extension-less program `<stem>`, or the package `<stem>/`, whose docstring
    is in its `__init__.py`.
    """
    problems: list[str] = []
    counted = 0

    for history in sorted(META.rglob("*.history.md")):
        counted += 1
        stem = history.name[:-len(".history.md")]
        candidate_py = history.parent / f"{stem}.py"
        candidate_bin = history.parent / stem
        candidate_pkg = history.parent / stem / "__init__.py"

        companion = next((c for c in (candidate_py, candidate_bin, candidate_pkg) if c.is_file()), None)
        if not companion:
            problems.append(f"{history.relative_to(META)}: no companion {stem}.py, {stem} or {stem}/__init__.py found")
            continue

        try:
            tree = ast.parse(companion.read_text(encoding="utf-8"))
            docstring = ast.get_docstring(tree) or ""
        except SyntaxError as e:
            problems.append(f"{companion.relative_to(META)}: failed to parse for docstring: {e}")
            continue

        if history.name not in docstring:
            problems.append(
                f"{companion.relative_to(META)}: module docstring does not name companion {history.name}"
            )

    if problems:
        return Found(problems)
    return Passed(f"{counted} history files under .meta/, each named by companion module docstring")


def receipt_symbols(tree: ast.Module) -> set[str]:
    """The names a receipt may cite in a parsed module: every top-level function and class, a class's methods as `Class.method`, and the label a decorator such as `@check` gives."""
    symbols: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        symbols.add(node.name)
        if isinstance(node, ast.ClassDef):
            symbols.update(f"{node.name}.{sub.name}" for sub in node.body
                           if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)))
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
                symbols.add(str(dec.args[0].value))
    return symbols


def receipt_problem(receipt: str | None) -> str | None:
    """Why `receipt` names nothing: no receipt, not `<path>::<symbol>`, a file that is not there or does not parse, or a symbol the file does not define; None where it resolves."""
    if not receipt:
        return "names no receipt"
    if "::" not in receipt:
        return f"receipt `{receipt}` does not have <path>::<symbol> format"
    path_str, symbol = receipt.split("::", 1)
    target = (ROOT / path_str).resolve() if (ROOT / path_str).is_file() else (META / path_str).resolve()
    if not target.is_file():
        return f"receipt `{receipt}` file '{path_str}' does not exist"
    try:
        tree = ast.parse(target.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return f"receipt `{receipt}` failed to parse '{path_str}': {e}"
    if symbol not in receipt_symbols(tree):
        return f"names `{receipt}`, which does not exist in {path_str}"
    return None


@check("meta history receipts")  # type: ignore[untyped-decorator]  # reason: flat `collect` import makes this Any; see collect.check
def meta_history_receipts() -> StepOutcome:
    """Every entry in a .meta/ history log names a check or probe that exists (solorepo's DR-171)."""
    problems: list[str] = []
    logs = 0
    entries = 0
    for history in sorted(META.rglob("*.history.md")):
        logs += 1
        for title, receipt in history_entries_of(history.read_text(encoding="utf-8")):
            entries += 1
            problem = receipt_problem(receipt)
            if problem:
                problems.append(f"{history.relative_to(META)}: '{title}' {problem}")
    if problems:
        return Found(problems)
    return Passed(f"{entries} entries across {logs} history logs, each naming a receipt that exists")
