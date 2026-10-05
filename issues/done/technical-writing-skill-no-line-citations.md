---
difficulty: developer
waits_on: [no-line-citations]
---
# State the no-line-citations rule in the technical-writing skill

`no-line-citations` refuses a citation of a file by line number and states
the rule in `AGENTS.md` and a Decision Record. The `/technical-writing`
skill should say it too, but its source is the `technical-writing` artifact
in `.meta/assertions/imported/structure.yaml`, and `just render` writes it to
the tracked `.claude/skills/technical-writing/SKILL.md`, which the seats'
sandbox cannot write (`render-in-seat-sandbox`).

## Wanted

The "Every citation dereferenced" invariant in the skill's text in
`structure.yaml` adds that code is cited by its path and the name of the
thing in it (a function, class, constant, test, heading or step), never by
line number, citing DR-355. Then
`just render` runs outside the sandbox and every rendered copy is committed.

## Done when

All the copies of the skill (`.meta/.apm/skills/technical-writing/SKILL.md`,
`.claude/skills/technical-writing/SKILL.md`) state the rule, and
`just render` leaves the tree unchanged.

## Finished by hand (2026-10-05)

The developer's session added the rule to the "Every citation dereferenced"
invariant in the `technical-writing` artifact in
`.meta/assertions/imported/structure.yaml`, ran `just render` outside the
sandbox, and committed both rendered copies. Both state the rule, a second
`just render` leaves the tree unchanged, and `just gate meta` passes.
