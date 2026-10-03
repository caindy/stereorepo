---
difficulty: medium
waits_on: [bootstrap-audit]
---

# Audit a Project that lives in another repository

`just audit <project> <bootstrap>` (DR-353) runs from a stereorepo checkout
and audits only the Projects stereorepo's own `structure.yaml` asserts:
`.meta/audit.py`'s `main` reads the Projects through `gate.structure()` and
`audit` runs the gate with `cwd=gate.ROOT`, both stereorepo's root. It is
scaffold-only because the bootstrap records it compares with
(`.meta/assertions/bootstraps.yaml`) do not ship to a portfolio. DR-312's
audit is for a brownfield product, which lives in its own repository, so
today the audit cannot reach the product it exists for.

## Wanted

- The audit takes a target repository, as `just adapt plan <repository>`
  does. It reads the named Project and its gate from that repository's
  `.meta/assertions/structure.yaml`, runs the gate with that repository's
  root as its working directory, and compares what it reports with
  stereorepo's Bootstrap, exactly as it does today.
- With no target, it behaves as today.
- How the target is passed (an optional flag on `audit`, such as
  `--repository <path>`, or a second recipe) is the pair's choice within
  DR-349: recipes take only flags, subcommands and atomic identifiers. If
  the recipe's signature changes, the `audit` entry in `justfile()` in
  `.meta/lib/render/writers.py` and the recipe contract in
  `.meta/checks/files/justfile.py` change with it.
- A target with no `.meta/assertions/structure.yaml`, or one that does not
  assert the named Project, exits with a message naming the repository and
  what is missing, as an unknown Project does today.

## Out of scope

- Adopting a repository that has no `structure.yaml` yet; that is
  `just adapt`'s business.
- Shipping the audit or the bootstrap records to a portfolio.

## Done when

- A probe case in `.meta/checks/probes/tools/audit.py` builds a temporary
  repository whose `structure.yaml` asserts one Project with a stub gate,
  audits it through `main` with that repository as the target, and finds the
  same gaps the existing probe cases find for the same stub output. The stub
  gate prints its report from a file that exists only in the temporary
  repository (`cat report.txt`, say), so the case fails if the gate runs
  from stereorepo's root.
- Probe cases audit a temporary directory with no `structure.yaml`, and a
  temporary repository whose `structure.yaml` does not assert the named
  Project; each ends `main` with a message naming the repository and what is
  missing, not a traceback.
- The existing probe cases, which audit with no target, pass unchanged.

## Pair notes

> **primary, backlog turn 1**
>
> I made one small change to `issues/underway/audit-another-repository.md` and committed it. The rest of the issue was already precise enough to plan. I checked its claims against the code and they hold:
> - `main` in `.meta/audit.py` reads the Projects through `gate.structure()`.
> - `audit` runs the gate with `cwd=gate.ROOT`, which is stereorepo's root.
> - The recipe's signature is set in two places: the `audit` entry in `writers.py` and the recipe contract in `.meta/checks/files/justfile.py`.
>
> I left `difficulty: medium` as it was. The change only tightens **Done when**:
> - **The gate must really run in the target.** The probe's stub gate now has to print its report from a file that exists only in the temporary repository, for example `cat report.txt`. As first written, the test would still pass if the gate ran from stereorepo's root, because the stub prints the same thing from anywhere.
> - **The second refusal case is now tested.** The issue asks for a message in two cases: a target with no `structure.yaml`, and a target that doesn't assert the named Project. Only the first had a probe case. Each must now end `main` with a message naming the repository and what is missing, not a traceback.

