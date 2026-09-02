## Decision record

_Every decision taken, with why. Newest last._

Newest last. Add an entry when a decision is settled *and* implemented.

### DR-001 · `.meta/` is the staging ground
*2026-09-02*

Structure-explaining tooling and Specialization machinery live in `.meta/`;
product material lives everywhere else. solorepo is meant to be cloned, so the
machinery that performs and explains that Specialization has to be separable from
the content it acts on.

### DR-002 · Rough in an ontology of work
*2026-09-02*

`work_ontology.md` establishes shared vocabulary for the repo before there is much
structure to name. Explicitly early; treating it as settled would over-commit,
ignoring it would fragment the language it exists to create.

### DR-003 · Formalise the ontology in LinkML
*2026-09-02*

`work_ontology.yaml` makes the prose checkable. Composition is by reference off an
abstract `WorkEntity`, so a Capability appears in many Roles without being copied.
A SMART Goal requires all four of its parts, so a non-SMART goal fails validation.
Definition of Done gained structure because "measurable" is what it contributes.
Verified with `gen-json-schema` and `linkml-validate`.

### DR-004 · Add the runtime half
*2026-09-02*

Workload identity, AIBOM and audit are one gap wearing three hats: the ontology
modelled intent only. Added `Execution`, split `Identity` into principal and
workload kinds with a delegation link, `AgentBillOfMaterials` with pinned
`Component`s, and `AuditRecord`. Without delegation, in a team of one every action
resolves to a single name and the audit trail collapses. `AuditRecord.under_permission`
is optional on purpose: a log that could not hold an unauthorized action would be
useless.

### DR-005 · Capability carries no projected dimensions
*2026-09-02*

Rejected a read/write dimension on `Capability`. What a Capability can change is
answered fully by its application to Securables via Permissions, so encoding it on
the Capability is either lossy or a restatement of the whole space. Granularity
comes from the product of the two axes.

### DR-006 · Skills compose tools; tools are atomic
*2026-09-02*

Taking "Capability = SKILLs + Tools" literally: `echo` and `bash` are tools, and
"reading and writing files" is a skill that combines them. Added
`Capability.composed_of` with a rule enforcing that a TOOL composes nothing. The
relation matters for BOM and audit resolution down to what actually runs.

### DR-007 · APM is the packaging target
*2026-09-02*

A Role and a Persona should be installable outside `.meta/`, and APM is the
vehicle. APM has no Securable-shaped concept anywhere, which confirms the
portability seam rather than exposing a deficiency: Role travels, Remit does not.

### DR-008 · Reverted: capability reification on the schema
*2026-09-02*

A `Provisioning` enum, a `PackageRef` class and a `package_ref` slot on
`Capability` were added, validated, and then removed. The intersection of BOM, APM
and reification of Capability is a step too far for now. Kept as a roadmap
direction, with the inclination to delegate reification to Dockerfile or nix
pointers instead. `composed_of` and the atomicity rule from DR-006 were kept.

### DR-009 · Commit per settled decision
*2026-09-02*

Commit as each decision is settled and implemented, rather than batching. The repo
is a record of how the scaffold was reasoned into being, not only of its final
state. Reverts are commits too.

### DR-010 · Placeholder READMEs in empty directories
*2026-09-02*

git does not track directories, so the empty scaffolding folders would not have
survived a clone — and cloning is how solorepo is distributed. Each carries a
README saying its contents are not yet decided.

### DR-011 · `.agents/` is staged under `.meta/`
*2026-09-02*

`.agents` is an open convention with enough consensus that its place at repo root
belongs to a *product's* agent definitions. The agents supporting solorepo's
opinionated approach are scaffold, so they keep the convention's name inside
`.meta/`. Trade-off: tooling that looks for `.agents/` at the root will not find
them.

### DR-012 · Decisions are recorded in the repo
*2026-09-02*

