---
difficulty: medium
parent: pair-versus-single-seat
---

# Run the pair loop with one seat

One part of `pair-versus-single-seat`. To compare one seat against two, the
loop needs a mode in which only the primary seat takes turns, with nothing
else changed.

Today every stage alternates `ROLES` (`primary`, `secondary`) in
`pair/loop.py`: `decide` hands the next turn to `other(role)`, and a stage
closes through `close_stage` only once `st.approvals` holds both roles.

## Wanted

- A flag on `just pair`, `--single-seat`, passed through to `pair.py run`.
  With it, every turn in every stage, grooming included, is taken by the
  primary seat, with the same prompts, models, stages, gates, round caps and
  desk checks.
- A stage closes when the primary seat leaves it as it stands (a quiet turn)
  and the stage's requirement (`requirement` in `pair/loop.py`) is met, as it
  closes today when both seats have. A turn that changes something never
  closes the stage, even though the primary seat is then the only role in
  `st.approvals`: `decide` must not read a non-quiet `[role]` as every seat
  having approved. An unmet requirement or a failed gate becomes the
  note for the primary seat's next turn, as now.
- The round cap counts the single seat's turns so that it gets as many turns
  as the pair does in total (the cap is `2 * cap` turns today), not half.
- The mode is chosen when the loop starts and kept with the Issue's state, so
  that a resumed or re-executed loop (`reexec`) keeps the mode it began with.
- Each row `turn` appends to `turns.jsonl` and each `started` event carries
  `"mode": "single"` or `"mode": "pair"`. Rows and events written before this
  change have no `mode` and are read as `pair`.
- Without the flag the loop behaves exactly as it does today.

## How anyone will know it is done

Tests in `pair/test_pair.py`, with the fake seats the suite already uses:

- With `--single-seat`, an Issue runs from `backlog/` to `main`, and every
  row in `turns.jsonl` has `"role": "primary"` and `"mode": "single"`.
- A primary turn that changes something does not close the stage, and the
  next turn is the primary seat's again.
- One quiet primary turn closes a stage whose requirement is met; a quiet
  turn on a stage whose requirement is unmet (for example a failed gate)
  does not close it, and the note reaches the primary seat's next turn.
- Without the flag, rows and the `started` event say `"mode": "pair"`, and
  the existing tests pass unchanged.
- A loop stopped mid-Issue in single-seat mode and run again without the
  flag continues in single-seat mode.

## Out of scope

- Any change to the prompts or stage requirements for one seat.
- Making single-seat the default; that is `pair-mode-decision`.
