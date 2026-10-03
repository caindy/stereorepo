---
difficulty: medium
---
# Cite code by path and name, never by line number

A citation of a file and a line number breaks whenever the file above that
line changes. The `path and line claims` step (`path_and_line_claims` in
`.meta/checks/citations/claims.py`) checks each one against the line it
names, so every edit that moves lines can fail the gate on a file nobody
touched. On 2026-10-03 adding three entries to `DISALLOWED` in
`pair/seats.py` failed the `meta` gate on a pair note in
`issues/done/pair-loop-spike-evidence.md`, which cited `CONTEXT` by its old
line. Earlier, on `release-recipe-is-scaffold-only`, seats spent two turns
rewording each other's notes for the same reason.

The developer decided on 2026-10-03 to stop citing line numbers entirely. A
citation names the file and the thing in it: a function, class, constant,
test, heading or step, such as `CONTEXT` in `pair/seats.py`.

## Wanted

- The step no longer opens the cited file or reads its lines. For each
  match of `PATH_LINE` in the prose it already reads (every `.md` file,
  Issue files included, and assertion YAML, with fenced code blocks
  stripped), it reports the file,
  the citation, and that a citation names the path and the thing in it
  instead of a line. It is renamed `no line citations`, and the function
  `no_line_citations`, with its docstring rewritten to match.
- Every place that names the old step follows the rename: the import and
  `__all__` entry in `.meta/checks/citations/__init__.py`, the comment on
  `_LINE_CITATION` and the `with_note` docstring in `pair/board.py`, and
  the pair notes paragraph in `pair/README.md`. The "Stale line numbers in
  cited file paths" entry in `.meta/checks/citations.history.md` keeps its
  account, and a new entry after it records that the step now refuses line
  citations instead of verifying them, with `no_line_citations` as its
  evidence. DR-130, DR-154 and DR-331 stay as written; the new Decision
  Record amends DR-130 and DR-331.
- Every existing `path:line` code span in prose is rewritten to the path
  and the name of what it pointed at, read from the file as it stood at the
  commit that wrote the citation. On 2026-10-03 they were all in
  `issues/done/`, in nine files.
- The rule is stated where writers look: a bullet in the Conventions list
  of `AGENTS.md`. The same rule in the `/technical-writing` skill is
  `technical-writing-skill-no-line-citations` in the backlog, because the
  seats cannot render the skill's tracked `.claude/skills/` copy.
- A new Decision Record (DR-355, or the next free number) records the
  decision, why, and that it amends DR-130 and DR-331, and the decisions
  index is re-rendered.

## Out of scope

- Tool output that prints `path:line`, such as a linter's findings or a
  probe's expected output in a fenced block, which is not a citation in
  prose.
- Pair notes: `board.with_note` already rewrites a note's `path:line` spans
  out of the `PATH_LINE` form (`pair-notes-escape-the-seats-gate`), and that
  stays, so a seat's closing message cannot fail the next seat's gate.
- Prose that mentions a line without the `path:line` code span, such as
  `` `pair/loop.py` line 1009 `` in old notes. The convention covers it,
  but the step does not check it and old Issue files are not rewritten for
  it.

## Done when

- `git grep` for a code span of a path, a colon and digits finds none
  outside fenced blocks.
- A probe recorded in this file: a scratch `.md` file holding a code span
  of a path, a colon and a line number fails `no line citations` with a
  message naming that file and citation; the same file citing `CONTEXT` in
  `pair/seats.py` instead passes it. The probe file is removed afterwards.
- No step called `path and line claims` remains, and the `AGENTS.md` bullet
  and the new Decision Record each state the rule.

## The plan

The skill moved out on planning: its source is the `technical-writing`
artifact in `.meta/assertions/imported/structure.yaml`, and `just render`
writes it to the tracked `.claude/skills/technical-writing/SKILL.md`, which
the seats' sandbox denies (`render-in-seat-sandbox`). Changing the source
here would leave the `rendered prose` step red on a page neither seat can
write (`pause-on-a-render-the-seat-cannot-write`). The new backlog Issue
`technical-writing-skill-no-line-citations` is `difficulty: developer` and
carries it.

Steps, in this order, so that the check and the citations it reads change
together:

