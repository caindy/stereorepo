---
difficulty: medium
---

# Lint the pair loop with the repository's ruff configuration

`pair/` is not checked by ruff in any gate. The `pair` Project's gate is
`pair/gate.py` (`.meta/assertions/structure.yaml`), and it runs only the
tests. Run against `.meta/ruff.toml`,
`ruff check --config .meta/ruff.toml pair/` with ruff 0.14.0 reports 62 findings
today (counted while grooming; the count drifts as `pair/` changes):
subprocess runs without `check` (PLW1510, 17), long lines (E501, 14), complex functions (C901, 9; PLR0912, 4), vanilla
exception messages (TRY003, 6), too many arguments (PLR0913, 3, including
`append_event`, `Loop.__init__` and one in `pair/seats.py`), and one each of
BLE001 (in `pair/gate.py`), N818 (the `Started` exception in
`pair/test_pair.py`), SIM102, F402, PTH109, PTH208, RUF021, C416 and B905. A `# noqa` written in `pair/` therefore documents a choice but
enforces nothing.

## Wanted

- `pair/gate.py` runs `ruff check` over `pair/` with `.meta/ruff.toml` as a
  step of its own, reported in the gate contract's shape (`ok ruff — ...` or `x  ruff (n)`
  with one indented line per finding), as the `meta ruff` step in
  `.meta/checks/files/python.py` does for `.meta/`. Pin ruff to the version `meta`'s gate pins
  (`ruff==0.14.0` in `structure.yaml`) by adding it to the PEP 723
  `dependencies` of `pair/gate.py`, which `uv run --script` already reads, and
  run it as `sys.executable -m ruff` so that no other route is needed.
- The step runs the whole ruleset, `E501` included. Unlike `meta ruff`, it
  does not hand `E501` to a ratchet: the 14 long lines are fixed.
- Each existing finding is fixed, or suppressed in the
  `# noqa: CODE  # reason: ...` form `.meta/` uses (as in
  `.meta/bundle.py`), with a reason
  that holds. A PLW1510 finding where the return code is read is fixed with
  an explicit `check=False`, not suppressed.
- No fix raises Python above the 3.11 floor `pair/gate.py` declares, though
  `.meta/ruff.toml` targets 3.13.

## Out of scope

- Changing ruff's rule set for the rest of the repository.
- Restructuring the loop beyond what a finding needs; a C901 or PLR0912
  finding that would need a redesign is suppressed with its reason.

## Done when

- `ruff check --config .meta/ruff.toml pair/` reports nothing.
- The `pair` gate's output carries a ruff step reporting `ok`.
- A test in `pair/test_pair.py` runs the ruff step over a temporary
  directory holding a file with an unused import (the step takes the
  directory it lints, `pair/` by default), and asserts that it reports
  `x  ruff (1)` with an `F401` line and counts as a failure, so that
  `pair/gate.py` exits non-zero.
- The pair tests still pass.

## The plan

1. **The step, in `pair/gate.py`.** Add `"ruff==0.14.0"` to the PEP 723
   `dependencies`. Add `CONFIG = HERE.parent / ".meta" / "ruff.toml"` and
   `lint(directory: Path = HERE) -> tuple[bool, list[str]]`, which runs
   `[sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format",
   "concise", "--config", CONFIG, directory]` with `check=False` and returns
   whether it passed and the lines to print: `ok ruff — <directory name>`, or
   `x  ruff (<n>)` followed by one `     <finding>` line per finding. A
   finding is one concise output line of the form `path:line:col: CODE ...`;
   the summary lines (`Found n errors.`, `[*] n fixable ...`) are dropped.
   If the exit code is 2 (ruff itself failed) or `ruff` cannot be imported,
   the step reports `x  ruff (1)` with ruff's stderr as the one line. It
   does not report "could not run" (`?`), because ruff is a declared
   dependency of the script, so a missing ruff is a fault in the gate, not a
   tool for the developer to supply. `main` runs `lint()` after the test
   steps, prints its lines, and sets `failed` when it did not pass.
   `--no-cache` keeps ruff from writing `.ruff_cache/` into the checkout or a
   seat's sandbox.
