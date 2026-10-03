---
difficulty: developer
---

# Move the technical-writing and search skills' citations to the successors

`trim-decision-records-065-177`, `trim-decision-records-179-217` and
`trim-decision-records-218-272`
superseded records and moved every citation of them except those in the
`/technical-writing` and `/search` skills. Both skills' sources are artifacts
in `.meta/assertions/imported/structure.yaml` (`technical-writing` and
`search`), and `just render` writes them to `.meta/.apm/skills/<skill>/SKILL.md`
and to the tracked `.claude/skills/<skill>/SKILL.md`. The seats' sandbox
denies writes under `.claude/skills/` (see the done Issue
`render-in-seat-sandbox`), so a seat that changes the source leaves
`rendered prose` red on the `.claude` copy, and the pair loop cannot land it.

## Wanted

In both skills' text in `structure.yaml`, each citation of a superseded
record names its successor instead:

| Old | New | Skill |
|---|---|---|
| DR-106 | DR-329 | technical-writing |
| DR-134 | DR-332 | technical-writing |
| DR-175 | DR-334 | technical-writing |
| DR-190 | DR-335 | technical-writing |
| DR-192 | DR-336 | technical-writing |
| DR-194 | DR-337 | technical-writing, search |
| DR-195 | DR-338 | technical-writing |
| DR-198 | DR-339 | technical-writing |
| DR-209 | DR-342 | technical-writing |
| DR-272 | DR-349 | search |

In the same edit, the `/technical-writing` skill's opening sentence drops
`(work:personality/technical-writer)`: the Personality class is gone, and
`work:role/technical-writer` beside it is the live entry.

Then `just render` runs outside the sandbox, and the four tracked copies
(`.meta/.apm/skills/` and `.claude/skills/`, for each skill) are committed.
The untracked `.agents/skills/` copies follow from the render.

## Out of scope

The skills' other citations (DR-103, DR-171, DR-177, DR-184, DR-185,
DR-187, DR-196, DR-207) are live records and stay. Nothing else in the
skills' wording changes.

## Done when

A grep for the ten old numbers finds none of them in `structure.yaml`'s
skill text or in any of the four `SKILL.md` copies, neither names
`work:personality/`, and `just render` leaves the tree unchanged.

## Pair notes

> **primary, backlog turn 1**
>
> The issue was already ready to plan, so I only made it more precise and committed that as `282826f3`.
>
> **What I checked:**
> - All ten old→new mappings in the table match the `superseded_by` field in each old record.
> - Each successor is about the same subject the skill cites it for. For example, DR-337 covers the BM25F retrieval skill, and DR-349 covers "a tool that takes prose is reached through a skill".
> - The other records the two skills cite (DR-103, 171, 177, 184, 185, 187, 196, 207) are all still in force.
> - The rendered copies still contain the old citations: 13 lines in `/technical-writing` and 4 in `/search`.
>
> **What I changed in the issue file:**
> - "All four copies" now names them: `.meta/.apm/skills/` and `.claude/skills/` for each skill. The `.agents/skills/` copies are listed in `.gitignore`, so they aren't among the four.
> - I added an **Out of scope** section. The live citations stay, and nothing else in the skills' wording changes.
>
> I left `difficulty: developer` as it was. The seats' sandbox blocks writes under `.claude/skills/`, so the developer has to run `just render` outside it before this can land.

> **secondary, backlog turn 2**
>
> I'm leaving the Issue as it is. It is precise enough to plan, and I checked what it claims against the repository:
>
> - **Citations:** all ten old record numbers appear in the two skills' text in `structure.yaml` and in the rendered copies, at the places the table implies. No other superseded numbers show up there.
> - **The DR-194 replacement:** DR-194 is superseded by DR-337, and DR-337 covers both the writing standard and the BM25F search. So replacing DR-194 with DR-337 fits in both skills.
> - **The removed phrase:** the `work:personality/technical-writer` text that the Issue asks to drop appears only in the opening sentence of `/technical-writing`.
> - **Scope and done check:** "Out of scope" lists the live citations that stay. "Done when" is a grep plus a check that `just render` leaves the tree unchanged, with no gate named.
> - **Difficulty:** `developer` is right. The seats' sandbox blocks writes under `.claude/skills/`, so the developer has to run `just render` and commit the `.claude` copies before this can land.