> **secondary, backlog turn 2**
>
> I made no changes. The issue is precise enough to plan, and `difficulty: medium` is right.
>
> I checked its claims against the code, and they hold:
> - **Where the Projects come from:** `main` in `.meta/audit.py` reads them through `gate.structure()`.
> - **Where the gate runs:** `audit` runs it with `cwd=gate.ROOT`, which is stereorepo's own root.
> - **The dependency:** the issue it waits on, `bootstrap-audit`, is already in `issues/done/`.
> - **The recipe:** it takes two fixed arguments, `audit project bootstrap:`. So taking a target means a change of signature within DR-349 (recipes take only flags, subcommands and atomic identifiers), and the issue already names the two other places that must change with it.
>
> Your partner's tightening of **Done when** fixes what was weakest:
> - **The gate really runs in the target.** The stub gate prints its report from a file that exists only in the temporary repository, so the test fails if the gate runs from stereorepo's root.
> - **Both refusals are tested.** The issue asks for a message in two cases (a target with no `structure.yaml`, and one that does not assert the named Project), and each now has a probe case.
>
> The rest is clear about scope, and its tests check behaviour through `main`, not a gate.

## The plan

The target is an optional `--repository <path>` flag. The recipe becomes
`audit project bootstrap *args:` running `.meta/audit.py {{project}}
{{bootstrap}} {{args}}`, so the two identifiers stay as they are and the
tail is flags only (DR-349). Bootstraps and Discipline names are still read
from stereorepo; only the Projects and the gate's working directory move to
the target.

1. **`.meta/gate`.** Give `structure` an optional `path` parameter that
   defaults to `STRUCTURE`, so the audit reuses the loader instead of
   copying it. The one existing caller, in `.meta/gate` itself, is
   unchanged.
2. **`.meta/audit.py`.**
   - `audit` gains a `root: pathlib.Path = gate.ROOT` parameter and passes it
     as the gate's `cwd`.
   - `main` parses its arguments with `argparse` (`project`, `bootstrap`,
     `--repository`). It resolves the target with `pathlib.Path(...).resolve()`
     and reads `<target>/.meta/assertions/structure.yaml` through
     `gate.structure(path)`. A target with no such file exits with
     `audit: <target> has no .meta/assertions/structure.yaml` and points to
     `just adapt plan`. A Project the target does not assert gets today's
     unknown-Project message, naming the target as well. With no
     `--repository`, `main` reads `gate.structure()` and runs from
     `gate.ROOT`, as it does today.
   - `argparse` parses `argv[1:]` with `prog="audit.py"`, so the existing
     `UNKNOWN` probe cases, which pass the script name first, keep working.
     A wrong number of arguments then exits with argparse's usage message
     and code 2 instead of today's `usage:` string; no probe pins the old
     one.
   - A `--repository` that does not exist, or is a file, has no
     `structure.yaml` beneath it, so it takes the same message: test with
     `is_file()` on the structure path, not `exists()` on the target.
   - The `projects` parameter keeps its meaning: when given, it replaces
     whichever `structure.yaml` would be read, and `--repository` still
     sets where the gate runs. The no-`structure.yaml` check applies only
     when `projects` is `None`.
   - `main` gains an `out: IO[str] | None = None` parameter and hands it to
     `audit`. `audit`'s default `out=sys.stdout` is bound when the module is
     imported, so `contextlib.redirect_stdout` cannot capture it, and the
     probe needs some way to read what `main` prints.
   - Update the module docstring and `main`'s docstring for the flag.
3. **`.meta/lib/render/writers.py`.** Change the `audit` `ConditionalRecipe`
   to the new signature, and mention `--repository` in its doc comment.
   Re-render the `justfile`.
4. **`.meta/checks/files/justfile.py`.** Change the `CONTRACT` entry for
   `audit` to `(("project", IDENTIFIER), ("bootstrap", IDENTIFIER),
   ("args", FLAGS))`.
5. **`.meta/checks/probes/tools/audit.py`.** Add cases that build a
   `tempfile.TemporaryDirectory`:
   - **Each `CASES` entry, run through the target.** The target's
     `structure.yaml` asserts `work:project/python-stub` with the gate
     `cat report.txt`, and `report.txt` holds that case's lines, which exist
     only in the target. Call `main(["audit.py", "python-stub", "python",
     "--repository", tmp], out=said)`. Expect the same exit code and the same
     substrings as the case run without a target.
   - **A target with no structure.yaml.** `main` exits, and the message
     carries the target's path and `structure.yaml`.
   - **A target that does not assert the Project.** `main` exits, and the
     message carries the target's path and the missing Project's name.

   The existing `CASES` and `UNKNOWN` loops stay as they are.
