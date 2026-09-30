---
difficulty: easy
parent: backlog-grooming-and-ranking
waits_on:
  - backlog-running-order
  - backlog-grooming-pass
---

# Say what roadmap and backlog now mean

The backlog is now ranked and groomed, and a sent-back Issue now stays in
`backlog/`. Most of the words already say this: `issues/README.md`,
`template/issues/README.md`, `issues/backlog/README.md` and `pair/README.md`
describe `ORDER` and send-backs to `backlog/`. What is left is `roadmap/`,
which every description still calls "not yet elaborated enough to work", as
if it were a waiting room for the backlog.

## Wanted

These files say that `roadmap/` holds the developer's coarse, speculative
intentions, which may never be done, and that no agent moves an Issue into
or out of it:

- the `roadmap/` row of the stage table in `issues/README.md` and in
  `template/issues/README.md`;
- `issues/roadmap/README.md`, which also says the developer promotes an
  Issue from it once elaborated, as if that were its purpose;
- the Delivery bullet on adding work in `AGENTS.md` and `template/AGENTS.md`
  ("or `issues/roadmap/`, if it is not yet elaborated");
- the board row of the load maps `.meta/README.md` and
  `template/.meta/README.md` ("`roadmap/` what is intended and not yet
  elaborated"); their later row routing "what is intended, or still
  undecided" to `issues/roadmap/` already fits and stays;
- the `scope_note` of the Stage concept (`work:concept/stage`) in
  `.meta/assertions/imported/vocabulary.yaml`, which should also say that a
  send-back leaves the Issue in `backlog/`. Its `definition` lists the stages
  "in that order", which reads as if every Issue passes through `roadmap`;
  reword it so the order runs from `backlog` and `roadmap` stands beside it.
  Re-render so `.meta/vocabulary.md` follows.

## Out of scope

- `WHY_FORK.md`, which still says a send-back moves an Issue to `roadmap/`;
  it is being written up and deleted by `why-fork-remove-file`.
- `issues/done/`, which records what was true when each Issue landed, and
  the Decision Records under `.meta/assertions/decisions/`, which are never
  rewritten (Journaling) and mean the older `roadmap.md` where they say
  "roadmap".
- Filename order where it is still true: `next_ripe` in `pair/board.py` and
  `board_order` in `.meta/checks/files/board.py` fall back to filename order
  for slugs `ORDER` does not name, and their docstrings say exactly that.

- Mentions that already fit: the developer Persona "moves the idea to the
  roadmap" (`.meta/assertions/personas.yaml`, `.meta/.apm/agents/the-developer.agent.md`),
  `stakeholders/README.md`, the grooming pass's ban on touching `roadmap/`
  (`pair/prompts/stage-grooming.md`, `pair/board.py`), the `STAGES`
  tuple in `pair/board.py`, the `roadmap` line of `just pair-status`
  (`status` in `pair/loop.py`), and `.meta/checks/citations.history.md`,
  which is about the old `roadmap.md`.

## Done when

`git grep -n -i roadmap` outside `WHY_FORK.md`, `issues/done/` and the
Decision Records finds nothing that calls `roadmap/` a stage the loop sends
Issues to, or merely unelaborated backlog waiting for promotion; the Stage
concept says both things above; and `just gate` passes.

## The plan

Prose only; no code or test changes. The draft wording below is a guide, not
a requirement.

1. **Stage table.** In `issues/README.md` and `template/issues/README.md`,
   make the `roadmap/` row's middle cell read roughly "the developer's coarse,
   speculative intentions, which may never be done; no agent moves an Issue
   in or out". Keep "the developer" as the one who moves an Issue in. Change
   both files the same way so the two tables stay identical apart from links.
2. **`issues/roadmap/README.md`.** Replace the paragraph: roadmap holds what
   the developer intends and may never do. It is not a queue for the backlog.
   The pair loop takes no work from it, and no seat or grooming pass edits
   it. When the developer decides to do one, they write it as a backlog
   Issue. Leave out the "promotes once elaborated" sentence.
3. **Delivery bullet.** In `AGENTS.md` and `template/AGENTS.md`, cut "(or
   `issues/roadmap/`, if it is not yet elaborated)". Add one sentence saying
   that a coarse intention which may never be done goes in `issues/roadmap/`,
   where no agent moves it. Edit `AGENTS.md` itself; `CLAUDE.md` and the
   other names for it are symlinks.
