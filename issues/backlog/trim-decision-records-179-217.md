---
difficulty: medium
parent: trim-kept-decision-records
---

# Trim PR First residue from DR-179 to DR-217

One part of `trim-kept-decision-records`: these kept Decision Records still
carry some of PR First, its GitHub choreography or the taxonomy of work in
their prose: DR-179, DR-185, DR-190, DR-192, DR-194, DR-195, DR-198, DR-200,
DR-204, DR-207, DR-209, DR-216 and DR-217.

## Wanted

For each record, read it and decide which of these holds, then act on it:

- **Only an example or an aside is stale**, and the rule stands on its own:
  write a successor that states the rule with a current example, and mark
  the old record superseded by it. One successor may cover several records
  in this part.
- **The rule stands, but its argument leans on what was removed** (a class
  the ontology no longer has, such as Actor, Job, Remit, Goal, Personality or
  Securable; a coder and a reviewer; a workflow or a pull request): write the
  successor that argues it from what the repository has now, and mark the
  old one superseded.
- **The record no longer decides anything:** withdraw it.
- **The mention is still true** (a word used in its ordinary sense, say):
  leave the record, and list it under a `## Left as is` heading in this file
  with the reason.

A Decision Record is never rewritten (Journaling): the only change to an old
record is its status and the link to its successor. Each new record takes
the highest number the record holds plus one, and is re-rendered.

Several of these records are cited by `CLAUDE.md` (`AGENTS.md`) and by
skills (DR-190, DR-194, DR-198, DR-207); where one is superseded, those
citations move to its successor.

## Out of scope

Records outside this part.

## Done when

Every record listed is superseded, withdrawn, or under `## Left as is` with a
reason; no successor's rule depends on a class, a verb or a workflow the
repository no longer has; and `just gate` passes.
