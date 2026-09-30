---
difficulty: medium
parent: flights
waits_on:
  - flight-check
---

# Desk-check a Flight on `main`, without holding the loop

One part of `flights`. An Issue's desk check today holds the worktree: the
loop pauses with `retry: desk-check` in `.pair/state.json` until
`just pair-accept` merges it or `just pair-resume` sends it back. A Flight's
parts are already on `main`, so its desk check gates nothing but the Flight
being called delivered, and should not stop the loop.

## Wanted

- A Flight that passes its check lands on `main` in `desk-check/`, not
  `done/`, with its brief, and its slug leaves `ORDER` as it would for `done/`.
  The loop does not pause; it goes on to the next ripe Issue.
- `just pair-accept <slug>` moves a Flight in `desk-check/` to `done/` in one
  commit on `main`, made in the developer's checkout, not the pair worktree, so
  it works while another Issue is underway.
- The developer writes notes in the Flight file in their checkout, as a
  `## Desk-check notes` section after the latest brief, one top-level bullet
  per note. `just pair-resume <slug>` commits that edit on `main` together
  with moving the Flight to `backlog/` and putting its slug at the top of
  `ORDER`. It refuses, changing nothing, if the Flight file has no notes
  section newer than its latest brief.
- The Flight is then ripe, since every child is done, so the loop takes it
  through its Flight check again. A check whose Flight file ends in a
  `## Desk-check notes` section (no later brief or children section) owes
  children: it writes each note as a new child with `parent:` naming the
  Flight, appends a `## Desk-check children` section with one bullet per new
  child slug, and must not write a brief. The supervisor holds it to this by
  accepting, in that case, only new children plus exactly one new
  `## Desk-check children` section, and the stage prompt says so. The
  children section is what marks the notes answered: without it, the check
  after those children land would still see unanswered notes and owe children
  forever. Once the children land, the next Flight check follows today's rule
  (gaps or a new brief), and a brief returns the Flight to `desk-check/`.
- The Flight file keeps each round's brief and notes; a new round appends, it
  does not overwrite.
- Without a slug, `pair-accept` and `pair-resume` keep today's meaning (the
  Issue desk check holding the worktree). With a slug that names neither, they
  say so and change nothing. The recipes take the slug as an atomic
  identifier (DR-259, DR-272).

## Out of scope

`just deliver` (`flight-deliver`), `just pair --flight`, and showing Flights in
`pair-status` (`status-lists-what-waits-on-the-developer`).

## Done when

The pair tests show: a checked Flight lands in `desk-check/` and the loop
carries on; `pair-accept <slug>` moves it to `done/`; `pair-resume <slug>` with
two notes returns the Flight to `backlog/` and the top of `ORDER`; its next
check is refused if it writes a brief or no children section, and accepted with
two children and a `## Desk-check children` section; after those children land
the next check is not asked for children again, writes a brief, and the Flight
returns to `desk-check/` with both rounds' briefs, notes and children sections
in its file. Both recipes
work while another Issue holds the worktree, and refuse an unknown slug or a
resume without new notes. `pair/README.md` describes the Flight desk check,
and `just gate` passes.

## The plan

All in `pair/`: `loop.py`, `board.py`, `pair.py`, `prompts/stage-flight-check.md`,
`test_pair.py`, `README.md`. `justfile` needs no change, since `pair-accept` and
`pair-resume` already pass `*args` through.

1. **`board.last_of(body, names)`**: which of the named headings comes
   last in `body` (`None` if none), matched as `sections` matches. With
   `NOTES = "Desk-check notes"` and `CHILDREN = "Desk-check children"` beside
   `BRIEF` in `loop.py`, a Flight *owes children* when
   `last_of(body, (BRIEF, NOTES, CHILDREN)) == NOTES`.
2. **Land a passed Flight in `desk-check/`.** Replace the `retires` bool with
   `retirement(st) -> str | None`, the stage landing moves the Issue to:
   `"desk-check"` when `st.stage == FLIGHT_CHECK` and no child waits;
   `None` when `st.stage == "desk-check"` and the Issue has children (a Flight
   already moved there by an earlier pass of the same merge); otherwise `"done"`
   under today's rule. `merge` calls `self.move(st, to)` when it is not `None`.
   The second case matters. `move` sets `st.stage = "desk-check"`, and `merge`
   goes round again when `main` moves (`continue`) or is rerun after
   `retry: merge`. A rule keyed only on `FLIGHT_CHECK` would then move the
   Flight on to `done/`. Excluding `desk-check` outright would break `accept()`
   for a `developer` Issue, which merges from that stage and must reach `done/`.
   A Flight always has children and a `developer` Issue that reaches the desk
   check has none, so the children test tells them apart. In `squash`, drop the
   slug from `ORDER` when `locations` is `["done"]` or `["desk-check"]`.
   `advance` and `run` already carry on to the next ripe Issue after a landing,
   so nothing pauses.
   - A Flight in `desk-check/` is not in `done/`, so `next_ripe` still holds
     back anything that `waits_on` it and its own parent Flight (for example
     `flights`, if a part were itself a Flight) until the developer accepts it.
     That is intended: the Flight is not delivered until accepted. Leave
     `next_ripe` unchanged.
