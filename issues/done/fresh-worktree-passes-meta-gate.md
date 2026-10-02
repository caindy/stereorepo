---
difficulty: easy
parent: onboard-fitch-mvp
---

# A fresh worktree of a portfolio passes the meta gate unrendered

In fitch-mvp, the `apm package` and `rendered prose` steps of the `meta` gate
read `.meta/apm.yml`, a render output (`.meta/lib/render/writers.py`) that
`.gitignore` ignores there. A worktree that has never run `just render` fails
both steps ("Not an APM project - no apm.yml found"), whatever the branch
changed. A seat cannot render to fix it: `render.py` writes `.claude/skills/`
first, which the seat's sandbox denies (DR-302), and stops before it writes
`apm.yml`. The seats got past it by copying `apm.yml` from the developer's
checkout, which holds only while the assertions are unchanged.

stereorepo's own worktrees do not hit this: its `.gitignore` lists the bare
pattern `apm.yml`, but `.meta/apm.yml` was force-added and is tracked. A
specialized portfolio is committed with `git add .`
(`.meta/test_specialization.py`, step 7), which honours the ignore, so the
file never reaches the portfolio's history.

## Wanted

A portfolio tracks `.meta/apm.yml` the way stereorepo does, by saying so in
the `.gitignore` the scaffold ships (for example a `!/.meta/apm.yml`
negation after `apm.yml`), so `git add .` in a specialized or adopted
portfolio commits it.

`apm.lock.yaml`, `apm_modules/` and every other `apm.yml` stay ignored.

## Out of scope

- A seat's `just render` stopping at `.claude/skills/`: that is
  `render-in-seat-sandbox`, in the backlog.
- Rendering in the loop when it creates a worktree, or reordering
  `render.py`'s writes.
- Fixing fitch-mvp itself; it picks the change up when it next takes the
  scaffold.

## Done when

- In a specialized portfolio, `git check-ignore .meta/apm.yml` exits 1 (not
  ignored), `git ls-files .meta/apm.yml` lists it after the specialization
  commit, and `git check-ignore` still reports `apm.yml` at the root,
  `apm.lock.yaml` and `apm_modules/` as ignored.
- `.meta/test_specialization.py` gains a step after the commit (step 7) that
  `git clone`s the specialized repository into a new directory and, without
  rendering there, runs `.meta/gate meta` in the clone and requires no `x  `
  step. `rendered prose` alone fails the step when `.meta/apm.yml` is
  missing, so it fails against the current `.gitignore` whether or not
  `apm` is on `PATH`; with `apm` installed, `apm package` passes too.

## The plan

1. **`.gitignore`** (shipped to portfolios as a managed file,
   `.meta/bundle.yaml:81`): add `!/.meta/apm.yml` on the line after
   `apm.yml`, with the reason in the existing comment's style (the meta gate
   reads it, so a fresh checkout must carry it). In stereorepo this changes
   nothing tracked; it only makes the ignore file say what the index already
   does.
2. **Fast probe** in `.meta/checks/probes/tools/test_specialization.py`: a
   `_check_gitignore` helper, called from `test_specialization_probes` and
   listed as point 8 of its docstring. It `git init`s a temporary directory,
   copies the scaffold's `.gitignore` in, and runs `git check-ignore -q` on
   each path: `.meta/apm.yml` must exit 1; `apm.yml`, `apm.lock.yaml` and
   `apm_modules/x` must exit 0. This runs on every meta gate, so a later edit
   to `.gitignore` that drops the exception is caught without the slow
   end-to-end run.
3. **End-to-end step** in `.meta/test_specialization.py`: a
   `step_9_gate_fresh_clone(target_path, verbose)`, appended to the `steps`
   tuple in `execute_specialization_test`. It runs
   `git clone -q <target_path> <clone>` into its own
   `tempfile.TemporaryDirectory(prefix="stereorepo-test-specialization-clone-")`
   (not inside or beside the target, so `--target` and `--keep` behave as
   before and the clone is always removed), then runs `.meta/gate meta` in the clone without
   rendering, and fails on a non-zero exit or any `\nx  ` line, printing the
   output as step 8 does. Factor step 8's run-and-judge body into a helper
   both steps call, so the two judge the gate output identically. Update the
   module docstring's numbered list and the "8 steps" wording in step 8's
   final message and `execute_specialization_test`'s docstring.
   `template/.meta/assertions/structure.yaml` declares `work:project/meta`,
   which `.meta/gate`'s `select` resolves from `meta`.

Order: 2 first, run against the current `.gitignore` to see it fail; then 1
and see it pass; then 3.

### Tests that show it works

- The new probe fails before step 1 and passes after.
- `CI=1 just test-specialization` passes with step 9; with the `.gitignore`
  line reverted locally, step 9 fails on `rendered prose` naming
  `apm.yml`. (Record both outcomes in this file; do not loop on it.)

### Risks

- **Other untracked render outputs.** `rendered prose` compares every page
  `render.py` writes under `.meta/` plus the root symlinks
  (`apm_compile.check_root_symlinks`). If any other such output is ignored
  in a portfolio, step 9 still fails after step 1. That would be a true
  finding of the same defect: add the exception for it here if it is a
  single file, or write a backlog Issue if it is wider.
- **Inspecting a failure.** The clone is removed even when step 9 fails;
  the gate output it prints is the evidence, and the clone can be
  reproduced from a `--keep` target with one `git clone`.
- **Runtime.** Step 9 adds one meta gate run to an already slow test; it
  only runs under `just test-specialization`, not in the ordinary gate.

## What was done

- `.gitignore` carries `!/.meta/apm.yml` after `apm.yml`, with a comment
  saying why.
- `_check_gitignore` in `.meta/checks/probes/tools/test_specialization.py`
  (probe point 8) failed against the old `.gitignore` with ".gitignore
  ignores .meta/apm.yml" and passes now.
- `.meta/test_specialization.py` gains `step_9_gate_fresh_clone`. Steps 8 and
  9 share `_run_gate`, which also prints the gate output on a failed `x  `
  step when not verbose. Before, that path failed without showing which step
  had failed.
- The file-size ratchet would not take the extra lines, so `main()` now
  binds the shared arguments once with `functools.partial`, and steps 5 and 6
  are written more tightly. The file ends 3 lines shorter than it began, and
  its baseline in `.meta/checks/file_sizes.baseline.yaml` drops from 123 to
  120.
- `CI=1 just test-specialization`: all 9 steps pass. With the `.gitignore`
  line removed, step 9 fails with `x  meta/apm package (3)` and
  `x  meta/rendered prose (1)`. No other ignored render output turned up, so
  the first risk in the plan did not happen.

The module docstring's "8-step Specialization Discipline" is the discipline's
own count, not the runner's, so it stays as is; `execute_specialization_test`'s
docstring says it runs those 8 steps and then gates a fresh clone. `bootstraps/python/apm.yml`
is also tracked only because it was force-added, but it lives in stereorepo
and never reaches a portfolio's ignore rules on its own, so it was left alone.