6. **DR-358.** Record the flag, and that the gate runs from the target's
   root while the Bootstraps stay in stereorepo. It amends DR-353's
   consequence "It audits the Projects stereorepo asserts". Re-render, so
   that `.meta/decisions.md` picks it up.

**Tests.** The new probe cases in step 5, and the existing cases passing
unchanged. The justfile shape check, run against the re-rendered
`justfile` and the new contract, shows that the recipe and the contract
agree.

**Risks.**
- **Relative paths.** `just` runs a recipe from the justfile's directory,
  so `--repository ../product` resolves against stereorepo's root, not
  against the directory the developer typed it in. `just adapt` behaves the
  same way. Say so in the flag's help.
- **The target's gate runs on this machine.** Its gate command comes from the
  target's own `structure.yaml` and runs with `shell=True`. That is the
  point of the audit, but the flag's help should say it runs the target's
  gate.
- **Overlap with `audit-gate-crash-misreported`.** That backlog Issue also
  touches `audit` and the probe. Leave the exit-code handling to it, so the
  two changes stay apart.

## Pair notes

> **primary, todo turn 1**
>
> I've added `## The plan` to `issues/todo/audit-another-repository.md` and committed it. Planning didn't turn up anything that blocks the issue, so it has no `# Needs elaboration` section.
>
> **How the target is passed:** an optional `--repository <path>` flag. The recipe becomes `audit project bootstrap *args`, which keeps within DR-349 (recipes take only flags, subcommands and atomic identifiers). The Bootstraps are still read from stereorepo. Only two things move to the target: where the Projects are read from, and the directory the gate runs in.
>
> **Steps, in order:**
> 1. **`.meta/gate`:** `structure` gets an optional `path` argument, so the audit can reuse it to read the target's `structure.yaml`. Its one existing caller doesn't change.
> 2. **`.meta/audit.py`:**
>    - `audit` takes a `root` and runs the gate from it.
>    - `main` reads its arguments with `argparse` and gives the two new error messages.
>    - `main` gains an `out` argument. The probe needs it: `audit` binds `sys.stdout` when the module loads, so redirecting stdout can't capture what it prints.
> 3. **The recipe:** the `audit` entry in `writers.py` and its entry in `CONTRACT` in `.meta/checks/files/justfile.py` change together, and the `justfile` is re-rendered.
> 4. **Probe cases** in `.meta/checks/probes/tools/audit.py`:
>    - Every existing case is also run through `main` against a temporary repository whose gate is `cat report.txt`. That file exists only in the target, so a case fails if the gate runs from stereorepo's root.
>    - Two refusal cases: a target with no `structure.yaml`, and a target that doesn't assert the named Project.
> 5. **A new Decision Record:** it amends DR-353, which says the audit "audits the Projects stereorepo asserts". The plan calls it DR-358, but it should take whatever number is next when it's written.
>
> **Risks:**
> - **Relative paths:** `just` runs recipes from the repository root, so a relative `--repository` path resolves from there, not from where the developer typed it. `just adapt` behaves the same way. The flag's help will say so.
> - **The target's gate runs on this machine:** the command comes from the target's own `structure.yaml`. That is what the audit is for, but the help should say so.
> - **Overlap with another Issue:** `audit-gate-crash-misreported` in the backlog touches the same function and probe. It keeps the exit-code handling, so the two changes don't mix.

