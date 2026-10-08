---
difficulty: developer
parent: pair-versus-single-seat
---

# Propose which landed Issues to replay

One part of `pair-versus-single-seat`. The replays are expensive, so the
developer chooses which landed Issues they run on. This Issue asks for a
choice, so it is `developer`: the seats write the proposal into this file,
and the developer chooses at its desk check.

## Wanted

A `## Proposal` section in this file, holding:

- **Candidates.** Between twelve and twenty Issues from `issues/done/` that
  did their own work. A Flight (an Issue that other Issues name in
  `parent:`) does not qualify, since its work landed in its parts. Only an
  Issue with a `Start <slug>` commit on `main` qualifies, since an Issue that
  landed before the pair loop has no start commit to replay from. Each comes
  with its slug, its `difficulty`, the area it changed (`pair/`, `.meta/`
  checks, bootstraps, documentation, or other), the commit it started from,
  and, where history shows one, the later Issue or revert that fixed its
  change.
- **Which start.** Some slugs have more than one `Start <slug>` commit,
  because the Issue was sent back, paused or reverted and started again
  (`pair-notes` and `python-seed-gate-format-check` have two each). The commit a candidate started
  from is the parent of the `Start <slug>` commit of the attempt whose
  landed change the fix corrects (for `pair-notes`, the attempt that
  `6fd1ea94 Revert pair-notes` undid). Where no fix names an attempt, it is
  the last `Start <slug>` before the Issue reached `issues/done/`. The
  proposal lists a slug's other start commits beside the one it uses.
- **Spread.** The candidates span every difficulty that has landed and every
  area above, and favour Issues whose change was later fixed. A table says
  how many fall in each difficulty and area.
- **How the fixes were found.** The `git log` searches used (a later
  Issue file or commit message that names the slug, a `Revert` commit), so
  the developer can check them.
- **Cost.** For each candidate, its logged two-seat cost (`cost_usd`),
  turns and wall-clock (`seconds`), summed over its rows in the
  `.pair/turns.jsonl` of the stereorepo checkout, saying when those rows span
  more than one attempt (if a seat cannot read that file, say so here). The
  single-seat estimate is the cost of its `primary` rows alone, labelled a
  lower bound: in `single-seat-mode` the one seat also takes the turns the
  secondary took, and closes each stage with a quiet turn of its own. Where a
  candidate has no rows, say so and estimate it from the mean of its
  difficulty. The section ends with the sum for replaying the whole proposal
  in each mode.
- **Recommendation.** The subset the seats would replay if the budget allows
  only eight to ten, and why.

The proposal is data in this Issue file. No code changes.

## How anyone will know it is done

- The section exists with every part listed under Wanted, holds twelve to
  twenty candidates, and no candidate is a Flight or lacks a `Start <slug>`
  commit.
- Every candidate's start commit resolves with `git rev-parse` and is the
  parent of a `Start <slug>` commit for that slug, and every named fix
  exists in history.
- The cost sums equal the sums of the per-candidate figures.
- The developer has chosen the sample at the desk check and written it into
  this file as a `## Chosen sample` list of slugs, which
  `pair-mode-decision` reads.

## Out of scope

- Running any replay.

## The plan

The only file that changes is this one: a `## Proposal` section goes in
above `## Pair notes`. The work is reading history and the turn log, and
any helper script lives in the seat's scratchpad, never in the repository.

What history shows, which the steps rely on:

- `main` is linear, and each attempt that landed did so as one squashed
  commit, titled for the Issue rather than its slug, that adds
  `issues/done/<slug>.md`. It need not follow its `Start <slug>` directly:
  the developer commits to `main` while the loop runs, so
  `9dc36c8e Start pair-notes` landed as `9f129a71`, four commits later.
  An attempt's landing is therefore the first commit after its start found
  by `git log --reverse --diff-filter=A <start>..main --
  issues/done/<slug>.md`, and an attempt with a later `Start <slug>` before
  any such commit was sent back and never landed. Its change is
  `git show <landing>`, never `git diff <start>^ <landing>`, which would
  sweep in the developer's commits between them.
- `issues/done/` holds 13 `developer`, 38 `easy`, 64 `medium` and 8 `hard`
  Issues. A Flight is any slug that appears in some `parent:` line there:
  `backlog-grooming-and-ranking`, `flight-instruments`, `flights`,
  `grooming-alongside-the-loop`, `keys-reach-the-landing-gate-not-the-seats`,
  `onboard-fitch-mvp`, `trim-kept-decision-records` and
  `write-why-fork-into-records`. `onboard-fitch-mvp`, the Issue's example
  of many starts, is therefore not a candidate.
