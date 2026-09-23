# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `<path>::<symbol>`
-->

### Fabricated attribution trailers on pull request comments

Autonomous workflow runs posted pull request comments with fabricated or duplicated attribution trailers by bypassing the signing channel, leaving pull requests unverifiable under shared repository credentials (solorepo's #639, solorepo's DR-260). Established: `audit_comment_trailers()` and `comment_trailers()` enforce structural trailer validity on all pull request comments posted by repository Role accounts, requiring exactly one Actor trailer, one Agent trailer, and conforming workflow run identifiers.

Evidence: `.meta/lib/check_pr/review.py::audit_comment_trailers`

### Required contexts drifted from workflow job names

A comment previously advised "rename in both places or in neither", but
renaming a workflow job left branch rulesets waiting on a context nothing
produced, blocking merges without explanation. Established: required status
checks are read directly from branch rulesets and verified against workflow
job definitions.

Evidence: `.meta/lib/check_pr/verdict.py::required_contexts`

### Unpushed commit detection failing silently on missing upstream

Executing `git rev-list @{u}..HEAD` on a branch without an upstream tracking
configuration failed non-zero with empty stdout, causing unpushed checks to pass
silently. Established: `unpushed()` verifies exit codes and explicit status so
unpushed branches fail as actionable findings.

Evidence: `.meta/lib/check_pr/branch.py::unpushed`

### Merge base diff swallows exit codes on unresolvable base references

Failing `git merge-base` or `git diff` operations on unresolvable base references
returned empty outputs, causing handoff checks to treat unparsed branches as clean.
Established: `touched()` returns `None` on non-zero exit codes to distinguish
unresolvable bases from empty diffs.

Evidence: `.meta/lib/check_pr/branch.py::touched`

### Render check distinguishes stale generated targets from unrendered files

Reporting unrendered files as plain sentences caused them to bypass index target
checks, allowing stale generated documentation to pass undetected. Established:
`unrendered()` categorizes stale targets and orphaned files into distinct collections.

Evidence: `.meta/lib/check_pr/branch.py::unrendered`

### Thread inspection truncation in interactive review resumes

