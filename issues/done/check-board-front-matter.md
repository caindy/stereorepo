---
difficulty: medium
---

# Hold the board's front matter to the Issue class

The ontology's `Issue` class (`.meta/work/purpose.yaml`) is the shape of an
Issue file's front matter: `difficulty` from the `Difficulty` enum, and
optionally `waits_on` and `parent`. Nothing reads it yet, so a typo such as
`dificulty: easy` or `difficulty: trivial` passes silently, and the loop treats
the Issue as ungroomed.

## Wanted

A step in the meta gate (`.meta/check.py`, a module registered like those under
`.meta/checks/files/`) that reads every `*.md` file under `issues/` in the
working tree, in every stage directory, and holds its front matter to the
class. `README.md` files are not Issues. The step reads the slots and the
enum's values from `purpose.yaml` rather than repeating them in code. It fails
on each of these mistakes and reports the file and the key:

- a key that the `Issue` class does not declare;
- a `difficulty` value that the `Difficulty` enum does not hold;
- a `waits_on` entry or a `parent` value that names no Issue on the board, in
  any stage. `waits_on` may be a scalar or a list, as `pair/board.py` reads it.
  A value written `<repository>:<slug>` names another repository and is accepted
  without being resolved;
- front matter that does not parse as a YAML mapping.

A file with no front matter passes, because every slot is optional.

## Out of scope

- Changing how `pair/board.py` or the supervisor reads front matter.
- Cycles in `waits_on`, a `parent` that is not `hard`, and a `hard` Issue with
  no children.
- Resolving slugs in other repositories.

## Done when

- A probe under `.meta/checks/probes/` fails the step on each mistake listed
  above and passes it on a well-formed board, including a cross-repository
  `waits_on` entry and a file with no front matter.
- `just gate meta` passes on this board.

## The plan

1. **The step.** Create `.meta/checks/files/board.py`. It defines
   `board_front_matter(views, md_files=None)`, registered with
   `@check("board front matter")`. It is not a precheck, because it needs the
   schemas loaded. `views` is the gate's existing source, whose work schema
   imports `work/purpose`. The step finds that schema by asking which view
   declares the class (`"Issue" in sv.all_classes()`). It then reads the allowed
   keys from `sv.class_slots("Issue")` and the allowed difficulty values from
   `sv.get_enum("Difficulty").permissible_values`. If no view declares `Issue`,
   the step returns `CouldNotRun`. `md_files` is the seam a probe fills, the
   same pattern `wiki_lead_paragraphs` uses; by default it is
   `sources.tree()` filtered to `issues/<stage>/*.md`. `README.md` is skipped
   in either case, so the probe can hold one and see it ignored.
   - It reuses the `FRONTMATTER` pattern from `checks/files/wiki.py`.
   - The board is every slug (file stem) among those files. A `waits_on` entry
     that contains `:` is accepted without being looked up. Any other entry,
     and `parent`, must be a slug on the board.
   - Each problem is one line, `<relative path>: <key>: <what is wrong>`.
     Front matter that raises `yaml.YAMLError`, or that loads as anything but
     a mapping, is reported under the key `front matter`, and its other keys
     are not checked. Entries are compared as `str(...)`, so
     `waits_on: [1]` is looked up as the slug `1` rather than crashing.
   - It returns `Passed("<n> Issues")`, so an empty board, as a fresh clone
     has, passes.
2. **Registration.** Import `checks.files.board` in
   `.meta/checks/files/__init__.py` after `wiki`, and add the step to
   `__all__`. Add an entry to `.meta/checks/files.history.md` in the existing
   shape: the problem, what was established, and the evidence path.
3. **The probe.** Create `.meta/checks/probes/files/board.py` with
   `@check("board front matter probes")`, taking `views`. It writes a small
   board to a temporary directory and calls `board.board_front_matter(views,
   files)`. The board holds one well-formed file of each shape: full front
   matter, `waits_on` as a scalar and as a list, a `<repository>:<slug>` entry,
   and no front matter at all. It also holds one file per mistake: an
   undeclared key (`dificulty`), `difficulty: trivial`, a `waits_on` and a
   `parent` naming a missing slug, front matter that is a YAML list, and
   front matter that is not valid YAML (`difficulty: [easy`). It also holds a
   `README.md` with front matter that would fail, to show it is skipped. The
   probe checks that each bad file is reported once, with its file and its
   key, and that no well-formed file is reported. Register it by re-exporting
   it from `.meta/checks/probes/files/__init__.py` and adding it to that
   module's `__all__`; the re-export is what registers the step.
4. **Verify.** Run `just gate meta`, and fix whatever the current board fails
   on, if anything. Then run `just gate` to confirm nothing else breaks.

**Risks.**
- Relative paths in problem lines: the probe's temporary files live outside
  `ROOT`, so the step must fall back to the path as given, as `_rel` in
  `checks/files/wiki.py` does. Copy that three-line fallback rather than
  importing a private name across modules.
- Line and size baselines: the new modules must stay under their ceilings.
  They should, since each is well under 150 lines.
- Two stages holding the same slug is not reported. It is out of scope, and
  the supervisor never makes that state.

## Implementation notes

- The plan held, with one step it missed: every operational file under
  `.meta/` must be asserted as an Artifact, so both new modules are declared in
  `.meta/assertions/structure.yaml` beside their siblings. Without that,
  `meta/operational artifacts` fails.
- `sources.tree()` lists tracked files the working tree has deleted, so the
  step also requires each Issue file to exist. Otherwise a seat that has just
  moved an Issue file would crash the step.
- A file with an empty front matter block (`---\n---`) passes, the same as a
  file with none; the probe covers both.
- The probe was observed failing: with the `<repository>:<slug>` exemption
  removed from the step, it reports `elsewhere.md is reported, and holds no
  mistake`.
- On this board the step reports `ok meta/board front matter — 10 Issues`, and
  `just gate` passes.
- `issues/README.md`, where the developer learns to write front matter, now
  says the gate holds it to the class and gives the `<repository>:<slug>` form
  of a `waits_on` entry.
