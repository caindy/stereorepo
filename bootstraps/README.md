# bootstraps

A **Bootstrap** is the standard for one language, together with the gates that
hold a project to it. Product material, not scaffold — which is why it lives out
here rather than in `.meta/`.

Disciplines are language-neutral by construction. That is what makes them
portable, and it is also what leaves them with nothing to bite on: "a guardrail
never observed to fail is not evidence" cannot fail a build. **A Bootstrap is
where a Discipline becomes a command that can fail**, for one language.

| Language | State |
|---|---|
| [`rust/`](rust/) | Built. A seed workspace whose gate, `cargo xtask gate`, holds six Disciplines; the workflow renders it and gates the result. |
| [`python/`](python/) | Built. A seed workspace whose gate, `uv run gate`, holds six Disciplines; the workflow renders it and gates the result. Pulled in from `python_bootstrap` (DR-094). |

## Why they live in the monorepo

A Portfolio is one repository, one Bounded Context, one Ubiquitous Language.
Bootstraps kept as separate repositories would each need their own copy of the
Disciplines they implement, and copies drift. Here they read the same
`.meta/assertions/imported/disciplines.yaml` the rest of the repository does, so
an implementation cannot fall out of step with what it implements.

It is also the monorepo claim, dogfooded: several Products, polyglot Projects,
one language holding them together.

## What a portfolio gets

Specialization asks which languages a portfolio will use, and it inherits those
Bootstraps' applied disciplines on the first day — the gates, the documentation
layout, the seed project. It does not inherit the Bootstraps themselves, which
stay here and are maintained here.
