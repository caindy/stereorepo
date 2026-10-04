# Let a seat build Rust in its sandbox without rediscovering how

The developer's shell sets `RUSTC_WRAPPER=sccache`, and inside a seat's
sandbox sccache is refused ("Operation not permitted"). Every `cargo` build
then fails, and `just gate rust-seed` and `just audit rust-seed rust` stop
before reporting a step. Running the command as
`env -u RUSTC_WRAPPER <command>` works and needs no approval.

Three Issues have found this one seat at a time (`bootstrap-render-step`,
`audit-gate-crash-misreported`, `rust-seed-gate-stdout`), and in the last of
them one seat left the Rust checks to the supervisor before its partner
found the workaround. Nothing durable records it: the seats' prompts in
`pair/` do not mention it.

Wanted: a seat that builds Rust does not hit the refusal, whether because
the loop clears `RUSTC_WRAPPER` for the seats, or because the seat's prompt
says how to run Rust commands.
