---
difficulty: medium
---

# Nothing renders a seed and gates the copy any more

`bootstraps/python/seeded-artifacts.md` and `bootstraps/rust/seeded-artifacts.md`
("Rendered, then gated"), the header comments of `bootstraps/python/render` and
`bootstraps/rust/render`, the closing paragraph of
`bootstraps/python/nothing-unconsumed.md` and `bootstraps/rust/nothing-unconsumed.md`,
and DR-091 and DR-094 say a `python seed` / `rust
seed` job in `.github/workflows/gate.yml` renders each seed as `acme` and runs
its gate on the result. That workflow was removed with the pull-request flow,
and no recipe, gate step or pair-loop step does the same now. Only the seeds'
in-place gates (`work:project/python-seed`, `work:project/rust-seed` in
`.meta/assertions/structure.yaml`) run, so a fault that only shows in a
rendered copy (a missed rename, a lockfile that no longer matches) goes
unseen.

Either restore a rendered-then-gated run somewhere the pair loop reaches, or
correct the prose and Decision Records to say the in-place gate is all there
is. Found while grooming `bootstrap-render-step`.

## Wanted

Restore it, through the seed Projects' own gates, which the pair loop
already runs when a branch touches a seed (`select` in `pair/touched.py`).
The pages themselves call the rendered run the stronger claim, and A9 asks
for it.