2. **The test, in `pair/test_pair.py`.** Add `import gate` and a
   `GateLintTest` class with two tests. The first writes `import os\n` into
   a temporary directory and asserts that `gate.lint(tmp)` returns `False`
   with `x  ruff (1)` as its first line and a second line containing
   `F401`. The second writes a clean file and asserts that it returns `True`
   with one `ok ruff` line. Update the module docstring's "Run:" line to
   `uv run --with pyyaml --with ruff==0.14.0 python -m unittest ...`, since
   the test needs ruff installed.
3. **Mechanical fixes,** each preserving behaviour:
   - PLW1510 (17): add `check=False` to every call. Where the result's
     return code is not read, `check=False` keeps today's behaviour exactly;
     making any of them raise would be a behaviour change and is out of
     scope.
   - RUF021 (`grooming_faults` in `pair/board.py`): add the parentheses ruff
     asks for.
   - B905 (the same function): `strict=False`, which is what `zip` does today.
     `strict=True` would be a behaviour change: `now` is deduplicated, but
     `was_now` is filtered from `ranked`, the previous commit's order file
     split as it stood. A slug listed twice there gives `was_now` an extra
     entry, and `strict=True` would raise `ValueError` where the check now
     reports that the ranking moved.
   - C416 (`confinement` in `pair/seats.py`): `set(...)`.
   - SIM102 (`Loop.merge`): join the two `if`s.
   - F402 (the stage-models test in `pair/test_pair.py`): rename the loop
     variable to `name`.
   - PTH208 and PTH109 (two tests in `pair/test_pair.py`): use
     `Path.iterdir()` and `Path.cwd()`.
   - N818 (a `ClaudeSeatTest` test): rename `Started` to `StartedError`.
   - E501 (14): rewrap. The usage lines in the docstrings of `pair/pair.py`
     and `pair/loop.py` are split across two lines, indented as a
     continuation.
4. **TRY003 (6).** The two in `board.py` are fixed: `GitError` gets an
   `__init__(command, where, detail)` that builds the message both raises
   build today, so they pass parts rather than a sentence. The other four
   are suppressed, each with a reason of its own: the `SystemExit` in
   `gate.py` is the text a person sees when the gate refuses
   `PAIR_TEST_WORKERS`; the `ValueError` in `seats.py` refuses a seat
   outside a linked worktree; the two `AssertionError`s are the fake seat's
   test failures, so a class of their own would only rename
   `AssertionError`.
5. **Other suppressions,** each in the `# noqa: CODE  # reason: ...` form:
   - BLE001 (the driving thread in `step`, `pair/gate.py`): any exception in a driving thread must become a
     reported problem, not a lost unit.
   - C901, PLR0912 and PLR0913 (16 findings across `board.py`, `gate.py`,
     `loop.py`, `seats.py` and `test_pair.py`): suppress, each with the
     reason the function is long. For example, `Loop.__init__` takes every
     seam the tests stand a fake in for, and `status` renders every section
     of the board. Splitting them is the redesign the issue puts out of
     scope. Each function gets its own reason, saying what it holds
     together, not a shared "too big to split".
6. Run `ruff check --config .meta/ruff.toml pair/` until it reports nothing,
   then run the pair tests.

**Risks.**

- `.meta/ruff.toml` targets 3.13, so a rewrap or fix that ruff suggests
  might use syntax newer than the 3.11 floor; none of the fixes above does.
- `meta`'s `suppression causes` and `repeated suppressions` steps
  (`.meta/checks/comments.py`) read every tracked Python file, `pair/`
  included. The first fails a reason that names a repository file path
  (anything ending `.py`, `.md`, `.toml` and so on) or a dotted name that
  resolves under `.meta/`. The second fails one rule written with the same
  reason at three sites or more. So a reason names the function by its bare
  name or not at all, never a path, and no reason is copied across sites.
  This is why TRY003 is part fixed and part suppressed with separate
  reasons, rather than suppressed six times with one reason.
- The ruff step runs in every worker's interpreter only through `gate.py`'s
  dependencies; a seat running the tests by the docstring's old route
  would see the new test fail on a missing ruff, which is why the docstring
  changes.

## Where the work left the plan

- **Two complexity findings were fixed, not suppressed.** `status_view` in
  `loop.py` was one point over the limit. Its `waiting` list moved into
  `waiting_on_developer`, which its docstring defers to `status_view` for.
  `ClaudeSeat.send` in `seats.py` lost the loop that drops waiting output
  (now `_drain`) and the summing of `usage` (now `summed`), which together
  took it under the limit. The other 13 complexity and argument-count
  findings are suppressed, each with a reason of its own.
