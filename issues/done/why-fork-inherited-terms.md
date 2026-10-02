---
difficulty: medium
parent: write-why-fork-into-records
waits_on:
  - why-fork-delivery-records
---

# Re-test the inherited terms against the rule for choosing terms

One part of `write-why-fork-into-records`. The rule for choosing terms
(DR-313, recorded from section 10 of `WHY_FORK.md` by
`why-fork-delivery-records`) says an inherited term is re-tested before it is kept: use the common word when a
competent engineer or model would guess its meaning from the word alone, and
coin one only for a genuinely new concept. The bootstrap applied it to the
board's vocabulary but not to the terms it inherited.

## Wanted

Each inherited term below, being every `work:concept/*` and `ddd:concept/*`
in `.meta/assertions/imported/vocabulary.yaml` that was there before
`dfeaf73` (the bootstrap; compare against `dfeaf73^`) and is still there,
gets one verdict:

- **kept**, because the common word would be guessed wrong, no common word
  exists, or the term is the standard name in its own canon (DDD, Toulmin,
  APM); one line of reason, written beside the term in the *Verdicts*
  section below;
- **replaced** by the common word or an existing term: change the
  vocabulary's `pref_label`, put the old label in its `avoid` list, rename
  or merge its wiki page, change every use in prose outside `issues/done/`
  and the existing Decision Records, and re-render.

*Client Repo* goes first. It names what the ontology already calls a
Portfolio's repository, has a page, `wiki/stereorepo/client-repo.md`, and is
used in `.meta/.apm/README.md` and DR-206. Its page also names the
synonyms *Specialization*, *Child Repo* and *Specialized Portfolio*; whatever
the verdict, *Child Repo* goes in the `avoid` list of the term that keeps
the concept. *Specialization* does not: it is the name of a Discipline
(`work:discipline/specialization`, rendered into `SPECIALIZE.md`), so it is
dropped as a synonym rather than avoided. Nor does *Specialized Portfolio*:
*specialized portfolio* is the ordinary phrase, used in some twenty places,
for a portfolio made by Specialization rather than Adoption. Its
likely verdict is replaced by Portfolio
(or merged into it), unless the re-test finds a distinction the common word
loses.

All replacements are covered by one new Decision Record, which names each
old term, its replacement and the reason in a line each.

The terms: Invariant (of an Aggregate), Bounded Context, Ubiquitous
Language, Concept, Published Language, Conformist, Persona, Business goal,
Technical goal, Capability, Role, Portfolio, Client Repo, Product, Project,
Job to be Done, Persona goal, Discipline, Decision record, Bootstrap,
Literate Programming, Progressive Disclosure, Journaling, Knowledge
Management, Dogfooding, Modelling the Developer, Ratchet, Observed Failure,
Article, Charter, Claim, Evidence, Citation, Dereference, Nothing
Unconsumed, Seeded Artifacts, Written Decisions, Skill (stereorepo
Capability kind), Externalized Memory, Skill (APM primitive), Prompt (APM
primitive).

## Out of scope

- The board's terms (Developer, Issue, Flight, Board, Stage, Seat,
  Supervisor, Quiet turn, Desk check, Meta-harness, Cockpit), which were
  chosen by the rule already.
- The `g-*` grouping concepts, which are headings in plain words, not terms.
- The terms the trimmed Decision Records use (the `trim-decision-records-*`
  parts), and editing any existing Decision Record, except to drop an
  `enacted_in` pointer to an artifact this Issue deletes (as `dfeaf73` did
  for the artifacts it removed).
- A replacement that needs more than relabelling, such as renaming a
  Discipline's assertion file and id: record the verdict as *replace*, and
  write the rename as a new Issue in `issues/backlog/` instead of doing it.

## Done when

- The *Verdicts* section lists every term above with its verdict and reason.
- For each replaced term, `git grep -i '<old label>'` and
  `git grep '<old wiki slug>'` (for example `client repo` and `client-repo`)
  find it only in the vocabulary's `avoid` list, `issues/done/`, this file
  and existing Decision Records, and the new Decision Record names it. Where
  the old label is a common word (*Concept*, *Role*, *Claim*), the check is
  that no remaining use means the term: the word in its ordinary sense may
  stay. A replacement deferred to a backlog Issue is exempt from this
  check; its verdict names that Issue instead.
- No `[[wikilink]]` points at a renamed or merged page.
- If nothing is replaced, no Decision Record is written, and the
  *Verdicts* section says so.
- Re-rendering changes nothing further: `.meta/vocabulary.md` and
  `.meta/decisions.md` match their sources as committed.

## Verdicts

Replaced (DR-319 records both):

