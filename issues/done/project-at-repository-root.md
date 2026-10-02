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

In `pair/touched.py`, when a Project's `name` is `.` (or `./`):

- A path that no deeper Project holds goes to that root Project, not to `meta`.
  A deeper Project (`name: pair`, say) still takes the paths under it.
- These paths still go to `meta`, whichever Project is at the root, so a
  change to the board alone does not run the product's gate:
  - every path under `issues/`, the board;
  - every path the tree's `.meta/bundle.yaml` places: under an item of
    `kind: dir`, or equal to an item of any other kind (`AGENTS.md`,
    `README.md`, `CLAUDE.md`, `.gitignore`, `wiki/stereorepo/…`,
    `stakeholders/…`, and so on);
  - every path under `.meta/`, even when the tree has no `.meta/bundle.yaml`.
- With no root Project, `home` behaves as it does now.

`.meta/gate` already selects a Project by its short id (`app`), so no change
is wanted there; a test confirms it.

## How anyone will know it is done

Tests in `pair/test_pair.py` over `touched.select`, in a temporary tree with
Projects `meta` (`name: .meta`) and `app` (`name: .`) and a `.meta/bundle.yaml`
listing `README.md` and `wiki/stereorepo/`:

- `tests/test_x.py` and `build.py` select `app` only;
- `issues/backlog/a.md`, `.meta/assertions/structure.yaml`, `README.md` and
  `wiki/stereorepo/x.md` select `meta` only;
- `tests/test_x.py` with `issues/backlog/a.md` selects both, which is every
  Project, so `select` returns `None`;
- with a third Project `lib` (`name: lib`), `lib/x.py` selects `lib` only.

In `.meta/checks/probes/tools/gate.py`, the gate runner probe adds a case
showing that `select_all(["app"], …)` chooses the Project with `id`
`work:project/app` and `name: .`. The existing `touched` tests and
`SELECTIONS` cases still pass unchanged.

## The plan

Three files change: `pair/touched.py`, its tests in `pair/test_pair.py`, and
the gate runner probe in `.meta/checks/probes/tools/gate.py`. `.meta/gate`
itself does not.

1. **`pair/touched.py`.**
   - In `select`, normalise each Project's directory as now
     (`rstrip("/")`), then treat `.` (from `.` or `./`) as the root
     Project. With one present, build the meta-held set once:
     `issues/` and `.meta/` as prefixes, plus every `path` in the tree's
     `.meta/bundle.yaml` `items`. An item of `kind: dir` is a prefix
     (its path already ends in `/`), and any other item is an exact path.
     A missing or empty `bundle.yaml` leaves only the two fixed prefixes.
     Read it with `yaml.safe_load`, the way `structure.yaml` is read.
   - Give `home` a keyword parameter for that set, defaulting to empty.
     Order inside `home`: the deepest non-root Project that holds the path
     wins; failing that, a meta-held path goes to `META`; failing that,
     the root Project if there is one; else `META`. The root's `.` is kept
     out of the `startswith` match, so it never counts as a holder.
   - Add a line to the module docstring for the root Project and the paths
     that stay with `meta`.
   - With no root Project the set is never built and `home` runs as now, so
     stereorepo's own selection and `pair/loop.py`'s single call site
     (`touched.select(self.wt, changed)`) are unchanged.
2. **`pair/test_pair.py`, `GateSelectionTest`.** A new test that writes, in
   the `Bench` repo, a `structure.yaml` built with `project("meta", ".meta")`,
   `project("app", ".")` and `project("lib", "lib")`, plus a
   `.meta/bundle.yaml` with a `README.md` file item and a `wiki/stereorepo/`
   dir item, committed together, then checks the issue's cases as subtests.
   The every-Project case returns `None`, so it uses a structure without
   `lib` (or puts a `lib` path in too). Also check `app` with `./` as its
   name selects the same way.
3. **`.meta/checks/probes/tools/gate.py`.** Add `app` to the probe's
   `projects` with `"name": "."` and a `SELECTIONS` entry `(("app",),
   ("app",))`. The every-Project entry `()` then expects `app` too, so it
   gains `"app"` in declared order.

**Risks.**
- An adopted product's own `README.md` (and anything else stereorepo's
  bundle places) goes to `meta`, so a change to it alone does not run the
  product's tests. The issue accepts this; the docstring says so.
- `bundle.yaml` is read from the worktree at the branch's head, so a branch
  that edits it routes by its own edit. That matches how `structure.yaml`
  is read now.

## Notes from implementing

- Done as planned in `pair/touched.py` (`ROOT`, `HELD`, `BUNDLE`, `placed`,
  and a `held=` keyword on `home`). The tests are in `GateSelectionTest`:
  each case runs with the root named both `.` and `./`, `wiki/app/x.md`
  (outside the bundle's `wiki/stereorepo/`) goes to the root, and a tree
  with no `bundle.yaml` still keeps `issues/` and `.meta/` with `meta` while
  `README.md` goes to the root.
- Docs that ride along: a consequence added to DR-303 and a clause in
  `pair/README.md`. `.meta/decisions.md` lists only titles, so it does not
  change. `just render` could not finish inside this seat's sandbox, which
  denies writes to `.claude/skills/`. Nothing it renders should depend on
  this change. The second seat hit the same denial.
- `placed` reads an item's `kind`, not its spelling: a `kind: dir` item is a
  prefix whether or not the bundle writes its trailing `/`. The test bundle
  carries `stakeholders` without one, so `stakeholders/p.md` goes to `meta`
  while `stakeholders.md` goes to the root.

## Out of scope

- Moving an adopted product into a directory of its own.
- Changing what the root Project's `gate` command runs, or adding one to
  fitch-mvp's `structure.yaml`.
- Mapping a break through a shared tool or generated file, which DR-303
  already accepts as a risk.
