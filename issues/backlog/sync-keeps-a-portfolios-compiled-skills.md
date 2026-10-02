---
difficulty: medium
parent: onboard-fitch-mvp
---

# A sync keeps the compiled skills of a portfolio's own

`.meta/.apm/` is a managed item in `.meta/bundle.yaml`, so `just sync
<checkout>` (`.meta/bundle.py sync`, `.meta/lib/bundle/sync.py`) removes from
it every path the checkout does not track. That includes what render
compiled there from the portfolio's own `.claude/skills/`
(`lib/apm_compile/skills.py`). In fitch-mvp both syncs reported:

```
removed .meta/.apm/skills/generate-decision-graph/SKILL.md
removed .meta/.apm/skills/generate-schema-code/SKILL.md
```

and `just render` put them back. Nothing is lost, but between the sync and
the render the working tree shows two deleted skills, and a sync committed
before rendering commits their deletion.

## Wanted

A sync leaves the compiled output of the portfolio's own skills under
`.meta/.apm/` alone, so a sync followed by nothing shows only stereorepo's
changes. A skill stereorepo stops shipping is still removed.

## Out of scope

- Changing where render compiles skills to, unless that is the fix chosen.
- Fixing fitch-mvp itself.
