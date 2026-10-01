"""Which Projects a change touches, as the loop gates them before landing (stereorepo's DR-303).

A changed path belongs to the Project whose `name` in
`.meta/assertions/structure.yaml` is a directory holding it, and to the `meta`
Project when no Project's directory holds it, since `meta`'s checks are the
ones that read the whole repository (the board under `issues/` included). Each
touched Project brings in every Product built from it, and the selection is
every Project those Products are built from. A break the path mapping cannot
see, through a shared tool or a generated file, lands unchecked: that is the
risk the decision accepts.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

STRUCTURE = Path(".meta/assertions/structure.yaml")
"""Where a repository asserts its Projects and Products, relative to its root."""

META = "work:project/meta"
"""The Project a path under no Project's directory belongs to."""


def short(ident: str) -> str:
    """The last segment of a CURIE, the name `just gate` takes: `meta` for `work:project/meta`."""
    return ident.rsplit("/", 1)[-1]


def select(tree: Path, paths: Iterable[str]) -> list[str] | None:
    """The Projects to gate for a change to `paths` in `tree`, by the names `just gate` takes.

    Returns `None` for the whole gate, which is `just gate` with no argument,
    in three cases: `tree` asserts no structure, so nothing maps a path to a
    Project; a path falls to a `meta` Project the structure does not declare;
    or the selection is every Project, so the run is the one it always was.
    Returns an empty list when `paths` is empty.
    """
    file = tree / STRUCTURE
    if not file.is_file():
        return None
    data = yaml.safe_load(file.read_text()) or {}
    projects = [p["id"] for p in data.get("projects") or []]
    dirs = {p["id"]: str(p.get("name", "")).rstrip("/") for p in data.get("projects") or []}
    touched = {home(path, dirs) for path in paths}
    if not touched:
        return []
    if not touched <= set(projects):
        return None
    chosen = set(touched)
    for product in data.get("products") or []:
        built = product.get("built_from") or []
        if touched.intersection(built):
            chosen.update(built)
    if set(projects) <= chosen:
        return None
    return [short(ident) for ident in projects if ident in chosen]


def home(path: str, dirs: dict[str, str]) -> str:
    """The Project whose directory holds `path`, the deepest where two do, else `meta`."""
    holders = [ident for ident, d in dirs.items() if d and path.startswith(f"{d}/")]
    return max(holders, key=lambda ident: len(dirs[ident]), default=META)
