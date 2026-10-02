# Let a seat's `just render` finish in the sandbox

A seat's `just render` stops at its first write to
`.claude/skills/<skill>/SKILL.md`, which the seat's sandbox denies (DR-302).
Pages are written in the order `.meta/lib/render/targets.py` lists them, so
every page after the skills goes unwritten. This was reported in
`portfolio-steps-without-subject`, `specialized-portfolio-gate`,
`gate-only-touched-projects`, `why-fork-delivery-records` and
`why-fork-inherited-terms`. Each worked
around it.

## Wanted

A seat can render every page its change affects. One way is for render to
skip writing a file whose content is already what it would write, so an
unchanged skill is never touched. A skill that has changed still needs a
way through, or a clear message naming the skill for the developer to
render.

## Done when

- In a seat's sandbox, `just render` after a change to a Decision Record
  writes every page and exits 0 when no skill changed.
- When a skill did change, it names that skill and every page it could not
  write, rather than stopping at a traceback.
