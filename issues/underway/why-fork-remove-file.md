---
difficulty: easy
parent: write-why-fork-into-records
waits_on:
  - why-fork-delivery-records
  - why-fork-board-wiki-pages
  - why-fork-harness-survey
  - why-fork-inherited-terms
---

# Delete WHY_FORK.md once its content has a home

The last part of `write-why-fork-into-records`. Once the other parts have
landed, every claim in `WHY_FORK.md` should be in a Decision Record or a
wiki page the gate checks.

## Wanted

- Audit the file section by section, and write in this Issue file where
  each section went. Sections 1 to 5 and 10 go to the records of
  `why-fork-delivery-records` and the pages of `why-fork-board-wiki-pages`;
  sections 6 and 7 to `why-fork-harness-survey`; section 8 to the Seat and
  Supervisor pages as evidence. Section 9 is a plan the bootstrap carried
  out, and needs no home. Anything found with no home is written where it
  belongs in this Issue.
- Delete `WHY_FORK.md`, remove the exemption
  `.meta/checks/citations/loaders.py` gives it, and remove every remaining
  reference to it outside `issues/done/`.

## Out of scope

Rewriting what the other parts wrote, beyond adding a missing claim.

## Done when

`WHY_FORK.md` is gone, no file outside `issues/done/` names it, the audit is
in this file, and `just gate` passes.
