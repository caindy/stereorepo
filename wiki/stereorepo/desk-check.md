---
slug: desk-check
context: stereorepo
minted: 2026-10-02
---

# Desk check

**Desk check** is the [[developer]]'s check, by hand, of a `developer` [[issue|Issue]]'s result before it lands on `main`, or of a [[flight|Flight]] after its parts have landed there.

## The one stage that waits for the developer

Every other move of an Issue is the [[supervisor]]'s, decided from what it can
observe (stereorepo's DR-306). A desk check is where the loop asks the
developer instead. The Issue waits in `desk-check/` with a brief the
[[seat|seats]] wrote, and the developer answers in one of two ways:

- `just pair-accept` accepts it;
- notes under `## Desk-check notes` in the Issue file, then
  `just pair-resume`, send it back.

For a Flight, both commands take the Flight's slug, since a Flight can wait at
its desk check while the loop works on another Issue.

The two kinds of desk check differ in whether they hold the loop.

- **A `developer` Issue** has not landed, so its desk check holds the loop.
  Accepting lands it; notes and a resume send it back to the pair.
- **A Flight**'s parts are already on `main`, so its desk check does not hold
  the loop (stereorepo's DR-298). Accepting moves it to `done/`; notes and a
  resume return it to `backlog/`, where its next Flight check writes each note
  as a new part.

A Flight is desk-checked once, on `main`, rather than part by part, because the
developer's attention is the scarcest thing in the repository and a part on its
own shows little of the value asked for.

## What a desk check is not

- **Not a review or an approval.** The pair has already done the reviewing in
  its turns; a desk check is the developer seeing the result, by hand, where it
  runs.

---

**See also:** [[flight]], [[developer]], [[stage]], [[ubiquitous-language]]
