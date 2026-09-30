---
difficulty: easy
parent: backlog-grooming-and-ranking
waits_on:
  - backlog-running-order
  - backlog-grooming-pass
---

# Say what roadmap and backlog now mean

The backlog is now ranked and groomed, and a sent-back Issue now stays in
`backlog/`. Most of the words already say this: `issues/README.md`,
`template/issues/README.md`, `issues/backlog/README.md` and `pair/README.md`
describe `ORDER` and send-backs to `backlog/`. What is left is `roadmap/`,
which every description still calls "not yet elaborated enough to work", as
if it were a waiting room for the backlog.

## Wanted

These files say that `roadmap/` holds the developer's coarse, speculative
intentions, which may never be done, and that no agent moves an Issue into
or out of it:

- the `roadmap/` row of the stage table in `issues/README.md` and in
  `template/issues/README.md`;
- `issues/roadmap/README.md`, which also says the developer promotes an
  Issue from it once elaborated, as if that were its purpose;
- the Delivery bullet on adding work in `AGENTS.md` and `template/AGENTS.md`
  ("or `issues/roadmap/`, if it is not yet elaborated");
- the rows naming `roadmap/` in the load maps `.meta/README.md` and
  `template/.meta/README.md` ("what is intended and not yet elaborated");
- the `scope_note` of the Stage concept (`work:concept/stage`) in
  `.meta/assertions/imported/vocabulary.yaml`, which should also say that a
  send-back leaves the Issue in `backlog/`; re-render so
  `.meta/vocabulary.md` follows.

## Out of scope

- `WHY_FORK.md`, which still says a send-back moves an Issue to `roadmap/`;
  it is being written up and deleted by `why-fork-remove-file`.
- `issues/done/`, which records what was true when each Issue landed, and
  the Decision Records under `.meta/assertions/decisions/`, which are never
  rewritten (Journaling) and mean the older `roadmap.md` where they say
  "roadmap".
- Filename order where it is still true: `next_ripe` in `pair/board.py` and
  `board_order` in `.meta/checks/files/board.py` fall back to filename order
  for slugs `ORDER` does not name, and their docstrings say exactly that.

## Done when

No file outside `WHY_FORK.md`, `issues/done/` and the Decision Records
describes `roadmap/` as a
stage the loop sends Issues to or as merely unelaborated backlog, the Stage
concept says both things above, and `just gate` passes.
