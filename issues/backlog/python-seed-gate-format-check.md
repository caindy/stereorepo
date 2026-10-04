---
difficulty: developer
---

# Check formatting in python-seed's gate, or stop expecting it

python-seed's gate runs `ruff check` but never `ruff format --check`, so
formatting drift goes unreported. On `pair/python-seed-gate-stdout`,
`ruff format --check` would reformat code nobody had touched: the `CITATION`
pattern in `bootstraps/python/seed/gate/src/gate/__init__.py` and the
`FLOOR_CASES` table in `bootstraps/python/seed/gate/tests/test_probes.py`.
On this branch, `ruff format --check .` in `bootstraps/python/seed` still
names those two files and no others.

## Decision

The gate holds formatting. The Rust seed's xtask already holds it with a
`fmt` step running `cargo fmt --check` (the `fmt` row in
`bootstraps/rust/seed/xtask/README.md`), and A21 makes the gates read alike,
so the Python gate should not be the one that lets formatting drift.

# Needs elaboration

This decision reverses an adopted one, and nothing in this change records
that. DR-193 (`.meta/assertions/decisions/DR-193.yaml`, ADOPTED) retired
exactly this step, `ruff format --check .`, from the Python seed's gate. Its
falsifier is "a formatting check failing the Python seed gate". The harm it
names is the cascade this change produces in `FLOOR_CASES`, where five
one-line or two-line rows become five-line ones. Grooming and planning both
missed it. The rest of the Python standard still says that formatting is
retired:

- the "Mechanical formatting is not a gate check" section of
  `bootstraps/python/ratchet.md`;
- the module docstring of `bootstraps/python/skills/py-git-hooks/lint-gate.py`
  and its `.apm` copy;
- the deliberate-differences paragraph in
  `bootstraps/python/skills/py-quality-setup/SKILL.md` and its `.apm` copy;
- `bootstraps/python/skills/py-refactor/METRICS.md`;
- the Ratchet row's "Held by" column in `bootstraps/python/README.md`
  (generated from `.meta/assertions/bootstraps.yaml`), which lists only
  `lints`, `ruff` and `types`.

The original backlog Issue offered the other outcome: "If it should not, say
why where the `ruff` step is defined." Reversing an adopted decision is the
developer's call, not a seat's, so this Issue is now `difficulty: developer`.
The developer should choose one of the following:

- **Keep the step.** Write a new DR that supersedes DR-193 and weighs its
  reasons (context-window cost, rebase churn) against A21 symmetry with the
  Rust `fmt` step. Then update every file listed above to match.
- **Honour DR-193.** Revert the `formatting` function, its `STEPS` entry, its
  tests, its README row and the reformatting. Then add a sentence to the
  `ruff` docstring in `gate/src/gate/__init__.py` saying that formatting is
  not checked, and why (DR-193). A test could also assert that
  `select("format") == []`. The secondary seat tried this revert in
  in-progress turn 2, and the command was declined at the permission prompt,
  so the implementation is still in place.

## Wanted

- A new step, `format`, in `STEPS` in `bootstraps/python/seed/gate/src/gate/__init__.py`,
  placed right after `ruff`. It runs `ruff format --check .` over the
  workspace through the existing `tool` helper, as the `ruff` function does.
  A separate step rather than a second command in `ruff`, so the report line
  says whether lint or formatting failed, as the Rust `fmt` step does.
- It only checks. Under A5 it never rewrites the tree, so the step must
  never run `ruff format` without `--check`.
- The two drifted files are reformatted with `ruff format`, using the
  `ruff` version pinned in `bootstraps/python/seed/pyproject.toml`, in the
  same change. Nothing else in them changes.
- The step table in `bootstraps/python/seed/gate/README.md` gains a
  `format` row, and the A5 bullet there names `ruff format` beside
  `ruff check --fix` as a fix a person runs.

## Out of scope

- Formatting rules: no `[tool.ruff.format]` settings are added or changed.
- The Rust seed, `.meta/gate`, and the git-hook scripts under
  `bootstraps/python/`.

## Done when

- `uv run gate format` in `bootstraps/python/seed` prints `ok format` with
  what it covered.
- If a file in the workspace is unformatted, the same command prints
  `x format` and exits non-zero, and ruff's `Would reformat:` line naming
  the file reaches standard error, as `tool` routes every tool's output.
- `uv run gate` runs `format` between `ruff` and `types`.
- New tests in `bootstraps/python/seed/gate/tests/test_probes.py`, using the
  `tree` fixture as `test_a_tools_output_stays_off_the_reports` does, show
  that the `format` function returns `Found` for a tree holding an
  unformatted `.py` file and leaves that file's bytes unchanged (A5), and
  `Passed` once the file is formatted.
