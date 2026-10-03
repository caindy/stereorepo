---
difficulty: developer
---

# Move the technical-writing skill's citations to the successors

`trim-decision-records-065-177` superseded DR-106, DR-134 and DR-175 with
DR-329, DR-332 and DR-334, and moved every citation of them except those in
the `/technical-writing` skill. The skill's source is the `technical-writing`
artifact in `.meta/assertions/imported/structure.yaml`, and `just render`
writes it to `.meta/.apm/skills/technical-writing/SKILL.md` and to the
tracked `.claude/skills/technical-writing/SKILL.md`. The seats' sandbox
denies writes under `.claude/skills/` (see the done Issue
`render-in-seat-sandbox`), so a seat that changes the source leaves
`rendered prose` red on the `.claude` copy, and the pair loop cannot land it.

## Wanted

In the skill's source in `structure.yaml`, each citation that names DR-175
names DR-334 instead, DR-134 becomes DR-332, and DR-106 becomes DR-329.
Then `just render` runs outside the sandbox and both copies are committed.

## Done when

A grep for DR-106, DR-134 and DR-175 finds none of them in
`structure.yaml` or either `SKILL.md`, and `just render` leaves the tree
unchanged.
