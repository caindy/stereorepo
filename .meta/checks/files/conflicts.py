"""Merge conflict markers left in tracked or unignored text by a rebase
that never finished.
"""
import re

from checks.collect import (
    ROOT,
    check,
)
from checks.files import sources

CONFLICT_MARKER = re.compile(r"^(?:<{7}|={7}|>{7})(?:[ \t].*)?$")
"""A line that is one of git's three conflict markers — seven `<`, `=` or `>`,
alone or followed by the ref name git appends to the two diamonds — and
nothing else, so a Setext heading underline or a YAML document separator of a
different width does not match."""


@check("merge conflict markers")
def conflict_markers() -> list[str]:
    """Every tracked or unignored text file is free of git's conflict markers.

    A Python or Rust syntax checker fails on a stray `<<<<<<<`, but Markdown,
    YAML and the defect-history logs parse it as text and carry it to `main`
    silently. Scans the tree as git sees it: tracked files
    and untracked files that git does not ignore (`sources.tree()`). Binary
    files and symlinks are not text a marker could land in and are skipped.

    Returns:
        list[str]: One `path:line: marker` entry per scanned file line that is
        a conflict marker.
    """
    problems = []
    for path in sources.tree():
        if path.is_symlink() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if CONFLICT_MARKER.match(line):
                problems.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    return problems