Design decisions and insights belong in the repository, not only in an assistant's
private memory. `AGENTS.md` at the root carries the overview and a directory of
pointers, with `CLAUDE.md` symlinked to it; this file records the rest.

### DR-013 · Specialization is an instruction, not a build step
*2026-09-02*

Turning a clone into a product repo is judgement about one product, made once, so
an agent following a written procedure beats a program to invoke — and it needs no
toolchain, which matters when the repo is picked up in an arbitrary thread. The
term was already in the repo from DR-001 and was reused rather than replaced;
its spelling is normalised to **Specialization**.

### DR-014 · A solorepo is a monorepo: one portfolio, one bounded context, one language
*2026-09-02*

One product **portfolio** holds one **bounded context** and therefore one
**Ubiquitous Language**, and contains multiple **products**, which may be
polyglot projects. This is a deliberate departure from the DDD literature, where
a system carries several bounded contexts: the constraint is what makes a single
Ubiquitous Language enforceable across everything one person builds. It corrects
the framing of DR-013, which spoke of specializing into a new *product* repo.
Specialization produces a *portfolio*. The Ubiquitous Language meant here is the
portfolio's **own domain** language; see DR-015.

### DR-015 · Two languages: the portfolio's own, and solorepo's imported
*2026-09-02*

A generated portfolio has its own *sui generis* Ubiquitous Language, drawn from
its domain. solorepo's vocabulary — Persona, Capability, Challenge, Goal, Job,
Specialization and the rest — is **imported** to articulate the discipline. It
never replaces the domain language and has no authority over it.

In DDD's context-mapping terms this looks like a **Published Language** offered
upstream by solorepo, which a portfolio **conforms** to for discipline talk while
staying sovereign over its own domain.

The consequence is structural: the two must be **separable in the file tree**, or
`sync` cannot tell them apart. Sync pulls the imported vocabulary and machinery
forward; a portfolio's own language is its own decision, and overwriting a
project's own decisions is the failure that sync exists to prevent.

### DR-016 · solorepo republishes DDD; portfolios conform transitively
*2026-09-02*

solorepo adopts DDD as a Published Language and republishes it alongside its own
work vocabulary, so a portfolio conforming to solorepo is transitively conformist
to DDD.

**Terms carry provenance.** The published language has two strata: terms adopted
from DDD (Bounded Context, Ubiquitous Language, Published Language, Conformist)
and terms solorepo originates (Persona, Capability, Securable, Remit, Agency,
Job, Specialization). An entry has to say which, because an adopted term is
defined by the canon and is not ours to redefine. Silently redefining an
established term is worse than minting a new one — the divergence is invisible.
A portfolio's own domain terms are a third stratum, owned by the portfolio.

**Minting a term has a search order.** Does DDD already name it? Use it. Does
solorepo's vocabulary already name it? Use it. Only when neither does is a term
minted, and that is the explicit decision with the solo. *Specialization* was
reused under rule two; *Published Language* and *Conformist* were adopted under
rule one.

**Departures must be marked.** Conformity is the default, so a deliberate
divergence from the canon is recorded as one or transitive conformity breaks
silently. DR-014 is already such a departure: one bounded context per portfolio,
where DDD would expect several per system.

### DR-017 · DDD is reified as LinkML alongside the work ontology
*2026-09-02*

`ddd_ontology.yaml` carries the DDD pattern language as a schema: Bounded
Context, Ubiquitous Language, Subdomain, Context Map and its relationship
patterns, plus the tactical patterns a portfolio will model its domain with.

Reification makes DR-016's provenance **structural instead of clerical**: which
stratum a term belongs to is the file it lives in, not a column someone has to
remember to fill. It also gives the three languages of DR-015 the separability
that `sync` needs, since they become three files with three owners.

Conformity is preserved by construction. The schema restates the canon for
reference and says in its own header that where it and the book disagree, the
book wins and the schema is wrong. Citations name the pattern rather than a
chapter number. Two departures are marked in place: `Term` is a solorepo
addition so a language can be enumerated rather than only described, and
`DomainEvent` postdates the book.

