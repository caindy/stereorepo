---
difficulty: easy
---

# Let a seat's `just render` finish in the sandbox

A seat's `just render` stops at its first write to
`.claude/skills/<skill>/SKILL.md`, which the seat's sandbox denies (DR-302).
`.meta/lib/render/cli.py` writes every target unconditionally, in the order
`.meta/lib/render/targets.py` lists them, so the first denied write raises a
`PermissionError` and every page after the skills goes unwritten. This was
reported in `portfolio-steps-without-subject`, `specialized-portfolio-gate`,
`gate-only-touched-projects`, `why-fork-delivery-records` and
`why-fork-inherited-terms`. Each worked around it.

## How to reproduce

In a seat's sandbox, change any Decision Record and run `just render`. It
stops with a traceback at `.claude/skills/wikisplain/SKILL.md`, and the
pages listed after the skills in `targets.py` are left stale. Outside a
sandbox, making one skill file read-only (`chmod a-w`) shows the same.

## Wanted

- Render writes a file only when its content differs from what it would
  write, so an unchanged skill is never touched.
- A write that fails does not stop the render: it carries on with the rest,
  then names every file it could not write, says the developer must render
  them outside the sandbox, and exits non-zero.
- `apm_compile.reconcile_root`, which render runs after writing, follows the
  same two rules. Its root symlinks already stay untouched when they are
  right. The part that does not is `reconcile_harnesses`
  (`.meta/lib/apm_compile/harness.py`). Without the `apm` CLI, it
  `shutil.copytree`s every skill into `.agents/skills/`, rewriting every file.
  It should copy only files whose content differs. A copy that fails is
  reported with the render's other failed writes. The `apm install` branch
  is left as it is. Render today discards what `reconcile_root` returns, and
  `apm_compile`'s own command line (`.meta/lib/apm_compile/cli.py`) also
  calls it and prints its list of action strings. `primitives.py` calls it
  too and discards the result. So a failed copy needs a form that render can
  tell apart from an action, without breaking the command line.

## Out of scope

- Widening the seat's sandbox to allow writes under `.claude/`.
- `.meta/render.py --check`, which already reads without writing.

## Done when

- A test renders into a scratch tree where every target is already current
  and one is read-only: it exits 0 and leaves every file's modification time
  unchanged.
- A test where a read-only target's content must change: every other target
  is written, the output names the read-only one, and the exit status is
  non-zero, with no traceback.
- A test runs `reconcile_harnesses` with `apm` absent (`shutil.which`
  patched to return `None`, so the result does not depend on the machine)
  twice over a scratch tree.
  The second run leaves every file's modification time under
  `.agents/skills/` unchanged. When one file under `.agents/skills/` is
  read-only and its source has changed, the run copies the rest and reports
  that file as a failed write instead of raising.

The tests sit beside the existing tool probes in
`.meta/checks/probes/tools/`. They need a way to point the write loop at a
scratch tree. `cli.py` binds `META` at import time, so patching
`lib.render.META` alone does not reach it. Splitting the write loop into a
function that takes the root and the pages is one way to provide this.

## The plan

The probes in `.meta/checks/probes/tools/` are `@check` functions that return a
list of problems. They are not pytest tests, so the tests below are written in
that form.

1. **`.meta/lib/render/cli.py`.** Move the write branch into
   `write_pages(root: pathlib.Path, pages: dict[str, str]) -> tuple[int, list[str]]`.
   For each target, it compares the wanted text with the file at
   `root / name`. It skips the file when the two match. Otherwise it creates
   the parent directory and writes the file, inside `try`/`except OSError`.
   A failure adds the target's name to the failed list. The function returns
   how many files it wrote and the names it could not write. `main` passes
   `META` and adds the failures that step 2 reports. It prints
   `wrote N files`, counting only the files it changed. If anything failed,
   it prints `could not write:` followed by one path per line, then a line
   saying the developer must run `just render` outside the sandbox, and
   exits 1. Each path is printed relative to the repository root, so
   `../.claude/skills/search/SKILL.md` prints as
   `.claude/skills/search/SKILL.md` and `a.md` as `.meta/a.md`. The `--check`
   branch is not changed. Update `main`'s docstring to match.
2. **`.meta/lib/apm_compile/harness.py`, `reconcile_harnesses`.** Replace
   `shutil.copytree(item, dest, dirs_exist_ok=True)` with a walk of each
   skill directory that copies the same set of files. A file is copied with
   `shutil.copy2` only when the destination is missing or its bytes differ.
   An `OSError` on one file adds
   `ERROR: could not write <path relative to root>` to the actions, and the
   walk carries on. Keep that whole phrase in one module-level constant in
   `harness.py`, such as `UNWRITTEN = "ERROR: could not write "`. Render
   treats an action that starts with the constant as a failure, and strips
   the constant to get the path. It must match the whole phrase, not just
   `ERROR:`. `reconcile_root` already returns
   `ERROR: AGENTS.md is missing from repository root`, and that is not a
   path. The
   `--reconcile` command line in `apm_compile` prints actions as before, so
   it now shows the failure. That command still exits 0; changing that is
   out of scope. `primitives.py` throws the result away, as it does now.
   The `apm install` branch is not changed.
