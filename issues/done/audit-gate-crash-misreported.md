---
difficulty: easy
---

# `just audit` reports a crashed gate as one that reports nothing

`audit` in `.meta/audit.py` does not read the gate's exit code, so a gate
that dies before printing a step (the Rust seed's gate under a seat's
sandbox, where the `sccache` named by `RUSTC_WRAPPER` is refused and the gate
exits 2 silently) comes out as the `<project>-gate-reports-nothing` gap,
asking for steps the gate already has.

## Wanted

When the gate printed no line in Article 21's step shapes (as `reported` in
`.meta/audit.py` reads them) and exited non-zero, `audit`:

- prints no Issue at all, not even the `-gate-report-shape` gap for any
  stray lines;
- writes to standard error, prefixed `audit:` like `main`'s other messages,
  that the Project's gate failed to run, naming the Project and the gate's
  exit code, and saying the audit could not compare it with the Bootstrap;
- returns 2, so a crashed gate is told apart from a gap (1) and a clean
  audit (0). argparse already exits 2 on a usage error; both mean no
  comparison was made, so sharing the code is acceptable.

The docstrings of `audit` and `main` say so: `audit`'s in place of "its exit
code is not read", and the `Returns` of both name 2.

Unchanged: a gate that printed at least one step is read as now whatever its
exit code (a failing step is still a reported one), and a gate that printed no
step and exited 0 is still the `-gate-reports-nothing` gap.

## Out of scope

Making the Rust seed's gate run under a seat's sandbox (`sccache` and
`RUSTC_WRAPPER`); diagnosing why a gate crashed beyond its exit code.

## Done when

`audit_probes` in `.meta/checks/probes/tools/audit.py` gains cases that:

- run a stub gate that prints nothing and exits non-zero (say `exit 3`), and
  check the audit returns 2, prints no Issue, and its message names the exit
  code;
- run a stub gate that prints only an out-of-shape line and exits non-zero,
  with the same expectations;
- run a stub gate that prints every step and exits non-zero, and check it
  still passes with no gap.

The probes capture the audit's standard error to check the message; `_stub`
there gains an exit code for its gate.

The existing `nothing` case (prints nothing, exits 0) still gives the
`-gate-reports-nothing` gap.

Found while implementing `bootstrap-render-step`.

## The plan

Two files: `.meta/audit.py` and `.meta/checks/probes/tools/audit.py`.

