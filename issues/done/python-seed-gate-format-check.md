---
difficulty: easy
---

# Check formatting in python-seed's gate, or stop expecting it

python-seed's gate runs `ruff check` but never `ruff format --check`, so
formatting drift goes unreported. On `pair/python-seed-gate-stdout`,
`ruff format --check` would reformat code nobody had touched: the `CITATION`
pattern in `bootstraps/python/seed/gate/src/gate/__init__.py` and the
`FLOOR_CASES` table in `bootstraps/python/seed/gate/tests/test_probes.py`.
On this branch, `ruff format --check .` in `bootstraps/python/seed` still
names those two files and no others.

## The developer's decision (2026-10-05)

Honour DR-193, which retired `ruff format --check .` from the Python seed's
gate for its context-window cost and its rebase churn. The gate does not
check formatting, and the rest of the Python standard already says so. The
formatting step an earlier turn wrote was sent back with this Issue and is
not on `main`.

## Wanted

- The `ruff` step's docstring in `bootstraps/python/seed/gate/src/gate/__init__.py`
  says that formatting is not checked, and why, citing DR-193, so the next
  reader does not add the step again.
- A test in `bootstraps/python/seed/gate/tests/test_probes.py` asserts that
  the gate has no formatting step.

## Out of scope

- The Rust seed's `fmt` step, which stays.
- Any change to DR-193 or to the files that already describe it.
- Reformatting the two files named above; with no formatting check, their
  drift is not a defect.

## Done when

- The `ruff` function's docstring in `gate/__init__.py` says formatting is
  not checked and names DR-193.
- A new test passes that fails if any entry of `STEPS` runs `ruff format`:
  no label in `STEPS` is `fmt` (the step DR-193 removed) or `format`, and the
  `ruff` step, with `gate.tool` monkeypatched to record its arguments, calls
  `ruff` with `check` as its first argument and `format` nowhere in them (it
  passes `["check", "."]` today).
- The existing tests in `test_probes.py` still pass.

## The plan

Two files under `bootstraps/python/seed/gate/`; no change to `STEPS`, to
`tool`, or to what the `ruff` step runs.

1. **Docstring.** In `src/gate/__init__.py`, extend the docstring of the
   `ruff` function with a paragraph saying the step lints only:
   `ruff format --check` is deliberately absent, because DR-193 retired it
   for its context-window cost and its rebase churn. Keep the existing
   `Args`/`Returns` sections, and keep lines within the file's line length.
