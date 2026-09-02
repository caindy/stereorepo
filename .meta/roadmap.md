## Roadmap

_What is intended and not yet built, and what is still open._

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
