---
difficulty: medium
---

# Pause the loop when a stale page is one the seat cannot write

When an Issue changes the source of a page that `just render` writes under
`.claude/skills/`, the seats' sandbox denies the write
(`render-in-seat-sandbox`), and the gate's `rendered prose` step
(`.meta/checks/files/rendered.py`) reports the stale copy as `x`. The loop
treats `x` as the seats' to fix: `run_gate` in `pair/loop.py` returns
`gate_fails` whenever the gate fails, so it hands the failure back turn after
turn until the round cap sends the Issue to the backlog. Neither seat can fix
it. Found in `trim-decision-records-065-177`, which went three rounds on it
before the change was split out.

## How to reproduce

On a branch, change the source of a skill that renders to
`.claude/skills/<skill>/SKILL.md` (for example the `/technical-writing`
skill's preamble in `.meta/assertions/imported/structure.yaml`) and commit
without rendering. Run the loop on it: every round's gate failure names the
stale `.claude/skills/` page, the seats' `just render` reports it could not
write it, and the Issue goes back to the backlog at the round cap.

## Wanted

- When every failure in the gate's output is a `rendered prose` finding for
  a page the seats cannot write, the loop pauses rather than handing it back,
  the way `GateUnrunnable` does for a `?` step. The pause reason names each
  such file and says to run `just render` outside the sandbox, then resume.
- "A page the seats cannot write" is one under a path the seats'
  confinement denies (`confinement()` in `pair/seats.py`) or that the
  sandbox otherwise holds back from writes. Today that is Claude Code's own
  denial of `.claude/skills/`, `.claude/settings.json` and similar entries,
  which `confinement()` does not name. Claude Code's denials cannot be read
  from it, so name them once in `pair/seats.py`, beside `confinement()`, with
  the date they were observed, and have the loop's rule read that list and
  `confinement()`'s `deny` rather than a second copy.
- Any other failure in the same gate run, including a stale page the seats
  can write, keeps today's behaviour: the whole failure goes back to the
  seats.
- How the loop tells such a finding apart (reading the gate's output in
  `pair/loop.py`, or having `rendered prose` report such a page as `?` with
  a reason) is the pair's choice. If the step changes, the developer's own
  `just gate` must still fail on a stale page outside any sandbox.

## Out of scope

- Widening the seats' sandbox to allow writes under `.claude/`.
- The loop rendering the page itself.

## Done when

- A pair-loop test in which the only gate failure is a stale page under
  `.claude/skills/` ends in a pause whose reason names the file and says to
  run `just render` outside the sandbox, not in another turn.
- A pair-loop test in which the gate fails on that page and on something
  else hands the failure back to the seats as today.
- A test in which the only failure is a stale page the seats can write hands
  it back as today.
- A gate run whose only finding is a `?` step still pauses as
  `GateUnrunnable` does today, and one with both a `?` step and an unwritable
  stale page pauses with a reason naming both.
- If `rendered prose` changes how it reports such a page, a test of that step
  shows it still fails on a stale `.claude/skills/` page when it runs
  outside any seat's sandbox.

## The plan

The loop reads the gate's output; `rendered prose` and `.meta/gate` stay
as they are. So the developer's own gate still fails on a stale page, and
the last "Done when" item does not apply.

### What the gate prints

For a stale `.claude/skills/` page, a failing `meta` gate prints a step
line rewritten with its Project's name, then its findings indented five
spaces (`PROBLEM` in `.meta/gate`). Each finding is a target name relative
to `.meta/` (`targets.py` in `.meta/lib/render/`). The output ends with the
closing block from `main` in `.meta/gate`:

```
x  meta/rendered prose (1)
     ../.claude/skills/technical-writing/SKILL.md
x  meta (1)
     meta: rendered prose
```

The closing block has one line for each failing Project. It lists that
Project's failing steps, or says why the Project failed with no failing
step (it printed no step, or it exited non-zero).

### Steps

1. **`pair/seats.py`.** Add `SANDBOX_DENIED`, a list of paths relative to
   the worktree that Claude Code's sandbox refuses writes to on its own:
   `.claude/skills`, `.claude/hooks`, `.claude/settings.json` and
   `.claude/settings.local.json`, as this session's sandbox listed them on
   2026-10-03. Its docstring gives that date and says that `confinement()`
   does not name these paths. Add `unwritable(cwd) -> list[Path]`, which
   returns `confinement(cwd).deny` plus `SANDBOX_DENIED` resolved against
   `cwd`. Nothing else holds this list.
2. **`pair/loop.py`, the parser.** Add `unwritable_pages(out, wt, denied)`,
   which returns the repository paths of the stale pages, or None when
   anything else failed. It returns the paths only when both of these hold:
   - each line of the closing block reads `<project>: rendered prose`;
   - every finding under a `<project>/rendered prose` step is a path that,
     once taken as `.meta/<finding>` and normalised, lies at or under one
     of the paths in `denied`.

   Anything else returns None. That includes a finding that is not a path,
   such as `… exists but nothing renders it`. It reads the whole of `out`,
   not the `GATE_TAIL` that `gate_fails` keeps.
3. **`pair/loop.py`, `run_gate`.** When the gate fails and
   `unwritable_pages` returns paths, return a `GateUnrunnable` instead of a
   `GateFailure`. Its reason names each page and says to run `just render`
   outside the sandbox in the worktree (`self.tree`), then run `just pair`
   again. If `gate_unrunnable(out)` also finds `?` steps, the reason
   includes those lines too. Both callers already pause on a
   `GateUnrunnable`, so they need no change:
   - `close_stage` pauses with `retry=GATE`;
   - `merge` pauses with `retry="merge"`.

   Update the `run_gate` docstring.
4. **`pair/loop.py`, resume.** In `work`, the `GATE` and `merge` retries go
   straight to the gate. They do not first commit what the developer left
   in the worktree. A render left uncommitted would then pass the re-run
   gate, and the dirty file would be left out of what lands, or would break
   the rebase. In those two branches of `work`, before calling
   `close_stage` or `merge`, commit a dirty worktree as
   `developer: edits on <slug>`. It must come before `merge`, because
   `merge` calls `rebase` before it runs the gate, and before `squash`, so
   the render is part of what lands. Keep the approvals,
   because the developer did what the pause asked for. `absorb_developer`
   clears the approvals, so it needs a parameter to keep them, or this
   needs a small sibling helper.

### Tests (`pair/test_pair.py`)

- A test class beside `GateUnrunnableTest` for the parser, using fixed
  gate output:
  - a stale `../.claude/skills/…` page alone returns its path;
  - a second failing step returns None;
  - a stale `../README.md` returns None;
  - a closing-block line `meta: every step reported ok or ? and the gate
    exited 1` returns None.
- Loop tests using `implemented` and `Bench.gates` with the output above:
  - The only failure is the `.claude/skills/` page. The loop pauses with
    `retry == "gate"`, a reason that names the file and says `just render`,
    and the approvals kept. When the test writes a file into the worktree
    and runs again, that file is committed and the Issue lands with it.
  - The same page plus `x  a (1)`. The failure goes to the primary seat,
    as in `test_a_failed_gate_with_a_step_that_could_not_run_goes_to_the_primary`.
  - A stale `../README.md` alone goes to the primary seat.
  - The `.claude/skills/` page plus a `?` step. The loop pauses, and the
    reason names both.
  - The same pause while landing, as in
    `test_a_gate_step_that_could_not_run_while_landing_pauses_the_landing`:
    `retry == "merge"`, and after the test writes a file and runs again,
    the landed commit on `main` holds that file.
- `UNRUNNABLE` alone: the existing tests already cover this.
- A test in `ConfinementTest` that `unwritable` holds both
  `confinement`'s `deny` and `.claude/skills` under the worktree.

### Risks

- **Projects are gated in parallel.** `.meta/gate` runs Projects in parallel, so a
  finding line might print under another Project's step. The closing block
  still names every failing step, so a mixed-up line cannot cause a wrong
  pause: at worst the failure goes back to the seats, as it does today.
- **The list can go stale.** `SANDBOX_DENIED` is a copy of what Claude
  Code does. If Claude Code starts denying more, the loop goes back to
  handing the failure to the seats, which is today's behaviour, not a wrong
  pause.
- **`confinement()` is not free.** It runs `git` and `gpg --version`. It is
  called only on a failed gate, so the cost is small. The tests need a real
  git repository, which `Bench` already provides.
- **Keeping approvals on resume.** If the developer edits more than the
  render before resuming, those edits land without a seat's turn. The pause
  message asks for the render only, and a gate pause works the same way
  today.

## What was done

- `SANDBOX_DENIED` and `unwritable` in `pair/seats.py`; `unwritable_pages`
  and `gate_unwritable` in `pair/loop.py`, which `run_gate` tries before
  `gate_fails`. The pause is a `GateUnrunnable`, so `close_stage` and
  `merge` needed no change.
- `work` commits a dirty worktree before resuming a `GATE` or `merge`
  retry, through `absorb_developer(st, keep_approvals=True)`. It does this
  only when the worktree is dirty. A developer who commits the render
  themselves leaves `st.head` behind HEAD: the commit still lands, and the
  next seat turn's `absorb_developer` reports it to the seats.
- The `merge` retry also follows pauses that have nothing to do with a
  render, such as "main kept moving". A dirty worktree there would
  previously have stopped the rebase; now it is committed as the
  developer's edit. That is a change of behaviour beyond the render case.
- `pair/README.md` describes the new pause beside the one for a step that
  could not run.
- The last "Done when" item does not apply: `rendered prose` and
  `.meta/gate` are unchanged.

## Pair notes

> **primary, backlog turn 1**
>
> The issue was already close to ready to plan, so I left its scope as it was and its difficulty at `medium`. It's one change to one loop function, with tests, and doesn't need splitting. I made three small corrections in `issues/underway/pause-on-a-render-the-seat-cannot-write.md` and committed them (dd39f325):
>
> - **Which pages the seats can't write:** the issue said the sandbox blocks all of `.claude/`. It actually blocks specific entries, such as `.claude/skills/` and `.claude/settings.json`. That block comes from Claude Code's own sandbox, not from `confinement()` in `pair/seats.py`. The issue now says so, so whoever builds the rule doesn't read it from `confinement()` alone.
> - **The pause test:** it now also checks that the pause message tells the developer to run `just render` outside the sandbox, not just that it names the file.
> - **The other tests:**
>   - The "hands it back as today" test now uses a stale page the seats *can* write, rather than "a page outside `.claude/`".
>   - I added a conditional test. If the pair changes how the `rendered prose` gate step reports these pages, that step must still fail on a stale `.claude/skills/` page when the gate runs outside any seat's sandbox.
>
> The issue still leaves the approach to the pair: the loop can either read the gate's output, or the gate step can report these pages differently.

> **secondary, backlog turn 2**
>
> I kept the issue's scope as it was and left its difficulty at `medium`. I made two changes to `issues/underway/pause-on-a-render-the-seat-cannot-write.md` and committed them as 82530ba1:
>
> - **Where the list of unwritable paths lives:** the issue told the pair to "derive the rule from one place" without naming the place. That place can't be the sandbox: Claude Code denies writes to `.claude/skills/`, `.claude/settings.json` and similar paths itself, and the loop can't read that list from it. The issue now says to write that list once in `pair/seats.py`, next to `confinement()`, with the date it was observed. The loop's rule then reads that list plus the paths `confinement()` already denies, rather than keeping a second copy.
> - **A missing test for steps that can't run:** today the loop pauses on a step that couldn't run (shown as `?`) only when the rest of the gate passes. A gate that also has a stale `.claude/skills/` page fails, so today that failure goes back to the seats. I added a "Done when" item: a gate whose only finding is a `?` step still pauses as it does today, and a gate with both a `?` step and an unwritable stale page pauses with a message naming both.

> **primary, backlog turn 3**
>
> I'm leaving the issue as it is. My partner made two changes, and both hold up against the code:
>
> - **Where the list of unwritable paths lives:** Claude Code's own write denials can't be read from anywhere, and `confinement()` in `pair/seats.py` doesn't list them. So the issue now says to write that list once, next to `confinement()`, and have the loop read it from there. That gives the "one place" rule an actual place.
> - **The test for a step that couldn't run alongside a stale page:** the loop only pauses for such a step when the rest of the gate passes. `run_gate` in `pair/loop.py` treats any failure as a `GateFailure` before it checks for steps that couldn't run. Without this test, the new pause could swallow the existing one or be swallowed by it.
>
> Difficulty stays `medium`.

> **primary, todo turn 1**
>
> I've written the plan under `## The plan` in `issues/todo/pause-on-a-render-the-seat-cannot-write.md` and committed it (19b0f77d, plus a one-line fix in 368f32f8). The issue can be done as written.
>
> The loop will read the gate's output itself, so `.meta/gate` and its `rendered prose` step stay as they are. That means the developer's own gate still fails on a stale page, and the last "Done when" item doesn't apply.
>
> The four steps:
>
> 1. **`pair/seats.py`:** add `SANDBOX_DENIED`, the paths Claude Code's sandbox refuses writes to on its own (`.claude/skills`, `.claude/hooks`, and the two settings files), dated 2026-10-03. Add `unwritable(cwd)`, which returns that list plus the paths `confinement()` already denies. Nothing else will hold the list.
> 2. **A parser in `pair/loop.py`:** it returns the stale pages only when every failing Project failed on `rendered prose` alone, and every stale page lies under a path the seats can't write. Anything else returns nothing, so the failure goes back to the seats as today.
> 3. **`run_gate`:** in that case it returns a pause instead of a failure. The pause message names each page and says to run `just render` outside the sandbox, then `just pair` again. It also names any step that couldn't run. Both places that call `run_gate` already pause on that result, so they don't change.
> 4. **Resuming after the pause:** this step isn't in the issue. When the loop resumes a gate pause, it runs the gate again without first committing what the developer left in the worktree. A page the developer rendered there would pass the re-run gate but be left out of what lands. So before re-running the gate, the loop will commit those edits as the developer's, and keep both seats' approvals.
>
> The tests are a direct test of the parser and four loop tests, one for each "Done when" case. The plan also notes the risks:
>
> - **Parallel output:** finding lines from Projects gated at the same time could mix. At worst that sends the failure back to the seats, not into a wrong pause.
> - **The list going stale:** if Claude Code starts denying more paths, the loop falls back to today's behaviour.
> - **Edits on resume:** anything the developer edits beyond the render lands without a seat's turn.

> **secondary, todo turn 2**
>
> I checked the plan against the code and it holds up. I made three changes to `issues/todo/pause-on-a-render-the-seat-cannot-write.md` and committed them as 103c1d5e.
>
> What I checked:
> - **Gate output:** `.meta/gate` prints the stale page's path, written relative to `.meta/` (as in `rendered_prose` in `.meta/checks/files/rendered.py`). It then ends with one closing line for each failing Project, which is what the plan's parser reads.
> - **Resuming a gate pause:** neither of the two ways the loop resumes one commits what the developer left in the worktree. `absorb_developer` also clears the approvals. So the plan's step 4 is needed, and so is the change to keep approvals.
>
> What I changed:
> - **When the developer's edits get committed (step 4):** it now says exactly where. In `work`, the commit has to come before the call to `close_stage` or `merge`, not just "before the gate runs". `merge` rebases the branch before it runs the gate, and a rebase on a dirty worktree would stop the landing. The commit also has to come before `merge` squashes the branch, or the rendered page would be left out of what lands.
> - **A new test for the landing case:** the plan only tested the resume from a gate pause during a stage. I added one where the pause happens while landing (resuming with `retry == "merge"`). After the developer's file is written and the loop runs again, the test checks that the commit landed on `main` holds that file.
> - **Where the `unwritable` test goes:** it now goes in the existing `ConfinementTest` class.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is. My partner made three changes, and each holds up against the code:
>
> - **Where the developer's render gets committed:** the commit now has to come before the call to `close_stage` or `merge` in `work`. That is right because `merge` calls `rebase` before it runs the gate, and a rebase with uncommitted files would stop the landing. Committing first also puts the render into what `merge` squashes onto `main`.
> - **The new landing test:** it covers the pause that happens while landing (resumed with `retry == "merge"`), which the plan had left untested.
> - **Where the `unwritable` test goes:** `ConfinementTest` exists in `pair/test_pair.py`, so that's the right place.

> **primary, in-progress turn 1**
>
> I've implemented the plan and committed it as c758b587. `just gate meta` and `just gate pair` both pass.
>
> **What changed:**
> - **The unwritable paths:** `pair/seats.py` now has `SANDBOX_DENIED`, the `.claude/` paths Claude Code's sandbox refuses writes to on its own (observed 2026-10-03). It also has `unwritable(cwd)`, which returns that list plus the paths `confinement()` denies. The list exists only there.
> - **The pause:** `run_gate` in `pair/loop.py` now pauses when every failing step is `rendered prose` and every stale page it names is one the seats can't write. Any other failure, or a stale page the seats can write, still goes back to the seats.
>   - The pause message names each page and says to run `just render` in the worktree outside the sandbox. If the gate also had a step that couldn't run, the message names that step too.
>   - It's the same kind of pause as for a step that couldn't run, so the two places that call `run_gate` needed no change.
> - **Resuming:** `just pair` now commits a dirty worktree as the developer's edit before it runs the gate again, and keeps both seats' approvals. So the render is part of what lands.
> - **`pair/README.md`:** it describes the new pause.
>
> **Tests** in `pair/test_pair.py`:
> - six for the output parser;
> - one in `ConfinementTest` for `unwritable`;
> - five loop tests:
>   - a pause, then landing with the developer's file;
>   - the same pause while landing;
>   - a stale page plus another failure, which goes to the primary seat;
>   - a stale page the seats can write, which goes to the primary seat;
>   - a stale page plus a step that couldn't run, with both named in one pause.
>
> **Change beyond the issue:** the commit on resume also runs for pauses that have nothing to do with a render, such as "main kept moving". Before, an uncommitted file at that point would have stopped the rebase; now it lands as the developer's edit. I've recorded this under `## What was done` in the issue file.
>
> The last "Done when" item doesn't apply, because the gate's `rendered prose` step is unchanged. Your own gate still fails on a stale page.

> **secondary, in-progress turn 2**
>
> I'm leaving my partner's implementation as it is. I checked it against the code and found nothing to fix, and `just gate pair` (243 tests and ruff) and `just gate meta` both pass.
>
> What I checked:
> - **The output parser:** `unwritable_pages` in `pair/loop.py` reads the gate's stale-page lines the way `.meta/gate` prints them. Its last failed block is the gate's closing block, which is printed only after every Project has finished. Each line there must read `<project>: rendered prose`, so any other failure sends the whole thing back to the seats.
> - **Steps that couldn't run:** they don't confuse the parser. Their summary block (`closing_block` in `.meta/check.py`) indents its detail lines two spaces, not the five the parser treats as a finding.
> - **Paths outside the repository:** a finding that resolves to a path outside the worktree is rejected.
> - **Resuming:** committing a dirty worktree in `work` before `close_stage` or `merge` puts the developer's render in the branch before `merge` rebases and squashes it. The two new tests for resuming show that it lands on `main`.
>
> There is one change of behaviour beyond what the issue asked for. When a landing pause resumes for any reason, such as "main kept moving", uncommitted files in the worktree are now committed as the developer's edit and land. Before, they would have stopped the rebase. It is already recorded under `## What was done` in the issue file.