- `test_a_word_selects_one_step_at_most`, or a new test beside it, shows
  that `select("format")` returns the `format` step.

## The plan

All paths are under `bootstraps/python/seed/`.

1. **Reformat first.** Run `uv run ruff format gate/src/gate/__init__.py
   gate/tests/test_probes.py` (ruff 0.14.0, pinned by the workspace).
   `--diff` shows only two changes: `CITATION` is split over three lines, and
   every multi-line row of `FLOOR_CASES` gets one element per line. No
   `# fmt: skip` is added: the issue says the code is reformatted, not
   exempted.
2. **The step.** In `gate/src/gate/__init__.py`, add `formatting(root)` right
   after `ruff`, with a docstring in the same shape. It returns
   `tool(root, "ruff", ["format", "--check", "."], "ruff format --check over
   the workspace")`. The function is called `formatting`, not `format`, so it
   does not shadow the builtin. Add `("format", formatting)` to `STEPS` right
   after `("ruff", ruff)`. The usage line is built from `STEPS`, so it picks
   up the new step without any other change.
3. **Tests** in `gate/tests/test_probes.py`. Import `formatting`.
   - `test_an_unformatted_file_is_found_and_left_alone(tree)`: write
     `x = ( 1 )\n` to `a.py`, then call `found(formatting(tree.root))` and
     assert that the file's bytes are unchanged.
   - `test_a_formatted_file_passes(tree)`: write `x = 1\n` and call
     `passed(formatting(tree.root))`.

   Both run the real ruff, as `test_a_tools_output_stays_off_the_reports`
   runs a real module. Extend `test_a_word_selects_one_step_at_most` with
   `assert [label for label, _ in select("format")] == ["format"]`.
