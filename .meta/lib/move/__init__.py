"""The body of `.meta/say/move`: the transitions, one module per lifecycle (solorepo's DR-264).

What each module holds, and what it imports, read off its `from lib.move
import` line. `common` imports nothing in the package: the levels, the pull
request shape, the failures a call through the channel raises short of
exiting, and which of the two a number names. `decisions` imports nothing in
the package either: the number minted and reserved, and a record's status.
`concepts` imports nothing in the package either: the reservation a row in the
Ubiquitous Language stands on.
`challenges` is the Issue lifecycle, from filing to the closes that are not a
merge, and imports `common`, `pull_requests` and `advance`. `pull_requests` is
the pull request's, opening, layering, the merge, the supersession, and the
review request that is the handoff, and imports `common`, `decisions` and
`advance`. `advance` is the sweep on a push to trunk and the passes it dispatches, and
imports `common`, `pull_requests` and `manager`; it reaches `reconcile` inside
function bodies only. `manager` is the standing merge manager and imports
`common`, `challenges`, `pull_requests` and `advance`. `reconcile` is what
every open Issue and pull request is owed on the clock, and imports `common`,
`challenges`, `pull_requests`, `advance` and `manager`, every module before it
but `decisions`. `cli` is the argument surface the script delegates to and
imports every module but itself.

The graph is not a layering. `advance` and `manager` import each other, and
`challenges` and `pull_requests` each import `advance`, which imports
`pull_requests`. The cycles are safe because every cross-module reference but
one is an attribute read inside a function body, resolved when the verb runs
and not when the module loads, and `from lib.move import x` answers from
`sys.modules` while `x` is still initialising. The one exception is
`reconcile`, which reads `manager.MERGE_MANAGER_FIELDS` at module level to
build its own field list; that holds because nothing `reconcile` imports reads
`reconcile` at load — `advance`'s references to it resolve inside function
bodies — and a module that came to must not read it at load.

The entry exports each module beside its names (solorepo's DR-217), so a
probe stands a seam in on the module that defines it. The modules are named so
that no verb's own local, `pulls` or `issues` among them, shadows the module it
must reach.
"""
