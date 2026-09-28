"""Markdown links that resolve to nothing, and the fence pattern every prose reader strips first.
"""
import os
import pathlib
import re

from checks.collect import (
    ROOT,
    TEMPLATE,
    check,
)
from checks.files import sources

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


FENCED = re.compile(r"```.*?```|`[^`\n]*`", re.S)


@check("markdown links")
def markdown_links() -> list[str]:
    """Validate that relative Markdown links in documentation resolve to existing files or directories.

    Scans Markdown documentation files outside `template/` and `.git/`, ensuring target paths
    resolve within the git-tracked tree (stereorepo's DR-036).

    Returns:
        list[str]: Validation problem messages for broken relative links.
    """
    problems = []
    files = {os.path.normpath(str(f)) for f in sources.tree()}
    for path in sources.tree():
        if path.suffix != ".md" or path.is_symlink() \
                or TEMPLATE in path.parents or ".git" in path.parts:
            continue
        try:
            text = FENCED.sub("", path.read_text())
        except (UnicodeDecodeError, OSError):
            continue
        for target in LINK.findall(text):
            if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = os.path.normpath(str(path.parent / target))
            if resolved not in files and not pathlib.Path(resolved).is_dir():
                problems.append(f"{path.relative_to(ROOT)}: [{target}] resolves to nothing")
    return problems
