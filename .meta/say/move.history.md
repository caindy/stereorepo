# History

### Difficulty label assigned without challenge label

Assigning a difficulty label to an issue that lacked the `challenge` label
failed to trigger autonomous coder workflows, which listen for difficulty
events on challenges (solorepo's DR-116, solorepo's #113). Established: `triage()`
and `file_issue()` enforce that `challenge` and difficulty labels are applied
in a single transactional operation, disallowing bare difficulty assignment.

Evidence: `.meta/say/move::triage`

### Human session and autonomous loop colliding on claimed challenges

A human session claiming an issue at an autonomous loop difficulty level
resulted in duplicate runs and concurrent conflicting review answers
(solorepo's DR-112, solorepo's #110, solorepo's #115). Established: `claim()`
refuses claims by interactive sessions on `easy` or `medium` issues, preserving
loop boundaries.

Evidence: `.meta/checks/probes/channel/claim.py::claim_probes`

### Unclaimed challenges remaining assigned to inactive sessions

When work was stopped or handed back, stale claim markers remained on GitHub
issues, blocking other actors or loops from claiming them (solorepo's #117).
Established: `unclaim()` and `stop()` synchronize GitHub issue assignees and
state transitions atomically before posting hand-back commentary.

Evidence: `.meta/checks/probes/loops/stop.py::stop_probes`

### Auto-merge arming on out-of-date branch heads

Enabling auto-merge on pull requests with stale or conflicting branch heads
caused auto-merge to fail silently or merge out-of-order layers (solorepo's DR-100,
solorepo's #93, solorepo's #98, solorepo's #201). Established: `advance()` and
`merge()` verify that pull requests are synchronized with trunk, disarm stale
auto-merge states during updates, and re-arm only once clean.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### Pull request squashing using arbitrary commit messages

Squash merges generated commit subjects from individual commit headers rather
than PR titles, leading to discrepancies between the git log and repository
issue index (solorepo's #26, solorepo's #27). Established: `merge()` explicitly
derives the squash commit title and subject from the validated PR title.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### Review requests submitted for conflicting branches

Submitting review requests on pull requests with merge conflicts or pending base
updates caused reviewer agents to fail on checkout or spend turns diagnosing merge
failures (solorepo's #102, solorepo's #192). Established: `request_review()`
checks that the branch is clean, conflict-free, and up to date before requesting
reviewer assignment.

Evidence: `.meta/say/move::request_review`

### Review request events suppressed for already-requested reviewer

GitHub emits no notification event when adding a reviewer that is already listed
on a pull request, leaving subsequent review requests silently ignored when a previous
turn answered nothing (solorepo's #87). Established: `request_review()` withdraws any
existing review request before requesting it again to trigger notification events.

Evidence: `.meta/say/move::request_review`

### Asynchronous rebase settlement and arming verification

GitHub's update-branch rebase endpoint returns before the rebase is completed on the
remote, causing immediate currency and auto-merge checks to observe stale head commits
and fail (solorepo's DR-158, solorepo's #253). Established: `advance()` polls until
the head commit moves and verifies whether auto-merge survived the update, re-arming
it if dropped.

Evidence: `.meta/say/move::advance`

### Detached HEAD branch detection in decision minting

Using `git rev-parse --abbrev-ref HEAD` printed `HEAD` on detached checkouts, writing
unresolvable tag messages during decision reservation (solorepo's #152). Established:
`branch_here()` uses `git symbolic-ref -q` and falls back cleanly to 'an unnamed branch'.

Evidence: `.meta/say/move::branch_here`

### Decision record number collision across concurrent branches

Allocating decision record numbers by reading local filesystem branches allowed
multiple concurrent pull requests to claim the same identifier, requiring manual
renumbering (solorepo's DR-125, solorepo's DR-128). Established: `mint()` allocates
numbers via atomic tag creation on GitHub with conflict retry loops.

Evidence: `.meta/say/move::mint`

### Workflow dispatch to nonexistent branch references

Dispatching GitHub Actions workflows against branches that had not been pushed
or were already deleted led to untracked workflow failures (solorepo's #95).
Established: `dispatch()` verifies remote branch existence prior to triggering
workflow runs.

Evidence: `.meta/say/move::dispatch`


### Re-arming read back as a lost arming when GitHub merged inside the window

After a rebase dropped the arming, `advance` re-armed the pull request and
waited for GitHub to show the arming. When the last check went green between the
arming and the read-back, GitHub merged the pull request and cleared the
`autoMergeRequest` that merged it, so the wait spent its whole bound and then
reported that the branch had lost its arming, over one that was already on trunk
(solorepo's #253). Established: the read-back after a re-arming ends on either
an arming shown or a `MERGED` state, and a merge in the window is reported as a
merge; the waiting itself is what solorepo's DR-158 requires of a read GitHub
may answer stale.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### Rebase read back off the commit the sweep listed rather than the one it asked GitHub to rebase

On 2026-09-11 every `advance` concluded failure while rebasing correctly each
time: `update-branch` returns when the rebase is queued, and a read that follows
it answers about the head the branch is being moved off, behind by what it was
behind by and still carrying the arming the move was about to drop
(solorepo's #245). Anchored to the commit listed by the opening `pr list`, a
push landing before the rebase satisfied the wait on its first read and answered
for the rebase, so a failure was reported that did not happen and a re-arming
was skipped that was needed; and a push that was itself a rebase, arranged by
this verb's own dispatch, left the sweep asking GitHub to rebase a branch with
nothing to rebase (solorepo's #252). Established: `head_now` reads the head and
its distance behind together, `advance` asks it again after the `mergeability`
wait and immediately before the call (solorepo's #252), and the settle wait and
the compare are anchored to that commit (solorepo's DR-158).

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### Stall reported over a merge that had landed or a branch already current

`merge --auto` collected the refusal `advance` exited with and reported it after
the arming, so a pull request GitHub had merged in the meantime was announced as
merged and then exited on as armed and behind, the defect of solorepo's #46 in a
new coat. One HTTP blip on the `compare` that reads a rebase back was reported
the same way over a branch the rebase had already fixed, and the exit code is
the last thing the Job says. Established: `merge --auto` reads the pull request
back after arming, reports a merge as a merge, and reports a stall only over a
branch that is still behind its base.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### Review request stranded by a merge on trunk went undispatched

A merge on trunk that left a waiting review request on a branch GitHub reported
`CONFLICTING` left it answerable by nobody: GitHub builds no merge ref, so
`review.yml` creates no run, and the sweep returned before it read the unarmed
pull requests at all (solorepo's #159, solorepo's #161). Read once, `mergeable`
answered `UNKNOWN` on the very push that invalidated it, so nothing would ever
have been dispatched. Established: `advance`'s sweep reads every open pull
request, waits out `UNKNOWN`, and dispatches the coder's rebase pass by task name
for a loop's branch that conflicts while a review is requested of it
(solorepo's DR-133), while it is armed (solorepo's DR-149), or once it is
approved (solorepo's DR-167); it leaves the lower layer of a stack alone, and
one refused dispatch is one pull request's problem.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### Sweep went red on every push for a Challenge the loop no longer held

After `stop` moved a Challenge to `human`, every push to trunk dispatched for or
failed on the same conflicting pull request again, a red sweep each time over a
conflict that was the solo's; an Issue deleted or transferred under its branch
failed the read the same way on every push. Established: `dispatch` reads the
Challenge before dispatching (solorepo's DR-142), leaves a closed one, one at a
level no loop takes, and one it cannot read alone by name in a printed line, and
exits 0 over them.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### Superseded check runs read as failing

`statusCheckRollup` lists every run of a check on the head, so a gate run that
failed and was re-run green under the same name was read as a failing check by
the merge manager and by the sweep alike, holding an approved pull request out
of eligibility (solorepo's DR-167) and dispatching the coder over checks that
were green (solorepo's #316). Established: `deduplicate_checks` keeps the
latest run per name, ordered by `startedAt`, then `completedAt` unless it is
GitHub's year-one placeholder, then `createdAt`, and `check_green` and
`check_pr.green` read the deduplicated list.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### Approved pull request left stranded behind trunk with nothing to move it

`advance.yml` triggers on a push to `main` and on nothing else
(solorepo's DR-113), so a pull request that goes behind trunk while it is in
review is skipped by that run and reached by no later one: the approval it
receives afterwards is not a push. The merge manager then read
`mergeStateStatus: BEHIND`, called the pull request ineligible and went idle,
and with no other candidate to move trunk nothing pushed — approved and green
work sat stranded until it was rebased by hand (solorepo's #452, behind
solorepo's #447). Established: `merge_manager`, idle with nothing eligible,
hands the open pull requests to `advance_stranded`, which calls `advance <n>`
on each whose only failing semaphore is `BEHIND_BASE`. The branch-safety
refusals stay `advance`'s own — the exclusion of a branch that is the base of
another open pull request is solorepo's DR-133's, and the refusal of one
nothing has asked to land is the verb's — while the readiness filter is
`advance_stranded`'s: a reason list of exactly `[BEHIND_BASE]` is what keeps
out a pull request that is behind *and* red, since `advance` reads no check
run, and the conversations are read here because `evaluate_pr` consults them
only while nothing else has failed. A refusal is printed rather than exited on,
and `--dry-run` rebases nothing.

Not on a push to `main`. `advance.yml` runs on that push and on nothing else,
and it sweeps the same branches by the same test under a concurrency group
`merge.yml` does not share, so both were in flight seconds after the push;
`pr update-branch --rebase` returns when GitHub has taken the rebase and not
when it has done it, so inside that window both read a branch still behind and
both issued one — a second gate restart on a branch already current, or a
refusal that paints `advance.yml` red on an ordinary push. `merge.yml` passes
`--no-advance` there, and the stranded sweep keeps the events `advance.yml`
does not see: the schedule, and the gate and review completions.

Evidence: `.meta/checks/probes/loops/merge_manager_advance.py::merge_manager_advance_probes`

### Review answer pass on solorepo's #361 stayed dormant after solorepo's #311 was relabelled easy

When Challenge solorepo's #311 had its difficulty lowered from `hard` to `easy`
after a review verdict stood down, the review answer pass on open pull request
solorepo's #361 was not triggered: a relabel fires the Issue door and starts a
take pass rather than re-delivering a review, so a standing verdict stayed
dormant until the solo found the pull request and invoked
`move dispatch --task review <pr>` by hand (solorepo's #366). Established:
`delegate()` accepts either the Challenge number or pull request number,
verifies or ensures an autonomous difficulty (`easy` or `medium`) while
refusing `hard` or `human` without `--level`, dispatches `rebase` if
conflicting or `review` for a verdict standing unanswered on an open pull
request, refuses clean pull requests with no changes requested, or assigns
the coder and triggers the loop on an unstarted Challenge.

Evidence: `.meta/checks/probes/loops/delegate.py::delegate_probes`

### Third layer of a stack left open and unlinked

`gh stack link` takes either two pull requests, which starts a stack, or a
stack's number and the layer to add, and refuses a call naming fewer pull
requests than the stack already holds. `link` passed two pull requests every
time, so `open --on` opened the third layer of a stack and left it unlinked,
which the merge manager reads as an ordinary pull request on a branch
(solorepo's #496). A first repair walked the open pull requests below by base
branch and passed them all, and broke once the bottom layer merged, because
the stack still counts a merged layer. Established: `link` names the stack's
number, read off the pull request below, when that pull request is a layer,
and the pull request itself when it is not.

Evidence: `.meta/checks/probes/channel/layer.py::layer_probes`

### A decision merged to the trunk while it was still proposed

The merge manager merged solorepo's #573 while solorepo's DR-227, the entry
that pull request carried, stood `PROPOSED`, which is the falsifier
solorepo's DR-222 states in its own words. Nothing misbehaved: the pull
request was approved, green and mergeable, which was the whole of what
`evaluate_pr` asked, and a decision waiting on the solo was a gate on the
merge path that no semaphore knew about — named as a consequence by
solorepo's DR-222 three hours before it happened (solorepo's #575).
Established: `evaluate_pr` reads the candidate's diff through
`check_decisions_in_force` and defers a pull request that writes a Decision
entry's `status` line as `PROPOSED`, which is a diff carrying a decision
rather than one correcting an adopted entry's prose.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### An Issue answered elsewhere closed by hand or not at all

Splitting solorepo's #571 left the parent answered — the finding had become
solorepo's #577 and the proposal solorepo's #589, and nothing of it was
unowned — and no verb could close it. `supersede` closes a pull request
another answer overtook and nothing did the same one level up, so the close
fell to the solo in the browser, unsigned and unrecorded by the channel, or
did not happen and `just next` kept offering the Issue as ripe
(solorepo's #597). Established: `obviate` closes the Issue as not planned
against what answered it, refusing unless that is an open Challenge or a
merged pull request, and posts the account of where the work went on the
Issue and the backlink on what answered it.

Evidence: `.meta/checks/probes/channel/obviate.py::obviate_probes`

### A refused pull request remained silent on any pass with eligible candidates

On passes where at least one pull request was eligible, `merge_manager()`
printed `chosen:` and `deferred:` lines for eligible candidates but omitted
evaluations for pull requests refused by semaphores, reporting refusal reasons
only on completely idle passes (solorepo's #585). As a result, a candidate
carrying a proposed decision or failing a check received no explanation for its
omission while other work merged. Established: `merge_manager()` prints every
refused pull request and its semaphore reasons across both idle and active
passes.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`
