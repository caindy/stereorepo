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
loop workflows' runs are flying, and whether trunk's own HEAD commit is green.
`drafts` is the one check before every way out of draft and the verb that makes
it, and imports `common`.
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
`pull_requests` and `ranking`. None of the three names anything out of the
package root, which imports all three as modules.
`reconcile` is what every open Issue and pull request is owed on the clock, and
imports `actions`, `common`, `challenges`, `handoff`, `pull_requests`, `advance`
and `manager`, every module before it but `decisions`, `concepts` and `drafts`.
`cli` is the argument surface the script delegates to and imports every module
but itself.

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

The entry exports each module beside its names (solorepo's DR-217), so a
probe stands a seam in on the module that defines it. The modules are named so
that no verb's own local, `pulls` or `issues` among them, shadows the module it
must reach.

Four modules the entry exports the names of and not the module itself, and they
are reached through one that imports them. `advance` and `reconcile` share a
name with the verb they hold, and there the name wins. `handoff` and `actions`
are each priced out by the entry's own line ceiling: the `from lib.move import`
line stands at 97 columns, so either `, handoff` or `, actions` takes it past
the hundred of `.meta/ruff.toml`, after which ruff's isort wants one name to a
line and the eight names cost ten. A probe reaching one of the four goes through
a module that imports it — `manager` for `advance`, `cli` for `handoff` and
`reconcile`, and `reconcile` for `actions` — which is what the reconciler's
probe does.

`concepts` is the other way about and is none of the four: the entry exports
the module and not the names, because the module on that same line costs only
its line in `__all__`, where each name would cost two, one in a `from
lib.move.concepts import` block of its own and one in `__all__` beside it.
"""
