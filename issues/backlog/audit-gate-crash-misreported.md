# `just audit` reports a crashed gate as one that reports nothing

`audit` in `.meta/audit.py` does not read the gate's exit code, so a gate
that dies before printing a step (the Rust seed's gate under a seat's
sandbox, where the `sccache` named by `RUSTC_WRAPPER` is refused and the gate
exits 2 silently) comes out as the `<project>-gate-reports-nothing` gap,
asking for steps the gate already has.

Wanted: when the gate printed no step and exited non-zero, `just audit` says
the gate failed to run, with its exit code, and prints no gap Issue. The audit's probe,
`.meta/checks/probes/tools/audit.py`, runs a gate command
that exits non-zero with no output and checks that message.

Found while implementing `bootstrap-render-step`.