## The plan

One source file changes: `.meta/assertions/imported/structure.yaml`, in the
artifacts `work:artifact/skill-search` (its `description` and `preamble`) and
the `technical-writing` skill artifact below it. No code changes.

1. In `skill-search`, replace DR-194 with DR-337 (twice) and DR-272 with
   DR-349 (twice). Each new number has the same width as the old one, so the
   folded `description` keeps its line breaks.
2. In the `technical-writing` artifact, replace each old number with its
   successor from the table: 16 citations on 13 lines across the opening sentence, the
   regimes heading, the standard, the routing list and the audit. Where a
   line already cites the successor's subject alongside it (none do today),
   do not duplicate it.
3. In the same opening sentence, delete `` (`work:personality/technical-writer`)``
   and leave `` `work:role/technical-writer` ``.
4. A seat runs `just render`. It writes `.meta/.apm/skills/*/SKILL.md`, and
   its writes to `.claude/skills/` fail in the sandbox. The seat commits the
   source and the `.meta/.apm` copies only.
5. At the desk check, the developer runs `just render` outside the sandbox
   and commits the two `.claude/skills/*/SKILL.md` copies.

**Tests.** No new probe. The check is the "Done when" grep, run over
`structure.yaml` and the four tracked copies:
`git grep -nwE "DR-(106|134|175|190|192|194|195|198|209|272)|work:personality"`
on those five paths finds nothing (today it finds 51 lines: 17 in the source
and 17 in each pair of copies), and `just render` followed by
`git status --porcelain` shows a clean tree.

**Risk.** Until step 5, the `.claude` copies disagree with the source, and
the `rendered prose` check fails. That is why the issue is `developer`. A
substitution must not touch a live citation: DR-196, DR-171 and DR-184 sit
on the same lines as old numbers, so edit by hand rather than with a
blanket replace keyed on prefixes.

## Pair notes

> **primary, todo turn 1**
>
> I added `## The plan` to the issue and committed it (`d812e08b`, then a correction to the citation count). The issue can be done as written, so there is no `# Needs elaboration` section.
>
> **What changes:** only one file, `.meta/assertions/imported/structure.yaml`, in two skill entries:
> - **`/search`:** DR-194 becomes DR-337 and DR-272 becomes DR-349, twice each. The new numbers are the same width as the old ones, so the wrapped description keeps its line breaks.
> - **`/technical-writing`:** 16 citations on 13 lines change to their successors. The opening sentence also loses `` (`work:personality/technical-writer`) ``.
>
> **Order:**
> 1. A seat edits `structure.yaml`.
> 2. The seat runs `just render`. That updates the `.meta/.apm` copies, but the sandbox blocks the `.claude/skills/` copies.
> 3. The seat commits the source and the `.meta/.apm` copies.
> 4. At the desk check, you run `just render` outside the sandbox and commit the two `.claude/skills/*/SKILL.md` copies.
>
> **Test:** no new automated test. A `git grep` for the ten old numbers and `work:personality/` over `structure.yaml` and the four tracked copies should find nothing. Running `just render` afterwards should leave `git status` clean.
>
> **Risks:**
> - Until step 4, the `.claude` copies don't match the source, so the `rendered prose` check fails. That is why the issue stays `developer`.
> - Live citations such as DR-196, DR-171 and DR-184 sit on the same lines as old numbers. The edit should be made citation by citation, not with a find-and-replace on a shared prefix.

> **secondary, todo turn 2**
>
> I fixed one real defect in the plan. Everything else in it checks out, so I changed nothing else.
>
> **The defect:** the check command in the plan would have passed even before the fix was made. It used `git grep -E` with `\b` to mark word boundaries, but `git grep -E` doesn't support `\b`. So the command already matched nothing in the current tree, where all the old citations are still present.
>
> **The fix:** the command now uses `git grep -nwE "DR-(106|…|272)|work:personality"`, where `-w` does the word matching. I ran it on today's tree and it finds 51 lines: 17 in `structure.yaml`, 17 across the two `.meta/.apm` copies and 17 across the two `.claude` copies. The plan now records that count as the starting point. I committed this as `a6eac387`.
>
> **What I confirmed in the rest of the plan:**
> - **Entries:** the two skill entries are named `work:artifact/skill-search` and `work:artifact/skill-technical-writing`.
> - **Count:** "16 citations on 13 lines" in `/technical-writing` is correct.
> - **No other files affected:** besides `structure.yaml` and the four rendered `SKILL.md` copies, no tracked file contains these citations, so `just render` changes nothing else.