- **Client Repo**: merged into Portfolio. One repository holds one
  Portfolio, so the two words always named the same thing; *Client Repo*
  and *Child Repo* are on the Portfolio entry's `avoid` list, and its page is deleted.
- **Journaling**: replace, deferred to `rename-discipline-journaling`. The
  common word means keeping a log; the Discipline means routing narrative to
  the artifact that owns it, which a reader of the word alone would get
  wrong.

Kept, as the standard name in its own canon:

- **Invariant (of an Aggregate)**, **Bounded Context**, **Ubiquitous
  Language**, **Published Language**, **Conformist**: DDD's names, which an
  engineer who knows DDD reads right and one who does not can look up.
- **Claim**, **Evidence**: Toulmin's, quoted from fitch-mvp's schema so the
  four systems meant to merge share one meaning.
- **Skill (APM primitive)**, **Prompt (APM primitive)**: APM's own names,
  minted only to state their collisions.
- **Persona**, **Persona goal**: Cooper's.
- **Job to be Done**: Christensen's.
- **Literate Programming**: Knuth's, used in his sense.
- **Progressive Disclosure**: the interface-design term, used in its sense.
- **Knowledge Management**: the common phrase, narrowed to a wiki by Bounded
  Context.

Kept, as the common word already:

- **Concept**, **Capability**, **Role**, **Product**, **Project**: each the
  ordinary word, with its narrowing and its *not* already in the scope note.
- **Portfolio**: the common sense (everything one person builds) is right;
  the narrowing to one per repository is in the definition.
- **Business goal**, **Technical goal**: plain phrases, guessed right.
- **Discipline**: the common word for a practiced way of working.
- **Decision record**: the common phrase; its `avoid` list already drops
  *ADR*.
- **Bootstrap**: guessed close (what starts a project); the scope note
  narrows it to a language's standard and gates.
- **Citation**, **Dereference**: an engineer reads *dereference* as
  following a reference to what it points at, which is the meaning.
- **Article**, **Charter**: the ordinary constitutional sense, a charter
  made of numbered articles.
- **Skill (stereorepo Capability kind)**: the common word; the qualifier
  exists only to separate it from APM's skill.
- **Externalized Memory**: memory held outside the agent, which is what the
  words say.

Kept, as Discipline names whose words carry the meaning:

- **Dogfooding**: the industry's word, used in its sense.
- **Modelling the Developer**: says what it does.
- **Ratchet**: an engineer knows a quality ratchet from lint baselines.
- **Observed Failure**: a guard is seen to fail before it is trusted, which
  is red-before-green said plainly.
- **Written Decisions**: says what it does.
- **Seeded Artifacts**: *seed* is the common word for starting data.
- **Nothing Unconsumed**: no common word names "an artifact is only worth
  something if a check consumes it", so the coinage is for a new concept.

## The plan

Most of the work is judgement written into *Verdicts*; the code changes are
expected to be one merge (Client Repo) plus whatever relabels the re-test
finds. Renames of Discipline names are deferred by the scope rule above,
because each Discipline name is also a `work:discipline/*` id in
`.meta/assertions/imported/disciplines.yaml`, a file name under
`.meta/.apm/instructions/` and `bootstraps/*/`, and a baseline key.

### Seams

- `.meta/assertions/imported/vocabulary.yaml`: `pref_label`, `avoid`,
  `alt_labels`, `confusable_with` and `scope_note` of each entry touched.
- `wiki/stereorepo/<slug>.md`, and its `work:artifact/wiki-stereorepo-<slug>`
  entry in `.meta/assertions/structure.yaml`.
- Prose that uses a replaced label, found by `git grep -i`.
- Generated pages, refreshed with `just render`: `.meta/vocabulary.md`,
  `.meta/decisions.md`, and anything else it rewrites.
- One new `.meta/assertions/decisions/DR-nnn.yaml`, numbered one above the
  highest present, if anything is replaced.

### Steps

