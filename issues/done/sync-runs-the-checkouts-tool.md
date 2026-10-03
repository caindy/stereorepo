---
difficulty: medium
---

# Run the checkout's sync, not the portfolio's copy of it

`just sync <checkout>` runs `.meta/bundle.py sync <checkout>`, which is the
portfolio's own copy of the sync (`_cmd_sync` in `.meta/bundle.py`, with the
logic in `.meta/lib/bundle/`), and that copy replaces itself from the
checkout as it runs. A change to the sync therefore takes effect one sync
late: the first sync after it runs the old code. In fitch-mvp, the first sync
after `sync-keeps-a-portfolios-compiled-skills` landed still removed the
portfolio's two compiled skills from `.meta/.apm/skills/`, and only the
second sync kept them.

## How to reproduce

Change what the sync keeps or removes in a stereorepo checkout, then run
`just sync <checkout>` in a portfolio synced from before the change: the
portfolio's `.meta/lib/bundle/` is updated, but the plan applied was the old
code's. A second `just sync` applies the new behaviour.

## Wanted

`just sync <checkout>` runs the sync logic the checkout holds, so that a
fix to the sync applies on the first sync after it lands. Whether the recipe
calls the checkout's `bundle.py` with `--root .`, or the portfolio's
`_cmd_sync` hands the work to the checkout's `bundle.py` (for example by
running it with `--root` set to the portfolio), is the implementer's choice.
Recipes still take only flags, subcommands and atomic identifiers (DR-259,
DR-272), and `just sync <checkout>` keeps its form.

## Out of scope

- What a sync copies, removes or merges.
- `ADOPT.md` step 4: its note explains why the first copy into a repository
  that has no `sync` recipe yet must call the checkout's `bundle.py`
  directly, and that stays true.
- The first sync of a portfolio after this Issue lands. That sync still
  runs the portfolio's old recipe and old `bundle.py`, so it is one sync late
  itself; only syncs after it run the checkout's logic.

## Done when

- A probe beside `.meta/checks/probes/tools/sync.py`, over a temporary
  portfolio and a temporary checkout whose sync logic differs from the
  portfolio's copy (for example, it writes a marker file the portfolio's copy
  does not): one sync, started the way `just sync` starts it, applies the
  checkout's logic.
- A sync from a checkout that cannot run (no `.meta/bundle.py`) refuses with
  a message and changes nothing, as a refused sync does today.
- The checkout's sync, once started, runs its own logic in place and does not
  hand off again: a sync whose checkout is the repository running it (a
  stereorepo checkout synced from itself, or the checkout's `bundle.py` run
  with `--root`) finishes in one process rather than looping.
- The existing probes in `.meta/checks/probes/tools/sync.py` still pass, and
  none is dropped. They test the sync logic itself, so they call it in place
  (`_sync_in_place`) and do not go through the hand-off. A runnable
  `bundle.py` in their scratch checkout would be copied into the portfolio and
  change what they expect.

## Pair notes

> **primary, backlog turn 1**
>
> I made one addition to the Issue and left `difficulty: medium` as it was. The Issue was already precise: it says what is wanted, what is out of scope, and how to tell it is done, and I checked its claims against the code. The `sync` recipe in `justfile` (lines 36–37) runs the portfolio's own `.meta/bundle.py sync`. `_cmd_sync` then runs the plan in that same process, using the portfolio's copy of `.meta/lib/bundle/`.
>
> I added two items under "Done when":
>
> - **No endless hand-off.** If the portfolio's sync passes the work to the checkout's `bundle.py`, the checkout's sync would see a checkout and try to pass it on again, forever. The checkout's sync must run its own logic and finish in one process. That includes a stereorepo checkout synced from itself, and the checkout's `bundle.py` run directly with `--root`.
> - **Existing tests still pass.** The current tests in `.meta/checks/probes/tools/sync.py` call `bundle.py` in-process against scratch checkouts. If the sync starts calling the checkout's `bundle.py`, any scratch checkout that lacks a runnable one gets one, so no check is dropped.

