---
difficulty: medium
parent: onboard-fitch-mvp
---

# Let a Project live at the repository root

A Project's `name` in `structure.yaml` is the directory that holds it, and
`pair/touched.py` (`home`) gives a changed path to the Project with the
deepest directory that holds it, or to `meta` when none does (stereorepo's
DR-303). An adopted repository's product usually sits at the root, as
fitch-mvp's does (`build.py`, `schema/`, `tests/`). Declared with `name: .`,
that Project holds no path, because no path starts with `./`. So every
change falls to `meta`, and the product's tests never run before a landing.

## How to reproduce it

Declare Projects `meta` (`name: .meta`) and `app` (`name: .`) in a temporary
repository's `structure.yaml`. Ask `touched.select` about a change to
`tests/test_x.py`. It answers `meta`, not `app`.

## Wanted

- A Project named `.` holds every path that no deeper Project holds.
- The paths that stereorepo's bundle places (`.meta/`, `issues/`, `wiki/`,
  `stakeholders/`, `AGENTS.md` and the other entries in `.meta/bundle.yaml`)
  still go to `meta`, so a change to the board alone does not run the
  product's gate.
- `.meta/gate` and `just gate` accept such a Project by its id, as they
  accept any other.

## How anyone will know it is done

Tests over `touched.select` with Projects `meta` and `.`:

- `tests/test_x.py` selects the root Project;
- `issues/backlog/a.md` and `.meta/assertions/structure.yaml` select `meta`
  only;
- a change to both selects both.

## Out of scope

- Moving an adopted product into a directory of its own.
