"""Which Projects a change touches, as the loop gates them before landing (stereorepo's DR-303).

A changed path belongs to the Project whose `name` in
`.meta/assertions/structure.yaml` is a directory holding it, and to the `meta`
Project when no Project's directory holds it, since `meta`'s checks are the
ones that read the whole repository (the board under `issues/` included). A
Project named `.` sits at the repository root and holds every path no deeper
Project holds, except those that stay with `meta`: the board under `issues/`,
everything under `.meta/`, and every path `.meta/bundle.yaml` places, an
adopted product's own `README.md` among them. Each touched Project brings in
every Product built from it, and the selection is every Project those Products
are built from. A break the path mapping cannot see, through a shared tool or
a generated file, lands unchecked: that is the risk the decision accepts.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml

STRUCTURE = Path(".meta/assertions/structure.yaml")
"""Where a repository asserts its Projects and Products, relative to its root."""

BUNDLE = Path(".meta/bundle.yaml")
"""Where a repository lists the paths stereorepo places in it, relative to its root."""

META = "work:project/meta"
"""The Project a path under no Project's directory belongs to."""

ROOT = "."
"""The `name` of a Project at the repository root, once a trailing `/` is dropped."""

HELD = ("issues/", ".meta/")
"""The prefixes that stay with `meta` beside a root Project, whatever the bundle lists."""


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
    held = placed(tree) if ROOT in dirs.values() else frozenset()
    touched = {home(path, dirs, held=held) for path in paths}
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


def placed(tree: Path) -> frozenset[str]:
    """The paths that stay with `meta` beside a root Project: `HELD` and every item of `tree`'s bundle.

    An item of `kind: dir` is a prefix, ending in `/` whether or not the bundle
    writes one; any other item is one path.
    """
    file = tree / BUNDLE
    data = (yaml.safe_load(file.read_text()) if file.is_file() else None) or {}
    items = {
        str(item["path"]).rstrip("/") + "/" if item.get("kind") == "dir" else str(item["path"])
        for item in data.get("items") or []
        if item.get("path")
    }
    return frozenset(HELD) | items


def home(path: str, dirs: dict[str, str], *, held: frozenset[str] = frozenset()) -> str:
    """The Project whose directory holds `path`, the deepest where two do, else `meta`.

    A Project named `ROOT` holds what no other Project holds, except a path
    `held` names, as a prefix ending in `/` or as the path itself, which stays
    with `meta`.
    """
    holders = [i for i, d in dirs.items() if d not in ("", ROOT) and path.startswith(f"{d}/")]
    if holders:
        return max(holders, key=lambda ident: len(dirs[ident]))
    if any(path == h or (h.endswith("/") and path.startswith(h)) for h in held):
        return META
    return next((ident for ident, d in dirs.items() if d == ROOT), META)
