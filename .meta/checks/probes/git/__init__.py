"""The two hooks under `.meta/hooks/`, run against the calls they exist to refuse and the calls they must let through (solorepo's DR-209).

`signed_channel.py` refuses a path to GitHub that does not sign what it posts,
which is any path but the channel's directory (solorepo's DR-117);
`worktree_only.py` confines the reviewer's reads to the worktree and its
commands to one plain inspection at a time, and names the nearest command it
would have taken (solorepo's DR-110). A hook is a boundary only while its
predicate holds, and every hole a review has found in one (solorepo's #86,
solorepo's #98) is a row in `verdicts` beside the innocent neighbour the
predicate must not catch, so the next edit to either predicate meets them
before a run does.

Four modules: `verdicts` holds the calls each hook must refuse beside their
innocent neighbours; `offers` the nearest command a `worktree_only` refusal
names, and the tool it names in a program's place; `events` the before-tool
payloads each harness sends; and `step` the one registered check that runs
all three. The loader comes from
`probes.harness`, which imports no sibling under `probes/`: the gate over
assertions takes no import from a probe, and a probe takes none from another
subject's (solorepo's DR-150). One module per table (solorepo's DR-218).
"""
import probes.git.verdicts  # noqa: I001  # reason: the modules are listed in the order the step runs their tables
import probes.git.offers
import probes.git.events
import probes.git.step  # noqa: F401  # reason: registers check steps
