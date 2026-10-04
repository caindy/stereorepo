---
difficulty: easy
---

# Let a seat build Rust in its sandbox without rediscovering how

The developer's shell sets `RUSTC_WRAPPER=sccache`, and inside a seat's
sandbox sccache is refused ("Operation not permitted"). Every `cargo` build
then fails, and `just gate rust-seed` and `just audit rust-seed rust` stop
before reporting a step. Running the command as
`env -u RUSTC_WRAPPER <command>` works and needs no approval.

Three Issues have found this one seat at a time (`bootstrap-render-step`,
`audit-gate-crash-misreported`, `rust-seed-gate-stdout`), and in the last of
them one seat left the Rust checks to the supervisor before its partner
found the workaround. Nothing durable records it: the seats' prompts in
`pair/` do not mention it.

## Wanted

The loop starts each seat without `RUSTC_WRAPPER` in its environment, so
`cargo` in a seat's shell compiles with plain `rustc`. The seat inherits the
loop's environment in `ClaudeSeat.__init__` in `pair/seats.py`, less
`ANTHROPIC_API_KEY` and the names in `Confinement.withheld`. Those two
fixed names move into one module-level constant in `pair/seats.py` whose
docstring says why each is dropped: the API key so the seat bills to the
developer's login, `RUSTC_WRAPPER` because sccache is refused in the
sandbox. `ClaudeSeat.__init__` drops that constant's names and the key
files' names, as it drops them now.

Claude Code's Bash tool starts from a snapshot of the developer's shell
profile, but that snapshot holds functions, aliases and options, not the
`RUSTC_WRAPPER` export (checked 2026-10-03 against the snapshots in
`~/.claude/shell-snapshots/`): the seat's shell gets the name only from the
process environment, so dropping it there is enough.

This is mechanical rather than a line in a seat's prompt: a prompt line
is one more thing a seat may not read in time, and the loop already owns
the seat's environment.

## Out of scope

- The supervisor's gate (`Loop.gate_env` in `pair/loop.py`) runs outside the
  sandbox and keeps the developer's `RUSTC_WRAPPER`; sccache works there.
