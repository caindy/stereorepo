---
difficulty: medium
parent: write-why-fork-into-records
waits_on:
  - why-fork-delivery-records
---

# Write the meta-harness survey and the cockpit's requirements as Explanation

One part of `write-why-fork-into-records`. Section 6 of `WHY_FORK.md`
surveys other meta-harnesses (three ways to hold a session, nine tools, and
seven reasons none is adopted), and section 7 lists eight things a
cross-repository cockpit must do. Neither is a decision; both are
Explanation, which the Knowledge Management discipline (DR-184, DR-196)
routes to `wiki/stereorepo/`.

## Wanted

Two concept pages, written with the `/wikisplain` and `/technical-writing`
skills:

- `wiki/stereorepo/meta-harness.md`. Its lead defines a meta-harness: a
  tool that runs coding-agent harnesses and passes work between them. It
  carries the three ways to hold a session, saying which one the seats use
  now (the `stream-json` stream, DR-309) and how the developer takes over a
  seat now (`claude --resume`, per `pair/README.md`), not the spike's plan;
  the nine-row table; and the seven reasons, each citing the record that
  settles the point where one does: no agent at the top (DR-306), agreement
  observed not declared (DR-307), state in files and git, not a `status`
  field (DR-308), harness CLIs with one session for the Issue (DR-309), and
  serial work within a repository (DR-311).
- `wiki/stereorepo/cockpit.md`. Its lead defines the cockpit: one
  deterministic view across every repository the developer runs a pair loop
  in. It carries the eight requirements as they stand now, per
  `pair/README.md`: the queue lists desk checks, Issues sent back to
  `backlog/` (by a `Needs elaboration` section or by a stage past its round
  cap; never to `roadmap/`), a loop paused because a seat crashed or was
  refused again after its one restart, a grooming pass paused past its round
  cap, and refused `--ff-only` merges; the status
  convention is the one `cockpit-status-convention` will publish (it has not
  landed, so the page says it is to come and names that Issue);
  cross-repository `waits_on` cites DR-301.

Each page needs a concept minted beside the others in
`.meta/assertions/imported/vocabulary.yaml` (`work:concept/meta-harness`,
`work:concept/cockpit`), because a page in `wiki/stereorepo/` without one
fails the wiki parity check, and an entry in `wiki/stereorepo/README.md`.
Re-render after minting.

The herdr row's doubt about its star count and its real repository is kept
as what was observed on 2026-09-28, when the survey was made. Words
`WHY_FORK.md` uses that are now out of date are replaced: the developer, not
"the solo"; no "spike".

## Out of scope

Building any part of the cockpit, the status file itself
(`cockpit-status-convention`), re-surveying the tools, and deleting
`WHY_FORK.md` (`why-fork-remove-file`).

## Done when

- Every one of the three ways, nine table rows, seven reasons and eight
  requirements in sections 6 and 7 of `WHY_FORK.md` appears in one of the
  two pages.
- Neither page says "solo", "spike", or that a sent-back Issue goes to
  `roadmap/`.
- Each page opens with a bold copular lead whose subject matches its title
  and its minted label, every wikilink in it resolves, and both concepts
  appear in the rendered vocabulary.

## The plan

No code changes. Both names already pass
`python3 .meta/wikisplain.py "<name>" --check-duplicate`.

1. **Mint the concepts.** In `.meta/assertions/imported/vocabulary.yaml`,
   after `work:concept/desk-check`, add `work:concept/meta-harness`
   (`pref_label: Meta-harness`) and `work:concept/cockpit`
   (`pref_label: Cockpit`), shaped like `work:concept/supervisor`:
   `definition`, `in_scheme: work:scheme/stereorepo`,
   `broader: work:concept/g-doing`, a `scope_note`, and `avoid`. The cockpit
   avoids `dashboard` and `captain`. It is `confusable_with` the supervisor:
   each repository has a supervisor, and the cockpit only reads what they
   publish. Then run `just render`, which regenerates `.meta/vocabulary.md`.
2. **Write `wiki/stereorepo/meta-harness.md`**, using the front matter
   `slug`, `context` and `minted: 2026-10-02` and the layout of
   `supervisor.md`:
   - The lead, matching the minted definition.
   - `## Three ways to hold a session`, which states what the seats do now:
     `stream-json` (DR-309), with takeover by `claude --resume` from the id
     that `just pair-status` prints.
   - `## Tool by tool`, with the nine-row table kept as it is. The herdr row
     says "as observed on 2026-09-28".
   - `## Why none is adopted`, with the seven reasons, citing DR-306, DR-307,
     DR-308, DR-309 and DR-311 as "stereorepo's DR-nnn", as the other pages
     do.
   - **See also:** [[supervisor]], [[seat]], [[cockpit]].
3. **Write `wiki/stereorepo/cockpit.md`** in the same layout:
   - The lead.
   - `## Requirements`, with the eight requirements:
     - The queue lists what Wanted above names.
     - The status convention is "to come", naming `cockpit-status-convention`.
     - `waits_on: [otherrepo:slug]` cites DR-301.
     - "No agent at the top" cites DR-306.
   - **See also:** [[supervisor]], [[meta-harness]], [[developer]].
4. **List both pages** in `wiki/stereorepo/README.md`, after Desk check.

### Checks

- Map every item to a page by reading `WHY_FORK.md` sections 6 and 7 side by
  side with the pages: 3 ways, 9 rows, 7 reasons and 8 requirements.
- `git grep -n -i -E 'solo|spike|roadmap' wiki/stereorepo/meta-harness.md wiki/stereorepo/cockpit.md`
  returns nothing. So the cockpit page says a sent-back Issue stays in
  `backlog/` and does not mention `roadmap/` at all, even to deny it.
- The wiki checks (wikilinks, lead paragraphs, parity, avoided synonyms) are
  part of the gate the loop runs. They need no new probe, because the
  existing probes already cover each rule.

### Risks

- **Words in quotations.** The table says "captain" and "lead" when it
  describes firstmate and Claude Code agent teams, and those words are on the
  supervisor's `avoid` list. The synonym check reads only the front matter's
  synonyms, so the quotations pass. Declare no synonyms that are on an
  `avoid` list.
- **Search rankings.** The search benchmark (`.meta/lib/search/benchmark.py`)
  ranks concepts. Two new concepts that mention seats and the supervisor
  could push an expected hit down. Check its cases for "seat" and
  "supervisor" queries after `just render`.

## Notes

- Done as planned: the two concepts are minted after `desk-check` in
  `.meta/assertions/imported/vocabulary.yaml`, `.meta/vocabulary.md` is
  re-rendered, and both pages are listed in `wiki/stereorepo/README.md`.
- `just render` fails in the seat sandbox when it tries to write
  `.claude/skills/wikisplain/SKILL.md`, because it writes every target
  whether or not the target changed. The targets ahead of that one, including
  `.meta/vocabulary.md`, were written before it failed, and `render.py --check` reports
  "up to date". The `render-in-seat-sandbox` Issue in the backlog already
  covers this.
- The meta-harness page's table keeps the survey's words "captain" and
  "lead" where it describes other tools. Neither page declares a synonym.
- The search-ranking risk did not come true: the search probes pass with
  both concepts minted.
- Seats are Claude Code only today, so the meta-harness page says each seat
  is a `claude -p` stream. When a second harness lands under DR-309, that
  sentence needs widening.
