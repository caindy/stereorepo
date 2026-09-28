"""The command line of `.meta/render.py`: write, or `--check`.
"""
import sys

from lib.render import META, targets


def main() -> None:
    """Runs the mode the arguments name and exits with the render's verdict.

    Every target is rendered: written to disk, or under `--check` compared with what
    is on disk. Writing also runs `apm_compile.reconcile_root`, which rewrites
    `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` as symlinks to
    `AGENTS.md`; those paths are in no target, and `--check` does not
    touch them. `--check` answers with two prefixes, because they are not the
    same answer and neither is the other's repair: `stale:` names pages made
    current by running this program, and `unrendered:` names pages nothing
    renders, where what is wrong is the target or the file. Exit status is 1
    when either list is non-empty.
    """
    check = "--check" in sys.argv
    snap = targets.snapshot()
    pages = targets.rendered(snap)
    orphans = targets.unrendered(snap)
    stale = []
    for name, text in pages.items():
        path, want = META / name, text.rstrip("\n") + "\n"
        if check:
            if not path.exists() or path.read_text() != want:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(want)
    if not check:
        import apm_compile
        apm_compile.reconcile_root(META.parent)
    if check:
        if stale:
            print("stale: " + ", ".join(stale))
        if orphans:
            print("unrendered: " + ", ".join(orphans))
        if not (stale or orphans):
            print("up to date")
        sys.exit(1 if stale or orphans else 0)
    print(f"wrote {len(pages)} files")