- **`GitError` takes git's arguments, not a sentence.** TRY003 also fires on
  a string literal holding a space, so `GitError("cat-file --batch", ...)`
  still counted. `GitError(args, where, detail)` joins `args` itself; both
  raises now pass a sequence.
- **SIM102 in `merge`** is a single `if` with `and`, and the `if to is not
  None` after it is unchanged.
- **`lint` treats any `path:line:col: ` line as a finding,** syntax errors
  included, which ruff prints in the same shape without a rule code. A
  non-zero exit with no such line (ruff could not read its configuration,
  or is not installed) is reported as `x  ruff (1)` with the last line ruff
  printed.
- **A third `GateLintTest` test checks the exit code.** It points `gate.HERE`
  at an empty directory, so no test module runs, and stands in for `lint`:
  `main` returns 1 when the ruff step fails and 0 when it passes. The first
  two tests check only `lint`'s verdict, not that `main` acts on it.
- **`pair/README.md`** says the gate runs ruff as well as the tests.
- **Plain-text `--fix` output was rewrapped by hand.** Ruff's PLW1510 fix put
  `check=False` on the same line as the next keyword argument in multi-line
  calls; each is now on a line of its own.

## Pair notes

> **primary, backlog turn 1**
>
> The issue was already groomed well enough to plan from: it says what is wanted, what is out of scope, and how to tell it is done, and it doesn't name a gate as the test. I left `difficulty: medium` as it was and made three corrections after checking the claims against the code:
>
> - **Finding count:** running `ruff check --config .meta/ruff.toml pair/` with ruff 0.14.0 now reports 62 findings, not 60. There are 14 long lines (E501) instead of 13, plus one N818 that wasn't listed: the `Started` exception in `pair/test_pair.py`. I also noted that the count will keep changing as `pair/` changes. The done condition doesn't depend on it, because it asks for ruff to report nothing.
> - **Model for the new step:** the issue said to copy how `.meta/check.py` runs ruff, but that file doesn't run it. The ruff step is in `.meta/checks/files/python.py`, so the issue now points there and spells out the output shape the step should print.
> - **Suppression example:** the `# noqa: CODE  # reason: ...` form is now shown with a real example from `.meta/bundle.py`.
>
> Committed as d846eba.

> **secondary, backlog turn 2**
>
> I checked my partner's grooming against the code and fixed four gaps in `issues/underway/pair-ruff-lint.md`. `difficulty` stays `medium`. Committed as c6c7a02.
>
> - **How ruff gets into the `pair` gate:** the gate runs as `uv run --script pair/gate.py`, and its only dependency is pyyaml, so ruff wasn't available to it. The issue now says to add `ruff==0.14.0` to the script's own dependency list and run it as `sys.executable -m ruff`. It also uses the step's real name, `meta ruff`, where it had said `ruff`.
> - **Long lines:** the `meta ruff` step skips the long-line rule (E501) because a separate step counts those against a baseline. The issue didn't say whether `pair/` should do the same. It now says the `pair/` step checks every rule, so the 14 long lines get fixed.
> - **Python version:** `.meta/ruff.toml` targets Python 3.13, but `pair/gate.py` must still run on 3.11. The issue now says no fix may use anything newer than 3.11.
> - **How to tell it's done:** "add an unused import to `pair/loop.py`" was a manual check. It's now a test in `pair/test_pair.py`: run the ruff step over a file with an unused import and check that it reports `x  ruff (1)` with an F401 line and that the gate exits non-zero.

> **primary, backlog turn 3**
>
> I checked my partner's four changes against the code and kept all of them:
>
> - **Long lines:** the `meta ruff` step in `.meta/checks/files/python.py` does skip E501 (long lines) and leaves them to a separate step. So it's right that the `pair/` step checks every rule and the 14 long lines get fixed.
> - **Python version:** `.meta/ruff.toml` targets Python 3.13. The note that fixes must still run on 3.11 is correct.
> - **Ruff dependency and name:** adding ruff to the gate script's own dependencies, and using the step's real name `meta ruff`, both match the code.
>
> I changed one thing: the done condition for the new test. As written, it ran "the ruff step" over a temporary directory but then checked "the gate's" exit code. That can't work unless the step can be pointed at a directory other than `pair/`. It now says the step takes the directory it lints (`pair/` by default). The test runs it over a temporary file with an unused import, checks that it reports `x  ruff (1)` with an F401 line, and checks that this counts as a failure that makes `pair/gate.py` exit non-zero.
>
> `difficulty` stays `medium`. Committed as 3933068.