### DR-018 · A Ubiquitous Language is a set of Concepts, not a set of Terms
*2026-09-02*

DR-017 modelled a language as `Term`s carrying a name, a definition and an
`avoid` list. That cannot state the problem it most needs to: `avoid` handles
**many words for one concept**, but the hazard here is **one word for many
concepts**. "Skill" already denotes three different things in scope for this
repo at once — a Capability of kind SKILL, an APM `skills` primitive, and the
loose use for what APM calls a `prompt`. If the unit of the model is the word,
a collision cannot even be written down.

SKOS is the standard for this, and its central move is decoupling the concept
from the label. `Term` is therefore replaced by `Concept` (`skos:Concept`) with
`pref_label`, `alt_labels`, `definition`, `scope_note` and `in_scheme`, plus
`confusable_with` for a Concept that shares a label but not a meaning. `avoid`
stays for the other failure mode and maps close to `skos:hiddenLabel`.

Two consequences. Provenance is no longer a field: the `TermProvenance` enum is
gone, and the stratum is read off `in_scheme`, so it cannot drift from the scheme
a Concept actually belongs to. And because schemes are first class, vocabularies
solorepo does not own — APM's primitives, a harness's terms — can be named as
schemes and pointed at, which the three-valued enum could not express.

SKOS and its constructs are adopted, not authored, and marked in place as
departures from DDD per DR-016.

### DR-019 · Persona splits into Personality and Persona
*2026-09-02*

The original sketch's *Persona* — SOUL.md plus a communication style — is really
a **Personality**: the character an Actor presents while working. **Persona** is
taken back for Cooper's sense from *The Inmates Are Running the Asylum*: a
specific, detailed, named user archetype the product is designed *for*, and a
first-class citizen of a solorepo rather than a borrowed metaphor.

The split earns itself twice over. It lets a Persona be **interrogated** — an
Actor adopts the Persona's Personality and holds a Job to be questioned, so no
new machinery is needed and the audit trail still attributes to the workload
identity rather than to a fictional person. And it lets a Persona **seed a design
tool**, which a two-slot character sketch could not.

Two things left deliberately unsettled. `persona_goals` is qualified rather than
reusing `Goal`, because a Cooper goal is a standing motivation with no deadline
and nothing marking it done — a genuine collision with the ontology's SMART Goal,
still to be resolved. And `Persona` is **not** linked to `JobToBeDone`, because
whether a JTBD states the user's job or the worker's is open, and the link would
silently decide it.

### DR-020 · Persona goals are typed, and the End tier is Goal-shaped
*2026-09-02*

`persona_goals` was a flat list of strings, justified by the claim that a Cooper
goal has "no deadline and nothing marking it done". Checking that against *About
Face* showed it is only half right, and only for two tiers of three:

| Tier | Norman level | Goal-shaped? |
|---|---|---|
| Experience | visceral | no |
| **End** | behavioural | **yes, apart from the Deadline** |
| Life | reflective | no |

An End goal — "process an invoice without manual reconciliation" — is specific
and has a plain test for having been reached. What it lacks is a Deadline: it is
standing and recurring, not a bounded commitment. So `PersonaGoal` now carries a
`goal_type`, and the End tier is recorded as Goal-shaped **without** being made
an instance of `Goal`, whose deadline is required to keep it SMART (DR-003).

Left open: whether `Goal` and an End goal should share an abstraction —
Challenge plus Definition of Done plus JTBD, with `Goal` adding the deadline —
or whether the work Goal simply *serves* an End goal and the two stay separate.
That decision also settles whether a `JobToBeDone` states the user's job or the
worker's, which DR-019 left open.

Verification also corrected `PersonaKind`, which had four values sketched from
memory. *About Face* defines six: CUSTOMER (the buyer, not the user) and SERVED
(affected without ever touching the interface) were missing. And the taxonomy is
attributed to *About Face* with Reimann, Cronin and Noessel, not to *Inmates*,
which introduced personas and the primary/secondary split only.

