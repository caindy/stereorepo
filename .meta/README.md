# .meta — the staging ground

Two kinds of thing belong here:

1. Tools and ideas that make sense of the repository structure.
2. Whatever specialises a fresh clone's contents to a new product.

Everything else in the repo is product material. "Staging" means pre-product, not
temporary. `.meta/` is also the **producer-side authoring surface**: what gets
bundled up and shipped is built from these definitions.

| Path | What it is |
|---|---|
| `work_ontology.md` | The ontology of work as prose. The source. |
| `work_ontology.yaml` | The same ontology as a LinkML schema, validatable. |
| `.agents/` | Agent definitions supporting the scaffold. Contents not yet decided. |

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

Structure-explaining tooling and clone-specialisation machinery live in `.meta/`;
product material lives everywhere else. solorepo is meant to be cloned, so the
machinery that performs and explains that specialisation has to be separable from
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