4. **README.** In `gate/README.md`, add a `format` row after `ruff`
   (`ruff format --check`, the layout ruff's formatter produces; Ratchet),
   and make the A5 bullet read "Fixing is `ruff check --fix` or
   `ruff format`, run by a person".
5. Check by running `uv run gate format`, `uv run gate ruff` and `uv run
   pytest gate` in the workspace.

**Risks.**
- The tests run ruff in `tmp_path`, outside the workspace. Ruff then uses its
  defaults, or a user-level ruff config if one exists. Neither changes the
  verdict on `x = ( 1 )`.
- Reformatting `FLOOR_CASES` makes the table longer but changes no values.
  Splitting `CITATION` over lines could in principle trip a lint rule, such as
  the implicit-concatenation rules. A copy of `gate/`, reformatted and then
  checked with the workspace's ruff config, gave the same findings as the
  copy before reformatting, so `ruff` stays green after step 1.
- `mutants` only mutates `packages/`, so the new function adds no mutants.

## Implementation notes

The plan held as written.
- `uv run gate` now runs 10 steps, with `format` between `ruff` and `types`,
  and every step passes.
- When a line `x = ( 1 )` was appended by hand to
  `gate/src/gate/__init__.py`, `uv run gate format` printed `x  format (1)`
  with the command's exit status, and ruff's `Would reformat:` line, naming
  the file, went to standard error. The file was then restored.
- On its first run, the step also caught a missing space in one of the new
  tests, which was then fixed with `ruff format`.
- The non-zero exit for a `Found` step is already covered by the existing
  `run` tests, so no new test checks it.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/python-seed-gate-format-check.md` and set it to `difficulty: easy`. It's committed as 83f7a793.
>
> - **Decision:** the gate will check formatting. The Rust seed's xtask already does this in its `fmt` step, which runs `cargo fmt --check`. Rule A21 says the gates should report the same way, so the Python gate shouldn't be the only one that lets formatting drift. On this branch, `ruff format --check` flags only the two files the issue names: `gate/src/gate/__init__.py` and `gate/tests/test_probes.py`.
> - **Wanted:**
>   - A separate `format` step goes in `STEPS` (in `gate/src/gate/__init__.py`), right after `ruff`. It runs `ruff format --check .` through the existing `tool` helper, and it never runs `ruff format` without `--check`, because rule A5 forbids a gate step from rewriting files.
>   - The two drifted files get reformatted in the same change, with the ruff version pinned in `pyproject.toml`.
>   - The gate's README gets a `format` row in its step table, and its A5 rule names `ruff format` as a fix a person runs.
> - **Out of scope:** formatting settings, the Rust seed, `.meta/gate`, and the git-hook scripts under `bootstraps/python/`.
> - **Done when:**
>   - `uv run gate format` prints `ok format` with what it covered.
>   - If a file is unformatted, the same command prints `x format`, names the file and exits non-zero. Someone checks this once by hand.
>   - `uv run gate` runs `format` between `ruff` and `types`.
>   - A test, either `test_a_word_selects_one_step_at_most` in `test_probes.py` or a new one beside it, shows that `select("format")` returns the `format` step.

> **secondary, backlog turn 2**
>
> I checked my partner's grooming against the code and it holds up. `STEPS`, the `tool` helper, the `ruff` function, `test_a_word_selects_one_step_at_most` and the README's A5 bullet and step table are all where the issue says they are. Running `ruff format --check .` in `bootstraps/python/seed` still names only the two files the issue lists. The `mutants` step only covers `packages/`, so a new function in `gate` adds no surviving mutants. I left `difficulty: easy` as it was.
>
> I changed two things in "Done when", committed as a17af22e:
>
> - **The hand check is now a test.** The issue had someone check a drifted file by hand once. Instead it now asks for tests in `gate/tests/test_probes.py` that use the `tree` fixture, as `test_a_tools_output_stays_off_the_reports` does. They show that the `format` function:
>   - returns `Found` when a `.py` file is unformatted;
>   - leaves that file unchanged, so A5 ("no gate step rewrites the tree") is held by a test;
>   - returns `Passed` once the file is formatted.
> - **Where the file name appears is now correct.** The issue said `x format` would name the file. It won't: `tool` only reports the exit status, and ruff's own output goes to standard error. The criterion now says the file name comes from ruff's `Would reformat:` line on standard error.

> **primary, backlog turn 3**
>
> I'm leaving the issue as it is. I checked my partner's changes against the code and both are right:
>
> - **The file name appears on standard error, not in the `x format` line.** In `bootstraps/python/seed/gate/src/gate/__init__.py`, the `tool` function sends the tool's own output to the gate's standard error. When the tool fails, its `Found` result holds only the command and its exit status. So ruff's `Would reformat:` line, which names the file, shows up on standard error.
> - **The tests the issue now asks for can be written.** `test_probes.py` has the `tree` fixture, and `test_a_tools_output_stays_off_the_reports` already runs a real module through `tool` in a temporary tree. Tests for the new `format` step can follow the same pattern: one tree with an unformatted file should give `Found` and leave the file unchanged, and one with the file formatted should give `Passed`.
>
> `difficulty: easy` still fits.

> **primary, todo turn 1**
>
> I've written `## The plan` in `issues/todo/python-seed-gate-format-check.md` and committed it as 7fd5ee0e. Nothing is implemented yet. Every path below is under `bootstraps/python/seed/`.
>
> 1. **Reformat the two drifted files first** with the pinned ruff 0.14.0. Ruff's preview of the change shows only two things move: the `CITATION` pattern gets split over three lines, and the multi-line rows of the `FLOOR_CASES` table get one value per line. The plan adds no "skip formatting" markers, because the issue asks for the code to be reformatted, not exempted.
> 2. **Add the step** in `gate/src/gate/__init__.py`: a function called `formatting` (not `format`, which would hide Python's built-in of that name). It runs `ruff format --check .` through the existing `tool` helper. It goes into `STEPS` as `("format", formatting)`, right after `ruff`. The usage message is built from `STEPS`, so it picks up the new step without any other change.
> 3. **Add tests** in `gate/tests/test_probes.py`, using the existing `tree` fixture and the `found` and `passed` helpers:
>    - A file containing `x = ( 1 )` gives `Found`, and its bytes are unchanged afterwards.
>    - A file containing `x = 1` gives `Passed`.
>    - `test_a_word_selects_one_step_at_most` also checks that `select("format")` returns only the `format` step.
> 4. **Update `gate/README.md`**: add a `format` row to the step table, and make the A5 rule name `ruff format` alongside `ruff check --fix` as a fix a person runs.
>
> **Risks are small:**
> - The tests run ruff in a temporary directory outside the workspace, so it uses its defaults or a user-level config. Neither changes the verdict on `x = ( 1 )`.
> - The `FLOOR_CASES` table gets longer, but no values change.
> - The `mutants` step only checks `packages/`, so the new gate function adds no work there.

> **secondary, todo turn 2**
>
> My partner's plan is sound, and I added one line to its risks, committed as 4e3578db. All paths below are under `bootstraps/python/seed/`.
>
> Checks against the code:
> - **Test helpers exist.** The plan's tests rely on the `tree` fixture and the `found` and `passed` helpers, and all three are in `gate/tests/test_probes.py` as the plan assumes.
> - **The new step needs nothing else.** The usage message is built from `STEPS`, so adding `("format", formatting)` there is enough. The `evidence` step only reads history entries, so there's no history file to add.
>
> **The risk I added:** step 1 splits the `CITATION` pattern over several lines, and that could trip a lint rule such as the implicit-concatenation rules. To check, I copied `gate/` to a temporary directory and ran `ruff check` with the workspace's ruff config on the copy before and after reformatting it. Both runs gave the same 65 findings, all `S101` (use of `assert`). They appear only because the copy's paths don't match the workspace rule that allows `assert` in tests. So reformatting adds no lint findings, and the `ruff` step should still pass after step 1.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is. My partner added one risk: step 1 splits the `CITATION` pattern over several lines, which might trip a lint rule. That risk is checked and harmless. The reformatted version still has the pattern as one string literal on a single line, just wrapped in the `re.compile(...)` call, so there is no implicit string joining for a lint rule to flag. My partner also ran ruff's lint check on a copy of `gate/` before and after reformatting, and got the same findings both times.

> **primary, in-progress turn 1**
>
> I've implemented the plan, and it needed no changes. Both `just gate python-seed` (now 10 steps, all passing) and `just gate meta` pass. The work is committed as b43a8758.
>
> All paths are under `bootstraps/python/seed/`.
>
> - **Reformatted code:** I ran `ruff format` on the two drifted files. In `gate/src/gate/__init__.py`, the `CITATION` pattern now spans three lines. In `gate/tests/test_probes.py`, the multi-line rows of the `FLOOR_CASES` table now have one value per line. No values changed.
> - **New step:** `gate/src/gate/__init__.py` has a function called `formatting` that runs `ruff format --check .` through the existing `tool` helper. Its docstring says it never rewrites files, per rule A5. It's in `STEPS` as `("format", formatting)`, between `ruff` and `types`.
> - **Tests:** `test_probes.py` has two new tests:
>   - `test_an_unformatted_file_is_found_and_left_alone`: a file containing `x = ( 1 )` gives `Found`, and the file is unchanged afterwards.
>   - `test_a_formatted_file_passes`: a file containing `x = 1` gives `Passed`.
>
>   `test_a_word_selects_one_step_at_most` now also checks that `select("format")` returns only the `format` step. All 27 tests in `gate` pass.
> - **README:** `gate/README.md` has a `format` row in its step table, and its A5 rule now names `ruff format` alongside `ruff check --fix` as a fix a person runs.
>
> I also checked the step by hand. I added `x = ( 1 )` to a file and ran `uv run gate format`. It reported `x  format (1)` with the command's exit status, and ruff's `Would reformat:` line, which names the file, went to standard error. I then restored the file.
>
> The new step also caught a missing space in one of my own tests on its first run, and I fixed it with `ruff format`.
>
> I didn't run the gate on a drifted file to see its exit code, because the sandbox blocked the command. The existing tests of `run` already check that a step reporting `Found` makes the gate exit non-zero. All of this is under "Implementation notes" in the issue file.

> **secondary, in-progress turn 2**
>
> This change shouldn't land as it stands. It adds the check that an adopted decision, DR-193, removed from the Python seed's gate. I couldn't revert the change because the command was declined, so I've flagged the conflict for you in the Issue file instead (commit b70f7439). `just gate meta` passes.
>
> **What's wrong.** DR-193 is "Retire mechanical formatting from the Python bootstrap gate", and it is adopted. It took out exactly `ruff format --check .`. It counts as proved wrong if "a formatting check fail[s] the Python seed gate", which is what the new `format` step does. The harm it names is long tables pushed into one-value-per-line columns, and that is what happened to `FLOOR_CASES` in `test_probes.py`. Several files in the Python standard still say formatting is retired: `bootstraps/python/ratchet.md`, the `lint-gate.py` git hook, the `py-quality-setup` and `py-refactor` skills, and the "Held by" table in `bootstraps/python/README.md`. My partner and I both missed DR-193 while grooming and planning.
>
> **What I did.** I tried to undo the code, test and README changes, but the command was declined, so the implementation is still in place. In the Issue file I:
> - changed it to `difficulty: developer`, so you check it before it reaches `main`;
> - added a `# Needs elaboration` section that sets out the conflict and every file involved.
>
> **Decision needed: which way should this go?**
> - **Keep the step.** This means a new decision record that overturns DR-193. Its arguments about agents' context windows and rebase churn would have to be weighed against keeping the Python gate in line with the Rust seed's `fmt` step. Every file above would then be updated to match.
> - **Follow DR-193.** This means undoing the new step, its tests, its README row and the reformatting. Then a short note in the `ruff` step's docstring would say formatting is not checked and why. The original backlog Issue offered this option itself: "if it should not, say why where the `ruff` step is defined."
