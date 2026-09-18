"""The PR First loops, run against a GitHub stood in for (solorepo's DR-209).

Not invariants over the record: these load `.meta/say/move` and
`.meta/check_pr.py` and run the verbs the loops turn on — `advance`, `merge
--auto`, the by-hand `dispatch`, `request-review`, `stop` and the merge
manager — and the readers beside them: `--watch`, the `unheld` sweep, and
`--handoff`'s reading of an enacted decision. Every one reaches GitHub in every
branch, and the states reviewers found them wrong in (solorepo's #98,
solorepo's #195, solorepo's #316) cost a merge on trunk to reach for real and
are gone by the time anyone could look; so GitHub is answered from a dict or
from a list of polls, and each state is a case rather than an argument about a
code path nothing ran.

One module for one subject, so that a history log's receipt names the file
holding the probe it cites (solorepo's DR-209). The fakes and the loaders are
the harness's, and the gate over assertions takes no import from a test suite
(solorepo's DR-150).
"""
import probes.loops.advance  # noqa: I001  # reason: registration order is deliberate
import probes.loops.dispatch
import probes.loops.handoff
import probes.loops.enacted
import probes.loops.stop
import probes.loops.merge_manager
import probes.loops.merge_manager_advance
import probes.loops.delegate  # noqa: F401  # reason: registers check steps