3. **The owed-children rule in `flight_checked`.** Read owed-ness from the
   Flight file at `st.base` (`was`), not HEAD. When it owes children, accept only
   when there is at least one new gap, briefs have not grown, the file has
   exactly one more `CHILDREN` section than `was`, and the bullets of its last
   `CHILDREN` section are exactly the new gap slugs. Otherwise the reason
   names that shape. When it owes nothing, today's rule stands. The merge then
   leaves the Flight in `backlog/`, since `waiting` is true.
4. **The prompt** `stage-flight-check.md` gains the notes branch: if the file
   ends in `## Desk-check notes`, write one child per top-level bullet, append
   `## Desk-check children` listing their slugs, and write no brief.
5. **`accept(slug)` and `resume(slug)`** in `Loop`. With no slug they behave as
   today. With a slug, they call new `accept_flight` / `resume_flight`. These work only in
   `self.repo` (the developer's checkout) and never read `.pair/state.json`
   or the worktree:
   - Refuse (say why, return `"none"`, change nothing) unless the checkout is on
     `main` and `issues/desk-check/<slug>.md` exists at `main`.
   - `accept_flight`: `git mv` to `done/`, commit with a pathspec
     (`git commit -- <old> <new>`) so the developer's other staged work stays
     out, and return `"accepted"`.
   - `resume_flight`: read the Flight file from the working copy and refuse
     unless it owes children (step 1). Refuse also if `ORDER` has uncommitted
     edits. Then `git mv` it to `backlog/`, `git add` the new path so the
     developer's notes are staged, put the slug as the first line of `ORDER`,
     and commit the three paths. Return `"resumed"`.
   - `pair.py`: an optional positional `slug` on the `accept` and `resume`
     parsers. The slug form skips `hold_lock`, so it runs while `just pair`
     runs.
6. **Tests** in `FlightCheckTest`: rename `test_a_brief_retires_the_flight` to
   land in `desk-check/` (and out of `ORDER`) and `run()` continues to a
   following ripe Issue. Add `pair-accept <slug>` moving the Flight to `done/`;
   `resume` with two notes returning the Flight to `backlog/` at the top of `ORDER`,
   then the next check refused for writing a brief and refused for children
   without a `CHILDREN` section, accepted for two children plus the section;
   the two children landing (scripted easy turns), and the next check owing
   nothing, writing a brief, back in `desk-check/` with two briefs, one notes
   and one children section. Add a Flight check whose landing pauses with
   `retry: merge` because the developer's checkout is on another branch. `land`
   refuses after `move` and `squash` have run, so the saved state already says
   `desk-check`. Switch back to `main` and run again, and show that the Flight
   ends in `desk-check/`, not `done/`. Keep the existing `developer` Issue
   `accept()` test passing, since it merges from stage `desk-check` to `done/`. Add the slug commands working while a state file
   holds another Issue (even at `retry: desk-check`) and leaving it untouched,
   refusing an unknown slug, and refusing a resume with no new notes. Add
   `BoardTest` for `last_of`. The existing no-slug desk-check tests stay as
   they are.
7. **`pair/README.md`**: the Flight-check row lands in `desk-check/`; a row or
   paragraph for the Flight desk check (notes format, the children section, and
   the slug recipes). Also the desk-check line of the developer table.

**Risks.**
- Skipping the lock lets the developer commit on `main` while the loop lands.
  If that commit falls between `squash` and `land`, the fast-forward fails and
  the loop pauses (`retry: merge`); a rerun lands. That is acceptable, and
  better than refusing the desk check while the loop runs.
- A developer who edits the Flight file on `main` while its Flight check is
  underway can make the rebase conflict. That already pauses cleanly.
- The destination rule in step 2 is the part most likely to go wrong: a
  second pass through `merge` must not move a Flight past `desk-check/`. The
  paused-landing test in step 6 covers it.
- The Flight's check can list slugs in its children section that differ from
  the files it wrote. Step 3's exact-match check catches that.

## What the next reader should know

- **Where the plan was wrong.** The `justfile` is rendered from
  `.meta/lib/render/writers.py`, so the recipe doc comments for `pair-accept`
  and `pair-resume` changed there and were re-rendered. The recipe contract in
  `.meta/checks/files/justfile.py` needed no change: its `FLAGS` kind already
  admits an atomic identifier such as a slug. `board` gained two helpers the
  plan did not name. `last_section` reads the latest round's
  `## Desk-check children`, and `bullets` reads its slugs, stripping backticks.
- **`pair.py` builds the loop before taking the run lock.** With a slug,
  `accept` and `resume` answer and return before `hold_lock`, so they run
  beside `just pair`. Without a slug they take the lock as before.
- **`retirement` replaces `retires`.** It returns the stage landing moves to,
  or `None`. `test_a_flight_paused_while_landing_still_lands_at_its_desk_check`
  covers the second pass through `merge`.
- **What the supervisor does not check.** The check owes a child per note, but
  the supervisor checks only that the new children section lists exactly the
  new children. It does not count those children against the note bullets,
  because one note may reasonably need two children, or two notes one.
- **Commits in the developer's checkout.** `commit_move` commits with a
  pathspec, so other work the developer has staged stays out. The commits
  carry `Seat: developer`, since the developer ran them.
- **A resume needs at least one note.** `resume_flight` refuses a
  `## Desk-check notes` section with no top-level bullet. Without that, the
  next Flight check would owe children for no notes, and the supervisor would
  keep asking for a child that nothing asks for.
- **`accept <slug>` also commits edits to the Flight file.** It stages the
  moved file as it stands in the checkout, so a half-written notes section goes
  to `done/` with it. That is deliberate: accepting means the notes need no
  answer.