2. **Test.** In `tests/test_probes.py`, add
   `test_the_gate_does_not_check_formatting(monkeypatch)`, near
   `test_a_word_selects_one_step_at_most`:
   - assert no label in `STEPS` is `fmt` or `format`;
   - `monkeypatch.setattr("gate.tool", recorder)`, where `recorder` takes
     `tool`'s signature `(cwd, module, args, scope)`, keeps `cwd`, `module`
     and `args`, and returns `Passed(scope)`; call `ruff(Path("workspace"))`;
     assert exactly one call, `cwd == Path("workspace")`, `module == "ruff"`,
     `args[0] == "check"` and `"format" not in args`. (Recording `cwd` is
     not decoration: an unused `cwd` parameter trips ruff's ARG001.)
   This works because `ruff` resolves `tool` as a module global at call
   time; the test file's own imported `tool` name is untouched, so
   `test_a_tools_output_stays_off_the_reports` is unaffected. Add `STEPS`
   and `ruff` to the existing `from gate import (...)` list (kept sorted, as
   ruff's isort rule requires); the string target needs no `import gate`.
3. Run the seed's tests (`pytest` in `bootstraps/python/seed/gate`) to see
   the new test pass alongside the old ones.

**Risks.** Small. The `comments` step scans this source, so the rationale
belongs in the docstring, not in an inline comment beside the `tool` call.
The `mutants` step does not reach this code (it mutates only members under
`packages/`, and `gate` sits under `bootstraps/python/seed/`), so the
`args[0] == "check"` assertion is there because the Issue asks for it, not
to kill a mutant. No history entry is needed: `evidence` checks only that
existing entries name real tests.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/python-seed-gate-format-check.md`, and `difficulty: easy` stays. The Issue was nearly ready to plan already. It records the developer's decision of 2026-10-05: follow DR-193, which keeps formatting out of the Python seed's gate. It also says what is wanted and what is out of scope.
>
> I changed three things:
>
> - **"Done when" no longer names a gate.** It now checks behaviour: the docstring of the `ruff` function in `gate/__init__.py` must say formatting is not checked and name DR-193.
> - **The test is spelled out.** A new test in `test_probes.py` must find no step in `STEPS` labelled for formatting. With `tool` stubbed to record its arguments, it must also show that the `ruff` step passes `ruff` only `check`. The existing tests must still pass.
> - **One more item is out of scope.** The Issue still names two files that `ruff format` would reformat. Since the gate won't check formatting, those differences aren't a defect, so reformatting them is now listed as out of scope.

> **secondary, backlog turn 2**
>
> I fixed the Issue's test criterion, which was wrong, and left the rest as my partner groomed it, including `difficulty: easy`.
>
> **The problem:** the "Done when" section said the `ruff` step must pass `ruff` only `check`. That isn't true of the code: the `ruff` function in `bootstraps/python/seed/gate/src/gate/__init__.py` calls `tool(root, "ruff", ["check", "."], ...)`. A test written to that wording would either fail against correct code or get bent to fit. The other half of the criterion, "no step labelled for formatting", also left the test writer to guess which labels count.
>
> **What it says now:**
> - No label in `STEPS` may be `fmt` (the step DR-193 removed) or `format`.
> - With `gate.tool` monkeypatched to record its arguments, the `ruff` step must call `ruff` with `check` as its first argument and `format` nowhere among them.
> - It notes that today's arguments are `["check", "."]`.
>
> I also checked that `.meta/assertions/decisions/DR-193.yaml` exists and that it does retire formatting from the Python seed's gate, so the docstring the Issue asks for can cite it as written. The change is committed as d1894319.

> **primary, backlog turn 3**
>
> I'm leaving the Issue as it stands. It's ready to plan, and `difficulty: easy` is right.
>
> My partner was right to correct the test criterion. I had written that the `ruff` step passes `ruff` only `check`, but the `ruff` function in `bootstraps/python/seed/gate/src/gate/__init__.py` passes `["check", "."]`. The new wording fits the code: the first argument is `check` and `format` appears nowhere. It also names the labels the test rejects, `fmt` and `format`, so whoever writes the test doesn't have to guess which labels count.

> **primary, todo turn 1**
>
> I've added `## The plan` to the Issue. The change touches two files under `bootstraps/python/seed/gate/`, and it leaves alone both `STEPS` and what the `ruff` step runs.
>
> 1. **Docstring:** In `src/gate/__init__.py`, the `ruff` function's docstring gets a paragraph saying the step only lints. `ruff format --check` is left out on purpose, because DR-193 retired it for its context-window cost and its rebase churn.
> 2. **Test:** In `tests/test_probes.py`, add `test_the_gate_does_not_check_formatting` with two checks:
>    - No label in `STEPS` is `fmt` or `format`.
>    - With `gate.tool` monkeypatched to record its arguments, `gate.ruff` calls `ruff` with `check` as the first argument and `format` nowhere among them.
>
>    The monkeypatch works because `ruff` looks `tool` up by its module-level name each time it runs. The test file needs `import gate`, plus `STEPS` added to its existing import list.
> 3. **Run:** Run `pytest` in `bootstraps/python/seed/gate` to see the new test pass alongside the old ones.
>
> There are two small risks, both noted in the plan:
> - The `comments` step scans this source file, so the reason has to go in the docstring rather than an inline comment.
> - The `mutants` step can change the `"check"` text in `ruff`, and the `args[0] == "check"` assertion is what catches that. It shouldn't be relaxed to only checking that `format` is absent.

> **secondary, todo turn 2**
>
> I kept my partner's plan and its steps, but corrected two things in it. Nothing is implemented yet.
>
> 1. **The mutants risk was wrong.** The plan said the `mutants` step might change the `"check"` text in `ruff`. It can't: `mutants` only tests packages under `packages/`, and the gate lives under `bootstraps/python/seed/`. The plan now says so. It keeps the `args[0] == "check"` assertion because the Issue asks for it, not to catch a mutant.
> 2. **The import was more complicated than needed.** The plan had the test file add `import gate` next to its existing `from gate import (...)`. The test can instead monkeypatch by name, `monkeypatch.setattr("gate.tool", recorder)`, and add `STEPS` and `ruff` to the existing import list, kept sorted. The plan now also says:
>    - the recorder must take the same arguments as `tool`;
>    - the test file's own imported `tool` is left alone, so the existing test `test_a_tools_output_stays_off_the_reports` is unaffected;
>    - no history entry is needed, because the `evidence` step only checks that existing entries name real tests.
>
> The change is committed as d202bd75.

> **primary, todo turn 3**
>
> I'm leaving the plan as my partner revised it. Both corrections hold up against the code.
>
> - **The mutants risk I wrote was wrong.** The `mutants` step in `gate/__init__.py` runs mutation testing only on packages whose parent directory is `packages`. The `gate` package sits directly under `bootstraps/python/seed/`, so its `ruff` function is never mutated. The `args[0] == "check"` assertion stays because the Issue asks for it.
> - **The import change is simpler and safe.** `monkeypatch.setattr("gate.tool", recorder)` replaces `tool` inside the `gate` module, which is where `ruff` looks it up. It doesn't touch the test file's own imported `tool`, which `test_a_tools_output_stays_off_the_reports` uses.

> **primary, in-progress turn 1**
>
> I've implemented the plan, both gates pass (`just gate python-seed` and `just gate meta`), and the work is committed as 74e0943f.
>
> - **Docstring:** The `ruff` function's docstring in `bootstraps/python/seed/gate/src/gate/__init__.py` now says the step only lints and leaves out `ruff format --check` on purpose. It cites DR-193 and gives its two reasons: formatters spread code over more lines, so an agent has more to read, and their whitespace rewrites cause rebase conflicts between branches being worked on at the same time.
> - **Test:** `test_the_gate_does_not_check_formatting` in `gate/tests/test_probes.py` checks that no label in `STEPS` is `fmt` or `format`. With `gate.tool` monkeypatched, it also checks that `ruff` makes exactly one call, in the directory it was given, running `ruff` with `check` as the first argument and `format` nowhere in the arguments.
>
> The plan needed one change, which I've written into the Issue file. Its stub test function kept only `module` and `args`, so the unused `cwd` argument failed ruff's ARG001 rule on the first gate run. The test now records `cwd` and asserts it as well.
>
> No other documents needed to change, because the Python seed's README already covers DR-193. I didn't find any work outside this Issue.

> **secondary, in-progress turn 2**
>
> I'm changing nothing this turn. My partner's work matches the plan and the Issue's "Done when" list, and both required gates pass.
>
> - **Docstring:** the `ruff` function's docstring in `bootstraps/python/seed/gate/src/gate/__init__.py` says the step only lints, that `ruff format --check` is left out on purpose, and why, citing DR-193.
> - **Test:** I ran `test_the_gate_does_not_check_formatting` in `gate/tests/test_probes.py` on its own and it passes. The gate's `test` step summary showed only 4 tests, which looked short. The full run shows `test_probes.py` is included, with 34 passing. The test would fail if any step were labelled `fmt` or `format`, or if `ruff` were run with anything other than `check` first or with `format` among its arguments.
> - **Other documents:** the other places that describe DR-193 (`bootstraps/python/ratchet.md`, the py-* skills and the Python README) already say formatting isn't checked, so nothing else needs to change with this work.
> - **Gates:** `just gate python-seed` (all 10 steps, mutants included) and `just gate meta` both pass.

Gated by the supervisor at 19:56: `meta`, `python-seed`, `pair`; 107 steps passed.
