# Gate only the Projects a change touches

Before an Issue lands, the loop runs the whole `just gate`: every Project in
the portfolio, the Rust and Python seeds' mutation testing included, whatever
the change touched. That is a catch-all, and it is slow: it is paid on every
landing, and for most changes most of it checks code nothing changed.

`.meta/assertions/structure.yaml` already says which Project each path belongs
to, so the loop could gate only the Projects a change touches, and the
Products built from them. The cost is the catch-all itself: a change that
breaks a Project through something the mapping does not see, such as a shared
tool or a generated file, would land unchecked.

On 2026-10-01 the developer decided not to wait for evidence that this is
safe, such as the "defects found after landing" measure from
`pair-versus-single-seat`: the loop needs to move faster, and the risk is
accepted. The full gate before each landing cost 2 to 2.5 minutes an Issue
that day. Record the decision and the risk it accepts in a Decision Record.
