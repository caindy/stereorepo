# Cite code by path and name, never by line number

A citation such as `pair/seats.py:143` breaks whenever the file above that
line changes. The `path and line claims` step in
`.meta/checks/citations/claims.py` checks each one against the line it names,
so every edit that moves lines can fail the gate on a file nobody touched. On
2026-10-03 adding three entries to `DISALLOWED` in `pair/seats.py` failed the
`meta` gate on a pair note in `issues/done/pair-loop-spike-evidence.md`, which
cited `CONTEXT` by its old line. Earlier, on `release-recipe-is-scaffold-only`,
seats spent two turns rewording each other's notes for the same reason.

The developer decided on 2026-10-03 to stop citing line numbers entirely. A
citation names the file and the thing in it: a function, class, constant,
test, heading or step, such as `CONTEXT` in `pair/seats.py`.

## Wanted

- The `path and line claims` step no longer resolves line numbers. It
  refuses any `path:line` citation in the prose it reads, durable prose and
  Issue files alike, and says to name the thing instead. Rename the step to
  match.
- Every existing `path:line` citation is rewritten to the path and the name
  of what it pointed at. On 2026-10-03, `git grep` found them only under
  `issues/`, in 11 files.
- The rule is stated where writers look: the citation conventions in
  `AGENTS.md`, and the `/technical-writing` skill.
- A Decision Record records the decision and why.

## Out of scope

- Tool output that prints `path:line`, such as a linter's findings or a
  probe's expected output, which is not a citation in prose.
- Pair notes: they keep whatever handling `pair-notes-escape-the-seats-gate`
  gave them, so a seat's closing message cannot fail the next seat's gate.

## Done when

- `git grep` finds no `path:line` citation in prose outside tool output.
- A probe shows the renamed step failing on a new `path:line` citation and
  passing on a citation by path and name.
- `just gate meta` passes.
