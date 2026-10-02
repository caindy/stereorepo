# Audit a brownfield product against its language's bootstrap

DR-312 makes a bootstrap a reference and an audit for a product that already
exists: the audit compares the product with the reference, and each gap it
finds becomes an Issue in the backlog. Nothing does that yet.
`.meta/adapt.py` plans how stereorepo is installed into an existing
repository, and `.meta/bootstrap.py` makes a new Project from a bootstrap.
Neither looks at an existing product's own build and gate.

## Wanted

A recipe that takes a Project in a portfolio and its language's bootstrap,
and reports where the Project's tooling falls short of the bootstrap's. One
example is a gate that does not report in the shape of the gate contract.
Each gap is written so it can become an Issue file in `issues/backlog/`.

## Done when

- Run on the Python seed itself, the audit reports no gaps.
- Run on a Python Project with a step removed from its gate, it reports
  that step as a gap.
