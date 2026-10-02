"""The paths a brownfield target's git index tracks (stereorepo's DR-217).

Adoption planning reads these, where it can, in place of walking the target's
working tree, so untracked and ignored files stay out of the plan.
"""

from __future__ import annotations

import os
import pathlib
import subprocess


def _git(target_dir: pathlib.Path, *args: str) -> str | None:
    """Runs a read-only git command in the target and returns its stdout.

    Every `GIT_*` variable is removed from the environment, because one
    inherited from a hook or the pair loop (`GIT_DIR`, `GIT_INDEX_FILE`,
    `GIT_WORK_TREE`) overrides `-C` and would point the command at another
    repository.

    Returns:
        The command's stdout, or None when git is missing or exits non-zero.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        res = subprocess.run(
            ["git", "-C", str(target_dir), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
    except OSError:
        return None
    return res.stdout if res.returncode == 0 else None


def git_tracked_files(target_dir: pathlib.Path) -> list[str] | None:
    """Lists the paths the target's git index tracks.

    Only `rev-parse` and `ls-files` run, neither of which writes the index,
    so planning stays read-only.

    Returns:
        The tracked relative paths, or None when the target is not the top
        level of a git work tree (a directory nested in another repository
        included) or git cannot list it.
    """
    toplevel = _git(target_dir, "rev-parse", "--show-toplevel")
    if toplevel is None or pathlib.Path(toplevel.strip()).resolve() != target_dir.resolve():
        return None
    listing = _git(target_dir, "ls-files", "-z")
    if listing is None:
        return None
    return [p for p in listing.split("\0") if p]