1. **The step.** In `.meta/checks/citations/claims.py`, replace
   `path_and_line_claims` with `@check("no line citations")`
   `no_line_citations()`. It keeps the loop over
   `loaders.durable(loaders.copied_files())` and `prose.prose(path)` and
   the `PATH_LINE` pattern, and drops everything after the match: no file
   lookup, no line count, no neighbouring spans. Each match appends
   ``f"{rel}: {m.group(0)} cites a line; name the path and the thing in it
   instead"``. The comment above `PATH_LINE` and the docstring say what is
   refused and why (line numbers move when the file above them changes),
   citing the new Decision Record. The module docstring's "a line that
   reads what it is cited for" goes, in `claims.py` and in
   `.meta/checks/citations/__init__.py`.
2. **The re-exports.** In `.meta/checks/citations/__init__.py`, the import
   and the `__all__` entry become `no_line_citations`, keeping `__all__`
   sorted.
3. **The pair package.** In `pair/board.py`, the comment on
   `_LINE_CITATION` and the `with_note` docstring name `no line citations`;
   the pattern and the rewrite do not change. `pair/README.md`'s pair notes
   paragraph names the new step.
4. **The history.** In `.meta/checks/citations.history.md`, after "Stale
   line numbers in cited file paths", a new entry "Line citations refused"
   says verifying lines still failed on files nobody touched, and that
   `no_line_citations()` now refuses the form. Evidence:
   `.meta/checks/citations/claims.py::no_line_citations`.
5. **The citations.** Rewrite the 17 spans in nine files under
   `issues/done/`: `adopt-probe-passes-in-a-portfolio`,
   `backlog-running-order` (2), `flight-vocabulary`,
   `fresh-worktree-passes-meta-gate`, `groom-alongside-pair`,
   `pair-loop-spike-evidence` (5), `pair-watch-exit-codes`,
   `rename-discipline-journaling`, `vocabulary-scope-note-paragraphs` (3).
   For each, `git log -S` finds the commit that wrote it and `git show
   <commit>:<path>` gives the line it pointed at. The span becomes the path,
   and the sentence names the function, heading, class or key that holds
   that line, for example `CONTEXT` in `pair/seats.py`. The
   `pair-loop-spike-evidence` notes argue about which line `CONTEXT` sits
   on; reword them to say the citation pointed at the wrong line, with no
   number in span form.
6. **The convention.** A bullet in `AGENTS.md`'s Conventions list: cite code
   by its path and the name of the thing in it, never by line number, with
   the new Decision Record's number. `CLAUDE.md` is a symlink, so nothing
   else is edited.
7. **The Decision Record.** `.meta/assertions/decisions/DR-355.yaml` (the
   next free number when written), modelled on DR-354: context from this
   Issue, the alternatives (keep verifying lines; defang every Issue file as
   notes are; refuse the form), `enacted_in` `work:artifact/meta-check` and
   `work:artifact/meta-checks-citations-prose` as DR-331 has, consequences
   naming the step and the `AGENTS.md` bullet, and that it amends DR-130
   and DR-331 (in words; there is no `amends` slot, and "amends" is not a
   word the `stated relations` step reads). Then `just render`, which
   rewrites `.meta/decisions.md` and touches nothing under `.claude/`.
8. **The backlog Issue.**
   `issues/backlog/technical-writing-skill-no-line-citations.md` was
   written while planning. Once the Decision Record has its number, replace
   "the Decision Record `no-line-citations` added" in it with that number.

**Tests.** There are no unit tests for the citation steps; the probe in
*Done when* is the test. Run it from `.meta/` with the gate's interpreter
(`uvx --python 3.13 --with pyyaml python`), calling `no_line_citations()`
directly before and after adding a scratch `.md` file, and record the
output here. The `git grep` in *Done when* confirms step 5. The `BoardTest`
case for `with_note` in `pair/test_pair.py` still passes untouched, since
the pattern did not change.

**Risks.**
- The new step is stricter: any `path:line` span in a `.md` file fails,
  even a correct one, so step 5 must land in the same commit as step 1.
- This Issue file, the new Decision Record, the `AGENTS.md` bullet and the
  history entry must not carry the form either. Write the form as a path,
  a colon and the word `line` (no digits, so `PATH_LINE` does not match),
  or without backticks, as here. Run the `git grep` from *Done when* last,
  after every file is written.
