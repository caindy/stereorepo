## Roadmap

_What is intended and not yet built, and what is still open._

**Package a Role and a Persona via APM.** [Microsoft APM](https://microsoft.github.io/apm/)
is a dependency manager for AI agents — an `apm.yml` of pinned dependencies,
integrity by content hash, `apm-policy.yml` at install time, and per-harness
compilation from a `.apm/` directory. Bundles are to be built from the
definitions in `.meta/`. Note the terminology trap: APM's "agent" primitive is
closest to our **Persona**, not our **Actor** — identity is exactly what cannot
be packaged.

**The APM package is derived, and late-bound.** The step that turns `.meta` into
`.apm/` primitives is the missing half of the packaging story, and its value is
not encapsulation — it is **late binding**. Which harnesses a portfolio needs is
not knowable when it is specialized, and a harness introduced years later should
cost an `apm compile`, not a migration. That works only if the package is a
*derived artifact* and `.meta` is the source: the assertions ride with every
portfolio, so the package can always be rebuilt from them. Built ahead of time is
a cache, never a source.

What maps to what, from APM's primitives-and-targets model:

| Assertion | Primitive |
|---|---|
| a Discipline | `instructions`, with `applies_to` as its `applyTo` glob |
| the Ubiquitous Language | `instructions` scoped to everything — this is how the language biases output in *any* harness |
| a Personality, or a Persona to interrogate | `agents` |
| a Capability of kind SKILL | `skills` |
| the gate | `hooks`, on Stop or PostToolUse |

Two consequences worth holding on to. **Specialization's copy step could become
an install**: the inherited half is exactly what an APM package would carry, and
re-installing is the `sync` verb that has been missing since DR-028. And the
schemas themselves are not primitives — they would ride as a skill's supporting
resources, which is the first place this mapping strains.

**Two harnesses on one Challenge.** The concrete mission: Claude picking up where
Gemini left off on a coding task, coordinating through a PR, each spun up in its
own container. Directional for now, but it is what the runtime half was built
for — two Actors with separate WorkloadIdentities answering one Challenge is a
**Collaboration**, and asking who did what across two vendors' agents is exactly
the diff an AuditRecord makes computable. It also sets the bar for the package:
the same Disciplines and the same language have to reach both containers, which
no hand-maintained per-harness config survives.

**Reification via Dockerfile and/or nix.** Rather than the ontology inventing its
own coordinate system for where a Capability comes from, point at a build that
already pins its closure exactly, and get the bill of materials for free. See
DR-008.

**Ambient versus provisioned Capabilities.** `bash` is present because the harness
provides it; an MCP server is installed by name at a version. Only one is
packageable. Deferred with DR-008.

**A declared context scope on Remit.** `Execution.visible_securables` records what
was in context after the fact, but nothing declares the intended scope up front.
Visibility is the one constraint where ex-post is worthless, since an audit record
cannot un-leak.

**A Ubiquitous Language, defined and maintained per solorepo.** Every solorepo
should explicitly define, maintain and adhere to a Ubiquitous Language in the
Domain-Driven Design sense. Beyond the purposes from the literature — alignment
across requirements, code and planning conversations — solorepo has two of its
own:

- Coding agents must not invent new terms unless absolutely necessary, and when
  they do, it is an explicit decision taken with the solo.
- Agents bias *all* output toward the language: not only code and docs, but
  conversational turns.

The regime is not settled. Its likely shape is a pair: something episodic and
invoked (a `/add-ubiquitous-language-term` command) alongside something ambient
and always-on (system instructions). Both are expressible as APM primitives —
the ambient kind as `instructions`, the invoked kind as `prompts`. Candidate
term for the ambient kind: *discipline*, itself awaiting an explicit decision.

**A checker for the invariants the schemas cannot enforce.** ✅ Built — `.meta/check.py`, DR-029. Six constraints are
documented in class comments and enforced by nobody. Each was written down where
it was discovered, which was right at the time and is now a scattering:

| Invariant | Stated in | Why LinkML cannot |
|---|---|---|
| `composed_of` has no cycles | `work/authority.yaml` | acyclicity is not expressible |
| a Collaboration's Jobs all share its Challenge | `work/assignment.yaml` | path depth — `job.agency.remit.goal.challenge` |
| an AuditRecord's `under_permission` is one of its Execution's Remit's | `work/provenance.yaml` | same |
| an AuditRecord's `target` is a member of its `securable` | `work/provenance.yaml` | selectors are rules, not sets |
| a reference resolves to something that exists | everywhere | separate tree roots are separate files |
| a Job to be Done serves END goals its own Persona holds | `work/purpose.yaml` | the tier is on the target; ownership crosses a path |

The last is the widest: `Portfolio.bounded_context` is typed, and a Portfolio
naming a context that does not exist still validates.

`.meta/render.py --check` is the seed — a meta-gate that fails on staleness
rather than trusting anyone to notice. `python_bootstrap` has the pattern
developed further, with reference resolution and orphan detection as separate
`scripts/check_*.py`. The natural home is the `.meta` Project's `gate`, which is
the slot that exists to hold exactly this.

**Language bootstraps, blessed by solorepo.** `rust_bootstrap` exists as of
2026-09-02, specialized from here — the first Specialization that was not a test
fixture. Its `docs/literate-programming.md` holds the Rust implementation of that
Discipline, and this file no longer restates it: a design kept in two places is
the drift these Disciplines exist to prevent.

Two parts of that implementation are candidates for pulling up, once a **second**
language confirms them and not before: routing documentation by the paragraph
test, and requiring a history entry to name the test that would fail if its
change were undone. Promoting either from one implementation would repeat the
mistake of generalising from `python_bootstrap` alone.

Still to settle: **how a bootstrap declares what it implements**, and how
solorepo checks the claim. Blessing is a conformance claim of the shape
everything else here takes — every Discipline has an implementation per blessed
language, or a stated reason it does not — and nothing yet records it.

Also unresolved: **a portfolio has no designated place for product material.**
`rust_bootstrap` put its standard in `docs/`, which the scaffold neither
suggested nor forbade. `stakeholders/` is the only product-side convention
solorepo ships.

**Guiding the solo through identifying research.** A Persona should be drawn
from research, and `stakeholders/customers/` is where that research lives — but
the goal is **not** a check that fails when it is missing. The goal is to carry
enough background that a coding harness can *guide* the solo through finding and
recording the research in the first place, which is the hard part and the part a
gate cannot help with. Deprioritised: the persona direction is not where effort
goes next.

**External stakeholders as a source for outward-facing writing.** Investors,
media, advisors. `stakeholders/external/` was dropped rather than kept as an
empty folder, but the idea it held is worth keeping: a place to draw on when
asked for a press release or a blog post, so that outward-facing writing has a
source rather than being improvised each time. Not everything about running a
company belongs in a solorepo; this might.

**Open questions.**

- `AGENTS.md` and `CLAUDE.md` are APM **outputs**: instructions primitives fold
  into them, written next to each directory matching an `applyTo` glob, or as one
  root file under `apm compile --single-agents`. Ours are hand-written and sit in
  that path. Either they become an `instructions` primitive that compiles, or
  compilation has to be kept away from them.

- Whether **stakeholder** should be minted as a term. It is doing real work now,
  and is in neither DDD nor the vocabulary — but its two halves are already
  named (Persona, Role), so it may be a grouping rather than a concept.
- `work:persona/the-solo` is drawn from what its subject said and did here, and
  is awaiting his review — the EXPERIENCE and LIFE goals most of all.
- The audit that found three defects in DR-036 — markdown link resolution and
  scaffold prose in copied docs — was run by hand. Both are gate-shaped.
- `README.md` describes the Disciplines and the invariant count in hand-written
  prose about generated content. It will drift.
- The frontmatter fields for each APM primitive type, and where `apm.yml` sits
  when primitives are authored at `.meta/.apm/`. Neither was verifiable from the
  pages read — the primitive-types reference is marked legacy — and both must be
  checked against *Package types* and the *Targets matrix* before anything is
  authored.
- The compile step from `.meta/` definitions to APM primitives is unbuilt, and
  building it runs into the reification question above.
