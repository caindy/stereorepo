---
slug: developer
context: stereorepo
minted: 2026-10-02
---

# Developer

**Developer** is the one person a repository serves, who builds it with agents and decides what they cannot.

## What the developer does

The developer adds work, as [[issue|Issues]] committed to `issues/backlog/` or
intentions in `issues/roadmap/`, and decides the running order. The pair loop
does the rest without them: the [[supervisor]] runs two [[seat|seats]] that
groom, plan, implement and land each Issue. The developer is asked for
something in only two places:

- a [[desk-check]], for a `developer` Issue before it lands and for a
  [[flight|Flight]] once its parts have landed;
- an Issue sent back with a `Needs elaboration` section, which waits out of
  the running order until the developer answers it (stereorepo's DR-307).

The developer may edit any file between turns. An edit clears both seats'
acceptance of the stage, so the seats see it before the stage advances.

The developer's attention is the scarcest thing in the repository, which is why
a Flight is desk-checked once rather than part by part (stereorepo's DR-298),
and why the loop runs one Issue at a time in a repository and in parallel only
across repositories (stereorepo's DR-311).

## What the developer is not

- **Not one of several.** A repository has exactly one developer. A process
  that needs a second person (a reviewer, a hand-off, a rota) is a poor fit.
- **Not a seat.** The seats write code too, but a seat is never the developer,
  and neither is any agent acting for the developer, however it is labelled.
- **Not a user, owner or operator.** Those name someone the product serves or
  someone who runs it; the developer is the person who builds it.

---

**See also:** [[seat]], [[desk-check]], [[ubiquitous-language]]
