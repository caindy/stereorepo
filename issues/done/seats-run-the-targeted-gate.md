---
difficulty: easy
---

# Seats run the targeted gate; the loop runs the full one

`pair/prompts/stage-in-progress.md` tells a seat to keep `just gate` green and
to run it before it finishes its turn. So every implementing turn runs the
whole gate, every Project in the portfolio: the Rust seed's build and mutation
testing and the Python seed's mutation testing included, however little of
them the change touches, and often more than once in a turn. On
`pair-notes`, a change confined to `pair/`, each seat's implementation turn
ran the full gate at least twice, and the turns took 12 and over 19 minutes.
The loop then runs the full gate again before it lands the Issue (`gate` in
`pair/pair.py`, called from `pair/loop.py`), which is the check that decides.
`AGENTS.md` already says to prefer a targeted gate while working.

## What is wanted

- **The stage prompts ask for the targeted gate.** `stage-in-progress.md` is
  the only stage prompt that names the gate today. It asks a seat to run the
  gate of each Project its change touches, by name, and to leave the whole
  `just gate` to the loop, which runs it before the Issue lands and hands back
  any failure with its output, as now. The Projects are those
  `just --list` shows under `gate`: `meta` (`.meta/`, and the repository-wide
  checks on `wiki/`, `issues/` and the instructions), `rust-seed`
  (`bootstraps/rust/seed/`), `python-seed` (`bootstraps/python/seed/`) and
  `pair` (`pair/`). The prompt says which directory belongs to which Project,
  or points at where that is written (each Project's `name` in
  `.meta/assertions/structure.yaml` is its directory), so a seat need not
  guess. Every turn edits the Issue file under `issues/`, which `meta` checks,
  so the prompt asks for `just gate meta` on every turn, plus the gate of each
  other Project whose directory the change touches.
- **The loop's gate is unchanged:** the full `just gate` before landing, and
  on a rebase after `main` moved.
- **The words follow:** `pair/README.md` says which gate a seat runs and which
  the loop runs. The targeted-gate sentence in `AGENTS.md` lists `pair` among
  its examples, and its "run it after authoring changes" does not contradict
  the prompt.

## Out of scope

- Narrowing the loop's own gate to the Projects a change touches (on the
  roadmap: `gate-only-touched-projects`).
- Changing how `.meta/assertions/structure.yaml` declares a Project's
  directory; the prompt may point at the `name` fields or state the mapping in
  words.

## Done when

- No stage prompt asks a seat to run the whole `just gate`, and
  `stage-in-progress.md` names the targeted gate and how to pick it:
  `just gate meta` always, and `just gate <project>` for each other Project
  the change touches. A seat that edits only `pair/` and its Issue file is
  told to run `just gate meta` and `just gate pair`, and nothing more.
- `test_gate_failure_goes_back_to_the_pair_with_its_output` in
  `pair/test_pair.py` still passes unchanged: a full-gate failure at landing
  still reaches the seats with its output.
- `just gate pair` and `just gate meta` pass, and then `just gate`.

## The plan

The change is to wording only. The loop's code does not change.

1. **`pair/prompts/stage-in-progress.md`.** Replace "Keep `just gate` green,
   and run it before you finish your turn; it is the gate the issue must pass
   to land." with a sentence that:
   - asks for `just gate meta` on every turn, because the Issue file is under
     `issues/`;
   - asks for `just gate <project>` for each other Project whose directory
     the change touches: `rust-seed` for `bootstraps/rust/seed/`,
     `python-seed` for `bootstraps/python/seed/`, `pair` for `pair/` (the
     `name` of each Project in `.meta/assertions/structure.yaml`);
   - tells the seat not to run the whole `just gate`, because the loop runs
     it before the Issue lands and hands back any failure with its output.

   The template goes through `str.format` (`Loop.message` in `pair/loop.py`), so the new
   text must have no `{` or `}` other than `{path}`. Write `<project>`, not
   `{project}`.
2. **`pair/README.md`.** In "How an Issue moves", after the paragraph on what
   a seat is told, add one sentence: a seat runs the targeted gate of the
   Projects its change touches (`prompts/stage-in-progress.md`), and the
   loop's full `just gate` at `in-progress/` (see the table) is what decides
   whether the Issue lands.
3. **`AGENTS.md`** (the file that `CLAUDE.md` links to). Add `just gate pair`
   to the targeted-gate examples. Reword "run it after authoring changes" so
   that it reads as the exit condition of a piece of work, not something every
   turn runs. For example: "`just gate` is an exit condition, not an entrance
   condition: it runs once the work is done (in the pair loop, before
   landing), not at session start." The sentence that says to prefer a
   targeted gate while working stays. The `template conventions agree` check
   in `.meta/checks/files/templates.py` requires the exact phrase "exit
   condition, not an entrance condition" in both `AGENTS.md` and
   `template/AGENTS.md`, so keep it word for word. Make the same rewording in
   `template/AGENTS.md` (lines 62–64), so that the two files still agree.
   Leave the template's generic example ("or a declared Project's") as it is,
   because a fresh portfolio has no `pair` Project.
4. Run `just gate pair`, then `just gate meta`, then `just gate`.

**Tests.** No test reads the text of the prompt, and none needs to. One test
did read it by accident: `test_the_run_lands_the_flight_and_stops_at_its_desk_check`
asserted that no message held the substring `other`, the slug of an Issue
outside the Flight, and the new prompt says "each other Project". That Issue's
slug in `FlightRunTest` is now `unflown`, a word no prompt uses. The test still
asserts on the bare slug, so it would still catch a message that names the
Issue by slug without its path. The evidence is:
- `test_gate_failure_goes_back_to_the_pair_with_its_output` in
  `pair/test_pair.py` still passes unchanged, which shows the loop's gate
  still decides landing;
- `just gate pair` passes, which shows the rendered template still formats;
- `just gate meta` passes, which covers the instructions and the wiki checks.

The Done-when example is checked by reading the new prompt: a seat that edits
only `pair/` and the Issue file is told `just gate meta` and `just gate pair`.

**Risks.**
- A stray brace in the prompt raises `KeyError` or `ValueError` at the first
  in-progress turn, not at authoring time. Check by eye, and by rendering the
  template with `str.format(path=...)` once.
- `meta` checks the wording of `AGENTS.md` against `template/AGENTS.md`
  (`template conventions agree`, above). If that phrase is reworded away,
  `just gate meta` fails.
