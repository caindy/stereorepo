# The board

This directory is the repository's board: one Markdown file per Issue, and the
subdirectory holding a file is that Issue's stage. The board on `main` is the
authoritative one.

| Stage | What sits there | Who moves an Issue in |
|---|---|---|
| [`roadmap/`](roadmap/) | the developer's coarse, speculative intentions, which may never be done; no agent moves an Issue in or out | the developer |
| [`backlog/`](backlog/) | ready to work, in the running order `backlog/ORDER` gives, which ranks Flights and standalone Issues, a Flight's parts running at its line; the queue | the developer, or a session working with the developer; the pair loop, when it sends an Issue back |
| [`underway/`](underway/) | the one Issue the pair loop is working, from its start until it lands: in its backlog stage or its Flight check on its branch, and in any stage on `main` | the supervisor, when it starts an Issue |
| [`todo/`](todo/) | groomed, with a difficulty, and waiting for a plan | the supervisor |
| [`in-progress/`](in-progress/) | planned, and being implemented | the supervisor |
| [`desk-check/`](desk-check/) | a `developer` Issue whose result waits for the developer's check, or a Flight whose parts have landed | the supervisor |
| [`done/`](done/) | landed on `main` | the supervisor |

## Writing an Issue

An Issue is `issues/backlog/<slug>.md`, committed to `main`. The slug is its id:
there is no number to reserve. The front matter holds only what cannot be
observed or derived, and all of it is optional:

```markdown
---
difficulty: medium      # easy, medium, hard or developer; the pair sets it if you do not
waits_on: [other-slug]  # Issues that must be done first; another repository's is <repository>:<slug>
parent: flight-slug     # the Flight this Issue is a part of
---

# What is wanted, as a title

What is wanted, what is out of scope, and how anyone will know it is done.
```

The loop cannot see another repository's board, so a `<repository>:<slug>`
entry in `waits_on` holds the Issue until you remove it, once that Issue has
landed (DR-301).

An Issue is groomed once its front matter sets a `difficulty` and it has no
`Needs elaboration` section. `just groom` grooms each Issue with neither a
`difficulty` nor such a section, and places it in the running order, unless it
is a part of a Flight in `backlog/`, which runs at its Flight's line instead;
an Issue you write with a `difficulty` is taken as
groomed, and deleting its `difficulty` asks for it to be groomed again.

The front matter is the ontology's `Issue` class (`.meta/work/purpose.yaml`),
and `just gate meta` holds every Issue file to it: a key the class does not
declare, a difficulty outside its values, or a `waits_on` or `parent` naming no
Issue on the board fails the gate rather than leaving the Issue silently
ungroomed.

When the pair loop starts an Issue, it moves the file from `backlog/` to
`underway/` on `main` in a commit of its own, so the board shows what is being
worked and nothing that edits the backlog can edit it. Its progress through the
later stages exists only on its branch, `pair/<slug>`, and the commit that lands
it moves it out of `underway/`: to `done/`, to `desk-check/` for a Flight that
passes its check, or back to `backlog/` for a Flight left waiting on its
children. A send-back moves it from `underway/` to `backlog/` in a commit of its
own, without the branch's work. Seats never move Issue files. `just pair-status`
shows the board and the Issue underway.

An Issue that other Issues name in `parent:` is a Flight: one unit of value,
and how the developer will know it has been delivered. Its children are its
parts, and each lands on its own. The Flight waits in `backlog/` until the
last one is in `done/`, then the pair checks its "Done when" end to end on
`main` in the Flight check, with the Flight in `underway/`, and either writes
each gap as a new child or moves the Flight to `desk-check/`. There the
developer checks it once, without holding the loop, and accepting moves it to
`done/`.
The loop's mechanics are in [`pair/README.md`](../pair/README.md).