Business and technical goals are deliberately excluded: *About Face* keeps them
outside the persona so they cannot pollute the user model.

### DR-021 · A Job to be Done states the user's job, and names a Persona
*2026-09-02*

The original sketch had a JTBD specify a **Role** — a named set of Capabilities,
which is a worker's role. It states the **user's** job, so it names a
**Persona**. This closes what DR-019 and DR-020 left open.

The chain that results: a Persona is interrogated, which surfaces END goals,
which yield a Job to be Done, which a Goal commits to serving by a deadline. The
work Goal *serves* the End goal rather than being one, because a Goal carries a
Challenge — defect, epic, feature, task — and a user's goal has no Challenge.
Forcing a shared abstraction would break on that.

One consequence worth stating: **an Agency's Role is no longer implied by its
Goal.** The old chain ran JTBD → Role → Agency, so the worker's role fell out of
the goal. Now the Persona says who the work is *for* and the Role says who does
it, which are independent facts. Choosing a Role becomes an explicit act.

Left open: a Persona holds several END goals, and which one a given JTBD serves
is reachable through the Persona but not stated. Whether that edge earns its
keep is undecided.


### DR-022 · Literate Programming and Progressive Disclosure are Disciplines
*2026-09-02*

Two Disciplines adopted for every solorepo, in the sense settled earlier: a
structured way of working that must be adhered to because it is not an imperative
program.

**Literate Programming** makes the schema an exposition for a human reader, with
the machine-readable part secondary. A module explains itself; the `description`
carries reasoning rather than an inventory.

**Progressive Disclosure** keeps one small thing always-loaded and routes the
rest on demand. Its operative rule is that the digest is *deliberately
insufficient* — a summary sufficient to act on gets acted on, and the source it
summarises rots. Taken from `python_bootstrap`, which implements it as a load map
even though it never uses the phrase.

### DR-023 · The work ontology splits into seven modules
*2026-09-02*

`work_ontology.yaml` had grown to 1,180 lines holding everything, which both new
Disciplines argue against: nothing that long is an exposition, and nothing that
undivided can be disclosed progressively.

It is now an umbrella of 213 lines — the compositional equations, a load map, and
the container — importing seven modules under `work/`: **core**, **authority**,
**actors**, **personas**, **purpose**, **assignment**, **provenance**. Each opens
with a narrative carrying its own reasoning, and each compiles standalone.
Provenance is the runtime half, peeled off as its own module.

`work_ontology.md` is dropped. It was a fifteen-line sketch that the schema had
long since overtaken, and keeping a "source" that contradicts what it sources is
the drift these Disciplines exist to prevent. Everything in it survives: the
compositional equations in the umbrella's description, and each definition in the
module that owns it.

Verified across the split: the umbrella validates instances that the single file
validated, every module compiles alone, and the tool-atomicity rule still
rejects what it rejected before.

### DR-024 · `.meta/README.md` splits into a core and six satellites
*2026-09-02*

The README had grown to 556 lines holding vocabulary, principles, disciplines,
roadmap, a procedure and twenty-three decision records — while being the one file
`AGENTS.md` points at, and so the one that always loads. It violated the
Progressive Disclosure Discipline adopted one commit earlier, in the same way and
for the same reason the work ontology did.

It is now a ~50-line core carrying two tables and nothing else: a **load map**
routing from what you are touching to what to read, and a **routing table** for
where a new paragraph goes. Six satellites own the rest — `vocabulary.md`,
`principles.md`, `disciplines.md`, `roadmap.md`, `decisions.md`, `schemas.md`.

Two consolidations came with it. The Specialization procedure moved into
`disciplines.md` beside the definition of Discipline, since the procedure *is* a
Discipline and having the two apart was the split that made Discipline hard to
see. And the schema tooling moved into `schemas.md` beside the files it operates
on.

The core states its own insufficiency, which is the discipline's operative rule
rather than a disclaimer.