1. **Client Repo.** Re-test it: the concept is "a repository that took
   stereorepo's `.meta/` and specialized it", which is what a Portfolio's
   repository is once specialized. Expected verdict: merged into Portfolio.
   - Delete the `work:concept/client-repo` entry; drop it from the Portfolio entry's
     `confusable_with` (Project's never named it); add `Client Repo` and
     `Child Repo` to the Portfolio entry's `avoid`; carry into the Portfolio entry's
     `scope_note` the one distinction still true (a Portfolio is specialized
     from a clone of stereorepo and keeps `.meta/`), and nothing of the page's
     stale material (signed channel, multi-harness projection, Kiro).
   - Delete `wiki/stereorepo/client-repo.md` and its `structure.yaml`
     artifact. `[[portfolio]]` already resolves to the minted concept, so no
     new page is needed for wikilinks.
   - Reword the two uses in `.meta/.apm/README.md` (lines 84 and 89) to say
     portfolio.
2. **Re-test the remaining 40** and write each verdict as one line under
   *Verdicts*. Provisional triage, to be confirmed term by term:
   - kept as canon: the DDD five (Invariant, Bounded Context, Ubiquitous
     Language, Published Language, Conformist), Claim and Evidence (quoted
     from Toulmin via fitch-mvp), the two APM primitives, Persona and Job to
     be Done;
   - kept as the common word already: Concept, Capability, Role, Product,
     Project, Portfolio, the three goals, Discipline, Decision record,
     Bootstrap, Citation, Dereference, Article, Charter, Skill (stereorepo
     Capability kind);
   - Discipline names, where a replacement would be deferred: Literate
     Programming, Progressive Disclosure, Journaling, Knowledge Management,
     Dogfooding, Modelling the Developer, Ratchet, Observed Failure, Nothing
     Unconsumed, Seeded Artifacts, Written Decisions; and Externalized Memory,
     which is a concept only and can be relabelled here if it fails the test.
   For each deferred replacement, write a backlog Issue named
   `rename-discipline-<slug>` and cite it in the verdict.
3. **Relabel** any non-Discipline term that fails the test, by the steps in
   *Wanted*.
4. **Record** the replacements in one Decision Record whose `enacted_in`
   names the vocabulary and every wiki page or artifact changed.
5. **Re-render** with `just render` and commit the sources with the
   rendered pages.

### Tests

- `git grep -i 'client repo'`, `git grep client-repo`, `git grep -i 'child
  repo'` find hits only in the places *Done when* allows.
- `just render` run a second time leaves the tree clean.
- The existing wiki checks cover the rest without new code: wikilinks
  resolving (`wikilinks`), page-to-concept parity
  (`ubiquitous_language_wiki_parity`, which would fail if the page stayed
  after its concept went), and no page synonym on its own entry's avoid
  list (`wiki_synonyms_are_not_avoided`). No new test is written; the
  change is data.

### Risks

- **DR-206 names the page.** Its `enacted_in` lists
  `work:artifact/wiki-stereorepo-client-repo`, which step 1 deletes. Drop
  that one line from DR-206, as *Out of scope* allows, and say so in the new
  Decision Record. The pointer is to a deleted file; what DR-206 decided is
  unchanged, and its prose keeps the words *Client Repo*, which *Done when*
  allows.
- **No Portfolio page.** `wiki/stereorepo/portfolio.md` does not exist;
  `[[portfolio]]` resolves through the minted concept (`wikilinks` accepts a
  minted concept), and parity in the scaffold's context runs page to
  concept only, so merging into Portfolio needs no new page.
- **Specialization** must not reach an `avoid` list (see *Wanted*).
- **"specialized portfolio" as ordinary prose** (`wiki/stereorepo/README.md`,
  `knowledge-management.md`) uses the adjective, not the avoided term; leave
  it.
- **Claim's scope note** still describes the removed channel verb `claim`.
  That is stale, not a term to re-test; write it as a backlog Issue rather
  than fixing it here.

## Notes

- **What changed.** `work:concept/client-repo`, its page and its
  `structure.yaml` artifact are gone; Portfolio's scope note now says its
  repository is a specialized or adopted clone of stereorepo, and its
  `avoid` list carries *Client Repo* and *Child Repo*. DR-206 lost only its
  `enacted_in` line for the deleted page. `.meta/.apm/README.md` says
  *portfolio* where it said *client repos*. DR-319 records the merge and the
  verdicts.
- **The plan was wrong twice.** *Specialized Portfolio* is not avoided (see
  *Wanted*), and Project's `confusable_with` never named Client Repo.
- **Journaling** is the one Discipline name that fails the rule; its rename
  is `issues/backlog/rename-discipline-journaling.md`. Claim's stale scope
  note is `issues/backlog/claim-scope-note-channel-verb.md`.
- **Rendering in the seat's sandbox** stops at the first write under
  `.claude/skills/`, which the sandbox denies; `render.py --check` then
  reported every page up to date, so no skill changed. That is
  `issues/backlog/render-in-seat-sandbox.md`, to which this Issue is now
  added as a reporter.
- **One paragraph, not two.** Portfolio's scope note is one paragraph in
  the source. The vocabulary renderer joins a blank line in a folded scope
  note with a single newline, so a second paragraph there renders as a
  stray line in the same paragraph of `.meta/vocabulary.md`.
  The defect already shows in Ubiquitous Language, Claim and Evidence;
  it is `issues/backlog/vocabulary-scope-note-paragraphs.md`.
