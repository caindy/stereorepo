---
slug: client-repo
context: stereorepo
synonyms:
  - Specialization
  - Child Repo
  - Specialized Portfolio
minted: 2026-09-14
---

# Client Repo

**Client Repo** is a software repository that specializes stereorepo by adopting its cognitive operating layer via the APM package, inheriting its SDLC and verification gates, and instantiating language Projects from Bootstraps on demand (stereorepo's DR-206).

In the ontology of work, stereorepo distinguishes between conceptual domain groupings and physical storage repositories. While a [[portfolio]] defines the monorepo boundary enclosing a single Bounded Context and its [[ubiquitous-language]], a *Client Repo* (synonymously termed a *Specialization*, *Child Repo*, or *Specialized Portfolio*) is the downstream version control repository created by a solo developer to build and operate products.

## Architectural Boundary & APM Consumption

Unlike legacy scaffolding approaches that relied on destructive file-copying or cloning, a Client Repo consumes stereorepo as an upstream versioned package via the [Agent Package Manager (APM)](https://github.com/microsoft/apm):

1. **Subdirectory Packaging:** The Client Repo declares an APM dependency on stereorepo's staging ground (`caindy/stereorepo/.meta@^0.1.0`), preserving the staging boundary rule that `.meta/` is the staging ground (stereorepo's DR-001) and that APM packages nest under `.meta/` (stereorepo's DR-172) without placing manifests or symlinks at stereorepo's root.
2. **Multi-Harness Projection:** Through APM, the Client Repo projects the unified disciplines, roles, capability skills, and signed-channel hooks into target harnesses (Claude Code in `.claude/`, OpenAI Codex in `.codex/`, Kiro in `.kiro/`, and Antigravity CLI in `.gemini/` and `AGENTS.md`).
3. **Upstream Synchronization:** The Client Repo runs `apm outdated` and `apm update` to receive upstream discipline refinements, role improvements, and skill bugfixes without repository re-initialization.

## Inheriting and Specializing the SDLC

A Client Repo inherits stereorepo's software development lifecycle (SDLC) mechanics, notably its verification gate orchestrator (`.meta/gate` per stereorepo's DR-104) and signed commit and communication channels:

- **Declarative Project Gates:** Each Project instantiated within the Client Repo declares its gate command in `assertions/structure.yaml` (e.g. `gate: cd products/app && uv run gate`). Running `just gate` executes every declared Project gate and prints standard A21 output (`ok`, `x`, `?`).
- **Repository-Level Specialization:** The Client Repo inherits `.meta/check.py`, which dynamically registers prechecks and structural invariants from `.meta/checks/`. Maintainers specialize repository verification by adding custom check modules decorated with `@check("check name")` in `.meta/checks/`.

## On-Demand Bootstrapping

Rather than forcing the adoption of all target programming languages during initial repository setup, a Client Repo brings stereorepo's language Bootstraps to hand:

- The operator recipe `just bootstrap <language> <path>` instantiates a standardized seed project (such as Python with `uv` or Rust with `cargo xtask`), substitutes package manifests, and appends the new Project declaration to `assertions/structure.yaml`.
- Bootstrapping can occur at the moment of specialization or be deferred indefinitely until a new product or service is required.

---

**See also:** [[portfolio]], [[concept]], [[ubiquitous-language]], [[knowledge-management]], stereorepo's Article 1, stereorepo's DR-001, stereorepo's DR-104, stereorepo's DR-172, stereorepo's DR-206.
