"""The command line of `.meta/render.py`: write, or `--check`.
"""
import os
import pathlib
import sys

from lib.render import META, targets


def write_pages(root: pathlib.Path, pages: dict[str, str]) -> tuple[int, list[str]]:
    """Writes each page whose file under `root` does not already hold it.

    A page already current is not touched, so a file the seat's sandbox denies
    is no obstacle while its content is right. A page whose file cannot be
    read or written is recorded and the rest are still written.

    Args:
        root: The directory every page name is relative to.
        pages: Each page's name and its text, as `targets.rendered` returns them.

    Returns:
        tuple[int, list[str]]: How many files were written, and the names of the
        pages that could not be.
    """
    written, failed = 0, []
    for name, text in pages.items():
        path, want = root / name, text.rstrip("\n") + "\n"
        try:
            if path.is_file() and path.read_text() == want:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(want)
        except OSError:
            failed.append(name)
        else:
            written += 1
    return written, failed


def main() -> None:
    """Runs the mode the arguments name and exits with the render's verdict.

    Every target is rendered: under `--check` compared with what is on disk,
    otherwise written by `write_pages` where it differs. Writing also runs
    `apm_compile.reconcile_root`, which rewrites `CLAUDE.md`, `GEMINI.md`, and
    `.github/copilot-instructions.md` as symlinks to `AGENTS.md` and projects
    the skills into `.agents/skills/`; those paths are in no target, and
    `--check` does not touch them. A file either step could not write is
    listed, relative to the repository root, under `could not write:`, with
    the instruction to render outside the sandbox, and the exit status is 1:
    the seat's sandbox denies writes under `.claude/`.
    `--check` answers with two prefixes, because they are not the same answer
    and neither is the other's repair: `stale:` names pages made current by
    running this program, and `unrendered:` names pages nothing renders, where
    what is wrong is the target or the file. Exit status is 1 when either list
    is non-empty.
    """
    check = "--check" in sys.argv
    snap = targets.snapshot()
    pages = targets.rendered(snap)
    orphans = targets.unrendered(snap)
    if check:
        stale = [name for name, text in pages.items()
                 if not (META / name).exists()
                 or (META / name).read_text() != text.rstrip("\n") + "\n"]
        if stale:
            print("stale: " + ", ".join(stale))
        if orphans:
            print("unrendered: " + ", ".join(orphans))
        if not (stale or orphans):
            print("up to date")
        sys.exit(1 if stale or orphans else 0)
    written, failed = write_pages(META, pages)
    unwritten = [os.path.normpath(pathlib.Path(META.name) / name) for name in failed]
    import apm_compile
    prefix = apm_compile.harness.UNWRITTEN
    unwritten += [action.removeprefix(prefix)
                  for action in apm_compile.reconcile_root(META.parent)
                  if action.startswith(prefix)]
    print(f"wrote {written} files")
    if unwritten:
        print("could not write:")
        for path in unwritten:
            print(f"  {path}")
        print("The developer must run `just render` outside the sandbox to write them.")
        sys.exit(1)
