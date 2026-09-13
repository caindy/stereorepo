# History

### Difficulty label assigned without challenge label

Assigning a difficulty label to an issue that lacked the `challenge` label
failed to trigger autonomous coder workflows, which listen for difficulty
events on challenges (solorepo's DR-116, solorepo's #113). Established: `triage()`
and `file_issue()` enforce that `challenge` and difficulty labels are applied
in a single transactional operation, disallowing bare difficulty assignment.

Receipt: `.meta/say/move::triage`

### Human session and autonomous loop colliding on claimed challenges

A human session claiming an issue at an autonomous loop difficulty level
resulted in duplicate runs and concurrent conflicting review answers
(solorepo's DR-112, solorepo's #110, solorepo's #115). Established: `claim()`
refuses claims by interactive sessions on `easy` or `medium` issues, preserving
loop boundaries.

Receipt: `.meta/checks/probes.py::claim_probes`

### Unclaimed challenges remaining assigned to inactive sessions

When work was stopped or handed back, stale claim markers remained on GitHub
issues, blocking other actors or loops from claiming them (solorepo's #117).
Established: `unclaim()` and `stop()` synchronize GitHub issue assignees and
state transitions atomically before posting hand-back commentary.

Receipt: `.meta/checks/probes.py::stop_probes`

### Auto-merge arming on out-of-date branch heads

Enabling auto-merge on pull requests with stale or conflicting branch heads
caused auto-merge to fail silently or merge out-of-order layers (solorepo's DR-100,
solorepo's #93, solorepo's #98, solorepo's #201). Established: `advance()` and
`merge()` verify that pull requests are synchronized with trunk, disarm stale
auto-merge states during updates, and re-arm only once clean.

Receipt: `.meta/checks/probes.py::advance_probes`

### Pull request squashing using arbitrary commit messages

Squash merges generated commit subjects from individual commit headers rather
than PR titles, leading to discrepancies between the git log and repository
issue index (solorepo's #26, solorepo's #27). Established: `merge()` explicitly
derives the squash commit title and subject from the validated PR title.

Receipt: `.meta/checks/probes.py::merge_manager_probes`

### Review requests submitted for conflicting branches

Submitting review requests on pull requests with merge conflicts or pending base
updates caused reviewer agents to fail on checkout or spend turns diagnosing merge
failures (solorepo's #102, solorepo's #192). Established: `request_review()`
checks that the branch is clean, conflict-free, and up to date before requesting
reviewer assignment.

Receipt: `.meta/say/move::request_review`

### Review request events suppressed for already-requested reviewer

GitHub emits no notification event when adding a reviewer that is already listed
on a pull request, leaving subsequent review requests silently ignored when a previous
turn answered nothing (solorepo's #87). Established: `request_review()` withdraws any
existing review request before requesting it again to trigger notification events.

Receipt: `.meta/say/move::request_review`

### Asynchronous rebase settlement and arming verification

GitHub's update-branch rebase endpoint returns before the rebase is completed on the
remote, causing immediate currency and auto-merge checks to observe stale head commits
and fail (solorepo's DR-158, solorepo's #253). Established: `advance()` polls until
the head commit moves and verifies whether auto-merge survived the update, re-arming
it if dropped.

Receipt: `.meta/say/move::advance`

### Detached HEAD branch detection in decision minting

Using `git rev-parse --abbrev-ref HEAD` printed `HEAD` on detached checkouts, writing
unresolvable tag messages during decision reservation (solorepo's #152). Established:
`branch_here()` uses `git symbolic-ref -q` and falls back cleanly to 'an unnamed branch'.

Receipt: `.meta/say/move::branch_here`

### Decision record number collision across concurrent branches

Allocating decision record numbers by reading local filesystem branches allowed
multiple concurrent pull requests to claim the same identifier, requiring manual
renumbering (solorepo's DR-125, solorepo's DR-128). Established: `mint()` allocates
numbers via atomic tag creation on GitHub with conflict retry loops.

Receipt: `.meta/say/move::mint`

### Workflow dispatch to nonexistent branch references

Dispatching GitHub Actions workflows against branches that had not been pushed
or were already deleted led to untracked workflow failures (solorepo's #95).
Established: `dispatch()` verifies remote branch existence prior to triggering
workflow runs.

Receipt: `.meta/say/move::dispatch`

