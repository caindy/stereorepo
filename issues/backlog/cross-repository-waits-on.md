---
difficulty: medium
---

# Stop matching a cross-repository `waits_on` against this board

`.meta/work/purpose.yaml` says a `waits_on` entry naming an Issue in another repository
is written `<repository>:<slug>`. `next_ripe` in `pair/board.py` strips the
repository (`w.split(":")[-1] in done`) and checks the bare slug against this
board's `done/` stage. So such an entry is satisfied by an unrelated local
Issue with the same slug, and otherwise it never is: the Issue waits forever,
and nothing says why.

The gate already treats such an entry as naming another repository
(`ELSEWHERE` in `.meta/checks/files/board.py`) and does not look it up on this
board; only the loop gets it wrong.

## How to reproduce

1. In `pair/test_pair.py`'s scratch-repository setup, put `a.md` in
   `issues/backlog/` with `waits_on: [elsewhere:b]`, and `b.md` in
   `issues/done/`.
2. `next_ripe` returns `a`, although `elsewhere:b` is not done.
3. Remove `b.md`: `next_ripe` never returns `a`, and `just pair-status` gives
   no reason.

## Wanted

The loop cannot observe another repository's board: it does not know where
that repository is checked out. So:

- A `waits_on` entry containing `:` is never satisfied by this board. The
  Issue is not ripe while it carries one; the developer removes the entry
  once the other repository's Issue has landed.
- `just pair-status` names each backlog Issue held by such an entry, with the
  entry, so the wait is visible rather than silent.
- A Decision Record states the rule and the alternative rejected (ignoring the
  entry, which would start work before what it depends on exists).

## Out of scope

Resolving the entry automatically by reading the other repository. That
belongs with the cockpit (`cockpit-status-convention`), which will know every
repository's board.

## Done when

`pair/test_pair.py` covers both steps of the reproduction with the new
behaviour, `just pair-status` shows the held Issue and its entry, the Decision
Record is written, and `just gate` passes.
