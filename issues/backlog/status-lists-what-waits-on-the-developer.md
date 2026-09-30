---
difficulty: medium
---

# `pair-status` lists what waits on the developer

The loop and the grooming pass can say that something needs the developer, but
nothing tells the developer. An Issue with a `# Needs elaboration` section sits
out of the running order silently, and the developer finds it only by reading
files. `just pair-status` shows the board's counts and the Issue being worked,
cutting the backlog list short, and says nothing about what is waiting for
the developer.

The developer's interface is the files, presented by a cockpit, and worked
with a transient interactive session. This is the first slice of that
presentation for one repository: one screen that answers "what needs me, and
what happens next".

## What is wanted

`just pair-status` shows, from the board on `main` and `.pair/`:

- **What waits on the developer**, first, one line each with the reason:
  - every Issue in `backlog/` with a `Needs elaboration` section, with the
    section's first line;
  - every Issue in `desk-check/`, a Flight among them with the first line of
    its latest desk-check brief;
  - a paused loop, with the reason it paused (a seat that failed twice, a
    grooming pass or stage past its round cap, a refused fast-forward).
- **What happens next:** the Issue being worked, its stage and turn; then the
  running order, in full, marking which Issues are ripe and, for each that is
  not, what it waits on. A Flight is one entry in that order, with its parts
  beneath it in the order they will run, each marked done, ripe or waiting,
  and last the Flight's own check.
- The board's counts per stage, as now.

Nothing new is stored: every line is derived from the board, `ORDER`, and
`.pair/state.json`.

## Out of scope

- Notifications, and anything across repositories (`cockpit-status-convention`).

## Done when

- Each kind of waiting item above appears under what waits on the developer,
  with its reason, and nothing appears there when nothing waits.
- The running order is shown in full, with ripe and waiting Issues told apart,
  and each Flight shown with its parts beneath it.
- The pair tests cover each case, and `just gate` passes.