- Running the step directly through `uvx` may need approval in a seat's
  sandbox. If it is refused, the probe's evidence is the `no line
  citations` lines in the `meta` gate's output with the scratch file in
  place, recorded the same way.
- A pair note in a later turn cannot fail it: `with_note` still defangs
  notes.

## Implementation notes

- **Where the plan was wrong.** Step 4 said the old history entry keeps its
  Evidence. The `history` step (`.meta/checks/files/history.py`) requires
  every Evidence to name a symbol that exists, and `path_and_line_claims` is
  gone, so the old entry now says the next entry replaced it and names
  `no_line_citations` as its Evidence. Running the step directly also needs
  `--with linkml-runtime`, because `checks.collect` imports it.
- **What each old citation became**, read from the file at the commit before
  the one that wrote it: the `Issue` class in `.meta/work/purpose.yaml`;
  `pages.adopt()` and `_scheme` in `.meta/lib/render/pages.py`; the
  `.gitignore` entry under `items` in `.meta/bundle.yaml`; `min_hits` in
  `run_benchmark` in `.meta/lib/search/benchmark.py`; and in
  `pair/README.md`, the "Sending back" step, the "A pass and an Issue share"
  paragraph under "Grooming the backlog", and the "Using it" table. The
  `pair-loop-spike-evidence` notes are about which line `CONTEXT` sat on, so
  they keep the numbers as prose ("line 141 of" the path), which the step
  does not read. The two notes that tell of rewording the old span into
  that prose describe the span in words (the path, a colon and 141), so
  they do not read as rewording the prose into itself.
- **Probe**, run from `.meta/` with
  `uvx --python 3.13 --with pyyaml --with linkml-runtime python -c "from checks.citations import no_line_citations; print(no_line_citations())"`
  and a scratch `probe-line-citation.md` at the root. With the line
  ``"`CONTEXT` lives at `pair/seats.py`"`` followed by a colon and 151
  inside the span, it printed one finding and nothing else in the tree:

  ```
  ['probe-line-citation.md: `pair/seats.py:151` cites a line; name the path and the thing in it instead']
  ```

  With the line rewritten to "`CONTEXT` lives in `pair/seats.py`." it
  printed `[]`. The scratch file was then removed.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/no-line-citations.md`, set it to `difficulty: medium`, and committed it as 84229a5f. It's one coherent change, so it isn't split into parts.
>
> What changed in the Issue:
>
> - **The check:** the `path and line claims` step will be renamed `no line citations` (`no_line_citations` in `.meta/checks/citations/claims.py`). It stops reading the cited file's lines. Instead it refuses every `path:line` code span in the prose it already reads, which is Markdown (Issue files included) and assertion YAML, with fenced code blocks stripped. Its message tells the writer to name the path and the thing in it instead.
> - **Other places that name the step:** `pair/board.py` (a comment and the `with_note` docstring) and `pair/README.md` get the new name. DR-130 and DR-331 also name the step; they stay as written, and the new Decision Record says it amends them.
> - **Existing citations:** the old line citations are all in `issues/done/`. I found nine files, not the eleven the Issue first gave. Each is rewritten to the path and the name of what the line held when the citation was written.
> - **Where the rule is stated:** a new bullet in the Conventions list of `AGENTS.md`, the `/technical-writing` skill, and a new Decision Record (the next free number, DR-355), with the decisions index re-rendered.
> - **Out of scope:** tool output in fenced blocks. Pair notes also stay out: `board.with_note` already rewrites their line citations so the check doesn't match them. So does prose like `` `pair/loop.py` line 1009 ``, which the convention covers but the step doesn't check.
> - **Done when:** no `path:line` code span is left outside fenced blocks, and no step is still called `path and line claims`. A probe recorded in the Issue shows a scratch file holding a line citation failing the new step, and the same file citing `CONTEXT` in `pair/seats.py` passing. Nothing in it names the gate as the test.

> **secondary, backlog turn 2**
>
> I checked the groomed Issue against the code. It's accurate, and `difficulty: medium` is the right level for one change of this size, so I left both as they were. I fixed one gap and committed it as 069707e6.
>
> **What was missing:** the rename list left out two places that name the old `path and line claims` step:
> - **`.meta/checks/citations/__init__.py`:** this file imports `path_and_line_claims` and lists it in `__all__`. If it isn't changed, the import breaks once the function is renamed.
> - **`.meta/checks/citations.history.md`:** this file has an entry for the old step that names `path_and_line_claims` as its evidence. The Issue now keeps that entry and asks for a new one after it, saying the step now refuses line citations instead of checking them.
>
> **Decision Records:** DR-154 also mentions the old step name. The Issue now lists it with DR-130 and DR-331 as records that stay as written.

