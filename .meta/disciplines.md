## Disciplines

_Structured ways of working that must be adhered to._

A **Discipline** is a structured way of working that must be adhered to because
it is not an imperative program. It has steps and order, it is followed rather
than executed, and it produces artifacts. Distinct from a Capability (what can be
done), a Permission (what may be done, to what) and a characterisation (what
something is like).

### Specialization

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

### Literate Programming

The schema is an exposition addressed to a human
reader; the machine-readable part is secondary to the account of what it means
and why. In practice: a module's `description` carries its *reasoning*, not an
inventory of its contents, and a class comment records what a reader would
otherwise have to reconstruct. The YAML is code to be read.

### Progressive Disclosure

One small thing loads always; everything else loads
on demand, routed by a load map from *what you are touching* to *what to read
first*. Its sharpest rule, taken from `python_bootstrap`:

> A digest tells you a rule exists and where it lives; only the file it points at
> is sufficient to apply it. **The digest is deliberately insufficient.**

A summary that is sufficient gets worked from, and the source it summarises
rots. Route each paragraph as you write it — *what to do*, *what happened*, or
*why* — because that is the only moment the routing decision is cheap.
