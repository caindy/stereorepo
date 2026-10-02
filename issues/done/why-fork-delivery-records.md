---
difficulty: developer
parent: write-why-fork-into-records
---

# Record the pair loop's settled choices as Decision Records

One part of `write-why-fork-into-records`. `WHY_FORK.md` argues for the pair
loop in sections 2 to 5 and 10, but none of its foundational choices is a
Decision Record. The records since (DR-299 to DR-303: the running order, the
grooming pass, cross-repository `waits_on`, the seat sandbox, the targeted
landing gate) refine the loop without recording why it exists.

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
Where a later record already settles part of a choice, the new record cites
it rather than restating it. Numbers start at DR-306 (the highest plus one at
the time of writing).

## Out of scope

Wiki pages (`why-fork-board-wiki-pages`), the survey and cockpit
(`why-fork-harness-survey`), re-testing terms (`why-fork-inherited-terms`),
and deleting `WHY_FORK.md` (`why-fork-remove-file`).

## Done when

- Each of the nine choices above is stated by a record under
  `.meta/assertions/decisions/`, and every alternative named for it appears
  in that record's `alternatives` with `chosen: false` and a `reason`.
- The seats write every new record as `PROPOSED`. DR-222 lets only the
  developer adopt a decision, and a change carrying one does not land ahead
  of it, so the developer reads the records at the desk check and moves each
  one to `ADOPTED` (or sends it back) before the Issue goes to `main`.
- No new record says "solo", `human` difficulty, `make`, or a send-back to
  `roadmap/`.
- `.meta/decisions.md` lists the new records (it is re-rendered, not
  hand-edited).
- A `## Records` section in this file maps each of the nine choices to the
  record that holds it, for `why-fork-remove-file` to audit against.

## The plan

Eight new files, `DR-306.yaml` to `DR-313.yaml` under
`.meta/assertions/decisions/`, each shaped like DR-300 (`id`, `name`,
`status: PROPOSED`, `enacted_in`, `context`, `alternatives`, `consequences`,
`falsifier`, `rationale`), then `just render` to regenerate
`.meta/decisions.md`. No code changes.

| Record | Choices | Alternatives not chosen |
|---|---|---|
| DR-306 · The pair loop: a supervisor that is a program, deciding from what it observes | 1 | the choreography of GitHub doors; an agent (a model) as supervisor |
| DR-307 · Agreement is a quiet turn, and sending back is a `Needs elaboration` section | 2 | a hand-off command; a `verdict:` field; OKF's `verified` fields or any semaphore |
| DR-308 · An Issue's stage is the directory its file sits in, moved with `git mv`, and front matter holds only `difficulty`, `waits_on`, `parent` | 3, 4 | a stage field, labels (GitHub Issues); `state`, `phase`, `round`, `landed`, `branch`, numeric ids; OKF as the file format |
| DR-309 · Seats are the vendors' harness CLIs, one session each for the Issue, in one shared worktree | 5 | an agent SDK; a fresh process per turn |
| DR-310 · Work lands by a local squash-merge to `main`, with no pull requests | 6 | pull requests on GitHub |
| DR-311 · A repository is the unit of parallelism, and its Issues run one at a time | 7 | several Issues at once in one repository |
| DR-312 · What the removal kept, and the bootstraps as a reference and an audit for a brownfield product | 8 | removing everything with the old delivery discipline; imposing a bootstrap on a brownfield product |
| DR-313 · A common word where it would be guessed right, a coined word only for a new concept | 9 | keeping *Challenge*; *Epic* as a type; carrying inherited terms untested |

The table lists only what each record rejects. The schema
(`.meta/work/decisions.yaml`) also requires exactly one alternative with
`chosen: true`, which is the choice itself, and its `reason` must say what
the choice costs. For example, DR-310's cost is that no review lives on
GitHub, and DR-311's is that Issues in one repository never run at once.

Choices 3 and 4 share DR-308 because both follow from one rule: record nothing
that can be observed. If writing them shows two questions, split them and
renumber before rendering.

Steps:

1. Write the records in table order. Draw contexts from `WHY_FORK.md`
   section 2 (cold start per hand-off, polling, a reviewer writing English,
   and the stall whenever an agent ignored an instruction) and reasons from
   section 5. Check every "now true" claim against `pair/README.md` and
   `issues/README.md` rather than `WHY_FORK.md`. That means: the developer;
   the `developer` difficulty and the desk check; send-back to `backlog/`;
   the `underway/` stage, which `WHY_FORK.md` omits; `just`; a session kept
   only while the model stays the same (`align_model`); the grooming pass
   (DR-300).
