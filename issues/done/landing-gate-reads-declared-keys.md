---
difficulty: medium
parent: keys-reach-the-landing-gate-not-the-seats
waits_on: [seats-never-hold-keys]
---

# Give the landing gate the keys a portfolio declares

Part of `keys-reach-the-landing-gate-not-the-seats`. The landing gate runs
in `worktrees/pair` (`run_gate` in `pair/loop.py` calls the loop's `gate`
callable, which is `gate` in `pair/pair.py`), which has no `.env` because git does not check out an ignored
file. A test that needs a key fails there or reports `?`, and since
`landing-gate-holds-on-could-not-run` a `?` holds the landing for good.
fitch-mvp's `live-generation-run` needs a Gemini key from its `.env` and
could not land.

## Wanted

- A portfolio names, in `.meta/assertions/structure.yaml` (under
  `portfolio:`, with a slot added to the schema in `.meta/work/structure.yaml`), the
  variables from its root `.env` that its gate may read. Names only, never
  values, so the list is auditable in git.
- The loop reads those variables, and only those, from the `.env` at the
  main checkout's root, and passes them in the environment of the gate's
  process alone, through the `gate` callable's signature so a test can
  inject a fake gate and read what it was given. The gate runs outside the
  seats' sandbox. A declared
  variable missing from `.env` is simply absent, so its test reports `?` and
  the landing holds as today.
- The declared list is read from `main`'s `structure.yaml`
  (`self.main` / `self.repo` in `pair/loop.py`), not from the branch under
  gate, so a seat cannot widen it by editing the file on its branch.
- Gate output reaches the seats when the gate fails (`gate_fails`,
  `gate_unrunnable`). Before the loop keeps or hands on that output, every
  non-empty value of a declared variable in it is replaced by a placeholder
  naming the variable, such as `<GEMINI_API_KEY>`, so a test that prints its
  key does not pass the key to a seat.
- `just gate` in the developer's own checkout is unchanged: it reads `.env`
  as the product already does.
- A coding Decision Record states the rule: keys reach the supervisor's
  gate and never a seat. It cites `seats-never-hold-keys`'s denial as the
  other half, and says that an Issue whose work is itself a live run stays a
  `developer` Issue: the developer runs it, and the pair records what it
  found. It also states what is left open: code on the branch runs with the
  declared keys, so a declared key is one the developer accepts the branch's
  tests may use.

## Out of scope

- The seats' side (`seats-never-hold-keys`).
- Secret managers or keychains: `.env` is the developer's convention.

## Done when

- A test over a temporary portfolio whose `.env` holds a declared variable
  and an undeclared one: the environment the landing gate's process is
  started with holds the declared variable and not the undeclared one.
- A portfolio that declares nothing starts the gate with the same
  environment as today.
- A test where the branch's `structure.yaml` declares a variable that
  `main`'s does not: the gate's environment does not hold it.
- A test where a failing gate prints a declared value: the output the
  loop records for the seats holds the placeholder and not the value.
- The Decision Record is written and `.meta/decisions.md` re-rendered.

## The plan

**Seams.** The loop's `repo` (`Loop.__init__` in `pair/loop.py`) is the
main checkout's root, so its `.env` is `self.repo / ".env"`. `main`'s copy of
the structure is `board.show(self.repo, self.main,
".meta/assertions/structure.yaml")` (`show` in `pair/board.py`). The `Gate`
alias in `pair/loop.py` is the callable's type, `gate` in `pair/pair.py` is
the real gate, and `pair/test_pair.py` has one fake gate, the nested `gate`
in its fixture.

1. **Schema.** Add an optional, multivalued `gate_keys` slot to `Portfolio`
   in `.meta/work/structure.yaml`. Its description says it lists the names of
   variables from the root `.env` that the landing gate is started with, and
   never their values. stereorepo's own `.meta/assertions/structure.yaml`
   declares none, so that file does not change.
2. **Reading values.** In `pair/seats.py`, move the line parsing out of
   `env_names` into a shared helper. Add `env_values(path, names)` beside it,
   which returns `{name: value}` for the lines naming one of `names`. It
   strips one pair of surrounding `"` or `'` from a value, as python-dotenv
   does, and returns nothing if the file is missing or unreadable.
   `env_names` keeps its current behaviour.