- `.pair/turns.jsonl` in `/Users/christopher/code/stereorepo` is readable:
  1227 rows for 123 slugs, from 2026-09-30 on, each with `slug`, `stage`,
  `role`, `seconds` and `cost_usd`. Rows whose `stage` is `grooming` are
  `just groom`'s, not an Issue's, and are left out of every sum.

Steps:

1. **Eligible set.** List the slugs in `issues/done/`, drop the Flights,
   and keep those with at least one `Start <slug>` commit on `main`'s
   history. For each, record every start, the landing of each attempt that
   landed, and its `difficulty`.
2. **Area.** Classify each attempt from `git show --stat <landing>`
   by where most changed lines fall: `pair/` → `pair/`; `.meta/` scripts
   and checks → `.meta/` checks; bootstrap or seed projects → bootstraps;
   `wiki/`, `README`s, assertions-only → documentation; anything else →
   other. Changes under `issues/` do not count.
3. **Fixes.** For each eligible slug, search later history with
   `git log main --grep='<slug>'`, `git log main -S'<slug>' -- issues/`
   (a later Issue that names it), and `git log main --grep='^Revert'`.
   Keep a hit only when its change touches the same files as the attempt.
   Record the exact commands for **How the fixes were found**, and pick the
   attempt per **Which start**.
4. **Cost.** For each slug sum `cost_usd` and `seconds` and count rows
   (turns), excluding `grooming`; separately sum the `primary` rows as the
   single-seat lower bound. Note a slug whose rows straddle more than one
   start commit's date. A slug with no rows (it started before 2026-09-30)
   gets its difficulty's mean, marked as estimated.
5. **Choose.** Pick twelve to twenty candidates, first every fixed Issue,
   then fill each empty difficulty-and-area cell, then the cheapest of the
   rest. Write the candidate table, the spread table, the searches, the
   cost table with totals for each mode, and the eight-to-ten recommended
   subset with its reasons.

How we will know it works, checked by hand before the stage closes:

