# .meta — the staging ground

Two kinds of thing belong here:

1. Tools and ideas that make sense of the repository structure.
2. Whatever specializes a fresh clone's contents into a new portfolio.

Everything else in the repo is product material. "Staging" means pre-product, not
temporary. `.meta/` is also the **producer-side authoring surface**: what gets
bundled up and shipped is built from these definitions.

| Path | What it is |
|---|---|
| `work_ontology.md` | The ontology of work as prose. The source. |
| `work_ontology.yaml` | The same ontology as a LinkML schema, validatable. |
| `ddd_ontology.yaml` | DDD reified, republished per DR-016. Restates the canon; never overrides it. |
| `.agents/` | Agent definitions supporting the scaffold. Contents not yet decided. |

---

## Specialization

**Specialization** is turning a fresh clone of solorepo into a new portfolio
repo. It is an instruction an agent follows, not a script: the work is judgement
about one specific portfolio, and it happens once.

1. Rewrite the overview in `AGENTS.md` for the portfolio — what it is, who it
   is for. Keep the directory table and the conventions.
2. In this file, keep the Vocabulary and the Design principles. They are what is
   being inherited. Empty the Roadmap and the Decision record, and delete this
   Specialization section: a product specializes nothing.
3. Leave `work_ontology.md` and `work_ontology.yaml` untouched. The shared
   vocabulary is the point of the scaffold.
4. Replace the placeholder READMEs under `stakeholders/` with the portfolio's
   actual stakeholders.
5. Record the portfolio's own DR-001: what it is, and why it exists.
6. Commit.

---

## Working with the schema

No toolchain is checked in; the schema is exercised with `uvx`:

```bash
uvx --from linkml gen-json-schema .meta/work_ontology.yaml   # compiles?
uvx --from linkml linkml-validate -s .meta/work_ontology.yaml <instance.yaml>
uvx --from linkml linkml-lint .meta/work_ontology.yaml       # style only
```

`linkml-lint` reports warnings for uppercase enum values. That is the common
LinkML convention and they are left as they are.

There is **no instance data in the repo**. Every change so far was validated
against a throwaway example covering all classes, including negative cases for
each rule, but that example was never committed.

---

## Vocabulary

The ontology of work exists to give solorepo a shared language. It is a
deliberate rough-in: expect it to move, and raise tensions found while using it
rather than quietly routing around them.

| Term | Definition |
|---|---|
| **Persona** | A SOUL.md plus a communication style. The character an Actor presents. |
| **Capability** | A kind of thing that can be done or used. Tools are atomic (`bash`, `echo`); skills compose tools ("reading and writing files"). |
| **Securable** | A set of objects, by enumeration or by a selector rule. |
| **Permission** | The authority to employ a Capability on a Securable. |
| **Role** | A named set of Capabilities. |
| **Challenge** | A problem to address: defect, epic, feature, task. Supplies *specific*. |
| **Definition of Done** | The completion test. Supplies *measurable*. |
| **Job to be Done** | The need, stated from a Role's point of view. Supplies *achievable* and *relevant*, and names the Role. |
| **Goal** | A SMART goal: Challenge + Definition of Done + JTBD + Deadline. All four required. |
| **Remit** | Permissions + Goal. What may be done, and what for. |
| **Agency** | Role + Remit. |
| **Actor** | Persona + Identity + Memory. |
| **Job** | Actor + Agency. An assignment. |
| **Collaboration** | For a Challenge C, the Jobs that meet on it. |

The schema adds a **runtime half**, because the terms above are all design-time —
they describe work that has been *assigned*, never work being *done*:

| Term | Definition |
|---|---|
| **Identity** | Abstract. Either a **PrincipalIdentity** (durable, credential-held) or a **WorkloadIdentity** (attested per run, short-lived, delegating via `acts_on_behalf_of`). |
| **Execution** | One carrying-out of a Job. Records the workload identity, the BOM, and what was actually visible. |
| **AgentBillOfMaterials** | What an Actor was made of at a moment: the Actor and Agency graph resolved to immutable references. |
| **AuditRecord** | One employment of a Capability on a Securable. A Permission in the past tense. |

---

## Design principles

**Keep the axes clean.** Expressiveness comes from the *product* of Capability ×
Securable, not from splitting one axis to encode the other. Never let an object
into a Capability name: "edit files" is a Capability, `.meta/**` is a Securable,
and the pair is a Permission. When tempted to add a dimension to Capability, ask
which axis it belongs to.

**Prefer derived over declared.** A summary that can drift from what it
summarises is worse than no summary, because people trust the flag over the
truth. This is why Capability carries no read/write dimension, and why
reification is likely to be delegated to a Dockerfile or nix expression that pins
its closure by construction.

**Role travels; Remit does not.** `Agency = Role + Remit`, and that is the
portability seam. A Remit's Permissions name Securables that exist only in the
host repo, so a package carries Role and Persona while the Remit is bound at
install time in the destination.

**Audit is Permission in the past tense.** Both are the same triple of
Capability, Securable and Actor — one as authority, one as fact. Diffing them
makes least privilege a report rather than a discipline: an ALLOWED record with
no authorising Permission is a violation, and a Permission with no matching
record is an over-grant. This matters more in a team of one, where no second
person is around to notice.

**Enforce what the schema can; comment the rest.** LinkML rules cover what is
expressible (a stopped Execution records its end time; a tool composes nothing).
Invariants crossing reference boundaries or deep paths are written as class
comments so the checker that must own them is at least identified.

---

## Roadmap

**Package a Role and a Persona via APM.** [Microsoft APM](https://microsoft.github.io/apm/)
is a dependency manager for AI agents — an `apm.yml` of pinned dependencies,
integrity by content hash, `apm-policy.yml` at install time, and per-harness
compilation from a `.apm/` directory. Bundles are to be built from the
definitions in `.meta/`. Note the terminology trap: APM's "agent" primitive is
closest to our **Persona**, not our **Actor** — identity is exactly what cannot
be packaged.

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

**Open questions.**

- `AGENTS.md` and `CLAUDE.md` are APM **outputs**: instructions primitives fold
  into them, written next to each directory matching an `applyTo` glob, or as one
  root file under `apm compile --single-agents`. Ours are hand-written and sit in
  that path. Either they become an `instructions` primitive that compiles, or
  compilation has to be kept away from them.
- "Skill" already means three things: a `Capability` of kind SKILL here, an APM
  `skills` primitive (a `SKILL.md` meta-guide), and the loose sense in which a
  `/command` is called a skill — which in APM is a `prompts` primitive. The first
  real test of the language discipline.
- Whether the LinkML schema and a Ubiquitous Language are the same artifact. The
  vocabulary tables above duplicate the schema by hand, which is the drift the
  design principles warn against.

- The `stakeholders/` taxonomy: why customers / external / internal, and what
  "internal" means when the team is one person plus agents.
- Persona as a durable *seat* versus Actor as a *filled* seat — likely the first
  place the model moves.
- Cycles in `Capability.composed_of` are unenforceable in LinkML and need a check
  in whatever tooling reads these files.
- Whether the `.agents` convention's file shape embeds file scopes, which would
  collide with securable-free Capability naming. APM's `instructions` primitive
  does exactly that with `applyTo` globs — the closest thing APM has to an
  enforced Securable selector.
- The compile step from `.meta/` definitions to APM primitives is unbuilt, and
  building it runs into the reification question above.

---

## Decision record

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
