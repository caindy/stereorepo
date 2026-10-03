---
difficulty: easy
---

# Keep python-seed's tools off its gate's standard output

python-seed's gate (`bootstraps/python/seed/gate/src/gate/__init__.py`)
runs ruff, mypy, pytest and mutmut with `subprocess.run` and lets them
inherit standard output. Their output lands between the step reports:
`All checks passed!`, pytest's session banners, and mutmut's spinner lines.
`just audit python-seed python` counted 100 such lines on a clean run and
reports them as a gap against Article 21 (DR-092, DR-353). `.meta/gate`
tolerates them only because it sends unshaped lines to standard error.

## Wanted

The two calls that let a tool inherit standard output, `subprocess.run` in
`tool` and the `mutmut run` call in `mutants`, send the tool's standard
output to the gate's standard error (`stdout=sys.stderr`), so the gate's
standard output is only its step reports and its closing block. Sending it
to standard error rather than capturing it keeps a long run's progress,
mutmut's above all, visible while it runs. The calls that already capture
(`mutmut results` in `mutants`, `pytest --collect-only` in `evidence`)
stay as they are.

`subprocess.run` needs a real file descriptor behind `stdout=sys.stderr`.
Where `sys.stderr` has none (pytest's `capsys` replaces it with an
in-memory stream), the call raises `io.UnsupportedOperation`, a subclass
of `OSError`, and `tool` would silently report the step as one that could
not run. That is why the probe below uses `capfd`, which keeps a real
descriptor behind `sys.stderr`.

## Out of scope

- The closing block that `closing_block` prints when a step could not run;
  whether it should go to standard error is its own question.
- Quoting a failing tool's output as problem lines in the step's report.

## Done when

- A probe in `bootstraps/python/seed/gate/tests/` passes `run` one step
  that calls `tool` on a module printing to standard output, captures at
  the file-descriptor level (`capfd`, since a child process writes to
  descriptor 1, which `capsys` does not see), and finds the module's line
  on standard error and only the step's report on standard output.
- `just audit python-seed python` reports no report-shape gap.

## The plan

All changes are in `bootstraps/python/seed/gate/`.

1. In `src/gate/__init__.py`, pass `stdout=sys.stderr` to the
   `subprocess.run` call in `tool` and to the `mutmut run` call in
   `mutants`. Add a sentence to the docstring of `tool` saying the tool's
   standard output goes to standard error so that the gate's standard
   output carries only step reports (Article 21).
2. In `tests/test_probes.py`, import `tool` and add a probe,
   `test_a_tools_output_stays_off_the_reports`, that takes `tree` and
   `capfd`. It writes a module `loud.py` at `tree.root` that prints a
   marker line, then calls `run(tree.root, [("loud", lambda root:
   tool(root, "loud", [], "loud"))], environ={})`. `python -m` puts the
   working directory on `sys.path`, so `tool` finds the module there. The
   probe asserts that `run` returns 0, that `capfd.readouterr().out` is
   exactly `"ok loud — loud\n"`, and that the marker is in `.err`.
   Written before step 1, the probe fails: the marker appears on standard
   output.
3. Run `just audit python-seed python` and confirm that the report-shape
   gap is gone. This is the only check on the `mutmut run` change: no
   probe runs mutmut, since that would need a package with tests and a
   mutation run inside the probe's tree.

Risks:

- If `sys.stderr` has no file descriptor, `subprocess.run` raises
  `io.UnsupportedOperation`. `tool` catches it as an `OSError` and reports
  the step as one that could not run (see **Wanted**). The probe uses
  `capfd` for this reason. No existing probe sends a real tool step through
  `capsys`: `test_only_a_finding_fails` uses lambdas only. The
  `mutmut run` call does not catch `OSError`, so there the error would
  surface as a traceback instead.
- Anything that reads the gate's standard output for a tool's text loses
  it. `.meta/gate` already sends lines that are not step reports to
  standard error (its `_emit(line, file=sys.stderr, …)` call), so nothing
  upstream depends on them.

## Outcome

Done as planned. The probe `test_a_tools_output_stays_off_the_reports`
failed before the fix (`LOUD` appeared on standard output) and passes after
it. With standard error discarded, `just audit python-seed python` now
reports one gap only: the missing `render` step, which
`issues/backlog/bootstrap-render-step.md` already covers. The audit still
exits non-zero because of that gap.

`ruff format --check` would reformat parts of `src/gate/__init__.py` (the
`CITATION` pattern) and `tests/test_probes.py` (the `FLOOR_CASES` table)
that this change does not touch. The gate checks with `ruff check` but not
`ruff format`, so I left them alone and filed
`issues/backlog/python-seed-gate-format-check.md`.

