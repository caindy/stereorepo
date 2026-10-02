"""Which scaffold-only paths an adoption plan leaves out (stereorepo's DR-305).

The plan copies a bundle directory as a whole, so a scaffold-only path inside
one, such as the adoption tool in `.meta/lib/` and its probe in
`.meta/checks/`, would reach the adopted repository, where it has no subject.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from lib.bundle import SCAFFOLD_ONLY_PATHS

OMIT_REASON = "scaffold-only, which a portfolio does not have, by stereorepo's DR-305"
"""Why a path inside a planned directory is left out of the adoption."""


def scaffold_only_inside(dir_dests: Iterable[str]) -> list[str]:
    """Returns the scaffold-only paths that lie strictly inside one of `dir_dests`.

    Args:
        dir_dests: The destinations of the bundle's `dir` items, without a trailing slash.

    Returns:
        list[str]: Each such path once, in the order of `SCAFFOLD_ONLY_PATHS`.
    """
    dests = tuple(dir_dests)
    return [p for p in SCAFFOLD_ONLY_PATHS if any(p.startswith(f"{d}/") for d in dests)]


def below(path: str, prefixes: Sequence[str]) -> bool:
    """Returns whether `path` is one of `prefixes` or lies below one."""
    return any(path == p or path.startswith(f"{p}/") for p in prefixes)
