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
  running", neither 1 nor 2 nor a code `EXIT` or `LOCKED` already uses: 12
  when every watched loop ended first, 13 when none is running.
- Each code is a named constant with a docstring in `pair/watch.py`, and
  `watch` returns the constants rather than literals. They live there, not
  beside `LOCKED` in `pair/pair.py`, because `pair.py` imports from `watch.py`
  and an import the other way would be circular. The tests import them from
  `watch`; `pair.py` passes `watch`'s return on unchanged and needs no import.
- The docstrings that name the old codes say the new ones: the module
  docstring of `pair/watch.py`, and the `watch` line in the module docstring
  of `pair/pair.py` if it names a code.
- `pair/README.md` lists both codes in the table under "Exit codes", with an
  empty Outcome cell as `11` has, and says `just pair-watch` exits with them
  without claiming it prints a `pair: <outcome>` line, which it does not. The
  paragraph under
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

## The plan

1. `pair/watch.py`: below `CONDITIONS`, add `ENDED_FIRST = 12` and
   `NOT_RUNNING = 13`, each with a one-line docstring in the style of
   `LOCKED`'s. `watch` returns `NOT_RUNNING` where it returns 2 now (line
   131) and `ENDED_FIRST` where it returns 1 (line 143). Its module docstring
   names 12 and 13 in place of 1 and 2, and adds that neither code is 1 or 2.
2. `pair/pair.py`: no change. Its module docstring says only "exits non-zero"
   (line 27), and `main` passes `watch`'s return straight to `sys.exit`, so
   nothing in it uses the constants. Importing them anyway would be an unused
   import that the lint rejects.
3. `pair/test_pair.py`: extend the `from watch import watch` line (line 24) to
   import both constants. The four tests the issue names assert
   `ENDED_FIRST` or `NOT_RUNNING` in place of 1 and 2. In
   `ExitCodeTest.test_each_outcome_has_its_own_code`, add both constants to
   `codes`, so that the existing checks for uniqueness and for staying clear
   of 0, 1 and 2 also cover them. That is the guard against a later `EXIT`
   entry taking 12 or 13.
4. `pair/README.md`: under "Exit codes", add rows 12 and 13 with an empty
   Outcome cell, and a sentence after the table saying `just pair-watch` exits
   with 0, 12 or 13 (see "The event log"); leave the sentence about
   `pair: <outcome>` naming only the four commands. Under "The event log",
   change "exits 1 … and 2 at once" to 12 and 13.
5. Run `just gate pair`, then `just gate`.

Risk: low. The only callers of `watch`'s code are sessions that read it.
Nothing in the repository branches on 1 or 2 from `pair-watch`: `AGENTS.md`
says only that it exits non-zero when the loop ends first, and
the "Using it" table in `pair/README.md` names the recipe without a code.

## Notes

- Done as planned. `ExitCodeTest.test_each_outcome_has_its_own_code` now
  lists `ENDED_FIRST` and `NOT_RUNNING` with `LOCKED`, so a later `EXIT` code
  of 12 or 13 fails there rather than passing unnoticed.
- `watch.py`'s module docstring says why the codes avoid 1 and 2, as the
  `EXIT` docstring in `pair.py` does, because `watch.py` is where a reader of
  `watch` looks.
