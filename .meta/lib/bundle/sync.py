"""Sync a portfolio's managed items from a stereorepo checkout (stereorepo's DR-315).

`plan` works out every change before `apply` makes any, so a refusal leaves
the portfolio as it was. A sync copies the files the checkout's git tracks
under each managed item of its bundle, and removes three kinds of file the
portfolio's git tracks: one a managed directory of the checkout no longer
holds, one under a managed item the checkout's bundle dropped, and one under
`SCAFFOLD_ONLY_PATHS`. It reads the old managed items from the portfolio's own
`.meta/bundle.yaml` before the copy replaces that file. Template items, symlink
items, untracked and ignored files, and every path no bundle manages are left
alone, and so is a path the old bundle managed that the new one lists as a
template or symlink item. Nothing under a portfolio item, such as `stakeholders/`, is
ever removed, even where the old bundle managed it or a later bundle stops managing
a file inside it; the managed files the bundle names inside it are still copied
(stereorepo's DR-317). Nor is a skill render compiled into the managed `.meta/.apm/`
from the portfolio's own `.claude/skills/`, which render would compile back; one
the checkout ships is still copied over it (stereorepo's DR-318). A managed file
with the `block` transformation, such as `.gitignore`, is merged rather than
copied: only stereorepo's block is replaced, or appended where the portfolio's
file has none, and the portfolio's own lines are kept (stereorepo's DR-316). Nothing is committed.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import shutil
import stat
import subprocess

from lib.bundle import (
    BLOCK,
    Bundle,
    BundleError,
    load_bundle,
    merge_block,
    scaffold_only,
    under,
)

BUNDLE = pathlib.PurePosixPath(".meta", "bundle.yaml")
"""Where a repository keeps its bundle manifest, relative to its root."""

GIT_LOCATORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
"""Variables that would point a `git -C` call at another repository, as a hook sets them."""


class SyncRefusedError(BundleError):
    """Raised when a sync would destroy work or cannot tell what to sync."""


@dataclasses.dataclass(frozen=True)
class Changes:
    """What a sync changes in a portfolio.

    Attributes:
        copies: Each destination path paired with the checkout path it is
            copied from, for every file that is added or differs.
        writes: Each `block` destination paired with its merged content, for
            every one whose bytes change.
        added: Destinations the portfolio does not hold yet, sorted.
        updated: Destinations the portfolio holds with other content, sorted.
        removed: Tracked portfolio paths the sync deletes, sorted.
    """

    copies: tuple[tuple[str, str], ...] = ()
    writes: tuple[tuple[str, bytes], ...] = ()
    added: tuple[str, ...] = ()
    updated: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()

    def touched(self) -> set[str]:
        """Every portfolio path the sync writes or deletes."""
        return {*self.added, *self.updated, *self.removed}


def _git(repo: pathlib.Path, *args: str) -> str:
    """Runs git in `repo` and returns its standard output.

    Raises:
        SyncRefusedError: Where git fails, as it does outside a work tree.
    """
    env = {k: v for k, v in os.environ.items() if k not in GIT_LOCATORS}
    res = subprocess.run(["git", "-C", str(repo), *args], check=False,
                         capture_output=True, text=True, env=env)
    if res.returncode != 0:
        reason = f"git {args[0]} failed in {repo}: {res.stderr.strip()}"
        raise SyncRefusedError(reason)
    return res.stdout


def _tracked(repo: pathlib.Path) -> set[str]:
    """The paths git tracks in `repo`, relative to its root."""
    return {path for path in _git(repo, "ls-files", "-z").split("\0") if path}


def _uncommitted(repo: pathlib.Path) -> set[str]:
    """The paths `git status` reports in `repo`, each untracked file listed on its own."""
    paths: set[str] = set()
    entries = iter(_git(repo, "status", "--porcelain", "-z", "--untracked-files=all").split("\0"))
    for entry in entries:
        if not entry:
            continue
        paths.add(entry[3:])
        if entry[0] in "RC":
            paths.add(next(entries, ""))
    return paths


def _own_skills(portfolio: pathlib.Path) -> set[str]:
    """The compiled skills render would write back from the portfolio's `.claude/skills/`.

    Mirrors the last source of `lib.apm_compile.skills.skill_primitives`: each
    directory there holding a `SKILL.md` compiles to `.meta/.apm/skills/<name>/SKILL.md`.
    """
    skills = portfolio / ".claude" / "skills"
    if not skills.is_dir():
        return set()
    return {f".meta/.apm/skills/{skill.name}/SKILL.md" for skill in skills.iterdir()
            if (skill / "SKILL.md").is_file()}


def _same(a: pathlib.Path, b: pathlib.Path) -> bool:
    """Whether two paths hold the same link target, or the same bytes and executable bit."""
    if a.is_symlink() or b.is_symlink():
        return a.is_symlink() and b.is_symlink() and a.readlink() == b.readlink()
    if not b.is_file():
        return False
    executable = stat.S_IXUSR
    return (a.stat().st_mode & executable) == (b.stat().st_mode & executable) and \
        a.read_bytes() == b.read_bytes()


def _copies(bundle: Bundle, tracked: set[str]) -> dict[str, str]:
    """Each destination path a managed item brings, against the checkout path it comes from."""
    copies: dict[str, str] = {}
    for item in bundle.managed_items():
        src_root, dest_root = item.source_path().rstrip("/"), item.dest_path().rstrip("/")
        for path in tracked:
            if not under(path, src_root):
                continue
            dest = dest_root + path[len(src_root):]
            if not (scaffold_only(path) or scaffold_only(dest)):
                copies[dest] = path
    return copies


def _blocks(bundle: Bundle, copies: dict[str, str], source: pathlib.Path,
            portfolio: pathlib.Path) -> dict[str, bytes]:
    """The merged content of each `block` destination whose bytes the merge changes.

    Raises:
        SyncRefusedError: Where the portfolio's file is a symlink, which a write
            would follow, is not a regular file, or its markers are malformed.
    """
    writes: dict[str, bytes] = {}
    for item in bundle.items_with_transformation(BLOCK):
        dest = item.dest_path()
        if dest not in copies:
            continue
        target = portfolio / dest
        if target.is_symlink():
            reason = f"{dest} is a symlink, so merging stereorepo's block would write through it"
            raise SyncRefusedError(reason)
        if target.exists() and not target.is_file():
            reason = f"{dest} is not a regular file, so stereorepo's block cannot be merged into it"
            raise SyncRefusedError(reason)
        current = target.read_text(encoding="utf-8", newline="") if target.is_file() else None
        block = (source / copies[dest]).read_text(encoding="utf-8", newline="")
        try:
            merged = merge_block(current, block)
        except ValueError as exc:
            reason = f"{dest}: {exc}; fix its stereorepo markers and sync again"
            raise SyncRefusedError(reason) from exc
        if merged != current:
            writes[dest] = merged.encode("utf-8")
    return writes


def plan(source: pathlib.Path, portfolio: pathlib.Path) -> Changes:
    """Works out what syncing `portfolio` from the checkout at `source` changes.

    Args:
        source: The root of a stereorepo checkout.
        portfolio: The root of the portfolio to sync.

    Returns:
        Changes: The copies and removals, touching nothing on disk.

    Raises:
        SyncRefusedError: Where `source` has no bundle, either root is not a git
            work tree, `portfolio` is the scaffold (it holds `template/`), or
            the portfolio has uncommitted changes, untracked files included,
            at any path the sync would write or delete, or a `block` file of
            the portfolio is a symlink or has malformed markers.
    """
    if not (source / BUNDLE).is_file():
        reason = f"{source} has no {BUNDLE}, so it is not a stereorepo checkout"
        raise SyncRefusedError(reason)
    if (portfolio / "template").is_dir():
        reason = f"{portfolio} holds template/, so it is the scaffold, not a portfolio"
        raise SyncRefusedError(reason)
    new = load_bundle(bundle_path=source / BUNDLE, repo_root=source)
    old = load_bundle(bundle_path=portfolio / BUNDLE, repo_root=portfolio) \
        if (portfolio / BUNDLE).is_file() else Bundle()

    copies = _copies(new, _tracked(source))
    merged = {item.dest_path() for item in new.items_with_transformation(BLOCK)}
    writes = _blocks(new, copies, source, portfolio)
    differing = {dest: path for dest, path in copies.items()
                 if dest not in merged and not _same(source / path, portfolio / dest)}
    kept = [item.dest_path() for item in
            (*new.template_items(), *new.symlink_items(), *new.portfolio_items())]
    own = _own_skills(portfolio)
    removed = sorted(
        path for path in _tracked(portfolio)
        if path not in copies and path not in own
        and not any(under(path, root) for root in kept)
        and (scaffold_only(path) or new.manages(path) or old.manages(path))
    )
    written = {*differing, *writes}
    present = {dest for dest in written if os.path.lexists(portfolio / dest)}
    changes = Changes(
        copies=tuple(sorted(differing.items())),
        writes=tuple(sorted(writes.items())),
        added=tuple(sorted(written - present)),
        updated=tuple(sorted(present)),
        removed=tuple(removed),
    )
    dirty = sorted(changes.touched() & _uncommitted(portfolio))
    if dirty:
        reason = "uncommitted changes at paths the sync would write or delete: " + ", ".join(dirty)
        raise SyncRefusedError(reason)
    return changes


def _prune(directory: pathlib.Path, root: pathlib.Path) -> None:
    """Removes `directory` and each parent below `root` that is left empty."""
    while directory != root and directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()
        directory = directory.parent


def apply(changes: Changes, source: pathlib.Path, portfolio: pathlib.Path) -> Changes:
    """Makes the changes `plan` worked out, and hands them back to be reported.

    Args:
        changes: What `plan` returned for the same two roots.
        source: The root of the stereorepo checkout.
        portfolio: The root of the portfolio.

    Returns:
        Changes: `changes`, unchanged.
    """
    for dest, path in changes.copies:
        src, target = source / path, portfolio / dest
        if target.is_symlink() or target.is_file():
            target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            target.symlink_to(src.readlink())
        else:
            shutil.copy2(src, target)
    for dest, content in changes.writes:
        target = portfolio / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    for path in changes.removed:
        target = portfolio / path
        if target.is_symlink() or target.is_file():
            target.unlink()
        _prune(target.parent, portfolio)
    return changes
