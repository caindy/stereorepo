---
difficulty: easy
parent: backlog-grooming-and-ranking
waits_on:
  - backlog-running-order
  - backlog-grooming-pass
---

# Say what roadmap and backlog now mean

Once the backlog is ranked and groomed, the words still describe filename
order and send-backs to `roadmap/`.

## Wanted

`issues/README.md`, `template/issues/README.md`, `issues/roadmap/README.md`,
`issues/backlog/README.md`, `pair/README.md` and the Stage concept in
`.meta/assertions/imported/vocabulary.yaml` (re-rendered) say that:

- `roadmap/` holds the developer's coarse, speculative intentions, which may
  never be done, and no agent moves an Issue into or out of it;
- `backlog/` is committed work, groomed and ranked by the pass, in the order
  `issues/backlog/ORDER` gives, where the developer's placements above the
  marker win;
- a sent-back Issue stays in `backlog/` with a `Needs elaboration` section and
  sits out until it is elaborated.

## Done when

No file above describes filename order as the running order or `roadmap/` as
where the loop sends an Issue, and `just gate` passes.