> **secondary, backlog turn 4**
>
> I'm leaving the issue as it is; it's ready to plan.
>
> My partner's one change was needed. The test needs the ruff step to accept a directory other than `pair/`, so it can be run on a temporary file with an unused import. The issue now says so, and checks the gate's failure through the step's verdict rather than by running the whole gate. Pointing the step at a temporary directory works, because `--config .meta/ruff.toml` applies the rules wherever the files are. `difficulty: medium` still fits.

> **primary, todo turn 1**
>
> I added a `## The plan` section to `issues/todo/pair-ruff-lint.md`. The issue can be done as written, and nothing is implemented yet. Committed as 3db6144.
>
> **Steps, in order:**
>
> 1. **The ruff step in `pair/gate.py`:**
>    - Add `ruff==0.14.0` to the script's dependencies and add a `lint(directory=HERE)` function.
>    - `lint` runs ruff on the directory with `.meta/ruff.toml`, and with `--no-cache` so it never writes a `.ruff_cache/` into the checkout or a seat's sandbox.
>    - It returns pass or fail plus the lines to print: `ok ruff — ...`, or `x  ruff (n)` with one indented line per finding.
>    - If ruff itself breaks, the step reports a failure, not "could not run", because ruff is a declared dependency of the script.
>    - `main` runs it after the test steps and fails the gate when it fails.
> 2. **The test in `pair/test_pair.py`:** one test checks that a temporary file with an unused import gives `x  ruff (1)` with an F401 line and a fail result. A second checks that a clean file gives `ok`. The docstring's instructions for running the tests by hand also need `--with ruff==0.14.0`, or the new test fails there for lack of ruff.
> 3. **Fixes that don't change behaviour:**
>    - `check=False` on all 17 PLW1510 calls.
>    - `strict=True` on the `zip` call (B905); the two lists are always the same length.
>    - Rewrap the 14 long lines.
>    - Small rewrites for RUF021, C416, SIM102, F402, PTH208, PTH109 and N818 (`Started` becomes `StartedError`).
> 4. **TRY003 (6):**
>    - The two in `board.py` are fixed: `GitError` builds its own message from the parts it is given.
>    - The other four are suppressed, each with its own reason.
> 5. **The 16 complexity and argument-count findings, and the BLE001:** suppressed, one reason per function. Splitting those functions up is the redesign the issue rules out.
> 6. **Check:** run ruff over `pair/` until it reports nothing, then run the pair tests.
>
> **Main risk, found while planning:** two of `meta`'s checks (`suppression causes` and `repeated suppressions`) read every tracked Python file, `pair/` included.
> - The first fails a suppression whose reason names a repository file path, or a dotted name defined under `.meta/`.
> - The second fails the same rule and reason written at three or more places.
>
> So no reason may name a file path, and none may be copied across sites. This is why TRY003 is partly fixed and partly suppressed with separate reasons, rather than suppressed six times with one reason. The other risk is the Python version: `.meta/ruff.toml` targets 3.13, but none of the planned fixes needs anything newer than 3.11.

> **secondary, todo turn 2**
>
> I kept my partner's plan except for one step that would have changed behaviour, which I corrected (commit 8e9d9df). I couldn't run ruff myself because the command needed approval, so I checked the plan by reading the code.
>
> **The correction:** the plan put `strict=True` on the `zip` call in `pair/board.py` at line 783, claiming the two lists always have the same length. They don't always:
> - `now` has its duplicates removed.
> - `was_now` is filtered from the previous commit's ranking as it was written, so a slug listed twice there leaves `was_now` with an extra entry.
>
> With `strict=True`, that case would raise `ValueError`, where today the code reports that the ranking moved. The plan now says `strict=False`, which is what `zip` already does by default.
>
> The rest of the plan matches the code:
> - **Error messages:** only two places raise `GitError`, both in `board.py`. Moving its message into the class keeps the existing test passing: it checks for the word "missing" in the message, which the new version still produces.
> - **Test instructions:** nothing outside `test_pair.py` runs the pair tests by another route. Updating its docstring's run line to include ruff is enough.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is; it's ready to implement.
>
> My partner's one change is right, and I checked it against the code. In `pair/board.py`, `held` is built straight from `ranked`, which is the previous commit's order file as written. If a slug is listed twice there, it appears twice in `held` and twice in `was_now`, while `now` has its duplicates removed. The two lists passed to `zip` can then differ in length, so `strict=True` would raise a `ValueError` where the check today reports that the ranking moved. `strict=False` keeps today's behaviour, and the plan now says so.

