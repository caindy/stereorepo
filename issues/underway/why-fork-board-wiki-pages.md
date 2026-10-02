---
difficulty: medium
parent: write-why-fork-into-records
waits_on:
  - why-fork-delivery-records
---

# Write wiki pages for the pair loop's concepts

One part of `write-why-fork-into-records`. The ontology added eight concepts
for the pair loop, and every concept in the Ubiquitous Language carries a
wiki entry (A17, DR-190), but `wiki/stereorepo/` has a page for none of them.

## Wanted

A page under `wiki/stereorepo/` for each of Issue, Board, Stage, Developer,
Seat, Supervisor, Quiet turn and Desk check, scaffolded and checked with the
`/wikisplain` skill. Each page's lead matches the concept's definition in
`.meta/assertions/imported/vocabulary.yaml`, and its body cites the Decision
Records `why-fork-delivery-records` wrote for the choices behind it.

- Issue says what an Issue is not (section 10 of `WHY_FORK.md`): no number,
  no status, labels or assignee, no comment thread.
- Board says it is one per repository, which board is authoritative, and
  that a view of it holds no state.
- Seat and Supervisor carry the booktutor spike's findings as evidence: the
  questions of section 8 and the spike's answers in `docs/PAIR_LOOP_SPIKE.md`
  in `caindy/booktutor`. If a seat cannot read that file, it adds a
  `# Needs elaboration` section asking the developer for a copy.

## Out of scope

Changing any concept's definition, and concepts other than these eight.

## Done when

The eight pages exist, the `/wikisplain` checks pass on each, and
`just gate` passes.
