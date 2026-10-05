---
difficulty: developer
---

# A seat's shell still has `RUSTC_WRAPPER=sccache`

Found while implementing `seed-rendered-gate-lost`. `UNSET_FOR_SEATS` in
`pair/seats.py` drops `RUSTC_WRAPPER` from the seat process's environment,
and its docstring says the seat's shell takes the name only from that
environment, since Claude Code's shell snapshot holds no exports. Both seats
on that Issue nonetheless saw `RUSTC_WRAPPER=sccache` in their Bash tool's
environment on 2026-10-03, and the developer's `~/.zshrc` exports it. Every
`cargo` build in the seat then fails on the sandbox's refusal of sccache,
until the seat runs it under `env -u RUSTC_WRAPPER`; the seats on
`bootstrap-render-step` hit the same thing.

## What grooming found

Checked from the primary seat's Bash tool on this Issue, 2026-10-03:

- `env` lists `RUSTC_WRAPPER=sccache`, so the name is in the shell's process
  environment.
- The current shell snapshot under `~/.claude/shell-snapshots/` has no
  `RUSTC_WRAPPER`, and no export from `~/.zshrc` other than `PATH`.
  `~/.zshenv` and `~/.zprofile` do not set it, and a non-interactive `zsh -c`
  does not read `~/.zshrc`. So neither the profile nor the snapshot is the
  route, and the docstring's claim holds.
- The drop landed in `3f92bfe9` (seat-sandbox-rust-builds) at 20:43, one
  minute before the same `just pair` run started `seed-rendered-gate-lost`.
  Nothing under `pair/` re-executes or reloads the loop's code after a
  landing, so a loop started before `3f92bfe9` still starts every seat with
  the old `ClaudeSeat.__init__`, which passes `RUSTC_WRAPPER` through.
  The loop's event log (`.pair/events.jsonl` in the primary checkout) bears
  this out: its last `ended` event for the `pair` loop is at 16:13, and every
  Issue since, through this one, was `started` and `landed` by one run that
  has not ended, so that run began before `3f92bfe9`.
- `test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` in
  `pair/test_pair.py` already shows that the current code starts a seat
  without the name.

The cause is therefore a loop process older than the fix, not a gap in the
fix.

## Wanted

- Confirm the cause: the developer restarts `just pair`, and a seat in the
  new run reports no `RUSTC_WRAPPER` in its Bash tool's `env` and runs
  `cargo build` in `bootstraps/rust/seed` with no `env -u`.
- If the restarted seat still has the name, find the route grooming missed,
  and then fix it in `ClaudeSeat.__init__`, for instance by setting
  `RUSTC_WRAPPER` to the empty string, which `cargo` reads as no wrapper.
  Extend the existing test to cover the fix.
- The docstring of `UNSET_FOR_SEATS` says that the drop takes effect only in
  a loop started after it lands.

## Out of scope

- Making a running loop pick up pair code that has landed since it started.
  That is `pair-loop-runs-the-code-it-started-with` in `issues/backlog/`.

## Done when

- A seat in a `just pair` run started after this lands runs `cargo build` in
  `bootstraps/rust/seed` with no `env -u`. The developer checks this by hand,
  since no seat can restart the loop it runs in.
- `test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` still
  passes, and covers any change made to how the seat's environment is built.

## The plan

The fix itself is already on `main` (`3f92bfe9`), so the code change is one
docstring. Nothing a seat can do in the running loop confirms the fix, so the
check falls to the developer at the desk check.

1. In `pair/seats.py`, add to the docstring of `UNSET_FOR_SEATS` that a
   `just pair` run reads `pair/` once at start, so a name added here reaches
   seats only in a run started after the change lands, and cite
   `pair-loop-runs-the-code-it-started-with` for the general problem. Keep the
   existing sentence about the shell snapshot, which grooming confirmed.
2. Change no test. `ClaudeSeat.__init__` is untouched, so
   `test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` in
   `pair/test_pair.py` covers the behaviour as it stands; run it alone to
   confirm it passes.
3. At the desk check, the developer answers this Issue with
   `just pair-resume`. Nothing needs stopping first: `Loop.run` in
   `pair/loop.py` returns when an Issue reaches `desk-check`, so the stale
   run ends there by itself. `pair-resume` is a new process, which reads the
   `pair/` on the developer's checkout and starts fresh seats from it. The resume note asks a seat to
   run `env` and `cargo build` in `bootstraps/rust/seed`, with no `env -u`,
   and report both. If `RUSTC_WRAPPER` is absent and the build passes, the
   developer accepts.

