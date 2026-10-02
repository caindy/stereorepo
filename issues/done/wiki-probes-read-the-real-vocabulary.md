---
difficulty: easy
---

# Keep the wiki parity probes off the portfolio's real vocabulary

The `wiki probes` step fails in every portfolio that mints a domain concept.
Its case "stereorepo pages of a minted discipline and concept"
(`.meta/checks/probes/knowledge.py`) hands `ubiquitous_language_wiki_parity`
a synthetic set of wiki pages and expects no finding. But
`_domain_vocabulary_problems` in `.meta/checks/files/wiki.py` reads the
repository's real `.meta/assertions/domain_vocabulary.yaml` whatever pages it
is given. stereorepo's own domain vocabulary has no concepts, so the probe
passes here. fitch-mvp minted 24 concepts, each with its page in
`wiki/fitch/`, and the probe fails there, reporting each concept as having no
wiki page because the synthetic set holds none of them.

This is the same class of defect as `_probe_adopt`: a check that is right in
stereorepo and wrong in every portfolio (`portfolio-gate-before-landing`).

## Wanted

- `ubiquitous_language_wiki_parity` takes the domain concept set as an
  argument, as it already takes `md_files`: when given, it reads that set;
  when omitted, as the gate calls it, it reads
  `.meta/assertions/domain_vocabulary.yaml` exactly as now, including the
  "failed to parse" finding.
- Every `wiki probes` case that calls the parity check passes its own concept
  set (empty for the existing cases), so no case reads the repository's file.
- Two new cases cover the domain direction, which no case covers today: a
  concept set holding one concept with its page under a non-`stereorepo`
  context passes, and the same set without the page yields "has no
  corresponding wiki page". The passing case needs the concept in the probe's
  index as well (as `ddd:concept/<slug>` or `work:concept/<slug>`), or the
  reverse direction reports the page as having no concept.
- The `wiki probes` step is also judged with the domain vocabulary read as a
  portfolio's would be (one minted concept whose page is absent from the
  probe's pages), in the manner of `_probe_adopt_in_a_portfolio` in
  `.meta/checks/probes/files/rendered.py`, so stereorepo's own run proves the
  probes hold in a portfolio.

## How anyone will know it is done

- `wiki_probes()` returns no problems in stereorepo, and returns no problems
  when `domain_vocabulary.yaml` is read as holding a concept with no page
  among the probe's pages (the portfolio view above, which fails before the
  change).
- The real parity check over the real tree is unchanged: in a tree whose
  `domain_vocabulary.yaml` mints a concept with no `wiki/<context>/<slug>.md`,
  it still reports that concept.

## Out of scope

- Running a portfolio's gate before landing, which
  `portfolio-gate-before-landing` covers.
- Any other probe that reads the real tree; write one found as a new Issue.

## The plan

1. **The check's seam** (`.meta/checks/files/wiki.py`). Split the file read
   out of `_domain_vocabulary_problems` into a module-level
   `domain_concepts() -> list[dict]`, which reads
   `ROOT/.meta/assertions/domain_vocabulary.yaml` and answers its
   `concept_set` (empty when the file is absent). Then
   `ubiquitous_language_wiki_parity(index, md_files=None, concepts=None)`
   uses `concepts` when it is given and calls `domain_concepts()` when it is
   not. `domain_concepts()` lets its errors propagate; the `try` stays in
   `_domain_vocabulary_problems(wiki_map, concepts)`, which calls
   `domain_concepts()` inside it when `concepts` is `None` and iterates the
   set inside it in either case. So a read error and a shape error (an item
   that is not a mapping) are both still reported as the one "failed to parse
   for parity check" finding, which
   `(OSError, UnicodeDecodeError, yaml.YAMLError, AttributeError, TypeError)`
   catches, and the gate's call with no `concepts` behaves as it does now.
   Update the docstring to name the new argument.