3. **Loop.** Add `Loop.gate_env()` in `pair/loop.py`. It parses `main`'s
   `structure.yaml` (`board.show(self.repo, self.main, str(touched.STRUCTURE))`
   through `yaml.safe_load`, as `select` in `pair/touched.py` loads the
   worktree's copy; `show` returns `''` for a missing file) and reads `portfolio.gate_keys`, which counts as empty if
   the file is missing, does not parse or has no slot. It returns
   `env_values(self.repo / ".env", keys)`, leaving out any empty value.
   The `Gate` alias gains a third argument, a `Mapping[str, str]` of the
   declared keys. `run_gate` calls `self.gate(self.wt, targets, env)`
   and then, before anything else reads `out`, calls `redact(out, env)`. That
   function replaces each value, longest first, with `<NAME>`, so
   `gate_fails`, `gate_unrunnable`, `gate_unwritable` and every pause reason
   only ever see the redacted text.
4. **Real gate.** `gate` in `pair/pair.py` takes `env` and passes
   `env={**os.environ, **env}` to `subprocess.run`. An empty `env` is the
   same environment the gate gets today.
5. **Tests** in `pair/test_pair.py`. The fake gate gains an `env` parameter
   and records it in `self.gate_envs`. The fixture writes `.env` into
   `self.repo` (it is untracked, so the worktree never has it), and commits
   `gate_keys` to `main`'s `structure.yaml`.
   - `.env` holds `DECLARED=a` and `OTHER=b`, and only `DECLARED` is
     declared on `main`: the gate receives `{"DECLARED": "a"}`.
   - Nothing is declared: the gate receives `{}`. Also a direct test of
     `pair.gate` with an empty `env`: the `env=` it hands `subprocess.run`
     equals `os.environ` (patch `subprocess.run`).
   - The branch's `structure.yaml` declares `OTHER` and `main`'s does not:
     the gate does not receive `OTHER`.
   - A failing gate prints the value of `DECLARED`: the requirement the
     loop records for the seats (or the pause reason) holds `<DECLARED>`
     and not the value.
   - A declared name missing from `.env` is absent from the gate's `env`.
   - `env_values` covers quotes, `export `, comments and a missing file.
6. **Decision Record.** Write `.meta/assertions/decisions/DR-357.yaml`, or
   one past the highest at the time, following an existing coding DR's
   shape. It says that keys reach the supervisor's gate and never a seat,
   and cites `seats-never-hold-keys`. It says that a live-run Issue stays
   `developer`, and that code on the branch runs with the declared keys.
   Then `just render` and commit `.meta/decisions.md`.

**Risks.**
- Changing `Gate`'s arity breaks any other caller. Search for
  `self.gate(` and `Gate` before the change. Only `run_gate` and the
  fixture are expected.
- Redaction is substring replacement. A short value such as `1` would blank
  unrelated text in the output, which only costs readability. The tail cut
  in `gate_fails` (`GATE_TAIL`) runs after redaction, so a value cut across
  the tail boundary cannot leak.
- Redaction covers the gate's captured output only. A test that writes its
  key to a file in `worktrees/pair` (a log, a cache, a snapshot) leaves it
  where the next seat can read it. This plan does not close that; the
  Decision Record names it with the other thing left open, that a declared
  key is one the developer trusts the branch's tests with.
- `.env` syntax is not standardised. The plan only claims the subset above,
  and a value with multiline or escaped quotes is passed as written.

## As built

- The plan held. `env_names` and `env_values` in `pair/seats.py` share
  `env_lines`, which yields each `(name, raw value)` in file order; a later
  line for the same name wins in `env_values`.
- `Loop.gate_env` also drops a declared name whose value is empty, so an
  `EMPTY=` line behaves like a missing one.
- `redact` is module-level in `pair/loop.py`, beside `gate_fails`, so it can
  be tested without a loop.
- `pair/README.md` gains a paragraph under "How an Issue moves", after the
  pause for unwritable pages, saying where the gate's keys come from. DR-357
  names it in `enacted_in`.
- Tests: `GateKeysTest` in `pair/test_pair.py` covers the four "Done when"
  behaviours, plus a declared value in the reason of a step that could not
  run (the `GateUnrunnable` path, whose pause reason the loop writes to its
  event log), a declared name missing from `.env` or set to nothing,
  `redact`'s longest-first order, and `gate` in `pair/pair.py` passing
  `os.environ` unchanged when no keys are declared.
  `SeatCommandTest.test_env_values_reads_only_the_named_values_and_unquotes_them`
  covers the parser.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/landing-gate-reads-declared-keys.md` and committed it. Difficulty stays `medium`. The issue already said what is wanted, what is out of scope and what tests show it is done. I closed two ways a seat could get a key through the landing gate:
>
> - **Where the list of key names comes from:** the loop now reads it from `main`'s `structure.yaml`, not from the branch being gated. Otherwise a seat could add names to the list on its own branch. A new test covers this: a name declared only on the branch must not reach the gate.
> - **Keys printed in gate output:** when the gate fails, the loop passes its output back to the seats. Before that happens, any declared key's value in the output is replaced with a placeholder naming the variable, such as `<GEMINI_API_KEY>`. A new test checks this: a failing gate that prints a declared value leaves only the placeholder in what the seats see.
>
> I also added a point the Decision Record has to make. Code on the branch runs with the declared keys, so declaring a key means the developer accepts that the branch's tests may use it.

> **secondary, backlog turn 2**
>
> My partner's grooming holds up, and `medium` is the right difficulty. I checked the issue against the code and made three small edits to it, all committed:
>
> - **Where the gate process starts:** the issue now names `gate` in `pair/pair.py` as the place the gate's process is started. `run_gate` in `pair/loop.py` reaches it through the loop's `gate` callable.
> - **Schema file:** the slot for the list of variable names now points to the schema file itself, `.meta/work/structure.yaml`, rather than just the `.meta/work/` directory.
> - **How the keys get passed:** the declared variables must reach the gate through the `gate` callable's signature. That lets the tests in "Done when" inject a fake gate and check which variables it received.
>
> I found nothing missing from what is wanted, what is out of scope or what tests show it is done.

> **primary, backlog turn 3**
>
> I'm leaving the issue as it stands. My partner's three edits check out against the code:
>
> - `run_gate` in `pair/loop.py` does call the loop's `gate` callable, and that callable is `gate` in `pair/pair.py`.
> - `.meta/work/structure.yaml` is the schema file that defines the portfolio.
> - Passing the declared keys through the `gate` callable's signature lets a test swap in a fake gate and check what it received. `pair/test_pair.py` already swaps in a fake gate that way.
>
> Difficulty stays `medium`.

> **primary, todo turn 1**
>
> I've written `## The plan` in `issues/todo/landing-gate-reads-declared-keys.md` and committed it. Nothing is implemented yet. The plan fits the issue as written, so it needs no elaboration section. The steps, in order:
>
> 1. **Schema:** add an optional `gate_keys` list to `Portfolio` in `.meta/work/structure.yaml`. It holds variable names only, never values.
> 2. **Reading `.env`:** add `env_values(path, names)` next to `env_names` in `pair/seats.py`. Both use the same line parsing.
> 3. **Loop:**
>    - A new `Loop.gate_env()` takes the names from `main`'s `structure.yaml`, not the branch's, and reads their values from the `.env` at the main checkout's root.
>    - The loop's `gate` callable takes a third argument for those variables.
>    - `run_gate` replaces each value with `<NAME>` in the gate output before anything else reads it.
> 4. **Real gate:** `gate` in `pair/pair.py` starts its process with `os.environ` plus the declared variables. When nothing is declared, that environment is the same as today's.
> 5. **Tests in `pair/test_pair.py`:** one for each "Done when" item, plus a declared name that is missing from `.env`, plus the edge cases of `env_values`. The existing fake gate records the variables it receives.
> 6. **Decision Record:** write `DR-357`, or the next free number at the time, then run `just render`.
>
> The plan records three risks:
> - **Changing the `gate` callable's arguments** breaks any other caller; I expect only `run_gate` and the one fake gate in the tests.
> - **Replacing values in the output** can also blank out unrelated text when a value is short. That only makes the output harder to read. The output is cut to its tail after values are replaced, so a value cut in half at that point cannot slip through.
> - **`.env` syntax varies.** The reader only handles plain lines, `export `, comments and one pair of surrounding quotes.

> **secondary, todo turn 2**
>
> My partner's plan holds up against the code. I made two additions to it and committed them.
>
> What I confirmed:
> - `show` in `pair/board.py` reads a file as it is on `main`.
> - `env_names` in `pair/seats.py` already has line parsing the new reader can share.
> - The `Gate` type alias in `pair/loop.py` has two callers. One is the real `gate` in `pair/pair.py`. The other is the one fake gate in the `pair/test_pair.py` fixture.
> - `DR-357` is the next free Decision Record number.
>
> What I added:
> - **How `main`'s structure file is loaded:** `Loop.gate_env()` reads `main`'s copy with `board.show(self.repo, self.main, str(touched.STRUCTURE))` and parses it with `yaml.safe_load`. That is how `select` in `pair/touched.py` already loads the worktree's copy. `show` returns an empty string when the file is missing, so a missing file counts as declaring nothing.
> - **A new risk: keys written to disk.** The plan only hides key values in the output the gate prints. If a test writes its key to a file in `worktrees/pair`, such as a log or cache, the next seat can read it there. The plan does not close that gap, so it now says the Decision Record must name it as left open, next to the existing point that a declared key is one the developer trusts the branch's tests with.
>
> The issue can be done as written, so it needs no `# Needs elaboration` section.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands. Both of my partner's additions check out against the code:
>
> - **Loading `main`'s structure file:** `pair/loop.py` already imports `touched`, so `board.show(self.repo, self.main, str(touched.STRUCTURE))` works without a new import. PyYAML is already a dependency of the pair scripts, so `yaml.safe_load` is available too.
> - **Keys written to disk:** the risk is real. The seats' sandbox only denies reading `.env` files at the root of each checkout, so a key a test writes elsewhere in `worktrees/pair` stays readable by the next seat. Naming it in the Decision Record as left open is the right response for this Issue.

> **primary, in-progress turn 1**
>
> I've implemented the plan and committed it. `just gate pair` passes with 255 tests, and so does `just gate meta`.
>
> What changed:
> - **Schema:** `Portfolio` in `.meta/work/structure.yaml` has a new optional list, `gate_keys`. It holds variable names only, never values.
> - **Reading `.env`:** `pair/seats.py` has a new `env_values(path, names)`. It shares its line parsing with `env_names`, strips one pair of surrounding quotes, and lets a later line for the same name win.
> - **Loop:**
>   - A new `Loop.gate_env()` in `pair/loop.py` takes the names from `main`'s `structure.yaml`, never the branch's, and reads their values from the main checkout's `.env`. A name that `.env` lacks or leaves empty is skipped.
>   - `run_gate` passes those values to the gate. Before anything else reads the output, it replaces each value with its name in angle brackets, such as `<GEMINI_API_KEY>`.
> - **Real gate:** `gate` in `pair/pair.py` starts its process with `os.environ` plus the declared keys, so with nothing declared the environment is the same as before.
> - **Tests:** a new `GateKeysTest` in `pair/test_pair.py` covers the four "Done when" behaviours, plus names missing from `.env` or empty there, the order of replacement, and the real gate's environment. Another new test covers `env_values`.
> - **Documents:**
>   - `DR-357` records the rule and what stays open: the branch's tests run with the declared keys, and a key a test writes to a file in the worktree can still be read by the next seat.
>   - `.meta/decisions.md` is re-rendered.
>   - `pair/README.md` has a paragraph saying where the gate's keys come from.
>
> `just gate meta` failed twice on the first run, and I fixed both:
> - The type I had written in the plan was read as a wiki link, so I reworded that line.
> - The citation of `DR-357` in the schema had to read "stereorepo's DR-357" on one line.
>
> The issue file has a new "As built" section for the next reader. The plan held, with one small addition: an empty value in `.env` is skipped like a missing one.

> **secondary, in-progress turn 2**
>
> My partner's implementation matches the plan, and I found nothing wrong with it. I checked these points:
>
> - The real gate and the fake gate in the tests are the only callables of the `Gate` type.
> - Every caller of `run_gate` gets output that has already had the key values replaced.
> - The test `.env` is never committed, so the worktree never has it.
> - `GATE_TAIL` cuts the output after the values are replaced, so a key split at that point cannot slip through.
>
> One path had no test. A gate can pass but report a step it could not run (a `?` line), and that step's reason can print the key. The loop then pauses, and it writes the pause reason to its event log. I added `test_a_declared_value_in_a_step_that_could_not_run_is_redacted` to `GateKeysTest` in `pair/test_pair.py`. It checks that the pause reason holds `<DECLARED>` and not the key's value. I also listed the test in the issue file's "As built" section.
>
> `just gate pair` passes with 256 tests, and `just gate meta` passes. Both changes are committed.

> **primary, in-progress turn 3**
>
> I'm changing nothing this turn. My partner added a test for the one path my tests missed: a gate that passes but reports a step it could not run. That step's reason can print the key, and the loop writes the reason to its event log when it pauses. The new test checks that the reason holds `<DECLARED>` instead of the value, and that is correct. `run_gate` replaces the values in the output before the `GateUnrunnable` check reads it, so this path never saw a key.
>
> I didn't run the gates again, because nothing has changed since my partner's run. They report that `just gate pair` passes with 256 tests and `just gate meta` passes.