1. **`audit` in `.meta/audit.py`.** After `subprocess.run`, read the steps
   with `reported(run.stdout.splitlines())`. If there are none and
   `run.returncode != 0`, print to `sys.stderr` a line such as
   `audit: python-stub's gate exited 3 before reporting a step, so it could not
   be compared with <standard>`, using the names that `gaps` uses
   (`gate.short(project["id"])`, and the Bootstrap's `name` or short id), and
   return 2 before calling `gaps`. `gaps` stays as it is: it never sees the
   exit code, so a gate that printed nothing and exited 0 is still the
   `-gate-reports-nothing` gap. Parsing the output twice costs nothing worth
   avoiding. The message goes through `sys.stderr` and not through a new
   parameter, because it is a diagnostic and not an Issue; `out` stays for
   Issues only.
2. **Docstrings in `.meta/audit.py`.** The module docstring, after "exits
   non-zero when there is one", says that a gate that exits non-zero without
   reporting a step is said to have failed and gets no Issue. `audit`'s
   docstring replaces "its exit code is not read: a failing step is still a
   reported one" with: the exit code is read only when no step was reported.
   `audit`'s `Returns` becomes 2 when the gate failed before reporting a step,
   1 when there is a gap, and 0 otherwise. `main`'s `Returns` names 2 the same
   way.
3. **The probe.** In `.meta/checks/probes/tools/audit.py`:
   - Each `CASES` entry gains the stub gate's exit status after its lines (0
     for the six existing cases). Add `("a crash", (), 3, 2, ("python-stub",
     "exited 3"))`, `("a stray line, then a crash", ("sccache: refused",), 3,
     2, (...same...))` and `("every step, exiting non-zero", FULL, 1, 0, ())`.
   - `_stub(lines, status)` appends `; exit {status}` to the `printf`, and
     uses `exit {status}` in place of `true` when there are no lines.
     `_repository` takes the same status, and its gate becomes `cat
     report.txt; exit {status}`, so every case also runs through `main
     --repository`. Its docstring, which says "The gate is `cat
     report.txt`", says so too. The status defaults to 0, so the `ELSEWHERE`
     calls are unchanged.
   - Both runs in the `CASES` loop are wrapped in
     `contextlib.redirect_stderr(io.StringIO())`. `_judged` takes the captured
     standard error. When the expected code is 2, it requires that no Issue
     was printed and checks `wanted` against the standard error, not against
     the Issues. Update the docstrings of `CASES` and `_judged`, and add the
     crash rule to the description in `audit_probes`'s docstring.
4. **Run the probe**, and also run `just audit rust-seed rust` by hand under
   the seat sandbox if it still reproduces, to see the new message on the
   real failure. That run is a look, not a test.

**Tests.** The three new `CASES` rows, each run once directly and once through
`main --repository`. The existing `nothing` row still expects code 1 and the
`-gate-reports-nothing` gap.

**Risks.** `redirect_stderr` replaces only `sys.stderr`. The gate's own
standard error goes to file descriptor 2 and still passes through, which is
the behaviour we want, but probe output will show it if a stub ever writes
there (the stubs do not). The audit's exit 2 is the same code argparse uses
for a usage error. That is accepted above. A gate whose shell is killed by a
signal gives a negative `returncode`. The `!= 0` test still counts that as a
failure, and the message prints the number as it is (say "exited -9"); no
probe covers it.

## What was done

As planned, with one departure. Ruff's argument limit (PLR0913, at most
five) rules out giving `_judged` a sixth argument. So it takes the run as one
tuple: what `audit` returned or exited with, what it printed, and what it
printed on standard error. The probe names the expected exit `CRASHED`
rather than writing a bare 2.

Evidence:

- **The probe catches the old behaviour.** With the old `.meta/audit.py`
  put back, `audit probes` fails 16 ways, starting with `a crash: gave 1,
  not 2` followed by the `-gate-reports-nothing` Issue. With the change, it
  passes.
- **The real case.** Run under the seat sandbox, `just audit rust-seed
  rust` exits 2 and says `audit: rust-seed's gate exited 2 before reporting
  a step, so it could not be compared with The Rust standard`. It prints no
  Issue.

No wiki page describes the audit's exits. DR-353 did, though: its
consequences say the exit code is ignored and that a gate reporting no step
is always one gap. The change narrows that, so it is recorded as DR-359,
which the module docstring and `audit_probes` cite, and `.meta/decisions.md`
was re-rendered.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/audit-gate-crash-misreported.md`, set it to `difficulty: easy`, and committed it.
>
> **Wanted.** Today, `audit` in `.meta/audit.py` ignores the gate's exit code. The change applies when the gate printed no step and exited non-zero. In that case `audit` will:
> - print no Issue, not even the gap for out-of-shape lines;
> - write to standard error that the gate failed to run, with the Project's name and the gate's exit code;
> - return 2, so a crashed gate can be told apart from a gap (1) and a clean audit (0).
>
> The docstrings of `audit` and `main` will say this instead of "its exit code is not read".
>
> **Unchanged.** A gate that printed at least one step is read as it is now, whatever its exit code. A gate that printed nothing and exited 0 is still reported as the `-gate-reports-nothing` gap.
>
> **Out of scope.** Getting the Rust seed's gate to run inside a seat's sandbox, and working out why a gate crashed beyond its exit code.
>
> **Done when.** `audit_probes` in `.meta/checks/probes/tools/audit.py` gets three new stub-gate cases:
> - prints nothing and exits non-zero;
> - prints only an out-of-shape line and exits non-zero;
> - prints every step and exits non-zero, which must still pass with no gap.
>
> The existing case that prints nothing and exits 0 must still produce the `-gate-reports-nothing` gap.
>
> Returning 2 and writing the message to standard error are choices I made while grooming; the original issue didn't say either. Your turn can change them if you see it differently.