> **secondary, backlog turn 2**
>
> I made no changes. The Issue is precise enough to plan, and `difficulty: medium` is right for it.
>
> I checked its claims against the code and they hold:
>
> - **The recipe:** the `sync` recipe in `justfile` (lines 36–37) runs the portfolio's own `.meta/bundle.py sync`.
> - **The sync itself:** `_cmd_sync` in `.meta/bundle.py` already accepts `--root` to name the portfolio, so either fix the Issue allows is open to the implementer.
> - **The probes:** the existing tests in `.meta/checks/probes/tools/sync.py` load `bundle.py` and run it in the same process. That is why my partner's added item matters: if the sync starts calling the checkout's `bundle.py`, any scratch checkout without a runnable one has to gain one, so no check is dropped.
>
> My partner's other addition, that the checkout's sync must finish in one process and not pass the work on again forever, covers the one real risk in the hand-off approach.

## The plan

The hand-off goes in `.meta/bundle.py`, not in the recipe. The `sync` recipe in
`justfile` stays `.meta/bundle.py sync {{args}}`, so `just sync <checkout>`
keeps its form and no recipe gains a path built from an argument.

1. **Split `_cmd_sync`.** Move its present body, which plans, applies and
   prints, into `_sync_in_place(source, portfolio) -> int` without changing
   it. `_cmd_sync` resolves `source` and `portfolio` as it does today and
   then decides who runs the sync.
2. **The hand-off seam.** Add `_checkout_tool(source) -> pathlib.Path | None`.
   It returns `source/.meta/bundle.py`, resolved, or None when that resolves to
   this file (`pathlib.Path(__file__).resolve()`). The path check is the
   guard against an endless hand-off. The checkout's `bundle.py`, started by
   the hand-off, finds its own file at `source/.meta/bundle.py` and runs in
   place. So does a stereorepo checkout synced from itself, and the checkout's
   `bundle.py` run directly with `--root`. No flag or environment variable is
   needed, and a checkout older than this change, which has no hand-off,
   still runs in place when the portfolio hands off to it.
3. **`_cmd_sync`.** If `source/.meta/bundle.py` is not a file, print
   `sync: refused, nothing changed: <source> has no .meta/bundle.py to run its
   sync` to stderr and return 1. If `_checkout_tool` returns None, return
   `_sync_in_place(...)`. Otherwise return the exit code of
   `subprocess.run([sys.executable, tool, "--root", portfolio, "sync", source],
   check=False)`, with stdout and stderr inherited.
   `sys.executable` already has pyyaml, because `bundle.py` re-runs itself
   under uvx when it does not. Running the checkout's file with this
   interpreter therefore needs no exec bit, no shebang and no second uvx
   start.
4. **Probes** in `.meta/checks/probes/tools/sync.py`:
   - `_run` calls `cli._sync_in_place(source.resolve(), portfolio.resolve())`
     instead of `cli.main([...])`. The existing checks test the sync logic,
     and their scratch checkout has no `bundle.py`, which would now refuse.
     Every existing check is kept. This replaces the Done-when item's
     "they gain one": a copy of the real `bundle.py` and `lib/bundle/` in the
     scratch checkout would be copied in turn through its managed
     `.meta/lib/` and change what those checks expect.
   - New `_check_handoff(cli, tmp)`, called from `bundle_sync_probes`, runs
     three cases through `cli.main(["--root", portfolio, "sync", checkout])`,
     the way `just sync` starts the sync:
     (a) A scratch checkout, made with `_repo`, whose `.meta/bundle.py` is a
     stub that writes `handed-off.txt` into its `--root` and exits 0. After
     one sync the exit code is 0 and the marker exists, so the checkout's
     logic ran. The portfolio's logic did not run: its tracked files are as
     they were apart from the marker.
     The stub checkout needs no `.meta/bundle.yaml`, since the portfolio's
     `bundle.py` never reads it.
     (b) The shared `source` checkout, which has `.meta/bundle.yaml` but no
     `.meta/bundle.py`. The sync exits non-zero, its stderr names the missing
     `.meta/bundle.py`, and `_snapshot` of the portfolio is unchanged.
     (c) `cli._checkout_tool(META.parent)` is None. This is the guard for a
     self-sync and for the started checkout, tested without syncing the
     real repository.
   - Extend the `bundle_sync_probes` docstring with the hand-off, and correct
     `_run`'s docstring, which now names `_sync_in_place`, not
     `bundle.py --root PORTFOLIO sync SOURCE`.
   - The refusal case "a source with no .meta/bundle.yaml" still goes
     through `_run`, so `sync.plan` keeps its own refusal under test.