Clipping discussion threads mid-paragraph in review summaries led autonomous agents
to reply to incomplete feedback (solorepo's #126). Established: `shown()` accepts
an optional character limit and preserves complete thread text during review resumes.

Evidence: `.meta/lib/check_pr/review.py::shown`

### Resolved review threads excluded from reviewer inspection

Excluding resolved review threads from reviewer inspection prevented arriving agents
from verifying whether claimed fixes matched discussion feedback (solorepo's #117,
solorepo's #122). Established: `settled()` surfaces resolved discussions with their
resolving login alongside open review items.

Evidence: `.meta/lib/check_pr/review.py::settled`

### Review verdict query ordering and preview truncation

Querying review records without reverse ordering omitted the most recent verdict
submitted against the active head commit (solorepo's DR-118, solorepo's #123).
Established: `verdicts()` inspects the newest review records and formats them
newest-first.

Evidence: `.meta/lib/check_pr/review.py::verdicts`

### Status check query permission failure on Actions resources

Using `gh pr view --json statusCheckRollup` executed GraphQL queries traversing
workflow run resources requiring `actions:read` permissions not held by gate
tokens (solorepo's DR-153, solorepo's DR-155, solorepo's #233). Established:
`rollup_of()` and `rollups()` query specific check context nodes directly.

Evidence: `.meta/lib/check_pr/github.py::rollup_of`

### Branch conflicts under standing review requests silently stalling

Merge conflicts arising on base branches after review requests were posted
suppressed notification events and prevented review workflows from running
(solorepo's DR-145, solorepo's DR-149, solorepo's #141, solorepo's #192).
Established: `watch()` and `unheld()` monitor mergeability transitions and prescribe
explicit rebase remedies.

Evidence: `.meta/lib/check_pr/polling.py::watch`

### Armed auto-merge blocked by unresolved review conversations

Auto-merge remained armed indefinitely on pull requests carrying unresolved
review conversations, with no standing job acting to resolve threads or unblock
merges (solorepo's DR-159, solorepo's #232). Established: `unheld()` identifies
idle armed pull requests blocked by unresolved threads and prescribes the required
promotion or reply action.

Evidence: `.meta/lib/check_pr/remedies.py::unheld`

### Sweep fetch failure silently masked as clean triage

A GitHub API fetch failure during `sweep_all` exited with an unhandled error
that parent jobs masked as an empty clean queue, leaving stale check statuses
unreported (solorepo's #229). Established: `sweep_all` handles CLI failures explicitly,
surfacing unreachable GitHub states as check failures.

Evidence: `.meta/lib/check_pr/sweep.py::sweep_all`


### Dropped webhooks left loop pull requests unheld with nobody standing on them

A review event was spent or a run ended without answering, leaving a request
for changes unanswered, an approved pull request with red checks, a review
request whose reviewer check failed with no verdict, and a green pull request
whose Challenge had been moved to `human` or `hard`, each idle with no Job
standing on it (solorepo's DR-167, solorepo's DR-178, solorepo's #316).
Established: `unheld()` reports each shape once it has been idle longer than a
run may last, reads the Challenge's level to say whether the loop or the solo
holds the remedy, and prescribes the verb that re-delivers it.

Evidence: `.meta/checks/probes/loops/handoff.py::handoff_probes`


### One unreadable pull request node ended the whole residue listing

`residue()` asks GitHub which pull request each gone branch carried, once per
branch, and `github.gh` exits the process on a non-zero `gh`. One node GitHub
answered with a server error under the role credential — and answered normally
under the solo's own — ended the sweep before it printed any of the branches it
had found, so the listing an operator runs the command for never appeared
(solorepo's #578). Established: a branch GitHub will not answer for keeps its
removal commands and reports what GitHub said in refusing, so an expired
credential, which fails every branch alike, is legible on the screen.

Evidence: `.meta/lib/check_pr/branch.py::residue`

### Embedded inline Python thread counting in coder workflow promotion

The unattended coder workflow relied on an unlinted inline Python one-liner
(`python3 -c '...'`) inside a Bash run step to count unresolved review
threads on approved pull requests, bypassing static analysis and prechecks
(solorepo's DR-241, solorepo's #666). Established: `check_pr.py` grew the
`--unresolved-count` flag, and `no_inline_python` fails the gate if a run
step goes back to counting threads inline.

Evidence: `.meta/checks/files/inline_python.py::no_inline_python`


### Unbounded watcher retry loop on fatal errors and persistent polling failures

Catching `SystemExit` unconditionally without backoff or error classification in
`watch()` caused background watchers to spin indefinitely when encountering fatal
environment failures (such as pruned worktrees or missing working directories) or
unrecoverable GitHub errors, hanging background processes and preventing reactive
agent harnesses from receiving task exit signals (solorepo's #683).
Established: `watch()` classifies unrecoverable environment errors to fail fast,
applies exponential backoff to transient failures, and terminates via a circuit
breaker when retry attempts after a failed poll are exhausted.

Evidence: `.meta/checks/probes/loops/handoff.py::handoff_probes`


### The sweep's other pull request lookup still ended the whole sweep

`print_sweep()` asks `owned_and_open()` what this branch owns before it asks
`residue()` what outlived its pull request, and that first question makes the
same `gh pr list --head <branch>` call against the same process-exiting
`github.gh`. Protecting the residue lookup alone left the symptom a second path
to it: standing on the branch GitHub will not answer for, the sweep exited
before the residue ran (solorepo's #578, solorepo's #579). Established: the
sweep's GitHub half reports itself unreadable and names the refusal, rather
than returning an empty list that reads as a branch owning nothing, and the
residue prints under it either way.

Evidence: `.meta/lib/check_pr/cli.py::print_sweep`


### A hung gh call stalled the watch that a handoff depends on

`github.gh` ran `gh` with no `timeout=`, and every poll `watch` makes goes
through it. A call that never returned produced no output, no retry and no
exit, so the watch stopped without stopping: the failure was indistinguishable
from the normal state of a watch, which is that nothing has happened yet, and
the process that would have woken the session was the one stuck
(solorepo's #738). The circuit breaker established for solorepo's #683 could
not fire, because a hang raises nothing for it to count. Established:
`github.gh` bounds each invocation at `GH_TIMEOUT` and exits with prose no
pattern in `FATAL_POLL_PATTERNS` matches, so a hung poll is retried under
backoff and a hang that persists exhausts `max_retries` and exits. A bound
alone did not reach every call a poll makes: `repo()` caught the exit and fell
back to the git remote, so a hang there cost the interval and degraded in
silence, and the evaluation that reads the reviewer's login sat outside the
retry. `gh` now raises `GhTimeout`, which `repo()` declines to catch, and a
poll is the snapshot and its evaluation together. The stand-in the probe runs
against answers an unbounded call successfully, so stripping `timeout=` from
the invocation fails the probe.

Evidence: `.meta/checks/probes/loops/handoff.py::handoff_probes`
