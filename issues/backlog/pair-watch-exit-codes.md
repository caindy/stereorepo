# `just pair-watch` exit codes clear of a crash and a usage error

`pair-exit-codes` gave `run`, `groom`, `accept` and `resume` codes that avoid
1 (Python's code for an uncaught exception) and 2 (`argparse`'s code for a
usage error). `watch` was out of scope there, and it still exits 1 when the
loops it watches end without meeting its condition, and 2 when no loop is
running (`pair/watch.py`, `pair/README.md` under the event log). A session
waiting on `just pair-watch` cannot tell either from a crash or a mistyped
`--until`.

## What is wanted

- `watch` exits with codes from the same space as `EXIT` and `LOCKED` in
  `pair/pair.py`: one for "the loop ended first" and one for "no loop is
  running", neither 1 nor 2 nor a code `EXIT` already uses.
- `pair/README.md` lists them beside the table under "Exit codes".

## Done when

- The watch tests assert the new codes, and `just gate` passes.
