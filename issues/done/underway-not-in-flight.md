---
difficulty: easy
parent: flights
---

# Call the Issue being worked *underway*, not *in flight*

One part of `flights`. "In flight" today means the one Issue the loop is
working. `flights` gives the phrase to a Flight's parts, so the Issue being
worked becomes *underway*.

## Wanted

Replace "in flight" meaning the Issue being worked with "underway" (or "being
worked" where that reads better) in:

- `pair/loop.py`: the `status` docstring and its `in flight:` and
  `nothing in flight` lines, and the grooming-pass uses in the `pair` and
  `groom` docstrings and refusal messages ("a grooming pass is in flight",
  "{slug} is in flight", "resuming the grooming pass in flight"). A grooming
  pass is worked the same way an Issue is, so it is *underway* too;
- `pair/pair.py` (the `status` help);
- `pair/README.md` (four uses: "the turn in flight", "while an Issue is in
  flight", "steer an Issue in flight" and "the Issue or grooming pass in
  flight"), `issues/README.md`, `template/issues/README.md`, and `AGENTS.md`
  (then re-render so `CLAUDE.md` and its siblings follow). The phrase may be
  wrapped across lines, as it once was in `AGENTS.md`;
- the `pair-status` recipe comment in `.meta/lib/render/writers.py`, then
  re-render the `justfile`;
- `.meta/checks/files/board.py` and `.meta/checks/probes/files/board.py`;
- `.gitignore`;
- `issues/backlog/cockpit-status-convention.md`.

Update any test in `pair/test_pair.py` that matches the old status text.

## Out of scope

`WHY_FORK.md`, `apm_modules/` (derived), and Issues in `issues/done/`, which
are history. Defining Flight (`flight-vocabulary`).

## Done when

Run at the repository root,
`rg --hidden -U -i -l 'in\s+flight' -g '!.git' -g '!WHY_FORK.md' -g '!issues/done/**' -g '!apm_modules/**' -g '!issues/backlog/flight*.md' -g '!issues/*/underway-not-in-flight.md'`
finds nothing. The search spans line breaks, which `git grep "in flight"` would
not. `just pair-status` says "underway", and `just gate`
passes.

## The plan

A wording change with one seam that tests observe: the `status` text in
`pair/loop.py`, which `pair/test_pair.py` asserts on.

1. **`pair/loop.py`.** `status` prints `underway: …` in place of
   `in flight: …`, and `nothing underway` in place of `nothing in flight`.
   Its docstring becomes "the board on `main` and the issue underway".
   The `run` and `groom` docstrings, and the three refusal messages in them,
   use "underway" in the same way ("a grooming pass is underway", "{slug} is
   underway", "resuming the grooming pass underway" reads badly, so use
   "resuming the grooming pass already underway").
2. **`pair/test_pair.py`.** In
   `test_a_pass_and_an_issue_never_share_the_worktree`, the two
   `assertIn(... status(b.repo))` lines follow the new text. No test asserts
   on the refusal messages.
3. **`pair/pair.py`.** The `status` subcommand help.
4. **`.meta/lib/render/writers.py`.** The `pair-status` recipe comment, then
   `just render` so the `justfile` follows.
5. **Prose.** `pair/README.md` (four uses), `issues/README.md` and
   `template/issues/README.md` (two each, kept in step), `AGENTS.md` (one;
   it is not generated, and `CLAUDE.md`, `GEMINI.md` and
   `.github/copilot-instructions.md` are symlinks to it, so no render is
   needed), `.gitignore` (the comment on `.pair/`), the docstrings in
   `.meta/checks/files/board.py` and `.meta/checks/probes/files/board.py`,
   and `issues/backlog/cockpit-status-convention.md` (two).

Where "underway" reads poorly, as in "restarts the turn in flight", write
"the turn being worked" instead. Keep the meaning: the one Issue or pass the
loop holds.

**Check.** Run the `rg` search under *Done when* until it finds nothing,
then `just pair-status` (expect `nothing underway` on a quiet board), then
`just gate pair` and `just gate meta` while working and `just gate` last.

**Risk.** Low. Nothing parses the `status` text except the one test; the
message strings are read only by the developer. Rewording could leave a line
too long for the formatter, which `just gate pair` catches.

## Notes

- Done as planned, with one addition: the probe in
  `.meta/checks/probes/files/board.py` named its in-progress fixture Issue
  `flight`. Once Flight is a term (`flight-vocabulary`), that slug would read
  as one, so it is now `underway`.
- The `status` line is `underway: <slug> in <stage>/, turn …`. For this very
  Issue it reads `underway: underway-not-in-flight in in-progress/`, which
  is correct, if awkward.
- The *Done when* search excludes this Issue's file in whatever stage it
  sits (`issues/*/underway-not-in-flight.md`), since the file names the old
  phrase by design. `just gate` passes, with 43 pair tests.
