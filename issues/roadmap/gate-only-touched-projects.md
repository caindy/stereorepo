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

This waits for evidence that it is safe: the "defects found after landing"
measure from the pair-versus-single-seat evaluation, with the targeted gate
the seats run (`seats-run-the-targeted-gate`) as the first step.