5. **Record the decision.** Write
   `.meta/assertions/decisions/DR-nnn.yaml`, numbered from the highest
   existing record plus one: the portfolio's `bundle.py sync` runs the
   checkout's `bundle.py` with `--root` set to the portfolio, and a sync
   whose checkout's tool is the running file runs in place. Name DR-315 as
   the decision it refines, then re-render.

**Risks.**

- The child's stdout bypasses `contextlib.redirect_stdout` in the probe, so
  probe (a) checks only the exit code and the marker, never the printed
  output. The stub uses only the standard library, so `sys.executable` can
  run it whether or not the probe runs under uvx.
- A checkout whose `bundle.py` fails before syncing, for example on an
  import error, makes the portfolio's sync fail with the checkout's
  traceback and exit code. That is the intended behaviour, since the
  checkout's logic is the logic wanted.
- A portfolio's `.meta/` imports nothing from the child, so a checkout's
  `lib/bundle/` can change its API freely.

## Pair notes

> **primary, todo turn 1**
>
> I added a `## The plan` section to the Issue. Nothing is implemented yet, and the Issue can be done as written.
>
> **The approach:** the hand-off goes inside `_cmd_sync` in `.meta/bundle.py`. The `sync` recipe in `justfile` doesn't change, so `just sync <checkout>` keeps its form.
>
> 1. **Split `_cmd_sync`.** Its current body (plan, apply, print) moves unchanged into a new function, `_sync_in_place(source, portfolio)`.
> 2. **Add `_checkout_tool(source)`.** It returns the checkout's `.meta/bundle.py`, or nothing when that file is the one already running. That single path comparison stops the endless hand-off. It covers:
>    - the checkout's `bundle.py` once the hand-off has started it;
>    - a stereorepo checkout synced from itself;
>    - the checkout's `bundle.py` run directly with `--root`.
>
>    It needs no extra flag or environment variable. A checkout older than this change, which has no hand-off of its own, still syncs correctly.
> 3. **`_cmd_sync` then does one of three things:**
>    - If the checkout has no `.meta/bundle.py`, it refuses with a message and changes nothing.
>    - If the checkout's `bundle.py` is the running file, it syncs in place.
>    - Otherwise it runs the checkout's `bundle.py` with `--root` set to the portfolio, using the current Python (which already has pyyaml), and returns that run's exit code.
> 4. **Tests** in `.meta/checks/probes/tools/sync.py`:
>    - The existing checks switch to calling `_sync_in_place` directly. Without that, they would all now be refused, because their scratch checkout has no `bundle.py`. No check is dropped.
>    - A new hand-off check starts the sync the way `just sync` does, in three cases:
>      - (a) a checkout whose stub `bundle.py` writes a marker file: one sync leaves the marker, and the portfolio's own sync did not run;
>      - (b) a checkout with no `bundle.py`: the sync refuses and the portfolio is unchanged;
>      - (c) `_checkout_tool` returns nothing for this repository itself.
> 5. **Record the decision** as a new numbered Decision Record refining DR-315 (the decision that introduced the sync), then re-render.
>
> **One change from the agreed "Done when":** it said the scratch checkouts in the existing tests would gain a runnable `bundle.py`. The plan has those tests call `_sync_in_place` instead. A real `bundle.py` and `lib/bundle/` placed in the scratch checkout would themselves be copied into the portfolio by the sync, which would change what every existing check expects.
>
> **Risks noted in the plan:**
> - The checkout's run prints straight to the terminal, past the test's output capture. So test (a) checks only the exit code and the marker file, not what is printed.
> - A checkout whose `bundle.py` crashes makes the sync fail with that crash, which is intended: the checkout's code is the code wanted.

