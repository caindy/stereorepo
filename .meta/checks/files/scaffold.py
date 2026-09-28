"""What the scaffold owes a portfolio: no scaffold-only path in an inherited file.

History in files.history.md (stereorepo's DR-171).
"""

import pathlib
from collections.abc import Sequence

from checks.collect import META, ROOT, TEMPLATE, CouldNotRun, Found, Passed, StepOutcome, check
from checks.files import sources

SCAFFOLD_ONLY = ("template/", "SPECIALIZE.md", "bootstraps/", "pair/")
"""Paths the scaffold has and a portfolio does not."""


@check("scaffold-only paths")
def scaffold_only_paths() -> StepOutcome:
    """Validate that files copied during Specialization contain no scaffold-only paths.

    Ensures that inherited files do not reference paths unique to the scaffold
    (`template/`, `SPECIALIZE.md`, `bootstraps/`) unless explicitly qualified
    with the scaffold's name (stereorepo's DR-036, solorepo's DR-115).

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
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if "stereorepo" in line.lower() or "solorepo" in line.lower():
                    continue
                for name in names:
                    if name in line:
                        problems.append(f"{path.relative_to(ROOT)}:{number} names "
                                        f"'{name}', which a portfolio does not have")

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
