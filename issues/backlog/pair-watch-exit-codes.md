---
difficulty: easy
---

# `just pair-watch` exit codes clear of a crash and a usage error

`pair-exit-codes` gave `run`, `groom`, `accept` and `resume` codes that avoid
1 (Python's code for an uncaught exception) and 2 (`argparse`'s code for a
usage error). `watch` was out of scope there, and it still exits 1 when the
loops it watches end without meeting its condition, and 2 when no loop is
running (`watch` in `pair/watch.py`, and `pair/README.md` under "The event
log"). A session waiting on `just pair-watch` cannot tell either from a crash
or a mistyped `--until`.

To see it: with no loop running, `just pair-watch --until landed; echo $?`
prints 2, the same code as `just pair-watch --until nonsense; echo $?`.

## What is wanted

- `watch` exits with codes from the same space as `EXIT` and `LOCKED` in
  `pair/pair.py`: one for "the loop ended first" and one for "no loop is
  running", neither 1 nor 2 nor a code `EXIT` or `LOCKED` already uses. The
  next free codes are 12 and 13.
- Each code is a named constant with a docstring in `pair/watch.py`, and
  `watch` returns the constants rather than literals. They live there, not
  beside `LOCKED` in `pair/pair.py`, because `pair.py` imports from `watch.py`
  and an import the other way would be circular. `pair.py` and the tests
  import them from `watch`.
- The docstrings that name the old codes say the new ones: the module
  docstring of `pair/watch.py`, and the `watch` line in the module docstring
  of `pair/pair.py` if it names a code.
- `pair/README.md` lists both codes in the table under "Exit codes", with
  `just pair-watch` named in the sentence above it, and the paragraph under
  "The event log" that says "exits 1 … and 2 at once" names the new codes.

## Out of scope

- The codes of `run`, `groom`, `accept`, `resume` and `status`.
- What `watch` waits for, or the conditions `--until` takes.

## Done when

- The watch tests in `pair/test_pair.py` that expect 1 today
  (`test_a_supervisor_that_ends_first_fails_the_watch`,
  `test_a_killed_supervisor_fails_the_watch`,
  `test_events_from_before_the_watch_are_not_read`) and the one that expects 2
  (`test_no_supervisor_fails_the_watch_at_once`, both of its assertions)
  assert the new codes through their constants.
- No 1 or 2 is returned by `watch`, and `grep` finds no "exits 1" or "2 at
  once" about the watcher in `pair/README.md` or `pair/watch.py`.
- `just gate pair` passes, and then `just gate`.
