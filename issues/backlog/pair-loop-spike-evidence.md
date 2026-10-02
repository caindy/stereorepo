---
difficulty: developer
waits_on:
  - why-fork-board-wiki-pages
---

# Cite the booktutor spike's answers on the Seat and Supervisor pages

Found grooming `why-fork-board-wiki-pages`. The Seat and Supervisor pages
list, as open questions, what the booktutor spike had to answer (once
section 8 of `WHY_FORK.md`, which `why-fork-remove-file` deletes), and its
answers are said to be in `docs/PAIR_LOOP_SPIKE.md` in `caindy/booktutor`. No seat can read that
file: the clone at `~/code/booktutor` and its `booktutor.gitbundle` hold no
`docs/` directory at any commit.

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

# Needs elaboration

The developer needs to put a copy of `docs/PAIR_LOOP_SPIKE.md` where a seat
can read it, for instance under this Issue's slug in the worktree, or say
where it lives.