**Risk:** if step 3 still shows `RUSTC_WRAPPER`, the cause is not the stale
loop. The resumed seats then trace the route, set `RUSTC_WRAPPER` to the
empty string in the `env` that `ClaudeSeat.__init__` builds (after
`env.update(confined.env)`, so nothing overwrites it), change the
docstring to match, and change the existing test to expect the empty string.
`cargo` treats an empty `RUSTC_WRAPPER` as no wrapper.

## What was done

Steps 1 and 2 are done: the docstring of `UNSET_FOR_SEATS` in
`pair/seats.py` now says that a run reads `pair/` once at start, and
`test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` passes
unchanged. Step 3 is the developer's: answer the desk check with
`just pair-resume` and a note asking a seat to run `env` and
`cargo build` in `bootstraps/rust/seed` with no `env -u`. The seats on this
turn still see `RUSTC_WRAPPER=sccache`, as expected of the old run.

Step 3, from the primary seat's first turn in the run the developer started
after the desk check (2026-10-05):

1. `env` lists no `RUSTC_WRAPPER`.
2. `cargo build` in `bootstraps/rust/seed`, with no `env -u`, succeeds. The
   build into the existing `target/` was already up to date, so the check
   used a fresh `--target-dir` under `/tmp/claude`, which compiled `xtask`
   and `seed` with `rustc` and finished. The output also carries
   `xcrun: error: couldn't create cache file` lines, because the sandbox
   refuses writes under `/var/folders`. These are warnings: the build does
   not fail on them, and sccache plays no part in them.

The stale run was the whole cause, and the Issue needs no further change.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/seat-shell-rustc-wrapper-returns.md` and set it to `difficulty: developer`. The bug can only be confirmed fixed in a fresh `just pair` run. No seat can restart the loop it runs in, so the developer has to check it by hand.
>
> I checked from my own Bash tool, since I'm a seat on this loop and see the same problem:
>
> - **The variable is set:** `env` shows `RUSTC_WRAPPER=sccache`.
> - **It doesn't come from the shell snapshot:** the snapshot under `~/.claude/shell-snapshots/` doesn't contain `RUSTC_WRAPPER` at all. `~/.zshenv` and `~/.zprofile` don't set it either, and a non-interactive `zsh -c` doesn't read `~/.zshrc`. So the docstring of `UNSET_FOR_SEATS` is right on that point.
> - **The likely cause is an old loop process:** the fix (`3f92bfe9`) landed at 20:43, and the same `just pair` run started `seed-rendered-gate-lost` one minute later. Nothing in `pair/` reloads its own code after a landing. A loop started before the fix still uses the old start-up code, which passes `RUSTC_WRAPPER` through to every seat.
> - **The current code is correct:** the existing test `test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` already shows it starts a seat without the variable.
>
> The issue now asks for three things:
> 1. The developer restarts `just pair` and confirms that a seat in the new run can run `cargo build` in `bootstraps/rust/seed` without `env -u`.
> 2. If the variable still appears after the restart, the seat finds the route this check missed and fixes it. Setting `RUSTC_WRAPPER` to an empty string is one option, since `cargo` reads that as no wrapper. The fix also extends the existing test.
> 3. The docstring of `UNSET_FOR_SEATS` says the change only takes effect in a loop started after it lands.
>
> The loop running stale code is a separate, wider problem, so I left it out of scope. I wrote it up as `issues/backlog/pair-loop-runs-the-code-it-started-with.md`. I didn't add it to `issues/backlog/ORDER`; `just groom` will place it.

> **secondary, backlog turn 2**
>
> I made one addition to the issue file. I left the rest of my partner's grooming as it was, because it's sound.
>
> **What I checked:** my own Bash tool also has `RUSTC_WRAPPER=sccache` set. The loop's event log (`.pair/events.jsonl` in the primary checkout) shows the last time the `pair` loop ended was 16:13. Every issue since then, including this one, was started and landed by one run that is still going. So that run started before the fix (`3f92bfe9`, 20:43). That confirms the issue's cause: the running loop is still using code from before the fix. Before, it was only "likely".
>
> **What I changed:** I added that evidence under "What grooming found".
>
> **What I left alone:**
> - `difficulty: developer` stays. No seat can restart the loop it runs in, so only the developer can check the fix.
> - The out-of-scope split to `pair-loop-runs-the-code-it-started-with` stays.
> - The "Done when" checks are about behaviour and the existing test, not a gate, so they were already right.

> **primary, backlog turn 3**
>
> I kept my partner's addition and made one small edit in `issues/underway/seat-shell-rustc-wrapper-returns.md`.
>
> My partner checked the loop's event log. The last time the `pair` loop ended was 16:13, and one unbroken run has carried every Issue since, including this one. That run therefore started before the fix (`3f92bfe9`, which landed at 20:43), so its seats still start with the old code that passes `RUSTC_WRAPPER` through. This turns the cause from likely into confirmed, so I changed the conclusion from "The likely cause is…" to "The cause is…".
>
> The rest stands as it was:
> - **Difficulty:** `developer`, since no seat can restart the loop it runs in.
> - **Out of scope:** the loop not reloading code that has landed since it started, which has its own backlog issue, `pair-loop-runs-the-code-it-started-with`.
> - **Done when:** a seat in a newly started `just pair` run can run `cargo build` without `env -u`, and the existing environment test still passes.

> **secondary, backlog turn 4**
>
> I'm leaving the issue as it is. My partner's only edit changes "likely cause" to "cause", which the event-log evidence supports. The issue is still `difficulty: developer`. The out-of-scope split stays in place, and "Done when" checks behaviour and the existing test rather than a gate. It's ready to plan.

> **primary, todo turn 1**
>
> I've written `## The plan` in `issues/todo/seat-shell-rustc-wrapper-returns.md`. The fix is already on `main` (commit `3f92bfe9`), so the only code change is one docstring. The real check falls to the developer at the desk check.
>
> 1. **Docstring:** in `pair/seats.py`, the docstring of `UNSET_FOR_SEATS` will say that a `just pair` run reads `pair/` once when it starts. A name added there only reaches seats in a run started after the change lands. It will point to the backlog issue `pair-loop-runs-the-code-it-started-with` for the general problem. The existing sentence about the shell snapshot stays, since grooming showed it is true.
> 2. **Tests:** no test changes, because `ClaudeSeat.__init__` isn't touched. The existing test `test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` will be run on its own to show it passes.
> 3. **Desk check:** the developer stops the running loop and answers this Issue with `just pair-resume`. That starts a new process, which reads the current `pair/` code and starts fresh seats from it. The resume note asks a seat to run `env` and `cargo build` in `bootstraps/rust/seed` without `env -u`, and report both. If `RUSTC_WRAPPER` is gone and the build passes, the developer accepts.
>
> **Risk:** if the seats still see `RUSTC_WRAPPER` after step 3, the old loop wasn't the cause. In that case the resumed seats find out where it comes from. They then set `RUSTC_WRAPPER` to an empty string in the environment that `ClaudeSeat.__init__` builds, after `env.update(confined.env)` so nothing overwrites it. `cargo` reads an empty value as no wrapper. They also update the docstring and the existing test to match.

