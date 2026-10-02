"""What the scaffold owes a portfolio: no scaffold-only path in an inherited file.

History in files.history.md (stereorepo's DR-171).
"""

import pathlib
from collections.abc import Sequence

from checks.collect import META, ROOT, TEMPLATE, CouldNotRun, Found, Passed, StepOutcome, check
from checks.files import sources

SCAFFOLD_ONLY = ("template/", "SPECIALIZE.md", "ADOPT.md", "bootstraps/", "pair/",
                 ".meta/adapt.py", ".meta/lib/adapt/",
                 ".meta/checks/probes/tools/test_brownfield.py")
"""Paths the scaffold has and a portfolio does not, at the top level or below it, such as the
brownfield adoption tool and its probe (stereorepo's DR-305)."""


def scaffold_only_lines(path: pathlib.Path, names: Sequence[str],
                        root: pathlib.Path = ROOT) -> list[str]:
    """One problem per line of `path` naming one of `names`, unless the line names stereorepo.

    Args:
        path: The file to read.
        names: The scaffold-only paths to look for.
        root: What the problem's path is given relative to.

    Returns:
        list[str]: `<path>:<line> names '<name>', which a portfolio does not have`
        for each occurrence.
    """
    problems: list[str] = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if "stereorepo" in line.lower():
            continue
        problems.extend(f"{path.relative_to(root)}:{number} names '{name}', "
                        "which a portfolio does not have" for name in names if name in line)
    return problems


@check("scaffold-only paths")
def scaffold_only_paths() -> StepOutcome:
    """Validate that files copied during Specialization contain no scaffold-only paths.

    Ensures that inherited files do not reference paths unique to the scaffold
    (`template/`, `SPECIALIZE.md`, `bootstraps/`) unless explicitly qualified
    with the scaffold's name (stereorepo's DR-036).

    Returns:
        Passed | Found | CouldNotRun: Validation result listing occurrences of scaffold-only paths.
    """
    problems: list[str] = []
    scanned: set[pathlib.Path] = set()

    def scan(paths: Sequence[pathlib.Path], names: Sequence[str]) -> None:
        for path in paths:
            if path.suffix not in (".md", ".yaml", ".yml") or not path.is_file():
                continue
            scanned.add(path)
            problems.extend(scaffold_only_lines(path, names))

    for token in sources.inherited():
        base = ROOT / token if (ROOT / token).exists() else META / token
        paths = [base] if base.is_file() else sorted(base.rglob("*")) if base.is_dir() else []
        scan(paths, SCAFFOLD_ONLY)
    scan(sorted(TEMPLATE.rglob("*")), tuple(n for n in SCAFFOLD_ONLY if n != "template/"))

    if not scanned:
        return CouldNotRun("no inherited paths or template/ to scan")
    if problems:
        return Found(problems)
    return Passed(f"{len(scanned)} file{'s' if len(scanned) != 1 else ''}")
