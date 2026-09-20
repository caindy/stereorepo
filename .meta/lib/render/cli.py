"""The command line of `.meta/render.py`: write, `--check`, or `--landed <n>`.
"""
import sys

from lib.render import META, decisions, targets


def main() -> None:
    """Runs the mode the arguments name and exits with the render's verdict.

    `--landed <n>` prints what a Challenge got and exits. Otherwise every
    target is rendered: written to disk, or under `--check` compared with what
    is on disk. Writing also runs `apm_compile.reconcile_root`, which rewrites
    `CLAUDE.md` and `GEMINI.md` at the repository root as symlinks to
    `AGENTS.md`; those two paths are in no target, and `--check` does not
    touch them. `--check` answers with two prefixes, because they are not the
    same answer and neither is the other's repair: `stale:` names pages made
    current by running this program, and `unrendered:` names pages nothing
    renders, where what is wrong is the target or the file. `check_pr.py`
    reads the two apart. Exit status is 1 when either list is non-empty.
    """
    if "--landed" in sys.argv:
        print(decisions.landed(sys.argv[sys.argv.index("--landed") + 1]))
        sys.exit(0)
    check = "--check" in sys.argv
    pages = targets.rendered()
    orphans = targets.unrendered()
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
