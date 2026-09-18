---
name: Challenge
about: Work to be taken up — noticed and not done, or arriving from outside
title: ""
labels: challenge
---

**Waits on.** Nothing — or `#<n>` per Issue that has to close first. One line,
first, because `move file` sets `#<n>` as GitHub's native blocked-by relationship
and `just next` reads it to say what is ripe; a blocker that is not an Issue
keeps this waiting until the line is rewritten.

**What was noticed.** The thing itself, and where. A path and a line if it has
one.

**What would make this worth doing.** The trigger, or the cost that will land.
If neither can be stated, this is an observation and not a Challenge.

**Where it was found.** The pull request or the work that turned it up, so the
context it was noticed in survives.

**Difficulty.** `easy`, `medium`, `hard` or `human`: your guess at what it
takes, proposed here and not landed as a label. The reviewer reads every
Challenge before a coder takes it, and its verdict lands the label; a level
landed with the filing is the solo's verdict given in advance and skips the
reviewer. `easy` and `medium` are taken up by a loop the moment the label
lands, and a loop that cannot finish relabels it `human` and says why. `hard`
waits for the solo with an agent beside him.
