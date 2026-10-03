"""The probes: the gate's regression tests, one module per subject under test (stereorepo's DR-342).

Not invariants over the record. These load the scripts under `.meta/` and
run them against the inputs they exist to refuse and the states they were
found wrong in. They are a package of their own because the gate over
assertions should not take its imports from a test suite (stereorepo's DR-150).

Importing a module registers its steps, so the order of the imports below is
the order the probes report in: what the repository writes down about itself,
then its verb surface, then the ruleset and the ceilings its own gate holds it
to, then the tools.
`harness.py` registers
nothing and is what every subject module imports; it imports no sibling, so
the package's import graph is a tree with the harness at its root.
"""
import checks.probes.knowledge  # noqa: I001  # reason: registration order is deliberate
import checks.probes.wiki
import checks.probes.structure
import checks.probes.citations
import checks.probes.surface
import checks.probes.ruleset
import checks.probes.files
import checks.probes.tools  # noqa: F401  # reason: registers check steps
