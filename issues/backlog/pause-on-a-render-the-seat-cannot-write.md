# Pause the loop when a stale page is one the seat cannot write

When an Issue changes the source of a page that `just render` writes under
`.claude/skills/`, the seats' sandbox denies the write
(`render-in-seat-sandbox`), and the gate's `rendered prose` step reports the
stale copy as `x`. The loop treats `x` as the seats' to fix, so it hands the
failure back turn after turn until the round cap sends the Issue to the
backlog. Neither seat can fix it. Found in `trim-decision-records-065-177`,
which went three rounds on it before the change was split out.

## Wanted

A stale rendered page that the seat could not write reaches the developer
the way a `?` step does: the loop pauses and names the file and the
`just render` to run outside the sandbox. A page that is stale for any other
reason stays an `x`.

## Done when

A pair-loop test in which the only gate failure is a stale page under
`.claude/skills/` ends in a pause that names the file, not in another turn.