- Making sccache itself work in the sandbox (its cache directory, its
  server's local port).
- `CARGO_BUILD_RUSTC_WRAPPER` and `build.rustc-wrapper` in a cargo config:
  nothing in this repository or the developer's setup uses them.

## Done when

- A test in `pair/test_pair.py` starts a seat through the stand-in program
  with `RUSTC_WRAPPER` set in the loop's environment, and the stand-in sees
  it unset; the test fails if the name is no longer dropped.
  The stand-in's `env` step writes an unset name as an empty file, so the
  test sets `RUSTC_WRAPPER` to a non-empty value and asserts the file is
  empty.
- The constant's docstring names `RUSTC_WRAPPER` and `ANTHROPIC_API_KEY`
  and the reason for each.
- The first seat started after this lands can run `cargo build` in
  `rust-seed/` without `env -u RUSTC_WRAPPER`. Whoever next works on a Rust
  Issue notes in that Issue whether it did; a failure there is a new Issue,
  not a reason to hold this one.

## The plan

Only `pair/seats.py` and `pair/test_pair.py` change.

1. In `pair/seats.py`, add a module-level constant `UNSET_FOR_SEATS`, a
   `frozenset` of `"ANTHROPIC_API_KEY"` and `"RUSTC_WRAPPER"`, beside
   `SANDBOX_DENIED`, with a docstring after it as `SANDBOX_DENIED` has. The
   docstring gives one reason per name: without the API key the seat bills
   to the developer's login; with `RUSTC_WRAPPER` set, every `cargo` build
   fails because the sandbox refuses sccache, and the seat's shell gets the
   name only from the process environment (the shell snapshot does not hold
   it, checked 2026-10-03).
2. In `ClaudeSeat.__init__`, replace the literal
   `{"ANTHROPIC_API_KEY", *confined.withheld}` with
   `UNSET_FOR_SEATS | confined.withheld`. Nothing else in the seat's start
   changes.
3. In `pair/test_pair.py`, `ClaudeSeatTest`: add a test that starts a
   seat through `self.seat` with a stand-in `env` step for `RUSTC_WRAPPER`
   inside `mock.patch.dict(os.environ, {"RUSTC_WRAPPER": "sccache"})`, sends
   one turn, and asserts the file the step writes is empty. The patch must
   cover the seat's construction, since `ClaudeSeat.__init__` copies the
   environment when it starts the process; the send may run after it. The test names
   `RUSTC_WRAPPER` literally rather than iterating over `UNSET_FOR_SEATS`,
   so removing the name from the constant makes it fail.
   `test_a_seat_starts_without_the_variables_its_key_files_name` already
   covers `ANTHROPIC_API_KEY` and stays as it is.

Risk is low. The shell snapshot was checked and holds no
`RUSTC_WRAPPER`, but a seat's `cargo build` working end to end can only be
seen after this lands; the last "Done when" item checks it then.

## What was done

As planned: `UNSET_FOR_SEATS` in `pair/seats.py`, used by
`ClaudeSeat.__init__`, and
`test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` in
`ClaudeSeatTest`. With `RUSTC_WRAPPER` taken out of `UNSET_FOR_SEATS`, that
test fails; with it back, it passes (run once each way). The `ANTHROPIC_API_KEY` reason in the docstring is still
inferred, not recorded anywhere earlier; the developer may want to check it.
A seat started before this lands, including the ones on this Issue, still
has `RUSTC_WRAPPER`; the loop picks the change up on its next start.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/seat-sandbox-rust-builds.md` and set it to `difficulty: easy`. I changed only the Issue file, no code.
>
> - **Wanted:** the loop starts each seat with `RUSTC_WRAPPER` removed from its environment. The seat's environment is built in `ClaudeSeat.__init__` in `pair/seats.py`, which already drops the names in `withheld`. `RUSTC_WRAPPER` joins that list, with a note saying why. I chose this over adding a line to the seats' prompts, because a seat might not read the prompt line in time, while the loop already controls the seat's environment.
> - **Out of scope:** the supervisor's gate, which runs outside the sandbox where sccache works. Also out: making sccache itself work in the sandbox, and cargo-config wrapper settings, which nothing here uses.
> - **Done when:**
>   - A test in `pair/test_pair.py` sets `RUSTC_WRAPPER` in the loop's environment, starts a seat through the existing stand-in program (a fake `claude` that records its environment), and checks that the stand-in sees it unset.
>   - The docstring that lists what a seat's environment loses names `RUSTC_WRAPPER` and why.
>   - The next seat that works on Rust records in its Issue whether plain `cargo build` worked.
>
> One risk is written into the Issue: `RUSTC_WRAPPER` is exported from line 136 of the developer's `~/.zshrc`. If the seat's shell reloads that file, removing the variable from the seat's process environment won't be enough. I couldn't check this from inside my own sandbox, so the Issue says a failure there becomes a new Issue rather than holding this one back.

> **secondary, backlog turn 2**
>
> I made two fixes to the Issue file and committed them. `difficulty: easy` stays. No code changed.
>
> 1. **The docstring the Issue pointed to didn't exist.** `ClaudeSeat.__init__` in `pair/seats.py` drops `ANTHROPIC_API_KEY` inline, with no docstring explaining it. The Issue now asks for that name and `RUSTC_WRAPPER` to go into one module-level constant in `pair/seats.py`. Its docstring gives the reason for each: the API key is dropped so the seat bills to the developer's login, and `RUSTC_WRAPPER` because sccache is refused in the sandbox. "Done when" now checks that docstring.
>
> 2. **Your `~/.zshrc` risk is settled.** Claude Code's Bash tool starts from a saved snapshot of the developer's shell profile, and none of the snapshots in `~/.claude/shell-snapshots/` contain `RUSTC_WRAPPER`. My own shell has `RUSTC_WRAPPER=sccache`, so it must be coming from the process environment. That means dropping the name there is enough, and the Issue now says so with today's date. The follow-up check by the next seat to work on Rust stays in.
>
> I also made the test precise. When the test stand-in program is asked to record a variable, it writes an empty file if the variable is unset. So the test sets `RUSTC_WRAPPER` to a non-empty value and asserts that the file comes back empty.

> **primary, backlog turn 3**
>
> I'm leaving the Issue as it stands. My partner's changes hold up against the code:
>
> - **The docstring:** I had pointed the "Done when" check at a docstring that doesn't exist. `ClaudeSeat.__init__` in `pair/seats.py` drops `ANTHROPIC_API_KEY` inline without explaining why. Moving that name and `RUSTC_WRAPPER` into one module-level constant with a docstring gives the check something real to look at.
> - **The shell-profile risk:** my partner found that Claude Code's saved shell snapshots don't carry the `RUSTC_WRAPPER` export. So the seat's shell gets the name only from its process environment, and dropping it there is enough. That settles the risk I had flagged as unchecked.
> - **The test:** the stand-in program in `pair/test_pair.py` writes an empty file when asked to record an unset variable. So setting `RUSTC_WRAPPER` to a non-empty value and asserting the file comes back empty is the right check.
>
> `difficulty: easy` still fits.

> **primary, todo turn 1**
>
> I've written `## The plan` into `issues/todo/seat-sandbox-rust-builds.md`. I changed no code, as this stage asks.
>
> The change touches only `pair/seats.py` and `pair/test_pair.py`, in three steps:
>
> 1. **New constant:** add `UNSET_FOR_SEATS` to `pair/seats.py`, holding `ANTHROPIC_API_KEY` and `RUSTC_WRAPPER`. Its docstring gives the reason for each: without the API key the seat bills to the developer's login, and with `RUSTC_WRAPPER` set every `cargo` build fails because the sandbox refuses sccache.
> 2. **Use it:** in `ClaudeSeat.__init__`, the hard-coded `{"ANTHROPIC_API_KEY", *confined.withheld}` becomes `UNSET_FOR_SEATS | confined.withheld`. Nothing else about how a seat starts changes.
> 3. **New test** in `ClaudeSeatTest`: set `RUSTC_WRAPPER=sccache`, start a seat through the stand-in program (the fake `claude` that records a variable to a file), and assert the file comes back empty. The test names `RUSTC_WRAPPER` directly rather than looping over the constant, so taking the name out of the constant makes it fail. The existing test `test_a_seat_starts_without_the_variables_its_key_files_name` already covers `ANTHROPIC_API_KEY`.
>
> The risk is low. One assumption can't be tested from inside a seat before this lands: that the seat's shell doesn't pick `RUSTC_WRAPPER` back up from the developer's `~/.zshrc`. The Issue's last "Done when" item has the next seat that works on Rust check it afterwards.

> **secondary, todo turn 2**
>
> Your plan holds up against the code. I tightened step 3 and the risk paragraph and committed the change; no code changed.
>
> - **Step 3, the test:** I took `ANTHROPIC_API_KEY` out of the new test. `test_a_seat_starts_without_the_variables_its_key_files_name` already checks it, so the new test only needs `RUSTC_WRAPPER`. I also wrote down when the environment has to be patched. `ClaudeSeat.__init__` copies the environment when it starts the process, so the `mock.patch.dict` must be in place while the seat is created; the turn it sends can run after.
> - **Risk:** the paragraph still called the `~/.zshrc` question untested, which contradicted the shell-snapshot check from grooming. It now says the snapshot was checked and holds no `RUSTC_WRAPPER`. What remains is whether a seat's `cargo build` works end to end, which can only be seen after this lands, and the last "Done when" item has the next seat that works on Rust check it.
>
> One thing I couldn't confirm: no commit or Decision Record says why `ANTHROPIC_API_KEY` is dropped. The plan's reason, that the seat then bills to the developer's login, is likely correct, because Claude Code uses API billing when the key is set. But it is an inference, so the developer may want to check the docstring once it is written.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands. My partner's two edits are right:
>
> - **Step 3, the test:** `ClaudeSeat.__init__` copies the environment when it starts the seat's process. So the test has to patch `RUSTC_WRAPPER` into the environment before the seat is created, not just around the turn it sends, and the plan now says so. Dropping `ANTHROPIC_API_KEY` from the new test is also right, because an existing test already checks that name.
> - **Risk:** the paragraph now agrees with the shell-snapshot check from grooming. What's left is whether a seat's `cargo build` works end to end, and the last "Done when" item has the next seat that works on Rust check that.
>
> I looked for a recorded reason why seats drop `ANTHROPIC_API_KEY`. The only commit that touches it is the one that brought the pair loop in (`b587231a`), and nothing in the Decision Records, the wiki or `pair/README.md` mentions it. So the plan's reason, that without the key the seat bills to the developer's login, is still an inference. It's a reasonable one, and my partner has already noted in the Issue that the developer may want to check that docstring once it's written.

> **primary, in-progress turn 1**
>
> Seats now start without `RUSTC_WRAPPER`, so `cargo` in a seat's shell runs `rustc` directly instead of going through sccache, which the sandbox refuses. I built it as planned and committed it, and both gates I was asked to run passed: `just gate pair` (269 tests plus ruff) and `just gate meta`.
>
> - **The constant:** `UNSET_FOR_SEATS` in `pair/seats.py` holds `ANTHROPIC_API_KEY` and `RUSTC_WRAPPER`, with a docstring giving the reason for each.
> - **Where it's used:** `ClaudeSeat.__init__` now drops those names plus the ones from the key files. Before, `ANTHROPIC_API_KEY` was written out inline there.
> - **The test:** `test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` sets `RUSTC_WRAPPER=sccache` before the seat starts. It then checks that the stand-in program (the fake `claude` the tests use) sees the variable unset. I tried to also run it once against code with the name removed to watch it fail, but that command was denied, so I didn't. If the name weren't dropped, the stand-in would record "sccache" and the test would fail.
>
> I added a short "What was done" section to the Issue file. It says that the stated reason for dropping `ANTHROPIC_API_KEY` is still an inference, which the developer may want to check. It also says that seats started before this lands, including the two working on this Issue, still have `RUSTC_WRAPPER` set. So whether a seat's `cargo build` now works can only be seen at the next seat start, as the Issue's last "Done when" item says.

> **secondary, in-progress turn 2**
>
> Your implementation matches the plan and works, so I left the code as it was. My only change is one sentence in the Issue file, now committed.
>
> - **The new test catches the bug:** you couldn't run it against the broken code, so I did. With `RUSTC_WRAPPER` taken out of `UNSET_FOR_SEATS`, `test_a_seat_starts_without_the_rustc_wrapper_its_sandbox_refuses` fails; put back, it passes. I restored the file, and the "What was done" section now records both runs.
> - **No documents need updating:** nothing in `pair/README.md`, the wiki or the Decision Records describes what a seat's environment loses.
> - **Gates:** `just gate pair` passed (269 tests plus ruff), and so did `just gate meta`.

> **primary, in-progress turn 3**
>
> I'm changing nothing this turn. My partner ran the check I couldn't: with `RUSTC_WRAPPER` taken out of `UNSET_FOR_SEATS`, the new test fails, and with it back, it passes. That sentence in the Issue's "What was done" section is accurate. My partner also confirmed that no other document describes what a seat's environment loses, so nothing else needed updating.
>
> Nothing has changed since `just gate pair` and `just gate meta` passed, apart from that one sentence in the Issue file, so I didn't run them again.