> **secondary, todo turn 2**
>
> I checked my partner's plan against `.meta/bundle.py` and `.meta/checks/probes/tools/sync.py`, and it holds up. The hand-off goes in `_cmd_sync`. A path comparison stops the checkout's `bundle.py` from handing off again, and the hand-off runs it with the current Python. I made three edits to the Issue file and committed them; nothing is implemented yet.
>
> - **"Done when" now agrees with the plan.** It still said the existing tests' scratch checkouts would gain a runnable `bundle.py`. The plan sensibly does the opposite: those tests call `_sync_in_place` directly. A real `bundle.py` in the scratch checkout would get copied into the portfolio and change what every check expects. I rewrote that item to say so, so that whoever checks the work is not judging it against a promise the plan drops.
> - **Case (b) is more precise.** The shared scratch checkout the existing tests use already has `.meta/bundle.yaml` but no `.meta/bundle.py`, so it serves as the "cannot run" checkout. I also made the test check that the refusal message names the missing `.meta/bundle.py`. I added that case (a)'s stub checkout needs no `.meta/bundle.yaml`.
> - **Two small gaps in the plan are filled.** `_run`'s docstring has to change, since it will no longer describe a call through `main`. And the existing refusal for a checkout with no `.meta/bundle.yaml` still runs through `_run`, so that refusal stays tested.

> **primary, todo turn 3**
>
> I changed nothing this turn: my partner's three edits hold up against the code, and the plan is ready to implement.
>
> - **"Done when" now matches the plan.** The existing tests call `_sync_in_place` directly instead of going through the hand-off.
> - **Case (b) works with the shared scratch checkout.** That checkout has `.meta/bundle.yaml` but no `.meta/bundle.py`. The refusal message is printed by the portfolio's own `bundle.py`, in the test's process, so the test can capture it and check that it names the missing `.meta/bundle.py`. The current `_run` throws stderr away, so the new check will need its own capture; that is a detail for implementation.
> - **The existing refusal stays tested.** A checkout with no `.meta/bundle.yaml` still runs through `_run`, so the refusal in `sync.plan` keeps its test.
>
> One small point for implementation: `_check_handoff` will need the shared checkout passed in as an argument, alongside `cli` and `tmp`, to use it for case (b).

## Implementation notes

- Done as planned, recorded as DR-322. `_cmd_sync` in `.meta/bundle.py`
  refuses a checkout with no `.meta/bundle.py`. When `_checkout_tool` names
  another file, it runs that file under `sys.executable` with `--root`;
  otherwise it calls `_sync_in_place`, which is the old body unchanged.
- The probe's stub checkout holds only `.meta/bundle.py`, and the stub uses
  only the standard library. Case (a) compares the portfolio's file hashes
  apart from the marker, not `git status`, because the marker is untracked.
- The hand-off's child output goes straight to the terminal, so no probe
  reads what the checkout's sync prints.

## Pair notes