> **primary, backlog turn 3**
>
> I'm leaving the Issue as it is this turn. I checked my partner's additions against the code, and all three are accurate:
>
> - **`.meta/checks/citations/__init__.py`** imports `path_and_line_claims` and lists it in `__all__`, so it has to follow the rename or the import breaks.
> - **`.meta/checks/citations.history.md`** has a "Stale line numbers in cited file paths" entry for the old step. Keeping that entry and adding a new one after it is the right way to handle it.
> - **DR-154** does mention the old `path and line claims` step. Listing it with DR-130 and DR-331 as records that stay as written is correct.
>
> The Issue stays at `difficulty: medium`, and I made no further edits.

> **primary, todo turn 1**
>
> I've written the plan under `## The plan` in `issues/todo/no-line-citations.md` and committed it as e47e541e. Nothing is implemented yet.
>
> **One scope change.** The Issue as groomed asked for the rule to go into the `/technical-writing` skill as well. Seats can't do that part. The skill's source is in `.meta/assertions/imported/structure.yaml`, and `just render` writes it to the tracked `.claude/skills/technical-writing/SKILL.md`. The seats' sandbox blocks writes there. If we changed the source anyway, that rendered copy would go stale and fail the gate on every round, and neither seat could fix it. The backlog Issue `pause-on-a-render-the-seat-cannot-write` describes exactly this happening before. So I took the skill out of this Issue and put it in a new one, `issues/backlog/technical-writing-skill-no-line-citations.md`. It's `difficulty: developer`, waits on this Issue, and needs you to run `just render` outside the sandbox.
>
> **The plan, in order:**
> 1. In `.meta/checks/citations/claims.py`, replace `path_and_line_claims` with a `no line citations` step (`no_line_citations`). It reads the same prose with the same pattern as before, but no longer opens the cited file; it refuses every `path:line` code span it finds.
> 2. Rename the import and the `__all__` entry in `.meta/checks/citations/__init__.py`.
> 3. Update the step's name in the comment and the `with_note` docstring in `pair/board.py`, and in `pair/README.md`. The code in `pair/board.py` doesn't change.
> 4. Add a new entry to `.meta/checks/citations.history.md`.
> 5. Rewrite the 17 existing line citations in nine files under `issues/done/`. For each, git history shows the commit that wrote it, and that commit's version of the file shows what the line held. The citation is then rewritten to name that thing.
> 6. Add a bullet to the Conventions list in `AGENTS.md`.
> 7. Write the Decision Record (DR-355), then `just render`. That only rewrites `.meta/decisions.md`, which the sandbox allows.
> 8. Write the new backlog Issue for the skill (already done this turn).
>
> **Tests.** The citation steps have no unit tests, so the probe in *Done when* is the test. It calls `no_line_citations()` directly, once with a scratch file holding a line citation and once without, and the output gets recorded in the Issue. The existing `with_note` test in `pair/test_pair.py` should pass unchanged.
>
> **Risks.**
> - The new step fails on every line citation, even a correct one. So the step change and the rewrite of the old citations have to land in the same commit.
> - This Issue file must not contain the citation form itself.

> **secondary, todo turn 2**
>
> My partner's plan holds up against the code. I made two corrections to it, committed as a62b9f25.
>
> **What I checked:**
> - **The citation count is right.** A `git grep` for the citation pattern finds 17 line citations in nine files under `issues/done/`, matching the plan. No Python or YAML file has one.
> - **The step itself.** `path_and_line_claims` in `.meta/checks/citations/claims.py` is as the plan describes: the same loop over files and the same pattern, so dropping everything after the match is all it needs.
> - **The Decision Record.** "Amends" is not one of the relation words the `stated relations` step checks, so the new record can say it amends DR-130 and DR-331 in plain words.
> - **The ignored copies.** The copies under `apm_modules/` are git-ignored, so they don't need editing.
>
> **What I changed:**
> - **Step 8.** It told the implementer to write the backlog Issue for the skill, but my partner already wrote it this turn. The step now says only to put the real Decision Record number into that backlog Issue once it is known.
> - **Risks.** I added two:
>   - The new Decision Record, the `AGENTS.md` bullet and the history entry must not contain a line citation either. The plan now says how to write the form without matching the pattern, and to run the final `git grep` after every file is written.
>   - The probe can't run here. The plan runs the step directly with `uvx`, and that command needed approval in my sandbox. If a seat is refused too, the plan now says to record the `no line citations` lines from the `meta` gate's output instead.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is this turn. I checked my partner's three edits against the code, and all three hold:
>
> - **Step 8.** I had already written the backlog Issue for the skill, so the step now only asks for the real Decision Record number to be filled in once it exists. That's correct.
> - **Writing about the citation form.** The suggested way, a path, a colon and the word `line`, is safe: the step only matches a path followed by a colon and digits, so it won't flag it. Running the final `git grep` after every file is written is also right.
> - **If the probe can't run directly.** Using the `no line citations` lines from the targeted `meta` gate's output as evidence is a sound fallback. The gate runs the same step function over the same files, so its output shows the same result.