The docstring of `mutants` now says, as the docstring of `tool` does, that
`mutmut run` prints its progress to standard error.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/python-seed-gate-stdout.md` and committed it as `c4891c42`. It was mostly plan-ready already, so I tightened it rather than rewriting it, and kept `difficulty: easy`.
>
> - **Wanted:** I checked the gate's code and named the two places where a tool's output reaches the gate's standard output. One is the `subprocess.run` call in `tool`, which runs ruff, mypy and pytest. The other is the `mutmut run` call in `mutants`. The issue had offered two fixes; it now settles on one: send that output to standard error (`stdout=sys.stderr`). That keeps a long run's progress visible while it runs, mutmut's above all. The calls that already capture their output (`mutmut results` in `mutants` and `pytest --collect-only` in `evidence`) stay as they are.
> - **Out of scope:** The other fix, quoting a failing tool's output as problem lines in the step's report, is now listed as out of scope, next to the existing note about `closing_block`.
> - **Done when:** The probe now passes `run` a single step that calls `tool` on a module that prints to standard output. It has to capture with `capfd`, because a child process writes straight to file descriptor 1 and `capsys` doesn't see that. It then checks that the module's line appears on standard error and that only the step's report appears on standard output. The existing criterion that `just audit python-seed python` reports no report-shape gap stays.

> **secondary, backlog turn 2**
>
> I checked the groomed issue against the gate's code and it is accurate. The two calls that let a tool print to the gate's standard output are where it says: the `subprocess.run` call in `tool`, and the `mutmut run` call in `mutants`. The calls it leaves alone already capture their output. The `audit` recipe it names in "Done when" exists in the `justfile`. I kept `difficulty: easy`.
>
> I added one paragraph to **Wanted**. Sending a tool's output to `stdout=sys.stderr` only works if `sys.stderr` has a real file descriptor (the operating system's handle for the stream). In tests, pytest's `capsys` replaces `sys.stderr` with an in-memory stream that has no descriptor. The call then raises `io.UnsupportedOperation`, a kind of `OSError`, which `tool` catches, so the step would be reported as one that could not run, with no other sign of what went wrong. That is why the probe has to use `capfd`, and the paragraph says so for whoever builds it.
>
> My attempt to commit was refused because the command needed permission, so the edit is uncommitted and the loop will commit it when my turn ends.

> **primary, backlog turn 3**
>
> I'm keeping my partner's paragraph unchanged, because it's correct. `subprocess.run(stdout=sys.stderr)` needs the operating system's handle for the stream (a file descriptor) behind `sys.stderr`. pytest's `capsys` replaces `sys.stderr` with an in-memory stream that has none. The call then raises `io.UnsupportedOperation`, which is a kind of `OSError`. `tool` catches that and reports the step as one that could not run, without saying why. That's a real trap for whoever writes the probe, and it's why the probe has to use `capfd`.
>
> My only edit was to rewrap one line in **Done when** that had run past the file's line width. I committed it, with my partner's paragraph, as `e49824aa`. `difficulty: easy` stays.

> **secondary, backlog turn 4**
>
> The issue is ready to plan and I left its content alone; `difficulty: easy` stays.
>
> My only change was finishing the rewrap my partner started in the first item under **Done when**. Their edit wrapped the first line, but the next one still ran past the file's line width, so I wrapped that too. I didn't commit it; the loop will commit it when my turn ends.

> **primary, backlog turn 5**
>
> I'm leaving the issue as it stands. It's ready to plan, and my partner's last change, which finished rewrapping the first item under **Done when**, is right. `difficulty: easy` stays.

> **primary, todo turn 1**
>
> I've added `## The plan` to `issues/todo/python-seed-gate-stdout.md` and committed it as `c839d74c`. Nothing is implemented yet. All the changes are in `bootstraps/python/seed/gate/`:
>
> 1. **The fix:** in `src/gate/__init__.py`, pass `stdout=sys.stderr` to the `subprocess.run` call in `tool` and to the `mutmut run` call in `mutants`. A sentence goes in the docstring of `tool` explaining that the gate's standard output is kept for step reports.
> 2. **The test**, written first so it fails before the fix: a new probe in `tests/test_probes.py`, `test_a_tools_output_stays_off_the_reports`.
>    - It writes a small module, `loud.py`, that prints a marker line, and runs it through `run` with one step that calls `tool`. Because `python -m` looks in the working directory, `tool` finds the module there.
>    - Using `capfd`, it checks three things: `run` returns 0, standard output is exactly `ok loud — loud`, and the marker is on standard error.
> 3. **The check:** run `just audit python-seed python` and confirm the report-shape gap is gone.
>
> The plan also records two risks:
> - **Streams with no file descriptor:** if `sys.stderr` is an in-memory stream with no file descriptor behind it, `tool` would quietly report the step as one that could not run. In `mutants`, the `mutmut run` call doesn't catch the error, so it would surface as a traceback. No existing probe sends a real tool through `capsys`: `test_only_a_finding_fails` uses stand-in steps only.
> - **Readers of tool output:** anything that reads a tool's text from the gate's standard output will lose it. The issue says `.meta/gate` already sends lines that aren't step reports to standard error. I took that from the issue and didn't check it in `.meta/gate`.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code and it's right; I added two short clarifications to it. Nothing is implemented, and I didn't commit; the loop will commit when my turn ends.
>
> What I confirmed in the code:
> - **The expected report line:** `rendered` formats a passed step as `ok <label> — <scope>`, so the probe's exact standard output, `ok loud — loud\n`, is correct.
> - **Where the probe gets its directory:** the `tree` fixture gives the probe a temporary directory as `tree.root`, which the probe passes to `tool` as the directory to run in.
> - **Upstream readers of standard output:** `.meta/gate` does send lines that aren't step reports to standard error (its `_emit(line, file=sys.stderr, …)` call). My partner had taken this from the issue without checking, so the second risk holds.
>
> What I added to the plan:
> - **Step 3:** running `just audit python-seed python` is the only check on the `mutmut run` change. No probe runs mutmut, because that would need a package with tests and a mutation run inside the probe's directory.
> - **The second risk:** it now names the `_emit` call in `.meta/gate` that sends those lines to standard error, so the claim can be checked.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands. My partner's two additions are correct and make it easier to check. One notes that running `just audit python-seed python` is the only check on the `mutmut run` change, since no probe runs mutmut. The other names the `_emit(line, file=sys.stderr, …)` call in `.meta/gate` as the evidence for the second risk. The plan is ready to implement.

