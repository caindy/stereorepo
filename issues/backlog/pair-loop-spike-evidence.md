---
difficulty: developer
waits_on:
  - why-fork-board-wiki-pages
---

# Cite the booktutor spike's answers on the Seat and Supervisor pages

Found grooming `why-fork-board-wiki-pages`. The Seat and Supervisor pages
list, as open questions, what the booktutor spike had to answer, and its
answers are said to be in `docs/PAIR_LOOP_SPIKE.md` in `caindy/booktutor`.
No seat can read that file: the clone at `~/code/booktutor` and its
`booktutor.gitbundle` hold no `docs/` directory at any commit.

## Wanted

`wiki/stereorepo/seat.md` and `wiki/stereorepo/supervisor.md` carry the
spike's answer to each section 8 question that concerns them, as evidence,
citing the spike document.

## Out of scope

Changing the pair loop on the strength of the answers; each change it
suggests goes in a new Issue.

## Done when

Each open question on the two pages is followed by the spike's answer
and a citation, and the developer has checked the answers against the spike.

## Where the spike lives

The developer's checkout of `caindy/booktutor` holds it at
`/Users/christopher/tutorly_project/booktutor/docs/PAIR_LOOP_SPIKE.md`, last
changed in commit `cdfa78d` (2026-09-29). A seat can read it there. Its
section "Open questions (WHY_FORK.md, section 8)" answers the questions, and
the hypothesis runs above it (H1 to H9) hold the evidence. Cite it as
`docs/PAIR_LOOP_SPIKE.md` in `caindy/booktutor` at `cdfa78d`.
