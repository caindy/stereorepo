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
> I added `## The plan` to the issue and committed it (`d812e08b`, then a correction to the citation count). The issue can be done as written, so there is no `## Finished by hand (2026-10-05)

The seats finished their part in in-progress turn 1, and the gate failed only
on `rendered prose` for the two `.claude/skills/` copies, which their sandbox
cannot write. The running `just pair` had started before
`pause-on-a-render-the-seat-cannot-write` landed, so it handed the failure back
instead of pausing, and the round cap sent the Issue back without its code.
The developer's session applied the seats' changes from the branch
`pair/technical-writing-skill-successor-citations` to `main`, ran `just render`
outside the sandbox, and committed all five files. The grep in "Done when"
finds nothing, and a second `just render` leaves the tree unchanged.
