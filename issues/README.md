# The board

This directory is the repository's board: one Markdown file per Issue, and the
subdirectory holding a file is that Issue's stage. The board on `main` is the
authoritative one.

| Stage | What sits there | Who moves an Issue in |
|---|---|---|
| [`roadmap/`](roadmap/) | intended, and not yet elaborated enough to work | the human; the pair loop, when it sends an Issue back |
| [`backlog/`](backlog/) | ready to work, in filename order; the queue | the human, or a session working with the human |
| [`todo/`](todo/) | groomed, with a difficulty, and waiting for a plan | the supervisor |
| [`in-progress/`](in-progress/) | planned, and being implemented | the supervisor |
| [`desk-check/`](desk-check/) | a `human` Issue whose result waits for the human's check | the supervisor |
| [`done/`](done/) | landed on `main` | the supervisor |

## Writing an Issue

An Issue is `issues/backlog/<slug>.md`, committed to `main`. The slug is its id:
there is no number to reserve. The front matter holds only what cannot be
observed or derived, and all of it is optional:

```markdown
---
difficulty: medium      # easy, medium, hard or human; the pair sets it if you do not
waits_on: [other-slug]  # Issues that must be done first
parent: parent-slug     # the Issue this one was split from
---

# What is wanted, as a title

What is wanted, what is out of scope, and how anyone will know it is done.
```

While an Issue is in flight its file on `main` stays in `backlog/`; its
progress exists only on its branch, `pair/<slug>`, and the commit that lands it
moves it to `done/`. Seats never move Issue files. `just pair-status` shows the
board and the Issue in flight.
