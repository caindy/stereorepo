---
difficulty: easy
---

# Stop matching a cross-repository `waits_on` against this board

`.meta/work/purpose.yaml` says a `waits_on` entry naming an Issue in another
repository is written `<repository>:<slug>`. `holds` in `pair/board.py` strips
the repository (`w.split(":")[-1]`) and checks the bare slug against this
board's `done/` stage. So such an entry is satisfied by an unrelated local
Issue with the same slug. Otherwise it is never satisfied, and `just
pair-status`, which prints what `holds` returns, says `waits on b`, which reads
as a wait on a local Issue.

`running_tree` strips the repository in the same way when it orders a Flight's
parts, so `elsewhere:b` puts part `a` after a local sibling `b`.

The gate already treats such an entry as naming another repository
(`ELSEWHERE` in `.meta/checks/files/board.py`) and does not look it up on this
board. Only the loop gets it wrong.

## Wanted

The loop cannot observe another repository's board, because it does not know
where that repository is checked out. So:

- `holds` returns a `waits_on` entry containing `:` unchanged, and never
  treats it as done. The Issue is not ripe while it carries such an entry. The
  developer removes the entry once the other repository's Issue has landed.
- `just pair-status` therefore shows the whole entry (`waits on elsewhere:b`).
  This follows from the change to `holds` and needs no change to `pair/loop.py`.
- `running_tree` ignores entries containing `:` when it orders siblings.
- The docstrings of `holds` and `running_tree` say so.
- A Decision Record states the rule and the rejected alternative: ignoring the
  entry, which would start work before the thing it depends on exists.

## Out of scope

Resolving the entry automatically by reading the other repository. That
belongs with the cockpit (`issues/backlog/cockpit-status-convention.md`),
which will know every repository's board.

## Done when

`pair/test_pair.py` covers these cases in a scratch repository:

- `a.md` in `backlog/` with `waits_on: [elsewhere:b]` and `b.md` in `done/`:
  `next_ripe` does not return `a`, and `holds` returns `["elsewhere:b"]`.
- The same with no `b.md` anywhere: the result is the same.
- A Flight with parts `a` (with `waits_on: [elsewhere:b]`) and `b`:
  `running_order` gives `a` before `b`. Today it gives `b` first.

The Decision Record is written, and `just gate` passes.

## The plan

The change is confined to `pair/board.py`; `pair/loop.py` reads `holds`
and `running_tree` and needs nothing.

1. **Tests first**, in `BoardTest` in `pair/test_pair.py`, beside
   `test_waits_on_holds_an_item_back` and
   `test_a_waits_on_cycle_among_parts_falls_back_to_filename_order`, using
   `Bench.issue(..., waits_on="[elsewhere:b]")` (YAML reads `elsewhere:b` as
   one string):
   - `test_a_waits_on_elsewhere_is_not_met_by_a_local_slug`: `a` waits on
     `elsewhere:b`, `b` in `done/`; `next_ripe` is `None` and
     `board.holds(b.repo, "main", "a", {"b"}, {})` is `["elsewhere:b"]`.
   - `test_a_waits_on_elsewhere_holds_with_no_local_slug`: the same with no
     `b`.
   - `test_a_waits_on_elsewhere_does_not_order_parts`: Flight `big` with parts
     `a` (waits on `elsewhere:b`) and `b`; `running_order` is
     `["a", "b", "big"]`.
   All three fail against today's code.
2. **`holds`**: replace the `w.split(":")[-1]` generator with the entries
   as written, so that `elsewhere:b` is never in `done` (no slug in `done/`
   contains `:`) and is reported whole. Hold an entry containing `:`
   explicitly, not by relying on that, so that a filename with a colon cannot
   satisfy it. Name the separator in a module constant (`ELSEWHERE = ":"`,
   as the gate's `.meta/checks/files/board.py` does) rather than repeating
   the literal. Update the docstring.
3. **`running_tree`**: in `expand`, build `waits[kid]` only from entries
   without `ELSEWHERE`. Add a sentence to the docstring.
4. **Decision Record** `DR-301.yaml` (check that 301 is still the next number
   when writing it), modelled on `DR-300.yaml`. The context is the defect.
   The alternatives are: ignore the entry (rejected: work starts before
   what it depends on exists); match the bare slug (today, rejected: a false
   match); hold until the developer removes the entry (chosen).
   `enacted_in: work:artifact/pair`.
5. **Tell the developer.** The `<repository>:<slug>` form is documented in
   two places that don't say the loop holds such an entry until the developer
   removes it: the `waits_on` description in `.meta/work/purpose.yaml` and
   the front-matter comment in `issues/README.md` (line 26). Add one clause to
   each saying so, citing the new DR. Then run `just render` once, for the DR
   and anything generated that quotes the description, and commit the
   regenerated `.meta/decisions.md` with it.
6. Run `just gate pair` while working, then `just gate`.

**Risk.** It is small. No Issue on the board has a `waits_on` naming another
repository today (checked while planning), so no Issue changes ripeness. The
`pair-status` text for such an entry changes from `waits on b` to
`waits on elsewhere:b`, and no existing test pins the old text.

## Notes

- Done as planned. `pair/board.py` now has `ELSEWHERE`, a twin of the gate's
  constant in `.meta/checks/files/board.py`. The two packages do not import
  each other, so the constant is repeated rather than shared.
- In `issues/README.md` the rule is a sentence after the front-matter
  example, not a clause in its inline comment, because the comment line was
  already at full width.
- The DR is `DR-301`. `just render` regenerated only `.meta/decisions.md`.
- `StatusTest.test_a_wait_on_another_repository_shows_whole` pins the
  `pair-status` line (`waits on elsewhere:b`) that Wanted promises. The three
  `BoardTest` cases reach it only through `holds`.
