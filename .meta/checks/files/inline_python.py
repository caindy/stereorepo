"""
The ban on inline Python (stereorepo's DR-348): a shell script or a recipe runs a
dedicated script under `.meta/` or a CLI flag, never an interpreter handed its
code on the command line, on standard input or down a pipe, which is how code
escapes the linters and the type checker this gate runs.

History in files.history.md (stereorepo's DR-171).
"""

import os
import pathlib
import re

from checks.collect import (
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)

INLINE_PYTHON = re.compile(
    r"\b(?:python[0-9.]*|uv\s+run\s+python)\b(?:\s+-[a-zA-Z0-9_.-]+(?:\s+[^\s-]\S*)?)*\s+(-c\b|<<|-\s*<<|-\s*$)|"
    r"\|\s*(?:python[0-9.]*|uv\s+run\s+python)(?:\s+-[a-zA-Z0-9_.-]+(?:\s+[^\s-]\S*)?)*\s*$"
)
"""Matches inline Python invocations executing embedded code from CLI strings, stdin heredocs, or piped interpreters."""


def _is_shell_script(path: pathlib.Path) -> bool:
    """Checks whether a non-symlink file without extension is a shell script."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
        return (first_line.startswith("#!")
                and ("bash" in first_line or "sh" in first_line)
                and "python" not in first_line)
    except OSError:
        return False


def _shell_scripts() -> set[pathlib.Path]:
    """Finds all shell script and recipe files across the repository."""
    scripts: set[pathlib.Path] = set()
    if (ROOT / "justfile").is_file():
        scripts.add(ROOT / "justfile")
    ignored_dir_prefixes = (".", "target", "venv")
    for root, dirs, files in os.walk(ROOT):
        rel_root = pathlib.Path(root).relative_to(ROOT)
        dirs[:] = [
            d for d in dirs
            if not any(d.startswith(prefix) for prefix in ignored_dir_prefixes)
            or (rel_root == pathlib.Path() and d in (".meta", ".github"))
        ]
        for file in files:
            p = pathlib.Path(root) / file
            if p.is_symlink() or not p.is_file():
                continue
            if p.suffix in (".sh", ".bash") or (not p.suffix and _is_shell_script(p)):
                scripts.add(p)
    return scripts


def _logical_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Joins backslash-continued lines into single logical lines while preserving line numbering."""
    logical: list[tuple[int, str]] = []
    current_line = ""
    start_num = 1
    for num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") and not current_line:
            continue
        if not current_line:
            start_num = num
        if stripped.endswith("\\"):
            current_line += line.rstrip()[:-1] + " "
        else:
            current_line += line
            logical.append((start_num, current_line))
            current_line = ""
    if current_line:
        logical.append((start_num, current_line))
    return logical


def _find_inline_python_in_file(path: pathlib.Path) -> list[str]:
    """Scans one file for embedded inline Python invocations, returning problem descriptions."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"{path.relative_to(ROOT)}: could not read — {exc}"]

    problems: list[str] = []
    for number, line in _logical_lines(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if INLINE_PYTHON.search(line):
            problems.append(
                f"{path.relative_to(ROOT)}:{number} contains inline Python: '{stripped}' "
                "— externalize to a dedicated .meta/ script or CLI flag (stereorepo's DR-348)"
            )
    return problems


@check("inline python")
def no_inline_python() -> StepOutcome:
    """Shell scripts contain no embedded inline Python invocations (stereorepo's DR-348).

    Ensures that shell scripts and recipe
    definitions execute dedicated, type-checked Python scripts under `.meta/`
    or existing CLI flags rather than inline Python strings (`python3 -c`,
    stdin heredocs, or piped interpreters) that bypass linters, type checkers,
    and repository gate checks.

    History in files.history.md (stereorepo's DR-171).
    """
    scanned = _shell_scripts()
    if not scanned:
        return CouldNotRun("no shell scripts found to scan")

    problems: list[str] = []
    for path in sorted(scanned):
        problems.extend(_find_inline_python_in_file(path))

    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(scanned)} files scanned, none containing inline Python")