> **primary, todo turn 3**
>
> I changed nothing this turn. My partner's correction holds and the plan is ready.
>
> My partner found that the plan's check command could not fail: `git grep -E` doesn't treat `\b` as a word boundary, so it found nothing even with every old citation still in place. They switched it to `git grep -nwE`, where `-w` does the whole-word matching.
>
> I ran the corrected command on the current tree. It finds 51 lines, matching the starting count the plan now records:
>
> | File | Lines |
> |---|---|
> | `.meta/assertions/imported/structure.yaml` | 17 |
> | `.meta/.apm/skills/technical-writing/SKILL.md` | 13 |
> | `.meta/.apm/skills/search/SKILL.md` | 4 |
> | `.claude/skills/technical-writing/SKILL.md` | 13 |
> | `.claude/skills/search/SKILL.md` | 4 |

## Implementation notes

Steps 1–4 of the plan are done. All 17 source lines in `structure.yaml`
now cite the successors, and the opening sentence of `/technical-writing`
names only `work:role/technical-writer`. Because none of the ten old
numbers appears anywhere else in `structure.yaml`, a whole-number
substitution was safe, and it left the live DR-103, DR-171, DR-177,
DR-184, DR-185, DR-187, DR-196 and DR-207 citations untouched. The grep
from **Tests** now finds 0 lines in the source and the `.meta/.apm`
copies.

`just render` wrote the two `.meta/.apm/skills/*/SKILL.md` copies, and
the sandbox refused `.claude/skills/search/SKILL.md` and
`.claude/skills/technical-writing/SKILL.md`, as the plan expected. Those
two copies still carry the old citations (17 lines), so `rendered prose`
stays red until step 5: at the desk check, the developer runs
`just render` outside the sandbox, commits the two `.claude` copies, and
reruns the grep, which should then find nothing in all five paths.

`just gate meta` fails only `rendered prose`, naming exactly those two
`.claude/skills/` files; every other meta check passes.

The loop handed this failure back to the seats rather than pausing on it,
and every in-progress turn after the first was quiet. That pause is what
`pause-on-a-render-the-seat-cannot-write` (`ae9512d0`) built. When
`unwritable_pages` in `pair/loop.py` reads the output of
`just gate meta pair specialization` on this branch, it returns both
`.claude/skills/` pages, so on that output the pause would fire. The likely
cause is a loop process that started before `ae9512d0` landed and still runs
the old code. If the developer restarts `just pair` after rendering, any
later Issue like this one should pause instead of looping.

## Pair notes

> **primary, in-progress turn 1**
>
> The seat's part of the change is done and committed. `just gate meta` fails on one check, `rendered prose`, as expected: the two `.claude/skills/` copies can only be written from outside the sandbox.
>
> - **Source:** in `.meta/assertions/imported/structure.yaml`, all 17 lines now cite the successor records. The `/technical-writing` opening sentence names only `work:role/technical-writer`. The ten old numbers appear nowhere else in that file, so changing each whole number was safe. The other citations, which point to records still in force, are unchanged.
> - **Render:** `just render` rewrote `.meta/.apm/skills/search/SKILL.md` and `.meta/.apm/skills/technical-writing/SKILL.md`. The plan's grep now finds nothing in the source or in those two copies.
> - **Gate:** the `rendered prose` failure names only `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`. Every other meta check passes.
>
> **You need to do this before it lands:** run `just render` outside the sandbox and commit the two `.claude/skills/` files. That clears the failing check, and the grep should then find nothing in any of the five files. The issue file's "Implementation notes" section says the same.
>
> I found no work outside this issue, so I added nothing to the backlog.

