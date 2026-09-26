"""The standing merge manager: the gate over an open pull request, the mutual exclusion
the two workflows that run it hold it under, and the landing in order of leverage
(solorepo's DR-161, solorepo's DR-264, solorepo's DR-267).

`lock` is the mutual exclusion (solorepo's DR-267), `ranking` is the candidate
evaluation and leverage ordering, `eviction` is the stall eviction and draft
restoration (solorepo's DR-258), and `orchestration` is the queue coordination
and merge execution. The root imports all four as modules and none imports a
name out of the root (solorepo's DR-217 for the route, the direction being this
package's own constraint): the root is mid-initialisation at the
`from lib.move.manager import eviction, lock, orchestration, ranking` line below,
so `from lib.move.manager import <name>` in a submodule would raise
`ImportError` on a name the root has not bound yet. Submodules still reach the
root transitively, `ranking` importing `advance` which imports `manager`, and
that survives only on the terms `lib.move`'s own docstring sets: `from lib.move
import manager` answers out of `sys.modules` and nothing in the closure
dereferences an attribute at import time. `lock` imports nothing else in
`lib.move`: the lease is a compare-and-set over a git ref and is read by a probe
of its own, apart from the gate and the ranking. The ranking does not reach the
lease at all, and `orchestration.merge_manager` is the one caller that does.
"""
from lib.move import advance, challenges, common, epics, pull_requests
from lib.move.manager import eviction, lock, orchestration, ranking
from lib.move.manager.eviction import (
    _refusal_notice_body,
    record_draft_recovery,
)
from lib.move.manager.orchestration import (
    MERGE_MANAGER_FIELDS,
    _close_completed_epics,
    _manage,
    merge_manager,
)

__all__ = [
    "MERGE_MANAGER_FIELDS",
    "_close_completed_epics",
    "_manage",
    "_refusal_notice_body",
    "advance",
    "challenges",
    "common",
    "epics",
    "eviction",
    "lock",
    "merge_manager",
    "orchestration",
    "pull_requests",
    "ranking",
    "record_draft_recovery",
]