2. **Move `wiki_probes` to its own module** (`.meta/checks/probes/wiki.py`),
   taking `WikiCase` with it, and import it in
   `.meta/checks/probes/__init__.py` straight after `knowledge`. The move is
   forced. `knowledge.py` is 585 lines, and the `meta file sizes` ratchet in
   `.meta/checks/file_sizes.baseline.yaml` holds it at exactly 85 lines past
   the 500-line ceiling, failing it if it grows or shrinks. The new cases
   would make it grow. In the new module, wrap every line to the 100-column
   `line-length` of `.meta/ruff.toml`, because a file with no entry in
   `lines.baseline.yaml` may carry no long lines. In `knowledge.py`, lower its
   entries in both baselines (`.meta/checks/file_sizes.baseline.yaml` and
   `.meta/checks/lines.baseline.yaml`) to the counts it holds after the move,
   deleting an entry that falls to zero, and update its module docstring,
   which lists the wiki probes among its subjects. Register the new module
   in `.meta/assertions/structure.yaml` as
   `work:artifact/meta-checks-probes-wiki`, beside
   `meta-checks-probes-knowledge`, or the `operational artifacts` check
   (`.meta/checks/graph/artifacts.py`) reports it as unasserted; then
   `just render`. Leave DR-190 and DR-231, which name
   `meta-checks-probes-knowledge`, as they are: a Decision is not rewritten,
   and that Artifact still exists.
3. **The cases.**
   - Give `WikiCase` a `concepts` field, defaulting to `()`.
   - In the loop, pass `concepts=case.concepts` only when `case.reads` is
     `files.ubiquitous_language_wiki_parity`, because the other three checks
     take no such argument.
   - Add a domain concept, for example `ddd:concept/ledger`, to the shared
     index, so that the reverse direction finds a concept for its page.
   - Add the two domain-direction cases: concepts
     `({"id": "ddd:concept/ledger"},)` with the page `wiki/billing/ledger.md`
     expect no finding; the same concepts with no page expect "has no
     corresponding wiki page".
4. **The portfolio view.**
   - Add `wiki_probes_in_a_portfolio()`, which runs the body of
     `wiki_probes` with `checks.files.wiki.domain_concepts` replaced by a
     function that answers one concept, for example `ddd:concept/fitch-term`,
     whose page no case gives. Restore the original in a `finally`, in the
     manner of `_disciplines_as` in `.meta/checks/probes/files/rendered.py`.
   - Prefix its problems with "in a portfolio minting a concept:" and append
     them to the step's own problems.
   - Patch the attribute on the `checks.files.wiki` module, not on
     `checks.files`, so that the patched name is the one the parity check
     looks up.

**How it is shown to work.** Revert step 1 alone, and the portfolio view
fails, reporting `fitch-term` as having no page. With step 1 in place, the
step passes. A one-off run of `ubiquitous_language_wiki_parity(index)` over
the real tree, with `domain_concepts` answering a concept that has no page,
still reports that concept. Do this run by hand and commit nothing for it.

**Risks.**
- The two ratchets and the Artifact registration are the main ways the
  change can fail. Re-count both files after the move.
- Moving the step changes the order of the probe report only by where
  `wiki probes` sits among its neighbours.
- `FakeWikiPath`'s docstring already names the parity check, so it needs no
  change.

## What was done

- The plan held. The portfolio view is a private helper,
  `_with_domain_concepts`, rather than a separate `wiki_probes_in_a_portfolio`
  function. `wiki_probes` runs the cases twice: once as they stand, and once
  through that helper.
- The cases, the shared `INDEX` and `PORTFOLIO_CONCEPTS` are module-level in
  `.meta/checks/probes/wiki.py`. Repeated page texts are named constants.
  The file has no line over 100 columns.
- `knowledge.py` fell to 433 lines, under the 500-line ceiling, so its entry
  left `file_sizes.baseline.yaml`. Its `lines.baseline.yaml` entry fell from
  36 to 22.
- The type checker narrows `case.reads` when it is compared with `is`. So the
  loop passes `concepts` through `**kwargs` rather than in a branch that calls
  the parity check directly with a `FakeWikiPath` list.
- Checked by hand:
  - `wiki_probes()` answers `[]`.
  - The call as the probe made it before this change, with no `concepts`,
    reports `ddd:concept/fitch-term` under the portfolio stand-in.
  - The parity check over the real tree, under the same stand-in, still
    reports it.
- The gate's own call, which gives no `concepts`, is now probed for good
  rather than only by hand: `_vocabulary_on_disk` in the step asserts that a
  concept read from `wiki.domain_concepts` with no page is reported, and that
  a `domain_concepts` that raises `yaml.YAMLError` gives the one "failed to
  parse for parity check" finding. With the fallback broken (the parity check
  iterating only `concepts`), the step fails with both findings.
  `_with_domain_concepts` now takes the stand-in function rather than a list,
  so that it can stand in a raising one.
- `just render` could not run in this session, because the sandbox refuses
  writes to `.claude/skills/`. The `meta` gate reported no stale rendered
  page, so the new Artifact entry in `structure.yaml` changes no rendered
  output.
