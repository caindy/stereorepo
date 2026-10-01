Groom these Issues in {path}:

{issues}

Groom each one as you would groom one Issue: make it precise enough to plan (what is wanted, what is out of scope, and how anyone will know it is done, in behaviour and tests rather than gates: do not name `just gate` or any targeted gate as the test, since the loop runs the gate before any issue lands), with the effort fitted to its size. For a bug report, say how to reproduce it. In each one's front matter, set `difficulty:` to one of easy, medium, hard or developer. Use developer when the result needs the developer to check it by hand before it goes to main. Use hard when it is too big to do in one piece; in that case, split it by writing each part as a new file in issues/backlog/, named for the part, with `difficulty:` and `parent:` naming the Issue split in its front matter, and `waits_on:` listing any part that must land first. If an Issue cannot be done as written, add a `# Needs elaboration` section saying what is missing: the Issue then sits out until the developer answers it, and the pass carries on. Leave the other backlog Issues as they are.

{ranking}

Do not delete a backlog Issue or move one out of issues/backlog/, and do not touch issues/roadmap/ or anything outside issues/.