> **primary, in-progress turn 1**
>
> I've implemented the plan. `just sync <checkout>` now runs the checkout's own `bundle.py`, so a fix to the sync applies on the first sync after it lands. `just gate meta` passes, including the sync tests, and the work is committed. The first sync of each portfolio after this lands still runs that portfolio's old `bundle.py`, so it is one sync late itself; every sync after it uses the checkout's code.
>
> - **`.meta/bundle.py`:** the old body of `_cmd_sync` moved unchanged into `_sync_in_place`. `_cmd_sync` now does one of three things:
>   - It refuses, changing nothing, a checkout that has no `.meta/bundle.py`.
>   - It syncs in place when the checkout's `bundle.py` is the file already running. That is the case for the checkout's own `bundle.py` once started, and for a checkout synced from itself, so the hand-off never repeats.
>   - Otherwise it runs the checkout's `bundle.py` with the same Python and `--root` set to the portfolio, and returns that run's exit code.
>
>   The `sync` recipe in `justfile` is unchanged.
> - **`.meta/checks/probes/tools/sync.py`:** the existing tests now call `_sync_in_place` directly, and none was dropped. A new test starts the sync the way `just sync` does and covers three cases:
>   - A checkout whose `bundle.py` is a stub that only writes a marker file: the marker appears and nothing else in the portfolio changes.
>   - A checkout with no `.meta/bundle.py`: the sync refuses with a message naming the missing file and leaves the portfolio as it was.
>   - This repository's own `bundle.py`: the check that stops a repeated hand-off recognises it.
> - **The decision is recorded as DR-322**, and `just render` regenerated `.meta/decisions.md`.
>
> No test reads what the checkout's sync prints, because its output goes straight to the terminal. I added notes for the next reader to the Issue file. Nothing turned up that needed a new backlog Issue.

> **secondary, in-progress turn 2**
>
> I reviewed the implementation against the plan, and it matches. The only change I made is to the Adoption Discipline's step "Copy the managed items" in `.meta/assertions/disciplines.yaml`: its last sentence now says that `just sync <checkout>` hands the sync to the checkout's own `bundle.py`, so a fix applies on the first sync after it lands (DR-322). I re-rendered `ADOPT.md` and `.meta/disciplines.md` from it. The step's first copy, which runs `<checkout>/.meta/bundle.py --root <repository>`, still syncs in place, because the running file is the checkout's own. `just gate meta` passes.

> **secondary, in-progress turn 2**
>
> My partner's implementation matches the plan and I found no bugs, so I left the code alone. My one change was a line of documentation. `just gate meta` passes, including the sync tests, and the work is committed.
>
> **What I checked:**
> - **The hand-off can't repeat.** The checkout's `bundle.py`, once started, compares the checkout's `.meta/bundle.py` with its own file, finds they are the same, and syncs in place.
> - **The first sync of a new repository still works.** Running `<checkout>/.meta/bundle.py --root <repository>` directly also syncs in place, so `ADOPT.md` step 4 needs no change.
> - **The tests.** The existing sync tests call `_sync_in_place` directly, and none was dropped. The new test covers a checkout whose stub `bundle.py` writes a marker, a checkout with no `.meta/bundle.py`, and the guard against a repeated hand-off.
>
> **What I changed:** in the Adoption Discipline's "Copy the managed items" step (in `.meta/assertions/disciplines.yaml`), the sentence on later syncs now says that `just sync <checkout>` hands the sync to the checkout's own `bundle.py`, so a fix applies on the first sync after it lands (DR-322). I re-rendered `ADOPT.md` and `.meta/disciplines.md` from it, and added a pair note to the Issue file.
>
> Two things remain untested, both as the Issue file already notes:
> - No test runs a full self-sync. The test only checks that the guard recognises this repository's own `bundle.py`.
> - No test reads what the checkout's sync prints, because that output goes straight to the terminal.

> **primary, in-progress turn 3**
>
> I'm leaving this turn's work as it stands and changing nothing. My partner's one edit is correct: the Adoption Discipline's "Copy the managed items" step now says that `just sync <checkout>` hands the sync to the checkout's own `bundle.py`, citing DR-322. `ADOPT.md` and `.meta/disciplines.md` were re-rendered to match. The step's first copy, which runs the checkout's `bundle.py` directly with `--root`, still syncs in place.
>
> The code matches the plan. My partner reported that `just gate meta` passes after their edit; I did not re-run it, because nothing has changed since.