4. **Load maps.** In `.meta/README.md` (line 33) and `template/.meta/README.md`
   (line 31), change "`roadmap/` what is intended and not yet elaborated" to
   something like "`roadmap/` the developer's speculative intentions, which
   may never be done". Leave the later "what is intended, or still undecided"
   rows alone.
5. **Stage concept.** In `.meta/assertions/imported/vocabulary.yaml`
   (`work:concept/stage`):
   - `definition`: list `backlog`, `todo`, `in-progress`, `desk-check`,
     `done` "in that order", then add that `roadmap` stands beside them and
     holds what the developer intends and may never do.
   - `scope_note`: keep "A directory, never a field". Add that no agent moves
     an Issue into or out of `roadmap`, and that a send-back returns the Issue
     to `backlog` on `main` with a `Needs elaboration` section, as
     `kick_back` in `pair/loop.py` does. The current "every other move is
     the supervisor's, and always a `git mv`" is already false for a
     send-back: `kick_back` runs `git rm` on the file and commits a
     rewritten copy under `backlog/`. Reword it so it stays true, for
     example "every other move is the supervisor's: a `git mv`, or for a
     send-back, the file rewritten into `backlog`".

   Then run `just render` and commit the regenerated `.meta/vocabulary.md`
   (lines 90 and 136) along with any other page it rewrites.
6. **Check.** Run `git grep -n -i roadmap -- ':!WHY_FORK.md' ':!issues/done'
   ':!.meta/assertions/decisions' ':!.meta/decisions.md'` and read each hit
   against Done when. Every remaining hit should be one of the mentions that
   Out of scope lists as already fitting. Run `git grep -n "not yet
   elaborated"` and expect hits only in this Issue file. Then run `just gate
   meta`, and `just gate` last.

### Risks

- **Search benchmark.** `.meta/lib/search/benchmark.py` expects
  `work:concept/stage` to rank for "which directory says what stage an issue
  is in" and "who moves an issue from one stage to the next", and the probe
  in `.meta/checks/probes/tools/search.py` expects it or the Supervisor
  concept in the top five for "who moves an issue between stages". Keep the words "directory", "stage", "Issue" and
  "moves" in the reworded entry, so the ranking holds.
- **Render drift.** A hand edit to `.meta/vocabulary.md` fails the gate's
  rendered-page check (`.meta/checks/files/rendered.py`). Edit only the YAML and re-render.
- **Template parity.** The `template/` copies are what a specialized clone
  starts from. They should change with their originals and must keep their
  placeholder tokens (double-underscored names such as the portfolio name)
  untouched. Do not write one out literally in this file either: the
  gate's surviving-placeholders check reads Issue files too.

## Notes

- Done as planned. The Stage `definition` now lists `backlog` to `done` in
  order and puts `roadmap` beside them; the `scope_note` says no agent moves
  an Issue into or out of `roadmap` and describes a send-back as the file
  rewritten into `backlog` on `main`. `.meta/vocabulary.md` is re-rendered.
- The remaining `git grep -i roadmap` hits are all ones Out of scope lists as
  fitting, plus `pair/test_pair.py` (fixtures for the grooming pass's ban on
  `roadmap/`) and `why-fork-delivery-records`, which already says send-backs
  go to `backlog/`.
- `STAGES` in `pair/board.py` still lists `roadmap` first. That is a lookup
  order for where a file sits, not a claim that Issues flow through it, so it
  stays.
- The Stage `scope_note` used to say only the developer adds Issues to
  `backlog`, but a seat that finds work outside its Issue writes it there
  too (AGENTS.md, Delivery). It now says the developer or a seat adds new
  Issues to `backlog`, and only the developer adds them to `roadmap`.
