# Roadmap form

A **roadmap** Issue is where intent lives: work meant to be done and deliberately
deferred. It is the same artifact as a Challenge Issue and faces the other way. A
Challenge looks back at something noticed and where; a roadmap Issue looks
forward at something meant and what it waits on. Both are intentional deferrals,
which is why the middle heading is the same question on both forms.

`.meta/roadmap.md` used to hold these as prose, and nothing consumed it (DR-088).
An Issue has what a file does not: an open and a closed, a title someone reads,
and a place for the argument that decides it.

```markdown
---
name: Roadmap
about: Work intended and deferred — what is meant to be built, and what it waits on
title: ""
labels: roadmap
---

**Waits on.** `#<n>` per Issue that has to close first, or the Decision, the
account or the Discipline that has to exist, in a few words. One line, first,
because `just next` reads it.

**What is intended.** The thing itself, in enough words to pick it up cold. What
it would change, and for whom.

**What would make this worth doing.** The trigger, or the cost that will land.
Intent with neither is a wish, and a wish is not deferred, it is dropped.

```

"Nothing" on the first line means it could start today, and then the question
is why it has not — which is the question a roadmap Issue exists to defer, so
a roadmap Issue waiting on nothing is usually a Challenge. `.meta/say triage
<n> <level>` makes it one, keeping its number, its thread and the reason it was
deferred; closing and refiling keeps none of them.

GitHub reads the front matter and removes it from the issue it creates, so what
is inside the fence is exactly what ships.

**Do not paraphrase the headings.** The forms beside this one are read by
`render.py` and `check_pr.py` the same way, and a renamed heading is a check
that stops asking for anything.