> **secondary, backlog turn 2**
>
> I checked my partner's grooming against the code and it holds up. `audit` in `.meta/audit.py` runs the gate without looking at its exit code, and the existing `nothing` case in `.meta/checks/probes/tools/audit.py` is the case the issue says must stay unchanged. `difficulty: easy` is right.
>
> I made three small additions to the issue file and committed them:
>
> - **Message prefix:** the new standard-error message starts with `audit:`, like the other error messages `main` already prints.
> - **Exit code 2:** argparse already exits 2 when the command is used wrongly. The issue now says sharing that code is acceptable, because both mean the audit made no comparison.
> - **Docstrings and tests:** the `Returns` sections of both `audit` and `main` must now mention 2. The tests have to capture the audit's standard error to check the message, and the test helper `_stub` needs a way to give its fake gate an exit code.
>
> I kept my partner's choices of exit code 2 and writing the message to standard error.

> **primary, backlog turn 3**
>
> I'm leaving the issue as it is. I checked my partner's three additions against `.meta/audit.py` and kept all of them:
>
> - **Message prefix:** the new standard-error message starts with `audit:`, like the messages `main` already passes to `sys.exit`.
> - **Exit code 2:** argparse already exits 2 on a usage error, and the issue now says sharing that code is acceptable. I agree, because in both cases the audit made no comparison.
> - **Docstrings and tests:** both `audit` and `main` must now mention 2 in their `Returns` sections. The tests capture the audit's standard error, and the test helper `_stub` gets a way to give its fake gate an exit code.
>
> The issue stays at `difficulty: easy`.

> **primary, todo turn 1**
>
> I wrote the plan under `## The plan` in `issues/todo/audit-gate-crash-misreported.md` and committed it. Nothing is implemented yet. The change touches two files:
>
> - **`.meta/audit.py`:** after running the gate, `audit` checks whether any step was reported. If none was and the gate exited non-zero, it writes an `audit:` line to standard error giving the Project, the gate's exit code and the standard. It then returns 2 without calling `gaps`. `gaps` doesn't change, so a gate that prints nothing and exits 0 is still the `-gate-reports-nothing` gap. The module docstring and the docstrings of `audit` and `main` change to match.
> - **`.meta/checks/probes/tools/audit.py`:** each row in `CASES` gets the exit status for its fake gate. `_stub` and `_repository` append `exit N` to the gate command, so every case also runs through `main --repository`. The probe captures standard error with `contextlib.redirect_stderr`. When a case expects 2, `_judged` requires that no Issue was printed and checks the expected text in standard error instead.
>
> **Tests:** three new rows, each run once directly and once through `--repository`:
> - prints nothing, exits 3;
> - prints a stray line, exits 3;
> - prints every step, exits 1, and must still pass with no gap.
>
> The existing case that prints nothing and exits 0 must still give the `-gate-reports-nothing` gap.
>
> **Risks:** only small ones.
> - The capture replaces `sys.stderr` only. A gate's own standard error still goes straight to the terminal, which is what we want.
> - Exit code 2 is the same code argparse uses for a usage error. We already accepted that in grooming.
>
> The plan also suggests running `just audit rust-seed rust` by hand to see the message on the real crash, if it still happens under the sandbox. That's a quick look, not one of the tests.

