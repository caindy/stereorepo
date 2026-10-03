---
difficulty: medium
---

# Keep each turn's closing message in the Issue file

A seat learns what the other did only from the diff of the working tree and
the Issue file. What the other seat said at the end of its turn goes to
`.pair/<seat>.log` and nowhere else. So a review that finds nothing to fix
leaves no trace: the next seat cannot tell a thorough check from a glance.

The seats already end every turn with a closing message. The loop keeps it
where the other seat will read it, and nothing about what the seats are told
changes.

## What is wanted

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
- **The words follow:** `pair/README.md` says what the loop keeps.

## Out of scope

- Any change to what the seats are told: the files under `pair/prompts/` and
  the turn message `Loop.message` builds stay as they are.
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
- The pair tests cover each of these, and no file under `pair/prompts/`
  changes.

## The developer's decision (2026-10-02)

The first implementation landed as `9f129a71` and was reverted (`6fd1ea9`):
its new instructions to the seats about their closing messages made the
model's safeguards refuse a fresh seat's first turn. Plainer wording was
tried and refused the same way. So this Issue keeps only the supervisor's
part, which tells the seats nothing new.

`9f129a71`'s changes to `pair/board.py` may be reused: read them with
`git show 9f129a71 -- pair/board.py`. Write the change to `pair/loop.py` and
the tests afresh. Do not open `9f129a71`'s changes to `pair/loop.py`,
`pair/prompts/` or `pair/test_pair.py`, which carry the refused wording, and
do not quote or rewrite that wording.