> **secondary, todo turn 2**
>
> I checked your partner's plan against the code and it holds up. I added three points to step 2 of `## The plan` and committed them. There is no `# Needs elaboration` section.
>
> **What I checked:**
> - **The one caller:** `gate.structure()` is called only by `.meta/gate` itself and by `main` in `.meta/audit.py`, so giving it a `path` parameter that defaults to today's file is safe.
> - **The recipe contract:** `CONTRACT` in `.meta/checks/files/justfile.py` already has the `FLAGS` kind, so `audit project bootstrap *args` fits it.
> - **The `out` parameter:** this is really needed. `audit`'s default output is fixed when the module loads, so redirecting standard output cannot capture what `main` prints.
> - **The Decision Record:** the highest record today is DR-357, so DR-358 is the next number. DR-353 does say the audit covers only the Projects stereorepo asserts.
>
> **What I added:**
> - **Argument parsing:** `argparse` must parse `argv[1:]` with `prog="audit.py"`. The existing probe cases for unknown names put the script name first, so they keep working. The cost is that a wrong number of arguments now gets argparse's own usage message and exit code 2, not today's `usage:` line. No probe checks the old message.
> - **A target that does not exist, or is a file:** it gets the same "no `structure.yaml`" message. The check is `is_file()` on the path to `structure.yaml`, not `exists()` on the target.
> - **`main`'s existing `projects` parameter:** the plan didn't say how it combines with `--repository`. When `projects` is given, it replaces whichever `structure.yaml` would have been read, and `--repository` still sets the directory the gate runs in. The missing-file check only applies when `projects` is not given.

> **primary, todo turn 3**
>
> I changed nothing; the plan is ready to implement. I checked your partner's three additions to step 2 against the code, and each is correct:
>
> - **Argument parsing:** parsing `argv[1:]` with `prog="audit.py"` keeps the existing unknown-name probe cases in `.meta/checks/probes/tools/audit.py` working, because they pass the script name first. The cost is that a wrong number of arguments now gets argparse's own usage message and exit code 2, not today's `usage:` line. No probe checks that line, so nothing breaks.
> - **A target that is missing or is a file:** checking `is_file()` on the path to `structure.yaml` means both cases get the same "no `structure.yaml`" message, with no extra branch.
> - **`main`'s `projects` parameter:** when it is given, it still replaces whatever `structure.yaml` would be read, and `--repository` still sets where the gate runs. The missing-file check applies only when `projects` is not given. This keeps the existing probe calls working and doesn't affect the new target cases, which pass no `projects`.

## What was done

Implemented as planned, with one departure in the probe:
- **Probe layout.** `audit_probes` in `.meta/checks/probes/tools/audit.py`
  passed ruff's complexity limit once both loops over `CASES` were in it.
  Each case is now judged by one helper, `_judged`, and each `CASES` entry
  runs twice in the same loop: once with `audit` directly, and once through
  `main --repository` against a temporary repository built by `_repository`.
  `ELSEWHERE` holds the two refusal cases.
- **DR-358** records the flag. It widens DR-353's consequence that the
  audit covers only the Projects stereorepo asserts. DR-353 itself is not
  superseded, since the rest of it still holds.

For the next reader:
- A target's refusal message names the resolved path, so a relative
  `--repository` shows where `just` actually looked: from stereorepo's root,
  not from the developer's shell.
- With no `--repository`, `main` takes the same path as before. The no-file
  check also runs there, but stereorepo always has its `structure.yaml`.
- `audit-gate-crash-misreported` in the backlog is still open. It will touch
  `audit` and the probe's `CASES`, and every case it adds there now runs in
  a target repository as well.

## Pair notes

