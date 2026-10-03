---
difficulty: easy
---

# Let a seat's `just render` finish in the sandbox

A seat's `just render` stops at its first write to
`.claude/skills/<skill>/SKILL.md`, which the seat's sandbox denies (DR-302).
`.meta/lib/render/cli.py` writes every target unconditionally, in the order
`.meta/lib/render/targets.py` lists them, so the first denied write raises a
`PermissionError` and every page after the skills goes unwritten. This was
reported in `portfolio-steps-without-subject`, `specialized-portfolio-gate`,
`gate-only-touched-projects`, `why-fork-delivery-records` and
`why-fork-inherited-terms`. Each worked around it.

## How to reproduce

In a seat's sandbox, change any Decision Record and run `just render`. It
stops with a traceback at `.claude/skills/wikisplain/SKILL.md`, and the
pages listed after the skills in `targets.py` are left stale. Outside a
sandbox, making one skill file read-only (`chmod a-w`) shows the same.

## Wanted

- Render writes a file only when its content differs from what it would
  write, so an unchanged skill is never touched.
- A write that fails does not stop the render: it carries on with the rest,
  then names every file it could not write, says the developer must render
  them outside the sandbox, and exits non-zero.
- `apm_compile.reconcile_root`, which render runs after writing, behaves the
  same way: it leaves a symlink alone when it is already right.

## Out of scope

- Widening the seat's sandbox to allow writes under `.claude/`.
- `.meta/render.py --check`, which already reads without writing.

## Done when

- A test renders into a scratch tree where every target is already current
  and one is read-only: it exits 0 and leaves every file's modification time
  unchanged.
- A test where a read-only target's content must change: every other target
  is written, the output names the read-only one, and the exit status is
  non-zero, with no traceback.