> **secondary, in-progress turn 2**
>
> I changed nothing this turn. My partner's work is correct and complete except for the part only you can do.
>
> **What I checked:**
> - **The citations:** each of the 17 changed lines in `.meta/assertions/imported/structure.yaml` names the successor from the Issue's table. The `/technical-writing` opening sentence now names only `work:role/technical-writer`, and the citations to records still in force are unchanged.
> - **The search:** the plan's `git grep -nwE` finds no old numbers in the source or in the two `.meta/.apm` copies. It finds 17 lines in the two `.claude` copies: 4 in `search` and 13 in `technical-writing`.
> - **The `.claude` copies:** I compared each `.claude/skills/*/SKILL.md` with its `.meta/.apm` copy. The only differences are those same 4 and 13 lines. So when you run `just render` it should change exactly those lines and nothing else.
> - **`just gate meta`:** it fails on one check, `rendered prose`, which names the two `.claude/skills/` files. Every other meta check passes.
>
> **What you need to do before this lands:** run `just render` outside the sandbox, then commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`. That should clear the `rendered prose` failure. Run the grep once more after you commit, and it should find nothing in any of the five files.

> **primary, in-progress turn 3**
>
> I changed nothing this turn. The only thing left is a step only you can do.
>
> `just gate meta pair specialization` fails on one check, `rendered prose`, which names `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`. Every other check passes. This is the failure the plan expected, and the reason the issue is `difficulty: developer`. The seats' sandbox blocks writes under `.claude/skills/`, so only `just render` run outside it can bring those two files in line with the source. I did not work around the sandbox, for example by committing the files through git plumbing, because that would get around the limit you set.
>
> **To finish it:**
> 1. Run `just render` outside the sandbox.
> 2. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 3. Rerun the plan's check; it should find nothing:
>    `git grep -nwE "DR-(106|134|175|190|192|194|195|198|209|272)|work:personality" -- .meta/assertions/imported/structure.yaml .meta/.apm/skills/ .claude/skills/`
>
> My partner compared each `.claude` copy with its `.meta/.apm` copy and found they differ only on the 17 citation lines (4 in search, 13 in technical-writing). So the render should change only those lines.

> **secondary, in-progress turn 4**
>
> I changed nothing this turn. The seats have done their part, and the rest is the step the plan leaves to you.
>
> `just gate meta` still fails on one check, `rendered prose`. It is failing because `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md` still carry the old citations. The seats' sandbox blocks writes to those files.
>
> **To finish it:**
> 1. Run `just render` outside the sandbox.
> 2. Commit the two `.claude/skills/` files.
> 3. Rerun the plan's `git grep -nwE` check. It should find nothing in any of the five files.

> **primary, in-progress turn 5**
>
> I changed nothing this turn: I ran `just render` again and the sandbox still blocks the two `.claude/skills/` files. The gate's one failure, `rendered prose`, is the step the plan leaves to you.
>
> The seats can't fix this, so each time the loop hands the failure back, the seats will make another empty turn. To stop that and finish the issue:
>
> 1. Run `just render` outside the sandbox.
> 2. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 3. Rerun this check, which should find nothing:
>    `git grep -nwE "DR-(106|134|175|190|192|194|195|198|209|272)|work:personality" -- .meta/assertions/imported/structure.yaml .meta/.apm/skills/ .claude/skills/`

> **secondary, in-progress turn 6**
>
> The citation work is unchanged; it still waits on the one step only you can do. This turn I found why the loop keeps handing the issue back to us.
>
> **What's happening:** the loop is supposed to pause when the only gate failure is a page the seats can't write. That rule is `unwritable_pages` in `pair/loop.py`, added by `pause-on-a-render-the-seat-cannot-write` (`ae9512d0`). I ran it on this branch's real output from `just gate meta pair specialization`. It returns both `.claude/skills/` pages, so on that output the rule should have paused.
>
> The loop's own records show the failure came back as an ordinary gate failure every time, so the loop never paused. The likely cause is that your `just pair` process started before `ae9512d0` landed and is still running the old code. I added a note saying this under "Implementation notes" in the issue file and committed it.
>
> `just gate meta` still fails on the same single check, `rendered prose`, naming the two `.claude/skills/` files.
>
> **What you need to do:**
> 1. Stop the loop.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`. Any later issue that hits this case should then pause instead of coming back to the seats.