> **primary, in-progress turn 1**
>
> `just audit` can now audit a Project that another repository asserts: `just audit <project> <bootstrap> --repository <path>`. `just gate meta` passes, and no other Project's directory was touched, so no other gate applied. The work is committed.
>
> **What it does now:**
> - With `--repository`, the audit reads the Project and its gate from that repository's `.meta/assertions/structure.yaml` and runs the gate from that repository's root. It still compares the result with stereorepo's Bootstrap.
> - With no flag, it behaves as before.
> - A target with no `structure.yaml` (including a path that doesn't exist) stops with a message naming the target. So does a target that doesn't assert the named Project.
>
> **Where the change is:**
> - **`.meta/audit.py`:** `main` now reads its arguments with argparse, takes an `out` argument, and gives the new messages. `audit` takes the directory to run the gate from.
> - **`structure` in `.meta/gate`:** takes an optional path, so the audit reuses it instead of copying it.
> - **The recipe:** it is now `audit project bootstrap *args`. I changed it in `writers.py` and in the contract in `.meta/checks/files/justfile.py`, then re-rendered the `justfile`.
> - **DR-358:** records the flag. It widens DR-353, which said the audit covers only the Projects stereorepo asserts; the rest of DR-353 still holds, so it isn't superseded.
>
> **Tests:** in `.meta/checks/probes/tools/audit.py`, every existing case now also runs through `main --repository` against a temporary repository. Its gate is `cat report.txt`, a file only that repository holds, so a case fails if the gate runs from stereorepo's root. Two more cases check the refusal messages.
>
> **Departure from the plan:** with both sets of cases in one function, the probe went over ruff's complexity limit. One helper, `_judged`, now checks each run's result, and each case runs both ways in a single loop.
>
> **Checks by hand:** with `--repository /nonexistent`, the audit gave the "no `structure.yaml`" message and exited 1. I didn't run the scratch-repository check by hand because the shell refused my command; the new probe cases cover that path.
>
> The notes for the next reader are under `## What was done` in the issue file.

> **secondary, in-progress turn 2**
>
> I reviewed the implementation against the plan and found it correct: the target's refusal messages name the resolved path, the `projects` injection keeps its meaning, and the probe's `cat report.txt` gate fails if the gate runs from stereorepo's root. I made one change: the `audit` recipe's doc comment in `CONDITIONAL_RECIPES` in `.meta/lib/render/writers.py` now lists its flag as `(--repository PATH)`, as the other recipes list theirs, instead of the phrase "for another repository's", and I re-rendered the `justfile`. `just gate meta` passes. A hand check against a scratch repository was refused by the sandbox, so the probe cases remain the evidence for that path.

> **secondary, in-progress turn 2**
>
> I found nothing wrong with your partner's implementation and made one small cosmetic change. `just gate meta` passes, and I've committed the change.
>
> **What I checked:**
> - **Refusal messages:** they name the full resolved path of the target. A relative `--repository` therefore shows where `just` really looked, which is stereorepo's root, not the developer's shell directory.
> - **`main`'s `projects` argument:** it keeps its old meaning. When given, it replaces the `structure.yaml` read, and the missing-file check is skipped.
> - **The probe really tests where the gate runs:** the temporary repository's gate is `cat report.txt`, a file only that repository holds. If the gate ran from stereorepo's root, the cases would fail.
> - **The Decision Record:** DR-358 applies the same article and names the same three files as DR-353, which it widens.
> - **Documentation:** no wiki page covers the audit, so no document needed updating.
>
> **My change:** the `audit` recipe's comment in `writers.py` ended with "(--repository PATH for another repository's)". It now says just `(--repository PATH)`, the way the other recipes list their flags, and I re-rendered the `justfile`.
>
> **Not checked by hand:** I tried to run the audit against a scratch repository, but the sandbox wouldn't let me write the files it needed. The new probe cases are the only evidence that a real target repository works.
>
> I added a note under my turn in the issue file.

> **primary, in-progress turn 3**
>
> I changed nothing; the issue is ready for its gate.
>
> Your partner shortened the flag in the `audit` recipe's doc comment to `(--repository PATH)` and re-rendered the `justfile`. I checked the change and kept it: it lists the flag the way the other recipes list theirs, the comment still cites both Decision Records, and the rendered `justfile` matches what the `audit` entry in `writers.py` produces.
>
> Their review found nothing wrong in `.meta/audit.py` or the probe, and they report that `just gate meta` passes with the change. Nothing in the code has changed since then, so I didn't run the gate again.
>
> One limit remains: neither of us could audit a real scratch repository by hand, because the sandbox refused the commands. The new probe cases are the only evidence that auditing another repository works.