> **secondary, todo turn 2**
>
> The plan holds up, and I corrected one wrong step in it.
>
> **What I fixed:** step 3 had the developer stop the running `just pair` loop before the desk check. That isn't needed. In `pair/loop.py`, `Loop.run` returns as soon as an issue reaches `desk-check`, so the old loop (the one started before the fix) ends there on its own. Step 3 now says that.
>
> **What I checked and left alone:** `just pair-resume` runs `pair/pair.py resume` as a new process from the developer's checkout. `Loop.resume` then works the issue with new seats built from the current `pair/` code, which already includes the fix. So the desk check really does test the fixed code.
>
> The rest of the plan stands as written: a docstring change, no test changes, and the fallback of setting `RUSTC_WRAPPER` to an empty string if the variable still shows up.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is. I checked my partner's correction against the code and it's right. In `Loop.run` in `pair/loop.py`, the loop returns `"desk-check"` once an Issue reaches its desk check. That happens either when it picks up an Issue already waiting there or when `self.work` returns that outcome. So the old loop, started before the fix, ends on its own at this Issue's desk check. The developer doesn't need to stop it first, and `just pair-resume` then starts fresh seats from the current `pair/` code, which includes the fix.
>
> The rest of the plan stands:
> - a docstring change to `UNSET_FOR_SEATS` in `pair/seats.py`
> - no test changes
> - the developer's check after `pair-resume`
> - the fallback of setting `RUSTC_WRAPPER` to an empty string if seats still see the variable

> **primary, in-progress turn 1**
>
> I've done the first two steps of the plan and committed them. The third step, the actual proof that the fix works, needs the developer at the desk check.
>
> - **Step 1, the docstring:** in `pair/seats.py`, the docstring of `UNSET_FOR_SEATS` now says that a `just pair` run reads `pair/` once, when it starts. So a name added to that set only reaches seats in a run started after the change lands. It also says this is why seats on 2026-10-03 still saw `RUSTC_WRAPPER`, and points to the backlog issue `pair-loop-runs-the-code-it-started-with` for the general problem.
> - **Step 2, the test:** no test changed. `test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` passes when run on its own. `just gate meta` passes (95 steps), and `just gate pair` passes (269 tests, plus ruff).
> - **Step 3, the developer's check:** I added a "What was done" section to the issue file that tells the developer what to do at the desk check. They answer it with `just pair-resume` and a note asking a seat to run `env` and `cargo build` in `bootstraps/rust/seed` without `env -u`. My own shell still has `RUSTC_WRAPPER=sccache`, which is expected, because this turn runs in the loop started before the fix.

