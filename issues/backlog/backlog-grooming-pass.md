---
difficulty: medium
parent: backlog-grooming-and-ranking
waits_on: backlog-running-order
---

# Groom the whole backlog before taking the next Issue

The loop grooms an Issue only when it picks it up. Nothing looks at the
backlog as a whole, which is the only place priority can be judged. This part
adds a grooming pass to the loop that grooms every backlog Issue and writes
the ranking below the marker in `issues/backlog/ORDER` (the format
`backlog-running-order` defines).

## Wanted

- **When it runs.** Before `run` starts the next Issue, the supervisor
  compares each `issues/backlog/*.md` file on `main` (not `README.md`) with
  what the last pass left, recorded in `.pair/` as path to blob id. If any
  file is new or its content differs, a pass runs first. A file that only
  left the backlog does not trigger one, and neither does an edit to `ORDER`
  alone. With no record, a pass runs. The record is written when the pass has
  landed on `main`.
- **What the seats do.** A new prompt, `pair/prompts/stage-grooming.md`, asks
  the seats to groom every Issue in `issues/backlog/` as `stage-backlog.md`
  asks for one: precise enough to plan, with a `difficulty`, split if `hard`,
  a `# Needs elaboration` section if it cannot be done as written, and for a
  bug report, how to reproduce it. They may remove a `Needs elaboration`
  section they have answered. They rank the backlog below the marker, judged
  across the whole backlog, and leave the lines above it alone. They do not
  touch `issues/roadmap/`.
- **How it ends.** The same agreement rule as a stage, on its own branch in the
  shared worktree. The supervisor holds the result, and hands anything missing
  back to the seats as it does for a stage: every backlog Issue has a valid
  `difficulty`; every `hard` Issue has children and is moved to `done/`, as
  the backlog stage does now; `ORDER` names every backlog slug and no other;
  the lines above the marker are identical to `main`'s; nothing under
  `issues/roadmap/` or outside `issues/` changed. The pass lands on `main` as
  one squash commit, with the landing path Issues use.
- **Past the round cap.** A pass that does not settle within the cap pauses the
  loop for the developer rather than sending anything back.
- **Status.** `just pair-status` says when a grooming pass is in flight.

## Out of scope

- Removing or shortening the per-Issue backlog stage.
- A different model for the pass (`seat-models-per-stage`).

## Done when

- Pair tests with scripted seats show: a new backlog file causes one pass
  before the next Issue is taken; an unchanged backlog, or one that only lost
  a file, causes none; a pass that changes a line above the marker is not
  accepted; and a settled pass lands as one commit and records the backlog.
- `just gate` passes.