> **primary, in-progress turn 7**
>
> I changed nothing this turn. The citation work is done, and the issue is still waiting on you to render the two `.claude/skills/` files.
>
> My partner added a note to the issue file explaining why the loop keeps handing the failure back to the seats instead of pausing. It's a reasonable explanation, and I kept it:
> - `unwritable_pages` is in `pair/loop.py`, and it is the rule meant to pause the loop when the only failure is a page the seats can't write.
> - My partner ran it on this branch's gate output and reports that it names both `.claude/skills/` pages, so it should have paused.
> - My partner's likely cause is that your running `just pair` started before commit `ae9512d0`, which added the pause, and is still on the old code. I couldn't confirm that commit's history myself, because my `git log` command was denied this turn.
>
> **What you need to do:**
> 1. Stop the loop.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`, so any later issue that hits this case should pause instead of coming back to the seats.

> **primary, in-progress turn 8**
>
> I changed nothing this turn, because the seats can't fix the one remaining failure. `rendered prose` still names `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`, and the sandbox blocks the seats from writing them.
>
> Until you finish it, the loop will keep handing this back for more empty turns:
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit the two `.claude/skills/` files.
> 4. Restart `just pair`. If my partner's diagnosis is right, the running loop predates the change that pauses on this kind of failure, and a restart would pick it up.

> **secondary, in-progress turn 9**
>
> I changed nothing this turn. The seats can't fix the one remaining failure.
>
> `just gate meta` still fails only on `rendered prose`. The two files it names, `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`, are ones the sandbox won't let the seats write.
>
> To finish it:
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit those two files.
> 4. Restart `just pair`. If the running loop predates `ae9512d0`, as I found last turn, the restart also lets it pause on this kind of failure instead of handing it back.

> **primary, in-progress turn 10**
>
> I changed nothing this turn. Only you can clear the remaining failure: `rendered prose` still names the two `.claude/skills/` files, and the sandbox blocks the seats from writing them.
>
> To finish it:
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`.

> **secondary, in-progress turn 11**
>
> I changed nothing this turn. `just gate meta` still fails only on `rendered prose`, which names the two `.claude/skills/` files the seats' sandbox won't let them write. Only you can finish this:
>
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`.

> **primary, in-progress turn 12**
>
> I changed nothing this turn, and the seats can't change anything that would help. The only failing check, `rendered prose`, names two files the sandbox won't let the seats write. Each turn the loop hands this back, the seats can only take another empty turn.
>
> To finish it:
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`.

> **secondary, in-progress turn 13**
>
> I changed nothing this turn. `just gate meta` still fails only on `rendered prose`, for the two `.claude/skills/` files that the seats' sandbox won't let them write.
>
> The loop has now handed this back for several turns with nothing for the seats to do. Only you can finish it:
>
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`.

> **primary, in-progress turn 14**
>
> I changed nothing this turn. I read the pause rule in `pair/loop.py` to see whether the loop has a fault that belongs in the backlog, and found nothing to file:
>
> - **The rule:** `unwritable_pages` returns the stale pages only when every failing step is `rendered prose` and every page it names is under a path the seats can't write. That is exactly this failure.
> - **Where it runs:** the gate check feeds it into `gate_unwritable`, which should pause the loop and ask you to render. My partner's earlier run of `unwritable_pages` on this branch's gate output named both `.claude/skills/` pages.
>
> So the code in this tree would pause on this failure. The likeliest reason the loop keeps handing it back is that your `just pair` process started before the pause landed and is still running the old code.
>
> To finish it:
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`, so later issues like this one pause instead of cycling back to the seats.

> **secondary, in-progress turn 15**
>
> I changed nothing this turn. `just gate meta` still fails only on `rendered prose`, for the two `.claude/skills/` files the seats' sandbox won't let them write. The seats have nothing left to do on this issue.
>
> To finish it:
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`.

> **primary, in-progress turn 16**
>
> I changed nothing this turn. The seats have no work left on this issue. The only failure is `rendered prose` on the two `.claude/skills/` files, which the sandbox won't let us write.
>
> To finish it:
> 1. Stop `just pair`.
> 2. Run `just render` outside the sandbox.
> 3. Commit `.claude/skills/search/SKILL.md` and `.claude/skills/technical-writing/SKILL.md`.
> 4. Restart `just pair`.

# Needs elaboration

The pair did not settle the in-progress stage within 16 turns.
