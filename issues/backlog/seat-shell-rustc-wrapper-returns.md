# A seat's shell still has `RUSTC_WRAPPER=sccache`

Found while implementing `seed-rendered-gate-lost`. `UNSET_FOR_SEATS` in
`pair/seats.py` drops `RUSTC_WRAPPER` from the seat process's environment,
and its docstring says the seat's shell takes the name only from that
environment, since Claude Code's shell snapshot holds no exports. Both seats
on that Issue nonetheless saw `RUSTC_WRAPPER=sccache` in their Bash tool's
environment on 2026-10-03, and the developer's `~/.zshrc` exports it. Every
`cargo` build in the seat then fails on the sandbox's refusal of sccache,
until the seat runs it under `env -u RUSTC_WRAPPER`; the seats on
`bootstrap-render-step` hit the same thing.

Wanted: a seat's Bash tool runs `cargo` without `RUSTC_WRAPPER`, whatever
the developer's shell profile exports, and the docstring of
`UNSET_FOR_SEATS` says truly why. Find out how the export reaches the shell
(the profile sourced per command, or the snapshot) before choosing a fix;
setting `RUSTC_WRAPPER=` empty in the seat's environment, which `cargo`
reads as no wrapper, may survive where unsetting does not.

Done when a seat started by `just pair` can run `cargo build` in
`bootstraps/rust/seed` with no `env -u`, shown by a test of the seat's
environment that `pair/test_pair.py` runs.
