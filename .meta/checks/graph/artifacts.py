"""What an Artifact owes the record: a path that exists, bidirectional coverage of operational scripts, an Article number that is reserved, and a Decision that names what enacts it.
"""

import fnmatch
import pathlib
from collections.abc import Sequence
from typing import Any

import yaml

from checks.citations import FOREIGN
from checks.collect import META, ROOT, check

# The record itself: naming it under `enacted_in` satisfies the letter of A20 and
# defeats the point, so it does not count. `.meta/work/decisions.yaml` is the
# schema and is a legitimate target, which is why this is a prefix and not a word.
RECORD = (".meta/assertions/decisions/", ".meta/decisions.md")

OPERATIONAL_GLOBS = (
    ".meta/*.py",
    ".meta/lib/**/*.py",
    ".meta/checks/**/*.py",
)


def load_excluded_paths(
    structure_path: pathlib.Path = META / "assertions" / "structure.yaml",
) -> list[str]:
    """Extracts declared path exclusion patterns from structure.yaml.

    Args:
        structure_path: Path to the structure assertion document.

    Returns:
        list[str]: File paths or glob patterns excluded from completeness checks.
    """
    if not structure_path.is_file():
        return []
    data = yaml.safe_load(structure_path.read_text(encoding="utf-8")) or {}
    excluded: list[str] = list(data.get("excluded_paths") or [])
    for proj in data.get("projects") or []:
        excluded.extend(proj.get("excluded_paths") or [])
    return excluded


def is_path_excluded(path_str: str, exclusions: Sequence[str]) -> bool:
    """Evaluates whether a relative path matches any exclusion pattern.

    Args:
        path_str: Repository-relative POSIX path string.
        exclusions: Patterns, directory prefixes, or exact paths to match.

    Returns:
        bool: True if the path matches an exclusion rule, False otherwise.
    """
    norm = path_str.strip()
    if norm.startswith("./"):
        norm = norm[2:]
    for pat in exclusions:
        p = pat.strip()
        if p.startswith("./"):
            p = p[2:]
        if not p:
            continue
        if norm == p:
            return True
        if p.endswith("/") and norm.startswith(p):
            return True
        if fnmatch.fnmatch(norm, p):
            return True
    return False


@check("operational artifacts")
def operational_artifacts(
    index: dict[str, Any],
    structure_path: pathlib.Path = META / "assertions" / "structure.yaml",
    root: pathlib.Path = ROOT,
) -> list[str]:
    """Every operational script and module under .meta/ is asserted as an Artifact or excluded.

    Args:
        index: Collected assertion index mapping identifiers to entity tuples.
        structure_path: Path to structure.yaml containing declarative exclusions.
        root: Repository root path for resolving filesystem files.

    Returns:
        list[str]: Formatting error messages for unasserted operational files.
    """
    asserted = {
        obj["path"]
        for _, (cls, obj, _) in index.items()
        if cls == "Artifact" and "path" in obj
    }
    exclusions = load_excluded_paths(structure_path)

    unasserted: list[str] = []
    for pat in OPERATIONAL_GLOBS:
        for p in root.glob(pat):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if rel in asserted:
                continue
            if is_path_excluded(rel, exclusions):
                continue
            unasserted.append(rel)

    return [
        f"{path}: operational file is neither asserted as an Artifact nor excluded"
        for path in sorted(set(unasserted))
    ]



@check("artifact paths")
def artifact_paths(index: dict[str, Any]) -> list[str]:
    """Every Artifact is a file that exists.

    The reference to an Artifact is resolved by the references check, like any
    other; what no schema can know is whether the path on the far side still
    names something. One check per Artifact rather than one per citation, which
    is the whole reason for making it an entity.
    """
    return [f"{ident}: {obj['path']} does not exist"
            for ident, (cls, obj, _) in sorted(index.items())
            if cls == "Artifact" and not (ROOT / obj["path"]).is_file()]


@check("reserved article numbers")
def reserved_article_numbers(index: dict[str, Any]) -> list[str]:
    """A retired Article's number is never issued again.

    The reservation is the only thing a retirement leaves behind, and it exists
    so that a citation written years ago cannot silently come to mean something
    new. Nothing else defends it: the Charter is hand-numbered, and a hole is an
    absence, which nothing notices on its own.
    """
    charter = yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    holes = charter.get("retired_articles") or []
    retired = {r["number"] for r in holes}
    live = {int(a["id"].rsplit("/", 1)[-1]) for a in charter.get("articles") or []}
    problems = [f"A{n} is retired and issued again; a retired number is reserved forever"
                for n in sorted(retired & live)]
    # The pointer to the account is prose, `stereorepo's DR-085`, since the entry
    # is stereorepo's and the Charter goes to every portfolio (stereorepo's DR-121). A string
    # slot is a slot nothing resolves, so the form is held here and the number
    # by `cited decisions`, which together are what the reference check was.
    problems += [f"A{r['number']}: retired_by is {r.get('retired_by')!r}, and the account "
                 "of a retirement is cited as stereorepo's DR-nnn"
                 for r in holes if not FOREIGN.fullmatch(str(r.get("retired_by", "")))]
    return problems


@check("enacted decisions")
def enacted_decisions(index: dict[str, Any]) -> list[str]:
    """A20. An adopted decision names an Artifact that carries its rule (stereorepo's DR-078).

    Whether the Artifact exists is a reference, resolved with every other. What
    is left here is the arithmetic no schema states: ADOPTED means in force, and
    in force with nowhere to be read from is in force over nobody.

    Naming the record itself would satisfy the letter and defeat the point, so
    it does not count.
    """
    record = {ident for ident, (cls, obj, _) in index.items()
              if cls == "Artifact" and obj["path"].startswith(RECORD)}
    return [f"DR-{ident.rsplit('/', 1)[-1]} is adopted and names no artifact "
            "carrying its rule"
            for ident, (cls, obj, _) in sorted(index.items())
            if cls == "Decision" and obj.get("status") == "ADOPTED"
            and not [a for a in (obj.get("enacted_in") or []) if a not in record]]
