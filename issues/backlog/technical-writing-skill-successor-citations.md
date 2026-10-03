---
difficulty: developer
---

# Move the technical-writing and search skills' citations to the successors

`trim-decision-records-065-177` and `trim-decision-records-179-217`
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

In the same edit, the `/technical-writing` skill's opening sentence drops
`(work:personality/technical-writer)`: the Personality class is gone, and
`work:role/technical-writer` beside it is the live entry.

Then `just render` runs outside the sandbox and all four copies are
committed.

## Done when

A grep for the nine old numbers finds none of them in `structure.yaml`'s
skill text or in any of the four `SKILL.md` copies, neither names
`work:personality/`, and `just render` leaves the tree unchanged.