> **secondary, todo turn 2**
>
> I checked my partner's plan against `.meta/audit.py` and the test file `.meta/checks/probes/tools/audit.py`, and kept it. I added two small details to it and committed them.
>
> **Why the plan holds:**
> - **One reading of the output:** `audit` reads the gate's steps once with `reported` before calling `gaps`. So a gate that prints nothing and exits 0 still reaches `gaps` and still gets the `-gate-reports-nothing` gap.
> - **Empty stub gate:** the plan's `exit {status}` in place of `true` matters. A `printf` given no lines still prints one blank line, which is why `_stub` used `true` for the empty case.
> - **Capturing standard error:** checks run one after another, not in parallel, and other probes already capture output with `contextlib.redirect_stdout` and `redirect_stderr`. So the plan's capture is safe.
> - **Message wording:** the Bootstrap's `name` is "The Python standard", so a message ending "could not be compared with The Python standard" reads correctly.
>
> **What I added:**
> - **`_repository`'s docstring:** it says "The gate is `cat report.txt`", which stops being true once the gate also runs `exit {status}`. The plan now says to update it. It also notes that the status defaults to 0, so the other tests that build a temporary repository don't change.
> - **A gate killed by a signal:** `subprocess` then reports a negative exit code. The `!= 0` check still treats it as a crash and the message prints the number as it is (say "exited -9"). No test covers that case.

> **primary, todo turn 3**
>
> I'm keeping the plan as it stands. I checked my partner's two additions against the probe and the audit:
>
> - **`_repository`'s docstring:** it says "The gate is `cat report.txt`", which stops being true once the gate also ends with `exit {status}`, so updating it is right. Because the new status defaults to 0, the other tests that build a temporary repository (the `ELSEWHERE` cases) don't need to change.
> - **A gate killed by a signal:** the note is accurate. If the shell running the gate is killed, `subprocess` reports a negative exit code, and the `!= 0` check still treats it as a crash. No test covers that case.

> **primary, in-progress turn 1**
>
> I've implemented the change and committed it. `just gate meta` passes. I only touched `.meta/`, so no other Project's gate needed running.
>
> **What changed**
> - **`.meta/audit.py`:** if the gate exits non-zero without reporting any step, `audit` writes one `audit:` line to standard error giving the Project, the gate's exit code and the standard. It prints no Issue and returns 2. Otherwise nothing changes: a gate that reported its steps is compared as before whatever its exit code, and a gate that prints nothing and exits 0 is still the `-gate-reports-nothing` gap. The docstrings of the module, `audit` and `main` now say this.
> - **`.meta/checks/probes/tools/audit.py`:** each test case now sets the exit code of its fake gate. There are three new cases: a gate that crashes with no output, one that prints a stray line and then crashes, and one that prints every step but exits non-zero. The probe captures standard error to check the message, and every case also runs through `main --repository`.
>
> **One change from the plan.** Ruff allows a function at most five arguments, so `_judged` couldn't take a sixth. Instead it takes the run's results (the exit, the printed output and the standard error) as one tuple. I recorded this in the issue file.
>
> **Checks**
> - With the old `.meta/audit.py` put back, `audit probes` fails 16 ways, starting with `a crash: gave 1, not 2`. With the change it passes.
> - Running `just audit rust-seed rust` under the seat sandbox now exits 2 and says `audit: rust-seed's gate exited 2 before reporting a step, so it could not be compared with The Rust standard`. It prints no Issue, where before it printed the wrong `-gate-reports-nothing` Issue.
>
> No wiki page or other document describes the audit's exit codes, so nothing else needed updating.

> **secondary, in-progress turn 2**
>
> I kept my partner's implementation as it was and added the missing Decision Record. I committed it, and `just gate meta` passes all 95 steps.
>
> The code and tests are correct. `audit` returns 2 and prints no Issue only when the gate exited non-zero without reporting a step. Otherwise it calls `gaps` exactly as before. The three new test cases and the exit-0 `nothing` case all check what the issue asks for.
>
> **What I added:**
> - **DR-359:** DR-353, the decision that created `just audit`, still said the gate's exit code is ignored and that a gate reporting no step is always a gap. This change narrows that, and AGENTS.md says a settled question gets a Decision Record. So I wrote `.meta/assertions/decisions/DR-359.yaml` with:
>   - the Rust seed's sandbox crash as context;
>   - the two rejected options: keep ignoring the exit code, or fail on any non-zero exit;
>   - its consequences: the exits are 0, 1 and 2, and 2 is shared with argparse's usage error.
>
>   I re-rendered `.meta/decisions.md` to index it.
> - **Citations:** the module docstring of `.meta/audit.py` and the docstring of `audit_probes` now cite DR-359.
> - **Line wrapping:** I re-wrapped a paragraph in each of those two docstrings that had been left with very uneven lines.
> - **Issue file:** the "What was done" section now names DR-359 and explains why it was needed.
>
> I touched only `.meta/` and the issue file, so no other Project's gate needed running.

