# Keep the backlog groomed and ranked between Issues

The backlog is work the developer has committed to doing, and a healthy
backlog is continuously groomed and prioritized. Today it is neither. The loop
grooms an Issue only when it picks it up, and it picks the first ripe Issue in
filename order, so the order is an accident of naming. Nothing looks at the
backlog as a whole, which is the only place priority can be judged.

`roadmap/` is different: coarse-grained, speculative work that may never be
done. It is the developer's alone. No agent moves an Issue into or out of it.

## What is wanted

- **A grooming phase in the loop.** Before the supervisor takes the next Issue,
  if the backlog on `main` has changed since the last grooming pass, the pair
  grooms it first: every Issue in `backlog/` is made precise enough to plan,
  given a `difficulty`, and split if `hard`. A bug report is committed work from
  the moment it is filed, so grooming also writes how to reproduce it. The
  phase uses the same agreement rule as a stage: it ends when both seats have
  accepted the same state. It lands on `main` like an Issue, as one commit.
- **A ranked backlog.** Grooming writes one ordered list of the backlog's slugs
  (for example `issues/backlog/ORDER`), judged across the whole backlog. A rank
  is relative, so it lives in one file, not in each Issue's front matter.
  `next_ripe` in `pair/board.py` takes the first ripe Issue in that order, and
  falls back to filename order for any Issue the list does not name.
- **The developer's order wins.** The developer may reorder the list at any
  time. Everything above a marker line is the developer's placement, and
  grooming keeps it as it is; grooming ranks only what is below the marker.
- **Send-backs stay in the backlog.** A `Needs elaboration` section, or a stage
  that runs past its round cap, currently moves an Issue to `roadmap/`. It
  should stay in `backlog/`, out of the running order until the next grooming
  pass or the developer elaborates it.
- **The words follow.** `issues/README.md`, `template/issues/README.md`, the
  `roadmap/` and `backlog/` READMEs, `pair/README.md` and the Stage concept in
  `.meta/assertions/imported/vocabulary.yaml` describe `roadmap/` as the
  developer's coarse, speculative intentions, which agents do not move, and
  `backlog/` as committed work kept groomed and ranked.

## Out of scope

- Flights, or any other grouping of Issues by the value they deliver.
- A different model for the grooming phase (`seat-models-per-stage.md`).

## Done when

- A backlog change on `main` causes one grooming pass before the next Issue is
  taken, and no pass runs when the backlog is unchanged.
- The loop takes Issues in the ranked order, keeps the developer's placements
  above the marker, and a sent-back Issue stays in `backlog/`.
- A gate step fails when the list names a slug that is not in `backlog/`.
- The pair tests cover each of these, and `just gate` passes.
