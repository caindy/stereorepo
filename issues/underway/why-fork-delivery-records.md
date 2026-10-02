---
difficulty: medium
parent: write-why-fork-into-records
---

# Record the pair loop's settled choices as Decision Records

One part of `write-why-fork-into-records`. `WHY_FORK.md` argues for the pair
loop in sections 2 to 5 and 10, but none of its choices is a Decision Record:
the highest record is DR-297, which only prunes the old ones.

## Wanted

A Decision Record for each settled choice, with its context drawn from
section 2 (what the choreography cost, and that it stalled whenever an agent
ignored an instruction) and its alternatives from section 5, each recorded
as an alternative not chosen, with its reason:

1. The pair loop, a supervisor working from what it observes, over a
   choreography of agents driving a state machine; with no agent at the top.
2. Agreement as a quiet turn after a turn that changed something, and
   sending back as a consequence (a `Needs elaboration` section), never a
   verdict. Alternatives: a hand-off command, a `verdict:` field, a semaphore.
3. The board as directories an Issue file is moved between with `git mv`.
4. Front matter holding only `difficulty`, `waits_on` and `parent`.
   Alternatives: `state`, `phase`, `round`, `landed`, `branch`, numeric ids,
   and OKF as the file format.
5. Seats as the vendors' own harness CLIs, with sessions kept for the whole
   Issue. Alternative: an agent SDK.
6. Local squash-merge to `main`, with no pull requests.
7. A repository as the unit of parallelism: serial within it.
8. What survived the removal (section 3), and the bootstraps as a reference
   and an audit for a brownfield product rather than something imposed.
9. The rule for choosing terms (section 10): the common word where it would
   be guessed right, a coined word only for a new concept, inherited terms
   re-tested. Include *Issue* replacing *Challenge*, and *Epic* dropped.

Several choices may share a record where they are one decision. Each record
states what is true now, which `pair/README.md` and `issues/README.md`
describe, where `WHY_FORK.md` is out of date: the developer (not "the
solo"), the `developer` difficulty (not `human`), a send-back that stays in
`backlog/` (not `roadmap/`), `just` (not `make`), and the grooming pass.

## Out of scope

Wiki pages (`why-fork-board-wiki-pages`), the survey and cockpit
(`why-fork-harness-survey`), re-testing terms (`why-fork-inherited-terms`),
and deleting `WHY_FORK.md` (`why-fork-remove-file`).

## Done when

Each of the nine choices is stated by a record, with its alternatives;
`.meta/decisions.md` is re-rendered; this file lists which record holds
which choice, for `why-fork-remove-file` to audit against; and `just gate`
passes.