- For every candidate, the table gives both its `Start <slug>` commit and
  the start commit (that commit's parent); `git log -1 --format=%s` of the
  first reads `Start <slug>`, and `git rev-parse <Start commit>^` equals
  the second. Every named fix resolves with `git rev-parse`.
- No candidate's slug appears in a `parent:` line under `issues/done/`.
- The candidate count is between twelve and twenty, and every difficulty
  and area that has eligible Issues appears in the spread table.
- Recomputing each total from the per-candidate rows gives the same figure.

Risks:

- **Fix attribution is judgement.** A later commit that names a slug may
  extend its work rather than correct it. The proposal says, for each fix,
  what it corrected, so the developer can reject one at the desk check.
- **Cost before the log.** Issues that started before 2026-09-30 have no
  rows, so their cost is an estimate; the spread may push several into the
  proposal, and the totals must say how much of them is estimated.
- **Area by majority.** An Issue that touched several areas gets one;
  the candidate table shows the `--stat` summary beside the area so the
  call can be checked.

What the work showed the plan had wrong:

- **No estimates were needed.** Every eligible Issue has rows in
  `turns.jsonl`; the log reaches back past every `Start <slug>` commit.
- **No `hard` Issue is eligible.** All eight `hard` Issues in
  `issues/done/` are the eight Flights, so the spread can cover only
  `easy`, `medium` and `developer`.
- **Rows split by attempt.** A slug's rows carry no attempt, so they are
  assigned to the attempt whose `Start <slug>` commit time (local) is the
  latest at or before the row's `at`. Only `pair-notes` among the
  candidates has two attempts.
- **Area by lines.** Area is the bucket with the most added plus removed
  lines in `git show --numstat <landing>`: `pair/`; `bootstraps/`;
  `.meta/` code (`.py`, `.toml`, `.sh`) and `justfile` as `.meta/` checks;
  Markdown, `wiki/`, `.meta/assertions/` and `.meta/.apm/` as
  documentation; anything else as other. Lines under `issues/`,
  `.meta/assertions/decisions/` and the generated `.meta/decisions.md` do
  not count: a Decision Record rides along with most changes, and counting
  it labelled two bootstrap changes (`bootstrap-render-step`, whose DR-356
  is 57 lines, and `seed-rendered-gate-lost`, whose DR-360 is 73)
  documentation.

## Proposal

99 Issues are eligible: done, not a Flight, with a `Start <slug>` commit.
Eighteen are proposed. Area is counted as the plan's **Area by lines**
says, so a candidate's Decision Record does not decide it. "Start" is the `Start <slug>` commit of the attempt
to replay; "from" is its parent, the commit a replay starts from.

### Candidates

| Slug | Difficulty | Area | Start | From | Other starts | Later fix |
|---|---|---|---|---|---|---|
| `pair-notes` | medium | pair/ | `9dc36c8e` | `2d2df317` | `187f3dfd` | `6fd1ea94` reverted it: its seat instructions were refused by the model |
| `land-retries-a-passing-race` | medium | pair/ | `5377b86b` | `4fd2044b` | — | `6256e389` `land-leaves-a-half-landed-checkout`: a refused fast-forward left the checkout half landed |
| `squash-reverts-commits-on-main` | easy | pair/ | `73a8ab38` | `ed26ba7f` | — | `53ddccdf` `land-retries-a-passing-race`: its landing could still be refused by a passing commit on `main` |
| `fresh-seat-after-refusal` | medium | pair/ | `54f6768f` | `0e926222` | — | `f417ef19` lines its last turn left uncommitted, wrapped after landing |
| `seat-sandbox-permissions` | developer | pair/ | `97969871` | `1b20c030` | — | `d45b1919` `seat-git-signature-check-hangs`: since it landed a seat's `git show` and `git log` hung |
| `seat-sandbox-rust-builds` | easy | pair/ | `e2620ddd` | `04b93de4` | — | `3b326a7c` `seat-shell-rustc-wrapper-returns`: `RUSTC_WRAPPER=sccache` was back in a seat's shell |
| `claude-seat-test-stalls-under-load` | medium | pair/ | `e2f33d79` | `55cb72ab` | — | `e035b0e6` `pair-seat-tests-flaky-under-load`: the seat's timing tests still failed under load |
| `pair-notes-belong-to-the-loop` | medium | pair/ | `04c38626` | `5eac045d` | — | `861ca5c9` `notes-rewrite-refused-citations`: a kept note failed the gate by quoting a refused citation (extends as much as it corrects) |
| `notes-rewrite-refused-citations` | medium | .meta/ checks | `cef9ccca` | `23a7fe94` | — | `5ba95507` `drop-note-line-citation-rewrite`: removed its line-citation rewrite |
| `release-recipe-is-scaffold-only` | easy | .meta/ checks | `639b7005` | `5c52abf5` | — | `f8c9d731` `scaffold-recipes-from-the-render`: replaced its hand-kept list with one derived from the render |
| `specialized-portfolio-gate` | medium | .meta/ checks | `d315d055` | `c90a8ef9` | — | `b72dc419` `portfolio-steps-without-subject`: the steps it had answer `?` fail every run where `CI` is set |
| `release-apm-package` | developer | .meta/ checks | `32201ff2` | `57005d08` | — | — |
| `bootstrap-render-step` | easy | bootstraps | `1cb49561` | `c75224b9` | — | `b12297f6` `seed-rendered-gate-lost`: once it stopped naming `render`, nothing rendered a seed and gated the copy |
| `seed-rendered-gate-lost` | medium | bootstraps | `9c454d35` | `3f92bfe9` | — | `cd6e14da` `python-seed-packages-rename-unseen`: the restored gate missed a wheel naming a missing package |
| `adoption-discipline` | medium | documentation | `de61a0b3` | `0cff40cc` | — | `3823e012` `adopt-probe-passes-in-a-portfolio`: the `_probe_adopt` it added failed in every portfolio |
| `claim-scope-note-channel-verb` | easy | documentation | `d5c1b057` | `16adecbc` | — | — |
| `rename-discipline-journaling` | developer | documentation | `a238948d` | `00f40a3c` | — | — |
| `template-excludes-retired-say-path` | easy | other | `ac87b3fa` | `aa09987f` | — | — |

### Spread

| Difficulty | pair/ | .meta/ checks | bootstraps | documentation | other | Total |
|---|---|---|---|---|---|---|
| easy | 2 | 1 | 1 | 1 | 1 | 6 |
| medium | 5 | 2 | 1 | 1 | 0 | 9 |
| developer | 1 | 1 | 0 | 1 | 0 | 3 |
| Total | 8 | 4 | 2 | 3 | 1 | 18 |

Fourteen of the eighteen have a later fix. The other four fill cells no
fixed Issue reaches: `developer` in `.meta/` checks and documentation,
`easy` in documentation, and other. Every difficulty and area with an eligible
Issue appears; `hard` has none. `pair/` holds 46 of the 99 eligible
Issues, which is why it holds eight of the eighteen.

### How the fixes were found

For each eligible slug, with `<landing>` its landing commit:

- `git log <landing>..main -F --grep=<slug>`: later commits whose message
  names it, such as `f417ef19 Wrap the lines fresh-seat-after-refusal left
  uncommitted`.
- `git log <landing>..main -S<slug> -- issues/`: later Issue files that
  name it, followed to the commit that landed them.
- `git log main --grep='^Revert'`: the one revert of a pair-loop Issue is
  `6fd1ea94 Revert pair-notes`.

A hit was kept only when its commit changed a file outside `issues/` that
the candidate's landing also changed, and its Issue file says the
candidate's change caused or left the problem. Hits that only followed on
from a candidate were dropped: `5e1b36ae` (`gate-failure-goes-to-primary`
left landing out of scope), `dcba9633` (`pair-exit-codes` never covered
`pair-watch`), `3013c3bb` (the sync ran one change late before
`sync-keeps-a-portfolios-compiled-skills`), and `c2a14895` (the formatting
drift predated `python-seed-gate-stdout`). Two hits on documentation
Issues were dropped the same way: `991cd9f1` (`adopt-python-prerequisite`
stated in `ADOPT.md` what `specialize-python-prerequisite` had stated in
`SPECIALIZE.md`) and `3e9ea3f9` (`vocabulary-scope-note-paragraphs` fixed
how every scope note renders, not `claim-scope-note-channel-verb`'s edit).

### Cost

From `/Users/christopher/code/stereorepo/.pair/turns.jsonl`, leaving out
`grooming` rows. Turns is the row count and minutes the summed `seconds`,
rounded per candidate. Single-seat is the sum of `primary` rows alone, a
lower bound: in `single-seat-mode` the one seat also takes the turns the
secondary took, and closes each stage with a quiet turn of its own. No
candidate lacked rows, so nothing is estimated.

| Slug | Turns | Minutes | Two-seat $ | Single-seat $ (lower bound) |
|---|---|---|---|---|
| `pair-notes` | 10 | 41 | 11.71 | 9.38 |
| `land-retries-a-passing-race` | 10 | 9 | 6.12 | 4.06 |
| `squash-reverts-commits-on-main` | 9 | 10 | 6.20 | 4.19 |
| `fresh-seat-after-refusal` | 9 | 8 | 4.78 | 3.48 |
| `seat-sandbox-permissions` | 15 | 28 | 23.10 | 17.57 |
| `seat-sandbox-rust-builds` | 9 | 5 | 4.83 | 3.56 |
| `claude-seat-test-stalls-under-load` | 8 | 19 | 6.59 | 5.48 |
| `pair-notes-belong-to-the-loop` | 13 | 12 | 11.65 | 6.26 |
| `notes-rewrite-refused-citations` | 9 | 12 | 9.17 | 7.27 |
| `release-recipe-is-scaffold-only` | 12 | 10 | 6.75 | 3.86 |
| `specialized-portfolio-gate` | 9 | 36 | 9.26 | 7.10 |
| `release-apm-package` | 10 | 13 | 9.39 | 7.59 |
| `bootstrap-render-step` | 10 | 7 | 7.03 | 4.48 |
| `seed-rendered-gate-lost` | 10 | 15 | 11.04 | 7.62 |
| `adoption-discipline` | 9 | 9 | 9.60 | 7.13 |
| `claim-scope-note-channel-verb` | 7 | 2 | 1.65 | 1.00 |
| `rename-discipline-journaling` | 8 | 5 | 3.96 | 2.73 |
| `template-excludes-retired-say-path` | 6 | 2 | 1.37 | 0.80 |
| **All 18** | 173 | 243 | 144.20 | 103.56 |
| **Recommended 10** | 102 | 176 | 98.64 | 72.08 |

`pair-notes`'s rows span two attempts; the figures are attempt 1's ten
rows, and the slug's twenty rows total $18.63. Replaying all eighteen in
both modes costs about $247.76 (144.20 + 103.56) by these figures, and
more in fact, since the single-seat figure is a floor.

### Recommendation

If the budget allows only ten, replay those whose change was later fixed,
so each replay can be judged against a known defect, spread over every
area a fixed Issue reaches and every difficulty:

1. `pair-notes`: the one reverted landing, the clearest failure.
2. `seat-sandbox-permissions`: the only `developer` Issue with a fix, a
   regression found in use.
3. `squash-reverts-commits-on-main`: an `easy` Issue whose landing logic
   still had a hole.
4. `fresh-seat-after-refusal`: a defect the pair left in its own last turn.
5. `notes-rewrite-refused-citations`: a `.meta/` change later withdrawn.
6. `specialized-portfolio-gate`: a `.meta/` change that failed under CI.
7. `release-recipe-is-scaffold-only`: a narrow fix later generalised; tests
   whether either mode sees the general case.
8. `bootstrap-render-step`: a bootstraps change that lost a check.
9. `seed-rendered-gate-lost`: the follow-on whose own fix missed a case.
10. `adoption-discipline`: the one documentation Issue with a fix, a
    probe that passed in stereorepo and failed in every portfolio.

That is 102 turns, about $99 in two-seat mode and at least $72 in
single-seat. It leaves out the four unfixed fillers, which give cost and
speed but no quality signal, and four fixed `pair/` Issues whose defects
overlap ones kept: `land-retries-a-passing-race` (the landing chain),
`pair-notes-belong-to-the-loop` (the notes chain),
`claude-seat-test-stalls-under-load` (a test-only change) and
`seat-sandbox-rust-builds` (the sandbox, as `seat-sandbox-permissions`).
Other is not in the ten, since no Issue there has a fix.

## Chosen sample

Chosen by the developer on 8 October 2026: the recommended ten first, in both
modes. The other eight are a second round, replayed only if the first leaves
the decision open.

First round:

1. `pair-notes`
2. `seat-sandbox-permissions`
3. `squash-reverts-commits-on-main`
4. `fresh-seat-after-refusal`
5. `notes-rewrite-refused-citations`
6. `specialized-portfolio-gate`
7. `release-recipe-is-scaffold-only`
8. `bootstrap-render-step`
9. `seed-rendered-gate-lost`
10. `adoption-discipline`

Second round, if needed: `land-retries-a-passing-race`,
`pair-notes-belong-to-the-loop`, `claude-seat-test-stalls-under-load`,
`seat-sandbox-rust-builds`, `release-apm-package`,
`claim-scope-note-channel-verb`, `rename-discipline-journaling` and
`template-excludes-retired-say-path`.

The loop could not carry this Issue to its desk check, because its work is
its own file and the `in-progress` stage closes only on a change outside
`issues/` (`land-an-issue-whose-work-is-its-file`). The developer completed
it by hand, moving it to `issues/done/` with this section.

## Pair notes

> **primary, backlog turn 1**
>
> This Issue was already groomed in the "Groom the backlog" commit just before this turn, and it holds up. It says what is wanted (a `## Proposal` section with candidates, spread, how fixes were found, cost and a recommendation). It also says what is out of scope (running any replay) and how anyone will know it is done (every start commit and fix resolves in history, and the developer writes a `## Chosen sample`). `difficulty: developer` is right, because the Issue asks the developer to choose.
>
> I checked that the facts it relies on exist:
> - **Start commits:** there are 112 `Start <slug>` commits on `main`.
> - **Reverts:** at least one exists, `6fd1ea94 Revert pair-notes`.
> - **Cost data:** `.pair/turns.jsonl` in the main stereorepo checkout is readable, and its rows give cost, turns and seconds per slug.
>
> I made one change. `issues/done/` holds 124 Issues but there are only 112 start commits, so some Issues landed before the pair loop and have no start commit to replay from. The candidate rule now says only an Issue with a `Start <slug>` commit on `main` qualifies.

> **secondary, backlog turn 2**
>
> My partner's grooming mostly holds up, and `difficulty: developer` is right because the Issue asks the developer to choose the sample. I found two gaps and fixed both in `issues/underway/replay-sample-proposal.md`.
>
> 1. **More than one start commit for some Issues.** The Issue said "the parent of its `Start <slug>` commit", but some slugs have several, because the Issue was sent back, reverted or started again. `onboard-fitch-mvp` has six, and `pair-notes` and `python-seed-gate-format-check` have two each. I added a **Which start** rule:
>    - Use the attempt whose landed change the fix corrects. For `pair-notes`, that is the attempt `6fd1ea94 Revert pair-notes` undid.
>    - Where no fix names an attempt, use the last start before the Issue reached `issues/done/`.
>    - List the Issue's other start commits beside the one used.
> 2. **No basis for the single-seat cost.** The Issue asked for the cost "in both modes" but gave no way to estimate the single-seat one. Each row in `turns.jsonl` records which seat ran the turn, so the single-seat estimate is now the cost of the `primary` seat's rows alone. The proposal must also say when an Issue's rows span more than one attempt.
>
> I also made the done criteria checkable:
> - The proposal holds twelve to twenty candidates, with no Flights and none that lack a start commit.
> - Each start commit is the parent of a `Start <slug>` commit for that slug.
> - The cost totals equal the sums of the per-candidate figures.
>
> I committed this as `cad85f9b`.

> **primary, backlog turn 3**
>
> I kept both of my partner's changes and made one correction to how the single-seat cost is estimated.
>
> **What I kept:**
> - **Which start:** when an Issue has more than one `Start <slug>` commit, the proposal uses the attempt whose change was later fixed, and otherwise the last start before the Issue landed.
> - **Done criteria:** they are now things anyone can check against the file and against history.
>
> **What I changed:** my partner estimated single-seat cost from the `primary` seat's rows in `turns.jsonl` alone. That figure is too low, so the Issue now asks for it to be labelled a lower bound and says why:
> - In the single-seat mode that `single-seat-mode` describes, the one seat also does the work the secondary seat did.
> - A stage there closes only after a quiet turn by that same seat, so each stage takes at least one turn more than the primary's share today.
>
> `difficulty: developer` stays, because the developer chooses the sample at the desk check.

> **secondary, backlog turn 4**
>
> I'm changing nothing this turn.
>
> My partner's one change is correct: the single-seat figure, taken from the `primary` seat's rows alone, is now labelled a lower bound. In single-seat mode the one seat also does the secondary seat's work, and it closes each stage with an extra turn in which it changes nothing. The rest of the Issue is as I left it, `difficulty: developer` still fits because the developer chooses the sample, and I see nothing else to fix.

> **primary, todo turn 1**
>
> I've written `## The plan` into `issues/todo/replay-sample-proposal.md`, above its Pair notes. Nothing is implemented yet: the only file that will change is the Issue itself, and any helper script stays in the seat's scratchpad.
>
> **What reading history and the turn log showed:**
> - **One commit per Issue's change:** on `main` (following first parents only), each `Start <slug>` commit is followed directly by one squashed landing commit. So an attempt's whole change is the diff from the commit before its start to its landing commit.
> - **`onboard-fitch-mvp` cannot be a candidate:** 15 Issues under `issues/done/` name it in `parent:`, which makes it a Flight. The Issue currently uses it as its example of a slug with several start commits. Eight Issues in `issues/done/` are Flights in all.
> - **What landed:** `issues/done/` holds 13 `developer`, 38 `easy`, 64 `medium` and 8 `hard` Issues.
> - **The cost log is partial:** `.pair/turns.jsonl` has 1227 rows for 123 slugs, but only from 2026-09-30 on. Issues that started earlier have no rows, so their cost will be estimated from the mean for their difficulty. Rows from `just groom` are not any one Issue's and are left out of the sums.
>
> **Steps in order:**
> 1. List the eligible Issues: done, not a Flight, and with at least one `Start <slug>` commit.
> 2. Assign each one an area from which files its change touched.
> 3. Find later fixes with `git log` searches (commit messages, later Issue files, `Revert` commits) and record the exact commands.
> 4. Sum each candidate's two-seat cost, turns and wall-clock, and its `primary` rows as the single-seat lower bound.
> 5. Pick 12 to 20 candidates (fixed Issues first, then whatever fills the spread), and write the tables and the recommended subset of eight to ten.
>
> **Checks:** these are done by hand. Every start commit must resolve and be the parent of a `Start <slug>` commit. Every named fix must exist in history. No candidate may be a Flight. Each total must equal the sum of its rows.
>
> **Risks:**
> - **Deciding what counts as a fix is judgement:** a later commit naming a slug may extend the work rather than correct it.
> - **Costs before 2026-09-30 are estimates:** the totals must say how much of them is estimated.
> - **Each Issue gets one area:** an Issue that touched several is classed by the majority of its changed lines.

> **secondary, todo turn 2**
>
> I corrected the plan in `issues/todo/replay-sample-proposal.md` and committed it as `be6750a6`. My partner's plan was otherwise sound, but it rested on a false claim about history.
>
> **The false claim.** The plan said each `Start <slug>` commit on `main` is followed directly by the squashed commit that lands it, so an attempt's change would be `git diff <start>^ <landing>`. That is not true. The developer commits to `main` while the loop runs, so other commits fall in between: `9dc36c8e Start pair-notes` landed as `9f129a71`, four commits later. A diff from the start would take in those other commits and give the wrong area for an Issue.
>
> **What the plan says now:**
> - **Finding the landing:** an attempt's landing is the first commit after its start that adds `issues/done/<slug>.md`. If another `Start <slug>` comes before any such commit, that attempt was sent back and never landed.
> - **The change:** an attempt's change is `git show <landing>`. The area is classified from `git show --stat <landing>`, ignoring anything under `issues/`.
> - **The steps:** they no longer rely on `main`'s first-parent line.
>
> I also took `onboard-fitch-mvp` out of the "Which start" example I had written into the Issue. My partner found that it is a Flight, so it can never be a candidate, and the example now names only `pair-notes` and `python-seed-gate-format-check`.

> **primary, todo turn 3**
>
> I'm changing nothing this turn: my partner's correction is right, and the rest of the plan stands.
>
> I checked their landing rule against the history of the two Issues the plan names as having more than one start:
> - **`pair-notes`:** the first attempt began at `9dc36c8e` and landed at `9f129a71`, four commits later, as my partner said. `6fd1ea94 Revert pair-notes` removed `issues/done/pair-notes.md` again. The second attempt began at `187f3dfd` and landed at `e6090fdb`.
> - **`python-seed-gate-format-check`:** the attempt that began at `6e57e1c0` has no commit adding `issues/done/python-seed-gate-format-check.md` before the next start, so it was sent back. The attempt that began at `0eaccd75` landed at `c2a14895`.
>
> So an attempt's landing is the first commit after its start that adds `issues/done/<slug>.md`, and its change is that one commit (`git show <landing>`). My earlier diff from the start commit would also have taken in the developer's own commits in between. No step of the plan still depends on that mistake.

> **primary, in-progress turn 1**
>
> I've written the `## Proposal` section into `issues/in-progress/replay-sample-proposal.md`: 18 candidates, with 10 recommended for replay. A script check against history passes, `just gate meta` passes, and it is committed as `06c54178`.
>
> **The candidates.** 99 Issues are eligible: in `issues/done/`, not a Flight, and with a `Start <slug>` commit.
> - Of the 18 proposed, 13 have a later fix: the `pair-notes` revert and 12 later Issues that corrected a candidate's change.
> - The other 5 fill difficulty and area cells that no fixed Issue reaches.
> - No `hard` Issue can be included: all eight `hard` Issues in `issues/done/` are Flights.
>
> **The recommendation.** Ten fixed Issues, so each replay can be judged against a known defect:
> - `pair-notes`, `seat-sandbox-permissions`, `squash-reverts-commits-on-main`, `fresh-seat-after-refusal` and `seat-sandbox-rust-builds` in `pair/`.
> - `notes-rewrite-refused-citations`, `specialized-portfolio-gate` and `release-recipe-is-scaffold-only` in `.meta/` checks.
> - `bootstrap-render-step` and `seed-rendered-gate-lost` in documentation.
>
> **Cost.**
>
> | | Turns | Two-seat | Single-seat |
> |---|---|---|---|
> | All 18 | 179 | $147.29 | at least $105.33 |
> | Recommended 10 | 102 | $93.87 | at least $68.51 |
>
> The single-seat figures are the `primary` seat's rows alone. They are a floor, because one seat would also take the secondary's turns and close each stage with an extra quiet turn. Every candidate had rows in `.pair/turns.jsonl`, so nothing is estimated.
>
> **The check.** A script in my scratchpad confirmed four things against the file and history:
> - Each "Start" commit's subject is `Start <slug>`.
> - Each "From" commit is that commit's parent.
> - Every named fix exists.
> - No candidate is a Flight, and both totals equal the sums of their rows.
>
> **Where the plan was wrong.** I recorded four corrections in the plan:
> - No cost estimates were needed.
> - `hard` cannot appear in the spread.
> - A slug's turn rows don't say which attempt they belong to, so I split them by the time of each `Start <slug>` commit. Only `pair-notes` among the candidates has two attempts.
> - An Issue's area is the one with the most changed lines in its landing commit.
>
> **Judgement calls the developer should check:**
> - **`pair-notes-belong-to-the-loop`:** the later Issue I counted as its fix extends the change as much as it corrects it, and the table says so.
> - **Four dropped hits:** I dropped four search hits that followed on from a candidate's change without correcting it, and the proposal names each one so the developer can restore any of them.
>
> The `## Chosen sample` is the developer's to write at the desk check.

> **secondary, in-progress turn 2**
>
> I re-checked every candidate against history: each Start commit's subject is `Start <slug>`, each From is its parent, and each fix lands after the candidate. All held. Costs I recomputed matched where I sampled them.
>
> **What I changed.** Area by lines counted the Decision Record that rides along with most changes. That made `bootstrap-render-step` (DR-356, 57 of its 98 lines) and `seed-rendered-gate-lost` (DR-360, 73 lines) documentation, when both changed `bootstraps/*/render`. With `.meta/assertions/decisions/` and `.meta/decisions.md` left out of the count, both are bootstraps, so:
> - **Dropped:** `python-seed-gate-stdout` and `python-seed-packages-rename-unseen`, the unfixed fillers for the bootstraps cells, which fixed Issues now fill.
> - **Added:** `adoption-discipline` (medium, documentation). Its `_probe_adopt` failed in every portfolio until `3823e012` (`adopt-probe-passes-in-a-portfolio`) fixed it; the `-S` search found that hit, and it touches `.meta/checks/probes/files/rendered.py`, which the candidate's landing added the probe to. `claim-scope-note-channel-verb` (easy, unfixed) fills easy documentation.
> - **Recommendation:** `adoption-discipline` replaces `seat-sandbox-rust-builds`, so the ten reach documentation as well; `pair/` keeps four.
>
> Totals are now $144.20 two-seat and at least $103.56 single-seat for all eighteen, and $98.64 and at least $72.08 for the ten. `just gate meta` passes.

> **primary, in-progress turn 3**
>
> I kept all of my partner's changes and corrected one count in the proposal. `just gate meta` passes.
>
> **My partner's changes check out.**
> - **Area rule:** an Issue's area no longer counts the lines of the Decision Record that comes with most changes. I re-ran my survey with that rule, and every candidate's area in the table matches.
> - **New fix for `adoption-discipline`:** `587ea4da`, its landing commit, added `_probe_adopt`. The Issue `adopt-probe-passes-in-a-portfolio` says that probe failed in every portfolio, so it is a real fix.
> - **Tables:** my check script still passes. Every start commit's subject is `Start <slug>`, each "from" commit is its parent, every named fix exists, and no candidate is a Flight. Both cost totals equal the sums of their rows, and the spread table matches the new set of candidates.
>
> **What I changed.** Under the corrected rule, `pair/` holds 46 of the 99 eligible Issues, not 45, so the Spread text now says 46. All other figures in the proposal are unchanged.

> **secondary, in-progress turn 4**
>
> I'm changing nothing this turn.
>
> My partner's one change is correct. Under the corrected rule, `pair/` holds 46 of the 99 eligible Issues: my own survey with the same rule finds 27 medium, 13 easy and 6 developer Issues there. Everything else in the proposal is as I left it and already checked. The developer chooses the sample at the desk check.

> **primary, in-progress turn 5**
>
> The loop can't land this Issue, so I've sent it back to the developer with the proposal intact instead of inventing a change outside `issues/` to get past the check.
>
> **Why it is stuck.** The in-progress stage only closes once something outside `issues/` has changed on the branch (`requirement` in `pair/loop.py`). This Issue's work is the proposal written into its own file, and the Issue itself says "No code changes", so that condition can never be met. Any change outside `issues/` made only to satisfy it would be work the Issue never asked for.
>
> **What I did** (committed as `ac7b6d2d`, and `just gate meta` passes):
> - **`# Needs elaboration`:** I added this section to `issues/in-progress/replay-sample-proposal.md`. A file with that section goes back to `issues/backlog/` and waits for the developer, and the proposal goes back with it. The section explains the problem and suggests the developer write `## Chosen sample` from the proposal and move the file to `issues/done/` by hand.
> - **New backlog Issue:** `issues/backlog/land-an-issue-whose-work-is-its-file.md` describes the gap in the loop. It offers two options and leaves the choice to grooming: let a `developer` Issue close with only its own file changed, or let an Issue declare in its front matter that its work is its file. It names a test in `pair/test_pair.py` that would show it is done.
>
> The proposal itself is unchanged from the version both seats checked.
