# The board

This directory is the repository's board: one Markdown file per Issue, and the
subdirectory holding a file is that Issue's stage. The board on `main` is the
authoritative one.

| Stage | What sits there | Who moves an Issue in |
|---|---|---|
| [`roadmap/`](roadmap/) | the developer's coarse, speculative intentions, which may never be done; no agent moves an Issue in or out | the developer |
| [`backlog/`](backlog/) | ready to work, in the running order `backlog/ORDER` gives; the queue | the developer, or a session working with the developer; the pair loop, when it sends an Issue back |
| [`todo/`](todo/) | groomed, with a difficulty, and waiting for a plan | the supervisor |
| [`in-progress/`](in-progress/) | planned, and being implemented | the supervisor |
| [`desk-check/`](desk-check/) | a `developer` Issue whose result waits for the developer's check | the supervisor |
| [`done/`](done/) | landed on `main` | the supervisor |

## Writing an Issue

An Issue is `issues/backlog/<slug>.md`, committed to `main`. The slug is its id:
there is no number to reserve. The front matter holds only what cannot be
observed or derived, and all of it is optional:

```markdown
---
difficulty: medium      # easy, medium, hard or developer; the pair sets it if you do not
waits_on: [other-slug]  # Issues that must be done first; another repository's is <repository>:<slug>
parent: parent-slug     # the Issue this one was split from
---

# What is wanted, as a title

What is wanted, what is out of scope, and how anyone will know it is done.
```

An Issue is groomed once its front matter sets a `difficulty` and it has no
`Needs elaboration` section. `just groom` grooms each Issue with neither a
`difficulty` nor such a section, and places it in the running order; an Issue you write with a `difficulty` is taken as
groomed, and deleting its `difficulty` asks for it to be groomed again.

The front matter is the ontology's `Issue` class (`.meta/work/purpose.yaml`),
and `just gate meta` holds every Issue file to it: a key the class does not
declare, a difficulty outside its values, or a `waits_on` or `parent` naming no
Issue on the board fails the gate rather than leaving the Issue silently
ungroomed.

While an Issue is underway its file on `main` stays in `backlog/`; its
progress exists only on its branch, `pair/<slug>`, and the commit that lands it
moves it to `done/`. Seats never move Issue files. `just pair-status` shows the
board and the Issue underway.