- The `gate:` of `work:project/python-seed` and `work:project/rust-seed`
  renders the seed with `bootstraps/<lang>/render` as `acme` into a fresh
  temporary directory (under `$TMPDIR`, so a seat's sandbox can write it) and
  runs the seed's own gate there: `uv run --locked gate` with
  `UV_PYTHON=3.13`, the support floor (DR-095), as the old job did; and
  `cargo xtask gate`. It replaces the in-place run rather than adding to it,
  so a seed's gate costs what it did. The temporary directory is removed
  afterwards whether the gate passes or fails, and nothing is written into
  `bootstraps/<lang>/seed/`. Whether that is a one-line shell `gate:` or a
  small wrapper beside each `render` is the plan's call; either way it is
  the `gate:` field that runs it. The Rust run may point `CARGO_TARGET_DIR`
  somewhere persistent so dependencies are not rebuilt from nothing each time.
  `render` refuses a destination that exists, so render into a path inside
  the temporary directory (say `$tmp/acme`), not the directory itself.
- A new Decision Record amends DR-091, DR-094 and DR-356: each seed Project's
  gate is its rendered copy's gate, run by the pair loop, not a workflow job.
  DR-356's consequence "Nothing now renders a seed and gates the copy" stops
  being true. DR-356 rejected "Add a `render` step to each seed's gate" for a
  Project *built from* a seed, which has nothing to render; that does not
  apply to the seed Projects themselves, and the new record says so.
- `just audit python-seed python` and `just audit rust-seed rust` run the
  `gate:` field and read its standard output for step lines (`audit` in
  `.meta/audit.py`), so the rendered copy's gate output still reaches
  standard output unaltered.
- Every place listed above, the `description` of both seed Projects in
  `structure.yaml`, and the Seeded Artifacts `exemption_reason` of both
  Bootstraps in `.meta/assertions/bootstraps.yaml` (which today says the seed
  "is gated where it sits", citing DR-356) say what now happens and stop naming `gate.yml`.
  Re-render, so `.meta/decisions.md` and the Bootstrap READMEs agree.

## Out of scope

- Making a change to `bootstraps/<lang>/render` select its seed's gate.
  `pair/touched.py` gives that path to `meta`; that is DR-303's accepted risk,
  and a separate Issue if it matters.
- Changing what either seed's gate checks, or the seeds themselves.
- `.meta/test_specialization.py`, which stages `bootstraps/<lang>` but is not
  asked to gate a rendered seed.

## Done when

- Running each seed Project's `gate:` command from the repository root
  renders a copy named `acme` in a temporary directory, runs that copy's gate,
  exits with its status, and leaves neither the temporary directory nor any
  new file under `bootstraps/<lang>/seed/`.
- Dropping one entry from `RENAMES` in `bootstraps/python/render` (say the
  `"packages/seed"` rename; `from seed.` overlaps `seed.example`, so dropping
  it alone shows nothing) makes the python-seed gate fail, where the in-place
  gate passed; the same holds for a rename in `bootstraps/rust/render`. Try
  it by hand and record the result here; it is not a committed test.
- `grep -rn "gate.yml" bootstraps .meta/assertions --exclude-dir=decisions`
  finds nothing that describes a seed job, and the new Decision Record exists,
  says which records it amends, and is listed in `.meta/decisions.md`. The
  amended records themselves keep their text: a record is amended by a later
  one, not rewritten (DR-355 amending DR-130 and DR-331 is the pattern).
- `just audit python-seed python` and `just audit rust-seed rust` report the
  same gaps (or none) as they do before the change.

## The plan

Data and prose, plus two `gate:` strings; no Python changes.

**What the code already gives.** `run` in `.meta/gate` and `audit` in
`.meta/audit.py` both run a Project's `gate:` with `shell=True` from the
repository root and read its standard output for step lines; `.meta/gate`
passes any other stdout line on to stderr, but `audit` keeps it, so anything
`render` prints must go to stderr. Both `render` scripts print one
`rendered seed into … ` line on stdout, refuse an existing destination, and
already skip tool output (`TOOL_OUTPUT` in the Python one; `target` and
`mutants.out*` in the Rust one), so a copy never carries the seed's `.venv`
or `target/`. Neither seed's gate reads a path outside its own tree. The
Rust seed's `Cargo.lock` holds only its two workspace crates, so a cold build
in a fresh directory is cheap: no `CARGO_TARGET_DIR` is needed, and the plan
drops that suggestion. Python 3.13 is on this machine (`uv python find 3.13`),
and the seed's `requires-python` is `>=3.13`, while its `.python-version`
says 3.14; `UV_PYTHON=3.13` overrides that, as the old job did.

1. **The two gates** (`.meta/assertions/structure.yaml`). Replace each
   `gate:` with a folded string of one POSIX `sh` line:

       t=$(mktemp -d "${TMPDIR:-/tmp}/seed.XXXXXX") && trap 'rm -rf "$t"' EXIT &&
       bootstraps/python/render "$t/acme" acme >&2 &&
       cd "$t/acme" && UV_PYTHON=3.13 uv run --locked gate

   and the same for Rust with `bootstraps/rust/render` and
   `cargo xtask gate`. *Corrected in implementation:* macOS `mktemp -d`
   with no template ignores `$TMPDIR` and uses `/var/folders/…/T`, which a
   seat's sandbox refuses, so the template names `$TMPDIR` explicitly. The
   `EXIT` trap removes it on success, failure, or a `render`
   that refuses; the shell exits with the gate's status, which the trap does
   not change. A one-liner rather than a wrapper script: there is nothing to
   test in it beyond what running it shows, and a wrapper would be one more
   file Nothing Unconsumed has to account for. Update both Projects'
   `description`, which say the gate runs "in place".
2. **The Decision Record** `DR-360` (recheck the highest number first),
   in the shape the recent records share. It applies A9 and is `enacted_in` the two render artifacts
   (`work:artifact/bootstraps-python-render`,
   `work:artifact/bootstraps-rust-render`) and
   `work:artifact/meta-assertions-structure`. Alternatives: correct the prose
   to say the in-place gate is all there is (rejected: a missed rename or a
   stale lockfile goes unseen); gate both in place and rendered (rejected:
   doubles each seed's gate, mutation testing included, for faults the copy
   also shows); render then gate as the seed Project's gate (chosen). A
   consequence says it amends DR-091 and DR-094 (the job that rendered each
   seed is now the Project's gate), DR-095 (the floor is run by the
   `UV_PYTHON` in that gate, not by a job) and DR-356 (its consequence that
   nothing renders a seed stops being true; its rejected "render step"
   concerned a Project built from a seed and still stands).
3. **The prose.** "Rendered, then gated" in both `seeded-artifacts.md`, the
   closing paragraph of both `nothing-unconsumed.md`, the header docstring
   of both `render` scripts: the seed Project's gate renders and gates the
   copy, cite the new record, drop `gate.yml`. Keep the "builds as it sits"
   paragraph, which stays true (the tree is real and buildable; it is just
   not where the gate runs). Both Seeded Artifacts `exemption_reason`s in
   `.meta/assertions/bootstraps.yaml`: the seed is gated by rendering it, by
   the gate of its Project (DR-356, DR-360).
4. **Re-render** with `just render`, so `.meta/decisions.md` lists DR-360 and
   anything generated from `structure.yaml` or `bootstraps.yaml` agrees.

**How we will know it works** (by hand, results recorded in this file):

- Run each new `gate:` string from the root under `sh`. It reports its steps,
  exits with the copy's gate status, and afterwards `ls "$TMPDIR"` shows no
  leftover directory and `git status` shows nothing new under
  `bootstraps/<lang>/seed/`.
- Comment out the `from seed.` entry of `RENAMES` in `bootstraps/python/render`
  and the `seed::` entry in `bootstraps/rust/render`, one at a time; each
  seed's gate fails, then passes once restored.
- Run `just audit python-seed python` and `just audit rust-seed rust` before
  step 1 and after; the gaps printed are the same.

**Risks.**

- The Python copy builds a fresh `.venv` on 3.13 and the Rust copy builds
  from cold, so each seed's gate is slower than the warm in-place run; the
  mutation steps dominate either way. If the Python copy's gate is found to
  pass on 3.14 and fail on 3.13, that is a real floor fault the in-place run
  hid, and goes to the backlog rather than into this Issue.
- `uv run --locked` needs the lockfile's packages; offline, it relies on the
  uv cache, which the seat's sandbox can write (`~/.cache/uv`).
- The first rendered run may fail where the in-place one passes. A fault in
  how `render` renames (a `RENAMES` entry missing) is what this Issue exists
  to catch, and is fixed in `render` here; a fault in the seed itself goes to
  the backlog. A trial render of both seeds as `acme` left the word `seed`
  only in prose (docstrings, comments and `description` fields), never in a
  name the gate resolves, so none is expected; the lockfiles were not
  searched, and `--locked` is what checks the Python one.
- A seat's sandbox refuses `sccache` (DR-359); the Rust copy is built the
  same way as the in-place seed, so whatever `seat-sandbox-rust-builds`
  arranged for the in-place build applies unchanged.

## What the implementation found

Run by the primary seat in its sandbox, 2026-10-03.

- **Both rendered gates pass.** `just gate python-seed`: 9 steps `ok` on
  Python 3.13, 18 s. `just gate rust-seed`: 8 steps `ok`, 69 s, of which
  `cargo mutants` is 64 s. In place, `--iterate` read the seed's
  `mutants.out` and tested 0 mutants; the copy has none, so it tests all 100
  each run (DR-360 records this). Afterwards no `$TMPDIR/seed.*` was left
  and `git status` showed nothing under either seed, including after the
  failing runs below.
- **Rust needs `RUSTC_WRAPPER` unset in a sandbox.** This seat's shell had
  `RUSTC_WRAPPER=sccache`, which the sandbox refuses; `env -u RUSTC_WRAPPER`
  was needed for every Rust run here, before the change and after.
  `UNSET_FOR_SEATS` in `pair/seats.py` is meant to drop it for seats; it did
  not reach this one's shell. The supervisor's gate runs outside the sandbox.
- **Dropping a `RENAMES` entry.** Rust, `seed::` dropped: `test` and
  `mutants` fail (`cannot find module or crate seed`), gate exits 1. Python,
  `'"packages/seed"'` dropped: uv refuses the workspace, gate exits 1. Two
  Python entries the plan and done-when named do not show a fault on their
  own: `from seed.` and `seed.example` each overlap the other, so dropping
  either changes nothing. Dropping `'packages = ["src/seed"]'` only turned
  `evidence` into `?` and the gate exited 0 (the loop holds a landing on a
  `?`, so the fault would still reach the developer). That weakness is in
  the seed's gate, not in this change: `issues/backlog/python-seed-packages-rename-unseen.md`.
- **Audit unchanged.** `just audit python-seed python` and
  `just audit rust-seed rust` both printed no gap and exited 0, before the
  change and after.
- **The search.** `grep -rn "gate.yml" bootstraps .meta/assertions
  --exclude-dir=decisions` finds nothing; DR-360 is in `.meta/decisions.md`.
  The opening paragraph of both `seeded-artifacts.md` also said the seed was
  gated "where it sits", and was corrected with the rest.
- **The Bootstrap READMEs.** Their "how a portfolio takes the seed" section
  is generated from the `description` of `work:artifact/bootstraps-python-readme`
  and `work:artifact/bootstraps-rust-readme` in `structure.yaml`, and still
  said "the workflow" proves the seed sound and that the seed's gate runs
  "where it sits". The secondary seat corrected both, added the two READMEs
  to DR-360's `enacted_in`, and re-rendered.
- **`RUSTC_WRAPPER` comes from the developer's `~/.zshrc`**, which a seat's
  shell still sources; `UNSET_FOR_SEATS` cannot reach it. Written as
  `issues/backlog/seat-shell-rustc-wrapper-returns.md`.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/seed-rendered-gate-lost.md`, set it to `difficulty: medium` and committed it as `7ccd5127`.
>
> **The choice.** Of the two options the issue offered, I picked restoring the rendered-then-gated run rather than correcting the prose. The seeds' own pages call the rendered run "the stronger claim", and A9 asks for it. The run goes into the `gate:` field of `work:project/python-seed` and `work:project/rust-seed` in `structure.yaml`. The pair loop already runs those gates whenever a branch touches a seed, so no new mechanism is needed.
>
> **What is wanted:**
> - Each seed's gate copies the seed into a fresh temporary directory under `$TMPDIR`, names the copy `acme`, and runs the seed's own gate on it:
>   - **Python:** `uv run --locked gate` on Python 3.13, as the old CI job did.
>   - **Rust:** `cargo xtask gate`.
> - This replaces the in-place run instead of adding to it, so a seed's gate takes about as long as it does now.
> - The temporary directory is removed afterwards, pass or fail.
> - A new Decision Record amends DR-091 and DR-094.
> - Every page that still names the deleted `.github/workflows/gate.yml` is corrected. That includes two places the original issue didn't list: the seed Projects' descriptions in `structure.yaml`, and the Seeded Artifacts `exemption_reason` in `bootstraps.yaml`.
>
> **Out of scope:**
> - Making a change to a `render` script trigger its seed's gate. `pair/touched.py` assigns that path to the `meta` Project, which is a risk DR-303 accepts.
> - Changing what either seed's gate checks.
> - `.meta/test_specialization.py`.
>
> **Done when:**
> - Each seed's gate gates a copy named `acme` in a temporary directory, exits with that gate's status, and leaves nothing behind in the seed's directory or the temporary one.
> - Removing one entry from `RENAMES` in either `render` script makes that seed's gate fail. This is checked once by hand and the result recorded in the issue; it is not a committed test.
> - No page describes a `gate.yml` seed job any more, and the new Decision Record exists.

> **secondary, backlog turn 2**
>
> I left my partner's grooming and `difficulty: medium` in place and made three additions to `issues/underway/seed-rendered-gate-lost.md`, committed as `dabcdc07`:
>
> - **DR-356 needs amending too.** That record says nothing renders a seed and gates the copy any more, and points to this issue to fix it. So the new Decision Record now amends DR-091, DR-094 and DR-356. DR-356 also turned down the option "Add a `render` step to each seed's gate", but that was about a project built *from* a seed, which has nothing to render. The new record has to say that the rejection doesn't cover the seed projects themselves. I also noted that the `exemption_reason` text in `bootstraps.yaml` cites DR-356.
> - **`just audit` reads the gate's output.** `audit` in `.meta/audit.py` runs each seed project's `gate:` command and reads the step lines it prints. The rendered copy's gate output must still reach standard output unchanged, so I added a done-when item: `just audit python-seed python` and `just audit rust-seed rust` report the same gaps after the change as before.
> - **`render` won't write into a directory that already exists.** The gate has to render into a path inside the temporary directory, such as `$tmp/acme`, not into the temporary directory itself.
>
> I checked the rest against the code and it holds: the current `gate:` lines in `structure.yaml`, the `RENAMES` lists in both `render` scripts, and where `gate.yml` is still mentioned in the seed pages.

> **primary, backlog turn 3**
>
> I'm leaving the issue as my partner left it. I checked their three additions against the code and all of them hold:
>
> - **DR-356 does need amending.** It says "Nothing now renders a seed and gates the copy". The option it rejected, "Add a `render` step to each seed's gate", is about a project built *from* a seed, not the seed projects themselves.
> - **`just audit` does read the gate's output.** `.meta/audit.py` runs the `gate:` command from `structure.yaml` and reads the step lines it prints. So the new "audit reports the same gaps as before" check is a real requirement.
> - **`render` won't overwrite.** It refuses a destination that already exists, so the gate has to render into a path inside the temporary directory, such as `$tmp/acme`.
>
> `difficulty: medium` stays, and I committed nothing this turn.

> **primary, todo turn 1**
>
> I wrote `## The plan` into `issues/todo/seed-rendered-gate-lost.md` and committed it as `6a98d347`. It only changes data and prose: no Python code changes.
>
> **What reading the code showed:**
> - **`render` has to print to standard error.** Both `.meta/gate` and `.meta/audit.py` run a Project's `gate:` command through the shell and read its standard output. `.meta/gate` sends stray lines on to standard error, but `audit` keeps them. Both `render` scripts print one "rendered … into …" line on standard output, so the gate must redirect that line (`>&2`).
> - **The partner's `CARGO_TARGET_DIR` idea isn't needed.** The Rust seed's `Cargo.lock` lists only its own two crates and no outside dependencies, so building a fresh copy from scratch is cheap. I dropped it.
> - **The copies start clean.** Both `render` scripts already skip `.venv`, `target/` and other tool output.
> - **Python 3.13 is available.** It is installed on this machine, and the seed claims to support it (`>=3.13`), even though its `.python-version` says 3.14.
>
> **Steps:**
> 1. In `structure.yaml`, replace each seed's `gate:` with one shell line: make a temporary directory with `mktemp -d`, set a trap that deletes it when the shell exits, run `render "$t/acme" acme >&2`, move into the copy, and run its gate (`UV_PYTHON=3.13 uv run --locked gate`, or `cargo xtask gate`). Also update both Projects' descriptions, which still say the gate runs "in place".
> 2. Add DR-360, which says it amends DR-091, DR-094, DR-095 and DR-356. I added DR-095 because it also describes the deleted `python seed` job.
> 3. Correct the prose: both `seeded-artifacts.md`, both `nothing-unconsumed.md`, both `render` header comments, and both `exemption_reason`s in `bootstraps.yaml`.
> 4. Re-render the generated pages.
>
> **Checks, done by hand and recorded in the issue:**
> - Each gate cleans up after itself and exits with the copy's gate status.
> - Commenting out one `RENAMES` entry in each `render` script makes that seed's gate fail, and restoring it makes it pass.
> - `just audit` reports the same gaps before and after.
>
> **Risks:**
> - Each seed's gate gets slower, because it builds a fresh copy every run.
> - `uv run --locked` depends on the uv cache when the network isn't available.
> - A real fault on Python 3.13 might surface that the in-place run on 3.14 hid. If it does, it goes to the backlog rather than into this issue.
>
> I also changed one done-when check. The `gate.yml` search now skips `decisions/`, because a Decision Record is amended by a later one, not rewritten. As first written, the check could never pass: DR-091, DR-094, DR-095 and DR-356 will always mention the old job.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code and it holds. I added one risk to it, committed as `66df0267`.
>
> **What I checked:**
> - **The two programs that run a gate.** `run` in `.meta/gate` and `audit` in `.meta/audit.py` both run the `gate:` command through the shell from the repository root and read its standard output. So `render`'s "rendered … into …" line does need to go to standard error (`>&2`).
> - **Nothing else depends on the old gate commands.** No check or test reads the `gate:` text of the two seed Projects, so replacing it with a one-line shell command breaks nothing.
> - **`CARGO_TARGET_DIR` isn't needed.** The Rust seed's `Cargo.lock` lists only its own two crates, so a fresh build has no outside dependencies to fetch.
> - **The copies start clean.** The Rust `render` skips `target` and `mutants.out*`, so the copy carries no old build output.
> - **The record IDs the plan cites exist.** All three IDs that DR-360 lists under `enacted_in` are already declared in `structure.yaml`.
>
> **What I added:** I rendered both seeds as `acme` into a scratch directory, searched the copies for the word `seed`, and then deleted the directory. The word was left only in prose: docstrings, comments and `description` fields. It never appeared in a name the gate actually looks up. I didn't search the lockfiles; `uv run --locked` is what checks the Python one.
>
> The new risk entry says what to do if the first rendered run fails where the in-place run passed:
> - If `render` missed a rename, fix it in `render` within this issue, since catching that is the point of the issue.
> - If the seed itself is at fault, write it up as a new issue in the backlog.
>
> I didn't run either seed's gate; those runs belong to the implementation stage.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands, with nothing new to commit this turn. My partner's one addition is a risk entry for a first rendered run that fails where the in-place run passed, and it is sound. A rename that `render` missed is fixed in `render` within this issue, because catching that is the point of the issue. A fault in the seed itself becomes a new issue in the backlog. Their trial render, which left the word `seed` only in prose, fits what the two `RENAMES` lists cover. `uv run --locked` will catch a Python lockfile the rename leaves out of step.

> **primary, in-progress turn 1**
>
> Each seed's gate now copies the seed into a temporary directory, renames the copy `acme`, and runs the seed's own gate there. This is committed as `a7f19b74`. Both rendered gates pass, and `just gate meta` passes.
>
> **What changed:**
> - **The two gates** (`.meta/assertions/structure.yaml`). Each seed's `gate:` is now one shell line that renders the seed into a temporary directory, runs the seed's gate in the copy, and removes the directory however the gate ends. The Python copy runs with `UV_PYTHON=3.13 uv run --locked gate`, so it also proves the renamed lockfile still matches.
> - **DR-360** records the decision and says it amends DR-091, DR-094, DR-095 and DR-356.
> - **The prose** in both `seeded-artifacts.md`, both `nothing-unconsumed.md`, both `render` header comments, and both `exemption_reason`s in `bootstraps.yaml` now describes this instead of the deleted `gate.yml` jobs. I also fixed one place the plan missed: the opening paragraph of each `seeded-artifacts.md` said the seed was gated "where it sits". `.meta/decisions.md` is re-rendered.
>
> **One correction to the plan:** on macOS, `mktemp -d` without a template ignores `$TMPDIR` and uses a folder the sandbox refuses. The gates use `mktemp -d "${TMPDIR:-/tmp}/seed.XXXXXX"` instead, and the plan in the issue file now says so.
>
> **Results**, recorded in the issue file under "What the implementation found":
> - **Python:** 9 steps passed on Python 3.13, in 18 seconds.
> - **Rust:** 8 steps passed, in 69 seconds. The fresh copy has no record of earlier mutation runs, so all 100 mutants are tested each time; in place it tested none. DR-360 records that cost.
> - **Cleanup:** no temporary directory was left behind and nothing changed under either seed, including after the failed runs below.
> - **Dropping a `RENAMES` entry from `render`:**
>   - Rust, `seed::` dropped: the gate fails.
>   - Python, the workspace-member entry dropped: the gate fails.
>   - Python, `from seed.` or `seed.example` dropped: no effect, because each covers the other's cases. The issue had suggested `from seed.` as the example to try.
>   - Python, `packages = ["src/seed"]` dropped: only one step reports `?` (could not run) and the gate still exits 0. The loop holds a landing on any `?`, so the developer would still see it, but as a step that couldn't run rather than a failure. That is a weakness in the seed's own gate, so I wrote it up as `issues/backlog/python-seed-packages-rename-unseen.md`.
> - **Audit:** `just audit python-seed python` and `just audit rust-seed rust` reported no gaps, both before and after the change.
>
> **Rust in this sandbox:** my shell had `RUSTC_WRAPPER=sccache` set, which the sandbox refuses, so I ran every Rust gate with `env -u RUSTC_WRAPPER`. `UNSET_FOR_SEATS` in `pair/seats.py` is meant to drop that variable for seats, but it didn't reach this shell. The supervisor's gate runs outside the sandbox and doesn't have this problem.

> **secondary, in-progress turn 2**
>
> My partner's implementation works. I fixed a few places it missed, logged one problem outside this issue, and committed it all as `05adfbe0`. `just gate meta` passes.
>
> **What I fixed:**
> - **The Bootstrap READMEs were still wrong.** `bootstraps/python/README.md` and `bootstraps/rust/README.md` still said "the workflow" proves the seed is sound, and that the seed's gate runs "where it sits". Both READMEs are generated from the `description` fields in `structure.yaml` (`work:artifact/bootstraps-python-readme` and `work:artifact/bootstraps-rust-readme`). I corrected those descriptions, cited DR-360, and re-rendered.
> - **DR-360 now lists the two READMEs** in `enacted_in`, so `.meta/decisions.md` shows DR-360 against them too.
> - **`bootstraps/python/seeded-artifacts.md` named the wrong command.** It said the gate runs `uv run gate`; it runs `uv run --locked gate`.
> - **One done-when example didn't work.** My partner found that dropping the `from seed.` rename on its own changes nothing, because the `seed.example` rename covers the same lines. The done-when check now uses the `"packages/seed"` rename as its example.
>
> **Logged for later:** `issues/backlog/seat-shell-rustc-wrapper-returns.md`. My partner had to run every Rust build with `env -u RUSTC_WRAPPER`. My shell had the same variable set (`RUSTC_WRAPPER=sccache`), and I traced it to the developer's `~/.zshrc`, which exports it. `UNSET_FOR_SEATS` in `pair/seats.py` removes it from the seat process, but the seat's shell still sets it from that profile. The new issue asks for a fix and a test in `pair/test_pair.py` that shows a seat can build Rust without the workaround.
>
> I didn't touch anything under either seed directory, so I didn't run the `python-seed` or `rust-seed` gates this turn. My partner ran both on the rendered copies, and both passed.

> **primary, in-progress turn 3**
>
> I kept all of my partner's changes after checking them against the code. My only change this turn is rewrapping one paragraph in `bootstraps/python/seeded-artifacts.md` that their edit left with an overlong line, committed as `e491a55f`.
>
> Their changes:
> - **The Bootstrap READMEs:** the generated text in both READMEs no longer says "the workflow" proves the seed sound, or that the seed's gate runs "where it sits". DR-360 now lists both READMEs among the files it applies to.
> - **The Python page:** it now names the right command, `uv run --locked gate`.
> - **The done-when check:** its example now uses the `"packages/seed"` rename. On its own, dropping `from seed.` shows no fault.
> - **A new backlog issue:** `seat-shell-rustc-wrapper-returns.md` covers `RUSTC_WRAPPER=sccache` reaching a seat's shell from the developer's `~/.zshrc`, which forces `env -u RUSTC_WRAPPER` on every Rust build in the sandbox.
>
> A search of the bootstrap pages, both `render` scripts, `structure.yaml`, `bootstraps.yaml`, `SPECIALIZE.md`, `ADOPT.md` and `wiki/` finds no other stale mention of the old workflow or of the seed being gated in place. After re-rendering, `just gate meta` passes. Nothing under either seed directory or `pair/` changed this turn, so no other targeted gate applied.

> **secondary, in-progress turn 4**
>
> I changed nothing this turn and committed nothing. The issue is implemented as planned. My partner's only change since my last turn was rewrapping one paragraph in `bootstraps/python/seeded-artifacts.md`, and it's correct.
>
> I checked one claim the plan relies on: the cleanup step in the new gate keeps the gate's exit status. I ran the same shell pattern with a failing command in place of the gate. It exited 1, and no `seed.*` temporary directory was left under `$TMPDIR`.
>
> I didn't run `just gate meta` again, since nothing has changed since it last passed (my partner re-ran it after their rewrap). No file under either seed directory or `pair/` changed, so no other targeted gate applies.
