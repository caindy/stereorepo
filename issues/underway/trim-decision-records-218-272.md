---
difficulty: medium
parent: trim-kept-decision-records
---

# Trim PR First residue from DR-218 to DR-272

One part of `trim-kept-decision-records`: these kept Decision Records still
carry some of PR First, its GitHub choreography or the taxonomy of work in
their prose: DR-218, DR-222, DR-229, DR-239, DR-241, DR-259, DR-262, DR-268,
DR-270 and DR-272.

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

DR-259 and DR-272 are cited by `CLAUDE.md` (`AGENTS.md`); where one is
superseded, that citation moves to its successor.

## Out of scope

Records outside this part.

## Done when

Every record listed is superseded, withdrawn, or under `## Left as is` with a
reason; no successor's rule depends on a class, a verb or a workflow the
repository no longer has; and `just gate` passes.