> **primary, in-progress turn 1**
>
> python-seed's gate now keeps its tools' output off its own standard output: ruff, mypy, pytest and mutmut print to standard error, and only the step reports go to standard output. It's committed as `d9b2df48`, and `just gate meta` and `just gate python-seed` both pass.
>
> - **The fix:** in `bootstraps/python/seed/gate/src/gate/__init__.py`, the `subprocess.run` call in `tool` and the `mutmut run` call in `mutants` now pass `stdout=sys.stderr`. The docstring of `tool` says why.
> - **The test:** the new probe `test_a_tools_output_stays_off_the_reports` in `tests/test_probes.py` runs a small module that prints `LOUD`. It failed before the fix, with `LOUD` on standard output. After the fix, standard output is exactly `ok loud — loud` and `LOUD` is on standard error.
> - **The audit:** with standard error discarded, `just audit python-seed python` no longer reports a report-shape gap, so the issue's second done-when item holds. It still exits non-zero because of one other gap: the gate has no `render` step. `issues/backlog/bootstrap-render-step.md` already covers that, so I didn't file a new Issue.
> - **Formatting I left alone:** `ruff format --check` would reformat two spots I didn't touch: the `CITATION` pattern in `src/gate/__init__.py` and the `FLOOR_CASES` table in `tests/test_probes.py`. The gate runs `ruff check` but not `ruff format`, so it doesn't catch them.
>
> I wrote both of these points under a new `## Outcome` heading in the issue file. The plan held, so it didn't need changing.

> **secondary, in-progress turn 2**
>
> My partner's change does what the issue asks: ruff, mypy, pytest and mutmut now print to the gate's standard error, so its standard output holds only the step reports. The new test, `test_a_tools_output_stays_off_the_reports`, shows it. I made two small additions. `just gate python-seed` and `just gate meta` both pass after them. I didn't commit; the loop will commit when my turn ends.
>
> - **Docstring:** the docstring of `mutants` now says that `mutmut run` prints its progress to standard error. It matches the sentence my partner added to `tool`, so both changed calls are documented.
> - **New backlog Issue:** `issues/backlog/python-seed-gate-format-check.md`. My partner found that `ruff format --check` would reformat code nobody touched in this change: the `CITATION` pattern in `src/gate/__init__.py` and the `FLOOR_CASES` table in `tests/test_probes.py`. The gate never runs that check, so nothing catches this kind of formatting drift. The new Issue asks whether the gate should check formatting; I left out `difficulty` so `just groom` can set it. The issue file's `## Outcome` now points to it and mentions the docstring change.
>
> Nothing else needs to change with this. Neither the seed's READMEs nor the wiki say where the gate's tools send their output.

> **primary, in-progress turn 3**
>
> I'm keeping both of my partner's additions, because both are correct:
> - **Docstring:** the docstring of `mutants` now says that `mutmut run` prints its progress to standard error, as the docstring of `tool` does.
> - **New backlog Issue:** `issues/backlog/python-seed-gate-format-check.md` asks whether python-seed's gate should check formatting. The gate runs `ruff check` but never `ruff format --check`, so nothing reports formatting drift.
>
> My only change was to rewrap one line in the issue file's `## Outcome` that ran past the file's line width. `just gate meta` passes, and I committed it as `b310ab12`. I didn't rerun `just gate python-seed` because I touched no code; my partner reports it passes with their docstring change.

> **secondary, in-progress turn 4**
>
> I'm changing nothing this turn. The work is complete: both calls send their tool's output to standard error, the probe covers it, and both docstrings say so. My partner's only change since my last turn was rewrapping one line of the issue file's `## Outcome`, which is correct. I last ran `just gate python-seed` and `just gate meta` after my own changes, and both passed. Nothing has changed since except that rewrap, which `just gate meta` passed when my partner ran it.
