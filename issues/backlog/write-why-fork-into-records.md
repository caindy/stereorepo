# Write WHY_FORK.md up into Decision Records and wiki pages

`WHY_FORK.md` at the root holds the reasoning behind this repository: why PR
First was removed, the pair-loop delivery paradigm that replaced it, the
alternatives rejected, the meta-harness survey, the cockpit requirements, and
the board's vocabulary. It was written out of band and follows none of the
repository's conventions. Work its content up into proper artifacts, then
delete it.

- Decision Records for each settled choice: the pair loop over a choreography;
  agreement as both seats accepting the same state; the board as directories
  moved with `git mv`; front matter holding only `difficulty`, `waits_on` and
  `parent`; seats as vendor harness CLIs; local squash-merge to `main` with no
  pull requests; no agent at the top; the rule for choosing terms (section 10).
  Record the alternatives section 5 rejected as the alternatives they are.
- Wiki pages, under `wiki/stereorepo/`, for the concepts the ontology added:
  Issue, Board, Stage, Human, Seat, Supervisor, Quiet turn and Desk check. The
  booktutor spike's findings (`docs/PAIR_LOOP_SPIKE.md` in caindy/booktutor)
  belong in the Seat and Supervisor pages as evidence.
- The meta-harness survey (section 6) and the cockpit requirements (section 7)
  as Explanation, wherever the Knowledge Management discipline routes them.
- Re-test the inherited terms section 10's rule did not reach in the
  bootstrap. *Client Repo* is the first candidate: it names what the
  ontology already calls a Portfolio's repository.
- Remove the exemption `.meta/checks/citations/loaders.py` gives
  `WHY_FORK.md`, with the file.

Done when `WHY_FORK.md` is gone, every claim it made is in a record or a page
that the gate checks, and `just gate` passes.