> **primary, in-progress turn 3**
>
> I'm keeping my partner's changes and adding nothing. `just gate meta` passes and the working tree is clean.
>
> - **Decision Record:** DR-353, the decision behind `just audit`, still said the gate's exit code is ignored and that a gate reporting no step is always a gap. This change narrows that, so it needs its own record, DR-359. The new record carries no supersession slot: it changes only one consequence of the older decision and leaves the rest standing.
> - **Citations and wrapping:** the module docstring of `.meta/audit.py` and the docstring of `audit_probes` now cite DR-359. The two re-wrapped paragraphs read correctly.
> - **Issue file:** the note on DR-359 in "What was done" is accurate.

> **primary, in-progress turn 4**
>
> The gate failure is fixed. `just gate meta` passes now, and I committed the change.
>
> The failing check was `meta/stated relations`, and it was my own pair note in the issue file. The note said the new record carried no supersession link to the older one, but it named both records alongside the slot. The check reads any sentence naming two Decision Records and a relation slot as a claim that the link exists, and the link does not exist.
>
> I reworded the note so it no longer names the two records alongside the relation. It now says the new record has no supersession link because it changes only one consequence of the older decision. The meaning is the same, and no code or Decision Record changed.

> **secondary, in-progress turn 5**
>
> `just gate meta` failed again when I started this turn, and it passes now; I committed the fix.
>
> The failing check was the same one as last turn, `meta/stated relations`. My partner's turn-4 note explained that failure by quoting the offending wording, which repeated the pattern by naming the older record's supersession slot and the newer record in one phrase. That check reads any sentence naming two Decision Records next to a relation such as `supersedes` as a claim that the link exists. Since the older record's slot does not hold the newer one, the note failed the check itself.
>
> I reworded the note so it no longer names the two records next to the relation. It says the same thing in general terms. Nothing in the code, the tests or DR-359 changed.

> **primary, in-progress turn 6**
>
> `just gate meta` passes again, and I committed the fix.
>
> The same `meta/stated relations` check failed a third time, and again the cause was a pair note. My partner's turn-5 note explained the earlier failure by quoting the bad wording, which repeated the same pattern, so the check flagged the note itself. I reworded that phrase in general terms ("the older record's supersession slot and the newer record") so it no longer names the two records next to the slot.
>
> Future notes should describe this failure without naming the two records at all.
>
> Nothing in the code, the tests or DR-359 changed.

> **secondary, in-progress turn 7**
>
> `just gate meta` failed a fourth time when I started this turn. It passes now, and I committed the fix.
>
> The cause was the same `meta/stated relations` check, and again it was a pair note in the issue file. That check reads any sentence naming two Decision Records next to a relation such as `supersedes` as a claim that the link exists, and DR-353 has no such link to DR-359. Each note that explained the previous failure quoted the offending wording, so it failed the check itself.
>
> I reworded three sentences in the turn-5 and turn-6 notes so none of them names DR-353 and DR-359 together. They now refer to "the older record" and "the newer one", or just state the rule: describe this failure without naming the two records. Two earlier notes still name both records, but with no relation in the same sentence, and the check passes them.
>
> Nothing in the code, the tests or DR-359 changed.

> **primary, in-progress turn 8**
>
> `just gate meta` passes and the working tree is clean, so I'm changing nothing.
>
> My partner's turn-7 note still names both records in one sentence, "DR-353 has no such link to DR-359". The check passes it because the sentence says "link" rather than naming a slot such as `supersedes`. The code, the tests and DR-359 are unchanged and correct, so the issue is ready to leave this stage. Each recent failure came from a note quoting the wording of the one before. Not adding another explanation is the surest way to stop that.
