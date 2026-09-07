# Issue form

An **Issue** is where a Challenge lives before it is taken up. It is what work
noticed and not done becomes (A15), and it is how a Challenge arrives from
outside — raised by the solo, by a scheduled job, or by an agent that has no
other way to reach this repository.

The middle heading is the filter. An observation earns an Issue when you can say
what would make it worth doing — a trigger, or a cost that will land. "This
function is long" has neither, and filing it makes the tracker into the
`TECH_DEBT.md` it replaced, with better tooling.

```markdown
---
name: Challenge
about: Work to be taken up — noticed and not done, or arriving from outside
title: ""
labels: challenge
---

**What was noticed.** The thing itself, and where. A path and a line if it has
one.

**What would make this worth doing.** The trigger, or the cost that will land.
If neither can be stated, this is an observation and not a Challenge.

**Where it was found.** The pull request or the work that turned it up, so the
context it was noticed in survives.

**Difficulty.** `easy`, `medium`, `hard` or `human`, as a label beside this
one: your guess at what it takes. `easy` and `medium` are taken up by a loop
the moment the label lands, and a loop that cannot finish relabels it `human`
and says why. `hard` waits for the solo with an agent beside him.
```

GitHub reads the front matter and removes it from the issue it creates, so what
is inside the fence is exactly what ships.

**Do not paraphrase the headings.** `.meta/check_pr.py` derives what a pull
request must contain from the form beside this one, and the two forms are read
the same way. A renamed heading is a check that stops asking for anything.
