---
difficulty: medium
parent: onboard-fitch-mvp
---

# Hold a landing whose gate has a step that could not run

A gate step that this environment cannot run reports `?` (Article 6,
`.meta/check.py`'s `closing_block`). A `?` passes where a person runs the gate
and fails only where `CI` is set (stereorepo's DR-261). The pair loop's gate
before landing (`pair/gate.py`) does not set `CI`, so an Issue lands even when
a step never ran.

fitch-mvp depends on that distinction. Its tests that need Neo4j report `?`
where neither Neo4j nor a Docker daemon is reachable, as in a seat's sandbox,
so a seat's targeted gate passes without them. The developer decided that
those tests must run before an Issue lands. Today nothing enforces that.

## Wanted

- When the gate before landing reports a step that could not run, the Issue
  does not land. The loop pauses with the reason, naming each step and why it
  could not run, so that the developer can supply what is missing (start
  Docker, say) and resume. It does not go back to the seats, which cannot
  provide an environment.
- A seat's targeted gate while it works is unchanged: a `?` there still
  passes.

## How anyone will know it is done

- A test with a fake gate whose output holds a `?` line: the loop pauses,
  `just pair-status` gives the step and its reason, and the Issue stays where
  it was.
- The same test with only `ok` lines lands as before.
- stereorepo's own gate, run as the loop runs it before landing, reports no
  `?`. Otherwise this change would hold every landing here.

## Out of scope

- What `?` means where a person runs the gate (DR-261 stands).