> **secondary, in-progress turn 2**
>
> The work is done apart from step 3, which needs the developer at the desk check. I made one change on this turn: I rewrote the paragraph my partner added to the `UNSET_FOR_SEATS` docstring in `pair/seats.py`.
>
> My partner's version told the story of what happened on 2026-10-03, when seats still saw `RUSTC_WRAPPER`. That history already lives in the issue file. The docstring now gives just the lasting rule: a `just pair` run imports `pair/` once, when it starts, so a name added to `UNSET_FOR_SEATS` only reaches seats in a run started after the change lands. A run already going keeps passing the name through. The docstring still points to the backlog issue `pair-loop-runs-the-code-it-started-with` for that general problem.
>
> Both checks passed after my edit: `just gate pair` (269 tests, plus ruff) and `just gate meta` (95 steps).
>
> **Step 3, for the developer:** answer the desk check with `just pair-resume`. Add a note asking a seat to run `env` and `cargo build` in `bootstraps/rust/seed` without `env -u`. If `RUSTC_WRAPPER` is gone and the build passes, accept the issue.

> **primary, in-progress turn 3**
>
> I'm leaving this turn's work as it stands. My partner's rewrite of the `UNSET_FOR_SEATS` docstring in `pair/seats.py` is better than mine. It keeps the lasting rule: a `just pair` run imports `pair/` once, when it starts, so a run already going keeps passing the name through. It drops the account of what happened on 2026-10-03, which the issue file already records. It also still points to the backlog issue `pair-loop-runs-the-code-it-started-with`.
>
> I didn't re-run the gates. My partner ran both after the edit and both passed: `just gate pair` (269 tests, plus ruff) and `just gate meta` (95 steps).
>
> Step 3 is still the developer's, at the desk check. They answer it with `just pair-resume` and a note asking a seat to run `env` and `cargo build` in `bootstraps/rust/seed` without `env -u`. If `RUSTC_WRAPPER` is gone and the build passes, they accept the issue.

## Desk-check notes (developer, 2026-10-05)

This run of `just pair` starts after the `UNSET_FOR_SEATS` change landed, so
its seats should start without `RUSTC_WRAPPER`. In the primary seat's first
turn:

1. Run `env` and record whether `RUSTC_WRAPPER` appears.
2. Run `cargo build` in `bootstraps/rust/seed`, with no `env -u`, and record
   whether it succeeds.
3. Write both results under "What was done" in this file.

If `RUSTC_WRAPPER` is absent and the build succeeds, the Issue is done and
needs no other change. If it is still present, find where the seat's shell
gets it, since the seat process's environment no longer carries it, and fix
that in `pair/seats.py`, with a test.

## Pair notes

> **primary, in-progress turn 1**
>
> I ran the developer's check in this new `just pair` run and it passes, so the issue is done and needs no code change.
>
> 1. **`env`:** `RUSTC_WRAPPER` is gone from my shell.
> 2. **`cargo build` in `bootstraps/rust/seed`, without `env -u`:** it succeeds. The existing `target/` was already up to date, so that first build didn't actually call `rustc`. I ran it again into a fresh build directory under `/tmp/claude`. That build compiled `xtask` and `seed` from scratch and finished, and I deleted the directory afterwards.
> 3. **Results recorded:** both results are under "What was done" in the issue file. The old loop, started before the fix, was the whole cause.
>
> The build output also includes `xcrun: error: couldn't create cache file` lines, because the sandbox refuses writes under `/var/folders`. They are only warnings: the build still succeeds, and they have nothing to do with sccache. I noted them in the issue file but didn't open a backlog issue.
>
> I changed only the issue file, so I ran `just gate meta`, which passes (95 steps), and committed.

> **secondary, in-progress turn 2**
>
> I'm changing nothing this turn. The fix works.
>
> I ran the developer's check again from my own shell in this new `just pair` run, which started after the fix landed:
>
> - **`env`:** `RUSTC_WRAPPER` does not appear.
> - **`cargo build` in `bootstraps/rust/seed`, without `env -u`:** it finishes. The build was already up to date, so it didn't recompile anything. My partner's build into a fresh directory, recorded in the issue file, already showed a full compile works.
>
> My partner's results under "What was done" are accurate. The issue file meets every "Done when" condition, and the only code change is the `UNSET_FOR_SEATS` docstring in `pair/seats.py`, which passed both gates on an earlier turn. I didn't re-run `just gate meta` because nothing changed.

Gated by the supervisor at 10:53: `meta`, `pair`; 97 steps passed.
