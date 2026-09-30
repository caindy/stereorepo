---
difficulty: medium
---

# Keep each turn's rationale and findings in the Issue file

A seat learns what the other did only from the diff of the working tree and
the Issue file. What the other seat said at the end of its turn goes to
`.pair/<seat>.log` and nowhere else. So a review that finds nothing to fix
leaves no trace: the next seat cannot tell a thorough check from a glance, and
must either re-derive it or take it on trust. The seats already write notes
into Issue files unprompted, but as recaps of what they did, which the diff
already shows.

The next reader needs two things the diff cannot give: why a change was made
the way it was, and what a review checked.

## What is wanted

- **The seats end each turn in a known shape.** The stage prompts ask a seat
  that changed the plan or the implementation to end its turn with its
  rationale: why this approach, what it considered and rejected, and what it
  is unsure of. They ask a seat reviewing the other's work to end with its
  findings: what it checked and how (the test it ran, the file it read, the
  case it tried), what it found wrong and why, and what it confirmed is
  right. Neither is a recap of the diff. Reasoning that belongs in a Decision
  Record or a docstring still goes there, as Journaling routes it.
- **The supervisor keeps the notes.** After each turn, the loop appends that
  turn's closing message (`TurnResult.text`) to the Issue file under
  `## Pair notes`, labelled by seat, stage and turn, and commits it as part of
  the turn. Its own append does not count as a change: a turn whose only
  change is its note is quiet. A grooming pass has no Issue file, and keeps no
  notes; nor does a turn whose Issue file is gone, which is sent back as now.
- **A note cannot steer the loop.** The loop reads headings from the Issue
  file: `Needs elaboration` sends an Issue back, `The plan` finishes `todo/`,
  and the `Desk-check` sections drive a Flight's desk check. `board.section`,
  `board.last_section` and `board.last_of` match a heading at any level, and a
  bold lead such as `**The plan.**`, even when indented, so demoting a heading
  is not enough: the loop appends each note as a block quote (every line
  prefixed `> `), which none of them matches. The `## Pair notes` heading
  itself is not a name the loop reads, and closes the section above it, so the
  Flight's brief and desk-check notes read as before.
- **The other seat reads them in its diff**, since the Issue file changed. No
  message passes between the seats except through the file, and the notes
  land in `issues/done/` with the Issue.
- **The words follow:** `pair/README.md` says what a turn is told and what the
  loop keeps.

## Out of scope

- Judging whether a review's findings are substantive; that belongs to the
  pair-versus-single-seat evaluation on the roadmap.

## Done when

- Each turn's closing message appears once under `## Pair notes` in the Issue
  file, labelled by seat, stage and turn.
- A turn whose only change is its appended note is quiet, and a stage still
  advances on two such turns.
- A closing message containing `# Needs elaboration`, `## The plan` or
  `**The plan.**` neither sends the Issue back nor finishes `todo/`, and a
  Flight whose check turns leave notes still reaches its desk check with its
  brief intact.
- The stage prompts ask for rationale from a changing turn and findings from a
  reviewing one.
- The pair tests cover each of these, and `just gate` passes.
