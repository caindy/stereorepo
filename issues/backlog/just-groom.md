# Groom with `just groom`, apart from implementation

The grooming pass runs inside `just pair`: before taking each Issue, the loop
compares every backlog file on `main` with `.pair/groomed.json` and runs a pass
whenever one is new or changed. The pass grooms the backlog and re-ranks all of
it below the `# groomed below` marker in `issues/backlog/ORDER`. So every
backlog commit, including the Issues the pair files itself, delays the next
Issue by a whole-backlog pass, and the running order can change under the
developer between two Issues.

Grooming and implementation are different activities. Implementation should
start from the running order as it stands.

## What is wanted

- **`just groom`** runs a grooming pass on its own, and `just pair` no longer
  runs one. The pass keeps the agreement rule, its own branch, the checks the
  supervisor holds it to, and landing as one commit on `main`.
- **Groomed is read from the Issue.** An Issue is groomed when its front
  matter sets a valid `difficulty` and it has no `Needs elaboration` section.
  The pass grooms only the Issues that are not; `.pair/groomed.json` and the
  staleness check go. An Issue the developer writes with a `difficulty` is
  taken as groomed, and deleting an Issue's `difficulty` asks for it to be
  groomed again. `just groom` with nothing to groom says so and exits.
- **Ranking is incremental.** The pass places each Issue it groomed, and each
  child it writes, into the order below the marker, and leaves every line
  already there where it is. `just groom --rerank` judges the whole order below
  the marker again, as the pass does now. Lines above the marker stay the
  developer's in both.
- **The loop takes the order as it stands.** `just pair` takes the first ripe
  Issue in running order. An ungroomed Issue is still groomed by its own
  backlog stage when the loop takes it, as before the pass existed.
- **The words follow:** `pair/README.md`, `issues/README.md`,
  `template/issues/README.md`, `issues/backlog/README.md`, `AGENTS.md` and the
  recipe comments in `.meta/lib/render/writers.py` (with `groom` added to the
  justfile contract in `.meta/checks/files/justfile.py` and to its
  scaffold-only recipes).

## Out of scope

- Running `just groom` on a schedule or automatically.
- Flights (`flights`).

## Done when

- `just pair` never runs a grooming pass, and `just groom` grooms only the
  Issues that are not groomed, and exits when there are none.
- A groomed Issue keeps its place in `ORDER` across a `just groom`, and
  `--rerank` re-ranks the whole order below the marker.
- `.pair/groomed.json` is no longer written or read.
- The pair tests cover each of these, and `just gate` passes.