2. Cite the later records rather than restate them: DR-299 and DR-300 in
   DR-311, DR-301 in DR-311, DR-302 in DR-309, DR-303 in DR-310. DR-313 cites DR-041 (*stakeholder* is
   not a term), DR-190 (one wiki page for every term) and DR-234 (the audit
   of unminted candidates) rather than restating them.
3. `enacted_in`: name existing Artifacts only (`work:artifact/pair`,
   `pair-readme`, `justfile`, `agents`; `wiki-stereorepo-ubiquitous-language`
   and the vocabulary assertions for DR-313; `meta-bootstrap` and the
   bootstrap READMEs for DR-312). Filling it now means adopting is only a
   change of status. `issues/README.md` has no Artifact, and adding one is
   out of scope.
4. `just render`, then add a `## Records` section to this file mapping
   choices 1 to 9 to DR-306 to DR-313.

Tests that show it works:

- `just render` run a second time leaves the tree unchanged, and
  `.meta/decisions.md` lists DR-306 to DR-313.
- `grep -niE "solo\b|\bhuman\b|\bmake\b|roadmap/" .meta/assertions/decisions/DR-30[6-9].yaml .meta/assertions/decisions/DR-31[0-3].yaml`
  finds nothing that describes the present. It may still match where a record
  names the old discipline as an alternative.
- Every alternative named in the table appears with `chosen: false` and a
  `reason`, and each record has exactly one `chosen: true`. Every `enacted_in` id resolves in `structure.yaml`.

Risks:

- **Old solorepo record numbers.** Section 2 cites solorepo's DR-112 to
  DR-296, and a bare `DR-214` in a new record would read as stereorepo's,
  which does not exist. Name those records by what they did, never by
  number.
- **Enacting citations.** A file named in `enacted_in` that cites a DR must
  cite one naming it (`checks/citations/record.py`). Adding names only widens
  that set, so no existing file breaks. Do not add citations of the new
  records to `pair/README.md`, since `PROPOSED` binds nothing yet.
- **The desk check.** The developer reads eight records by hand, so keep each
  to its decision. Section 4's prose belongs in the wiki pages of
  `why-fork-board-wiki-pages`.

## Records

| Choice | Record |
|---|---|
| 1. The pair loop over a choreography, no agent at the top | DR-306 |
| 2. Agreement as a quiet turn; sending back as a consequence | DR-307 |
| 3. The board as directories moved with `git mv` | DR-308 |
| 4. Front matter holding only `difficulty`, `waits_on`, `parent` | DR-308 |
| 5. Seats as vendor harness CLIs, one session for the Issue | DR-309 |
| 6. Local squash-merge to `main`, no pull requests | DR-310 |
| 7. A repository as the unit of parallelism | DR-311 |
| 8. What survived, and the bootstraps as reference and audit | DR-312 |
| 9. The rule for choosing terms; *Issue* for *Challenge*; *Epic* dropped | DR-313 |

## Notes

- All eight records are `PROPOSED`. At the desk check, the developer reads
  each one and changes its `status` to `ADOPTED` or sends it back. Their
  `enacted_in` is already filled, so adopting a record changes only its
  status, then runs `just render`.
- Section 5's last alternative, deleting the choreography before the spike,
  is in no record. It was a question about the fork's sequence, and the
  fork made it moot.
- The records name solorepo's old records by what they did, never by
  number.
- A seat's `just render` writes `.meta/decisions.md`, then stops at
  `.claude/skills/wikisplain/SKILL.md`, which the seat sandbox (DR-302)
  will not let it write, so later pages go unwritten. Here the rendered-prose
  step of `just gate meta` still passed, so no page was left stale. A change
  that alters a skill or a page rendered after the skills would leave it
  stale for the developer to render.
- DR-312 originally stated the brownfield audit as if it existed. It does
  not: `.meta/adapt.py` plans an installation and reports no gaps. The
  record now says the audit is to be built, and
  `issues/backlog/bootstrap-audit.md` asks for it. The developer may prefer
  to hold DR-312 at `RECOMMENDED` until that lands.
