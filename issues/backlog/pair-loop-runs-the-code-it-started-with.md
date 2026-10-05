# The pair loop runs the pair code it started with

Found while grooming `seat-shell-rustc-wrapper-returns`. `just pair` imports
`pair/` once and carries Issue after Issue to `main` in the same process.
Nothing re-executes or reloads it after a landing, so a change to `pair/`
that lands, such as `UNSET_FOR_SEATS` in `pair/seats.py` gaining
`RUSTC_WRAPPER` in `3f92bfe9`, has no effect on the running loop. The seats
that follow keep hitting the problem the change fixed until the developer
restarts the loop, and nothing tells the developer that a restart is needed.

Wanted: after landing an Issue that changes `pair/`, the loop either
continues on the landed code (for instance by re-executing itself between
Issues) or stops and tells the developer to restart it.
