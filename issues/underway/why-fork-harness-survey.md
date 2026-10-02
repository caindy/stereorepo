---
difficulty: medium
parent: write-why-fork-into-records
waits_on:
  - why-fork-delivery-records
---

# Write the meta-harness survey and the cockpit's requirements as Explanation

One part of `write-why-fork-into-records`. Section 6 of `WHY_FORK.md`
surveys other meta-harnesses (three ways to hold a session, nine tools, and
why none is adopted), and section 7 lists what a cross-repository cockpit
must do. Neither is a decision; both are Explanation.

## Wanted

Both written where the Knowledge Management discipline (DR-184, DR-196)
routes Explanation, which is `wiki/stereorepo/`, following the Diátaxis
compass (DR-194) and the `/technical-writing` skill:

- the survey, with its table, citing the records `why-fork-delivery-records`
  wrote (seats as harness CLIs, no agent at the top) where it argues for
  them;
- the cockpit's requirements, stated as they are now: an Issue sent back
  stays in `backlog/`, and the status convention is whatever
  `cockpit-status-convention` publishes (if that has not landed, say it is
  to come, and cite the Issue).

Claims that can no longer be checked, such as the herdr entry's
"unverified" star count, are kept as what was observed when the survey was
made, dated.

## Out of scope

Building any part of the cockpit, and re-surveying the tools.

## Done when

Every row and bullet of sections 6 and 7 is in a page, each page passes the
`/wikisplain` checks, and `just gate` passes.