3. **New probe module `.meta/checks/probes/tools/render.py`.** Import it in
   `checks/probes/tools/__init__.py` after `apm_compile`, and add one clause
   to that module's docstring. It holds three steps, each over a
   `tempfile.TemporaryDirectory`:
   - *Current tree.* Write a small `pages` dict such as
     `{"a.md": ..., "../x/SKILL.md": ...}` under `root/meta`, then make one
     file read-only. A second `write_pages` call must return `(0, [])` and
     leave every file's `st_mtime_ns` unchanged.
   - *Stale read-only target.* Change two pages, one of which is read-only.
     The writable one must be rewritten. The failed list must be exactly the
     read-only one's name, and no exception may be raised. Then check the
     same case through `main`, in-process rather than as a subprocess.
     `cli` imports `META` by name, so patching `lib.render.cli.META` to the
     scratch `meta` directory does reach the write loop. Also patch
     `cli.targets.snapshot`, `cli.targets.rendered` (which returns the small
     dict) and `cli.targets.unrendered`, and `apm_compile.reconcile_root`
     (which returns `[]`). `main` runs `import apm_compile` when it is called,
     so patch the attribute on `sys.modules["apm_compile"]` after importing
     the façade the same way. A copy made by `load_module(..., register=False)`
     is not the module `main` sees. Set `sys.argv` to `["render.py"]`. Call `main()`
     under `contextlib.redirect_stdout` and catch `SystemExit`. The exit
     code must be 1, and the output must name the read-only path and the
     line about rendering outside the sandbox. A second case where
     `reconcile_root` returns one `UNWRITTEN` action must list that path as
     well.
   - *Harness copy.* Patch `harness.shutil.which` to return `None` and lay
     out `meta/.apm/skills/s/SKILL.md` under a scratch root. Call
     `reconcile_harnesses` twice. On the second run, make the destination
     file read-only first, then record its `st_ctime_ns`. The run must
     return no `UNWRITTEN` action, and the file's `st_ctime_ns` must not
     change. Then
     change the source of that file and add a second file. The run must
     copy the new file, report the read-only one as an `UNWRITTEN` action, and
     not raise.
4. Run the three probes, then `just render` here, to confirm a real render
   still writes nothing new on a clean tree. Under the seat's sandbox that
   is itself the reproduction.

### Risks

- `copy2` keeps the source's modification time. A destination that is
  rewritten with unchanged content therefore keeps the same `st_mtime`, so
  checking the modification time alone would pass against today's code.
  `st_ino` would pass too, because `copy2` opens the existing file and
  writes into it, so the inode stays the same. The harness probe relies on
  the read-only destination instead, because today's `copytree` raises
  `PermissionError` on it. It also relies on `st_ctime_ns`, which every
  write changes and `copy2` cannot restore.
- Restore write permission (`chmod u+w`) before the temporary directory is
  cleaned up, or the cleanup fails on some platforms.
- Matching on `UNWRITTEN` means relying on the wording of a string. The
  wording lives in one constant that both sides import, and the probe pins
  it, so a dataclass return is not worth breaking the command line for.

## Notes from the implementation

- The plan held. These are the places the code differs from it:
  - The probe patches `lib.render.targets` directly, not through
    `cli.targets`. It is the same module object, but `mypy --strict` refuses
    the attribute that `cli` does not re-export. For the same reason it
    patches `shutil.which` on `shutil`, not through `harness.shutil`.
  - `cli.py` does not cite DR-302. The record names `cli.py` in DR-217, and
    the "enacting citations" check rejects a file that cites a decision that
    does not name it. The probe module cites DR-302 instead.
  - The new probe module is registered as an Artifact in
    `.meta/assertions/structure.yaml`, next to the other tool probes.
  - `.meta/apm_compile.history.md` has an entry for the projection defect
    (DR-171). Render has no history file.
- `wrote N files` now counts only the files that changed. On a clean tree it
  prints `wrote 0 files`. Before this change it printed the number of
  targets.
- Run in this seat's sandbox on a clean tree, `just render` printed
  `wrote 0 files` and exited 0. Before the change it stopped at
  `.claude/skills/wikisplain/SKILL.md`.
- `apm_compile --reconcile` still exits 0 when a copy fails, as the plan
  scoped. It now prints the `ERROR: could not write …` line.
- In `write_pages` and `reconcile_harnesses`, the comparison with what is on
  disk is inside the `try` too. A file the sandbox will not even let the
  seat read is listed as unwritten, instead of ending the run with a
  traceback.
- The probes use `chmod a-w` to stand in for the sandbox. Run as root,
  `chmod` denies nothing, so the read-only cases would fail. No gate here
  runs as root today. A portfolio whose gate runs in a root container would
  need these probes to raise `PermissionError` through a patch instead.
- `just gate meta pair` once failed on two timing tests in
  `pair/test_pair.py`. This branch touches nothing under `pair/`. Both tests
  passed in `just gate pair` alone (all 223 tests) and when run on their own
  three times. They are written up in
  `issues/backlog/pair-seat-tests-flaky-under-load.md`.
