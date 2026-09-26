"""The body of `.meta/say/move`: the transitions, one module per lifecycle (solorepo's DR-264).

What each module holds, and what it imports, read off its `from lib.move
import` line. `common` imports nothing in the package: the levels, the pull
request shape, the failures a call through the channel raises short of
exiting, which of the two a number names, and the `**Waits on.**` line, which
sits here because `challenges` rewrites it as the relationship moves and
`pull_requests` holds a revised body to it, and neither may import the other to
reach it. `decisions` imports nothing in the package either: the number minted
and reserved, and a record's status.
`concepts` imports nothing in the package either: the reservation a row in the
Ubiquitous Language stands on. `actions` imports nothing in the package either:
what GitHub's check machinery says that neither listing answers — which of the
loop workflows' runs are flying, whether trunk's own HEAD commit is green, and
what a red trunk owes (solorepo's #913, solorepo's #1027).
`drafts` is the one check before every way out of draft and the verb that makes
it, and imports `common`.
`epics` creates child Challenges under an approved hard Challenge and closes a
parent Epic after all its native GitHub sub-issues close; it imports `challenges`.
`challenges` is the Issue lifecycle, from filing to the closes that are not a
merge, and imports `common`, `pull_requests` and `advance`. `pull_requests` is
the pull request's, opening, layering, the merge and the supersession, and
imports `common`, `decisions`, `advance` and `handoff`. `handoff` is the review
request that names the Role a Challenge passes to, and imports `drafts` and
`pull_requests`. `advance` is the sweep on a push to trunk and the passes it dispatches, and
imports `common`, `handoff`, `pull_requests` and `manager`; it reaches
`reconcile` inside function bodies only. `manager` is the standing merge manager
and imports `common`, `pull_requests` and `advance`. It is the one package here
rather than a module. `manager.lock` holds the git tag lease the queue is
managed under and imports nothing else in `lib.move`, which is what lets a probe
reach the lease apart from the gate and the ranking; `manager.ranking` is that
reading, one pass's judgement of every open pull request and the order the
eligible ones are landed in, and imports `advance`, `challenges`, `common` and
`pull_requests`; `manager.eviction` is the stall eviction, draft demotion and
restoration lifecycle, and imports `advance`, `challenges`, `common`, `drafts`,
`pull_requests` and `ranking`; `manager.orchestration` is the queue coordination
and merge execution, and imports `advance`, `challenges`, `common`, `epics`,
`pull_requests`, `eviction`, `lock` and `ranking`. None of the four names anything
out of the package root, which imports all four as modules.
`reconcile` is what every open Issue and pull request is owed on the clock, and
imports `actions`, `common`, `challenges`, `handoff`, `pull_requests`, `advance`
and `manager`, every module before it but `decisions`, `concepts` and `drafts`.
`cli` is the argument surface the script delegates to and imports every module
but itself. `manager.orchestration` imports `epics` to close completed parents
before ranking pull requests.

The graph is not a layering. `advance` and `manager` import each other, `handoff`
and `pull_requests` import each other, and `challenges` and `pull_requests` each
import `advance`, which imports `pull_requests`. The cycles are safe because
every cross-module reference but one is an attribute read inside a function
body, resolved when the verb runs and not when the module loads, and `from
lib.move import x` answers from `sys.modules` while `x` is still initialising.
The one exception is `reconcile`, which reads `manager.MERGE_MANAGER_FIELDS` at
module level to build its own field list; that holds because nothing `reconcile`
imports reads `reconcile` at load — `advance`'s references to it resolve inside
function bodies — and a module that came to must not read it at load.

The entry exports the package's submodules and the CLI entry point
(solorepo's DR-217, solorepo's #1028), so callers and test probes access verbs
and seams qualified by submodule.
"""
