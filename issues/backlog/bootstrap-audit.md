---
difficulty: medium
---

# Audit a brownfield product against its language's bootstrap

DR-312 makes a bootstrap a reference and an audit for a product that already
exists: the audit compares the product with the reference, and each gap it
finds becomes an Issue in the backlog. Nothing does that yet; DR-312's second
consequence says so. `.meta/adapt.py` plans how stereorepo is installed into
an existing repository, and `.meta/bootstrap.py` makes a new Project from a
bootstrap. Neither looks at an existing product's own build and gate.

## What the reference already says

The reference is machine-readable today. Each bootstrap in
`.meta/assertions/bootstraps.yaml` lists its `discipline_implementations`,
and each implemented Discipline names the gate steps that hold it in
`held_by` (the Python standard: `doc`, `test`, `orphans`, `lints`, `ruff`,
`types`, `mutants`, `evidence`, `render`). A Discipline marked `exempt`
carries its `exemption_reason` and asks nothing of the Project. The gate
contract is the report shape `.meta/gate` parses: `ok <step>`,
`x  <step> (<count>)` and `?  <step>: <why>` (Article 21, DR-092).

## Wanted

A recipe, `just audit <project> <bootstrap>` (atomic identifiers only,
DR-259, DR-272), that runs the named Project's gate as
`.meta/assertions/structure.yaml` declares it, reads its reports, and
compares them with the named bootstrap. A gap is any of:

- a line of the gate's output that is not in the gate contract's shape, or
  a gate that reports no step at all;
- a step that some implemented Discipline's `held_by` names and the gate
  does not report, named with the Discipline it leaves unheld.

The audit prints each gap as the text of an Issue file (a `# ` title naming
the gap, then what is missing and which Discipline it serves), so the
developer can commit it to `issues/backlog/`. It exits non-zero when it
finds a gap. Record the recipe's shape in a Decision Record that builds on
DR-312.

## Out of scope

- Writing the Issue files itself; it prints them.
- Judging whether a reported step does what the bootstrap's step does. The
  audit compares step names and report shape, nothing deeper.
- Fixing any gap it finds, in any product.

## Done when

- A test with a temporary Project whose gate is a stub printing every step
  of the Python standard's `held_by` lists finds no gap and exits 0.
- The same stub with `mutants` removed reports one gap naming `mutants` and
  Observed Failure, and exits non-zero.
- A stub that prints a line in no contract shape reports that line as a gap.
- Run once by hand on `python-seed` against `python`, the audit reports no
  gap; the run's output is noted here.
