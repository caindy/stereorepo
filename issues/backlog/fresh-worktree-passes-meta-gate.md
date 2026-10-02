---
difficulty: medium
parent: onboard-fitch-mvp
---

# A fresh worktree of a portfolio passes `just gate meta` unrendered

In fitch-mvp, the `apm package` and `rendered prose` steps of the `meta` gate
read `.meta/apm.yml`, a render output (`.meta/lib/render/writers.py`) that
`.gitignore` ignores there. A worktree that has never run `just render` fails
both steps ("Not an APM project - no apm.yml found"), whatever the branch
changed. A seat cannot render to fix it: `render.py` writes `.claude/skills/`
first, which the seat's sandbox denies (DR-302), and stops before it writes
`apm.yml`. The seats got past it by copying `apm.yml` from the developer's
checkout, which holds only while the assertions are unchanged.

stereorepo's own worktrees do not hit this. `.gitignore` lists `apm.yml`, but
stereorepo tracks `.meta/apm.yml`, so every worktree has it. A specialized or
adopted portfolio does not track it, so the difference lies in what the bundle
places.

`render-in-seat-sandbox`, in the backlog, covers the related failure of a
seat's `just render`.

## Done when

- A new worktree of an unchanged `main` of a specialized portfolio passes
  `just gate meta` without anyone rendering in it. Any of these would do: the
  portfolio tracks `.meta/apm.yml` as stereorepo does, the gate compiles the
  package first, the loop renders when it creates the worktree, or
  `render.py` writes `apm.yml` before the harness files.
- `CI=1 just test-specialization` checks it on a fresh clone.
