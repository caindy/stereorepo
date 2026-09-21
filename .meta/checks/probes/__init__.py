"""The probes: the gate's regression tests, one module per subject under test (solorepo's DR-209).

Not invariants over the record. These load `.meta/hooks/`, `.meta/say/` and
the scripts beside them, and run them against the calls they exist to refuse
and the states reviewers found them wrong in. They are in the gate because a
boundary is a boundary only while its predicate holds, and the predicates are
where reviewers have found holes (solorepo's #86, solorepo's #98). They are a
package of their own because the gate over assertions should not take its
imports from a test suite (solorepo's DR-150), and a package rather than one
module because one module had become the grab-bag that decision's falsifier
names: twenty-three suites over five subjects, and all the Evidence in every
history log routed to the same file.

Importing a module registers its steps, so the order of the imports below is
the order the probes report in: the hooks, then the channel, then the loops'
verbs, then what the repository writes down about itself, then its verb
surface, then the `gh` wrappers the channel and the tools both read, then the
tools. `harness.py` registers nothing and is what every subject module
imports; it imports no sibling, so the package's import graph is a tree with
the harness at its root.
"""
import checks.probes.git  # noqa: I001  # reason: registration order is deliberate
import checks.probes.channel
import checks.probes.loops
import checks.probes.knowledge
import checks.probes.surface
import checks.probes.wrappers
import checks.probes.tools  # noqa: F401  # reason: registers check steps