> **primary, in-progress turn 1**
>
> Line citations are now refused: the gate step `path and line claims` is replaced by `no line citations`, which fails on any citation of a file by line number. Committed as 5b24d718. `just gate meta` passes 94 steps, including the new one, and `just gate pair` passes 231 tests and ruff.
>
> **What changed:**
> - **The step.** In `.meta/checks/citations/claims.py`, `no_line_citations` replaces `path_and_line_claims`. It no longer opens the cited file; every `path:line` code span in prose is a finding, and the message says to name the path and the thing in it instead. Fenced code blocks, where tool output lives, aren't read.
> - **The step's new name** is in `.meta/checks/citations/__init__.py`, the comment and `with_note` docstring in `pair/board.py`, and `pair/README.md`. The way pair notes are rewritten doesn't change.
> - **The 17 old citations** in nine files under `issues/done/` now name a function, constant, class or heading. I took each from the file as it stood when the citation was written. The `pair-loop-spike-evidence` notes are an argument about which line `CONTEXT` sat on, so they keep the numbers as plain words ("line 141 of `pair/seats.py`"), which the step doesn't read.
> - **The rule** is now a bullet in the Conventions list of `AGENTS.md`, and in a new Decision Record, DR-355, which says it amends DR-130 and DR-331. `just render` updated `.meta/decisions.md` and nothing under `.claude/`. The backlog Issue for the skill now cites DR-355.
>
> **Where the plan was wrong:**
> - **History entry.** The plan kept the old entry in `.meta/checks/citations.history.md` as it was. But the gate requires each entry's Evidence to name a function that exists, and `path_and_line_claims` is gone. So the old entry now says the next entry replaced it, and points at `no_line_citations`.
> - **Probe command.** Running the step directly needs `--with linkml-runtime` as well as pyyaml, because the checks package imports it.
>
> **The probe:** I put a scratch file with a line citation at the repository root and called the step directly. It reported that file and nothing else. Rewritten to "`CONTEXT` lives in `pair/seats.py`.", the file passed, and I removed it. The command and output are in the Issue's new "Implementation notes" section.
>
> The rule still isn't in the `/technical-writing` skill. That stays with `technical-writing-skill-no-line-citations` in the backlog, because you have to run `just render` outside the sandbox to write the skill's copy under `.claude/skills/`.

> **secondary, in-progress turn 2**
>
> My partner's implementation matches the plan, and the Issue's checks hold. I fixed one pair of old notes that the rewrite had made confusing, committed as 8e4239a7, and `just gate meta` passes all 94 steps.
>
> **What I checked:**
> - **No line citations are left.** A `git grep` for a code span of a path, a colon and digits finds only the probe's recorded output, which sits in a fenced block where the step doesn't look.
> - **The old step name is gone from live code.** `path and line claims` remains only in history: done Issues, the old Decision Records, the old history entry, and the new Decision Record (DR-355), which says what replaced it.
> - **The pair package is consistent.** `pair/board.py` and `pair/README.md` name the new `no line citations` step. The pattern and the rewrite of pair notes are unchanged.
>
> **What I fixed:** in `issues/done/pair-loop-spike-evidence.md`, two notes told how a seat reworded a line citation into prose. After the rewrite, each said the old citation, already in its new wording, "was reworded to say" that same wording, which made no sense. Both now describe the old citation in words: the path, a colon and 141. I added a line about this to the Issue's implementation notes.
>
> I didn't touch `pair/`, so I didn't run `just gate pair`; my partner reported it passing last turn.

> **primary, in-progress turn 3**
>
> I changed nothing this turn. My partner's fix is correct: after my rewrite, two old notes in `issues/done/pair-loop-spike-evidence.md` said a citation had been reworded into the very wording they already showed. Describing the old citation in words (the path, a colon and 141) makes them read correctly again. `just gate meta` passes all 94 steps. Neither of us touched `pair/` this turn, so I didn't rerun `just gate pair`; it passed with 231 tests last turn.