> **primary, in-progress turn 1**
>
> The `pair` gate now runs ruff over `pair/` with `.meta/ruff.toml`, and all 62 findings are gone. Both targeted gates pass: `just gate pair` (229 tests, and the ruff step reports `ok`) and `just gate meta`. Committed as 54607d4.
>
> - **The step:** `pair/gate.py` adds `ruff==0.14.0` to its script dependencies and has a new `lint(directory)` function. It runs after the test steps and prints `ok ruff — pair/`, or `x  ruff (n)` with one line per finding, and a failure makes the gate exit non-zero. If ruff itself breaks, that is reported as a failure, because ruff is a declared dependency of the script.
> - **Tests:** a new `GateLintTest` in `pair/test_pair.py` checks two cases. A file with an unused import gives `x  ruff (1)` with an F401 line and a fail result; a clean file gives `ok`. The docstring's instructions for running the tests by hand now include `--with ruff==0.14.0`.
> - **Fixed rather than suppressed:**
>   - All 17 subprocess findings got `check=False`, which keeps their current behaviour.
>   - The 14 long lines are rewrapped.
>   - The small rule fixes went as planned; the `zip` call got `strict=False`, as my partner corrected.
>   - `GitError` now takes git's arguments and builds its own message.
> - **Two departures from the plan:**
>   - Two of the complexity findings were fixed with small helper extractions instead of being suppressed: `status_view` and `ClaudeSeat.send`.
>   - `GitError` takes a sequence of arguments rather than a command string. Ruff also flags a string literal with a space in it, so passing `"cat-file --batch"` would still have been reported.
> - **Suppressed:** the remaining 13 complexity and argument-count findings, four of the error-message findings, and the catch-all `except` in the gate's worker threads. Each suppression has its own reason, and no reason names a file path, so `meta`'s suppression checks accept them.
> - **Issue-file fix:** `meta` first failed on the plan's `file.py:line` references, which don't resolve as repository paths. They now name the functions instead.
> - **Docs:** the comment in `.meta/assertions/structure.yaml` that said the pair gate is only its tests now mentions the ruff step.
>
> The departures and the reasons behind them are written up under "Where the work left the plan" in the issue file.

> **secondary, in-progress turn 2**
>
> My partner's implementation was sound; I filled two gaps and committed them as fffbe70. `just gate pair` passes (230 tests, and the ruff step reports `ok ruff — pair/`), and so does `just gate meta`.
>
> - **The gate's exit code was untested.** The two new tests checked only what `lint` reports for a temporary directory, not that `main` fails the gate when ruff finds something. I added a third test in `pair/test_pair.py` that points the gate at an empty directory, so no test files run, and fakes `lint`'s result. It checks that `main` returns 1 when the ruff step fails and 0 when it passes.
> - **The README was out of date.** `pair/README.md` still said the `pair` gate is only the loop's tests. It now says the gate also runs ruff over `pair/`, so a `# noqa` written there is actually checked.
>
> I also read the rest of my partner's diff and changed nothing else:
> - Every subprocess call that got `check=False` behaves exactly as before.
> - The `zip` call kept `strict=False`, as the plan says.
> - The function names my partner gave in the plan in place of `file.py:line` references are correct.
>
> Both changes are noted under "Where the work left the plan" in the issue file.

> **primary, in-progress turn 3**
>
> I'm changing nothing this turn; both of my partner's additions are correct.
>
> - **The exit-code test:** `main` calls `lint` from the module at run time, so faking `gate.lint` in the test does replace the real ruff step. Pointing the gate at an empty directory means no test files run, so the fake ruff verdict alone decides whether `main` returns 1 or 0. The test also restores `sys.path`, which `main` changes when it starts. The way it groups several `with` items in parentheses needs Python 3.10, within the 3.11 floor.
> - **The README line:** it is accurate. It sits with the other text about the `pair` gate in `pair/README.md`, alongside the comment I updated in `.meta/assertions/structure.yaml`.
>
> My partner reports that `just gate pair` (230 tests, ruff step `ok`) and `just gate meta` both passed on that commit. Since nothing has changed since then, I didn't run them again.
