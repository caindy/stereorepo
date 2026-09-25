# History

### Difficulty label assigned without challenge label

Assigning a difficulty label to an issue that lacked the `challenge` label
failed to trigger autonomous coder workflows, which listen for difficulty
events on challenges (solorepo's DR-116, solorepo's #113). Established: `triage()`
and `file_issue()` enforce that `challenge` and difficulty labels are applied
in a single transactional operation, disallowing bare difficulty assignment.

Evidence: `.meta/lib/move/challenges.py::triage`

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

Evidence: `.meta/lib/move/handoff.py::request_review`

### Review request events suppressed for already-requested reviewer

GitHub emits no notification event when adding a reviewer that is already listed
on a pull request, leaving subsequent review requests silently ignored when a previous
turn answered nothing (solorepo's #87). Established: `request_review()` withdraws any
existing review request before requesting it again to trigger notification events.

Evidence: `.meta/lib/move/handoff.py::request_review`

### Asynchronous rebase settlement and arming verification

GitHub's update-branch rebase endpoint returns before the rebase is completed on the
remote, causing immediate currency and auto-merge checks to observe stale head commits
and fail (solorepo's DR-158, solorepo's #253). Established: `advance()` polls until
the head commit moves and verifies whether auto-merge survived the update, re-arming
it if dropped.

Evidence: `.meta/lib/move/advance.py::advance`

### Detached HEAD branch detection in decision minting

Using `git rev-parse --abbrev-ref HEAD` printed `HEAD` on detached checkouts, writing
unresolvable tag messages during decision reservation (solorepo's #152). Established:
`branch_here()` uses `git symbolic-ref -q` and falls back cleanly to 'an unnamed branch'.

Evidence: `.meta/lib/move/decisions.py::branch_here`

### Decision record number collision across concurrent branches

Allocating decision record numbers by reading local filesystem branches allowed
multiple concurrent pull requests to claim the same identifier, requiring manual
renumbering (solorepo's DR-125, solorepo's DR-128). Established: `mint()` allocates
numbers via atomic tag creation on GitHub with conflict retry loops.

Evidence: `.meta/lib/move/decisions.py::mint`

### Workflow dispatch to nonexistent branch references

Dispatching GitHub Actions workflows against branches that had not been pushed
or were already deleted led to untracked workflow failures (solorepo's #95).
Established: `dispatch()` verifies remote branch existence prior to triggering
workflow runs.

Evidence: `.meta/lib/move/advance.py::dispatch`


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

### An advance sweep red for the weather of the pull requests it read

Every failure the sweep collected — a `gh` call that hit `net/http: TLS
handshake timeout`, a branch GitHub refuses to rebase because it conflicts
with its base — was spent on one `sys.exit` at the end, so `advance.yml` was
red on eleven consecutive pushes to trunk on 2026-09-18 and on nine of the
fourteen before them, naming the same two pull requests each time. Nothing
stalled from it, because the dispatch had already run; what was lost was the
colour, and the stall on solorepo's #568 had nothing but that colour to
signal it (solorepo's DR-238, solorepo's #635). Established: `advance()`
exits on a failure only when it was given a pull request, and a sweep prints
what the pull requests it read reported and returns, so its exit code answers
for whether the sweep ran.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### The decision semaphore would have cleared a decision recommended but not built

`check_decisions_in_force` deferred only a diff writing `PROPOSED`, while both
`PROPOSED` and `RECOMMENDED` fall short of `ADOPTED` — the only status
`.meta/work/decisions.yaml` describes as in force. The function's name and
docstring claimed to catch every Decision short of in force, but the semaphore
would have cleared a diff writing `RECOMMENDED` and printed `carries no proposed
decision`, read as clearance, though the solo had not adopted it. The latent
gap was caught by inspection on solorepo's #582 before any candidate carried
one (solorepo's #586). Established: `check_decisions_in_force` defers on
either `PROPOSED` or `RECOMMENDED`, both named in `NOT_IN_FORCE`.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### A coder dispatch that would not start counted as one pull request's weather

`dispatch()` caught `run_coder`'s refusal in the same `except SystemExit` arm
as the reads that belong to one pull request, and the collection that arm
appends to is the one a sweep prints and returns from rather than exiting on
(solorepo's DR-238). `gh workflow run coder.yml` is refused the same way
whichever pull request asked for it — the credential without the Actions
write, `coder.yml` disabled on the repository — so a rotation would have
appended a line for every conflicting pull request in the sweep, started no
coder pass for any of them, and left `advance.yml` green, which is the
falsifier solorepo's DR-238 wrote for itself (solorepo's #651). Established:
each `run_coder` call is caught on its own and
its refusals are returned apart from what the pull requests reported, so the
sweep dispatches for the rest and then exits naming the ones whose pass never
started.

Evidence: `.meta/checks/probes/loops/dispatch.py::dispatch_probes`

### A refused mergeability re-read ended an advance sweep mid-list

`dispatch()` called `mergeability(pull)` in three arms outside any `try`, and
that function reaches GitHub whenever the answer in hand is `UNKNOWN` — which
is what GitHub answers while it computes a merge ref, and so is routine on the
push to trunk the sweep runs on. The re-read is an ordinary `gh pr view` and
failed the ordinary way, on `net/http: TLS handshake timeout` among others, so
one pull request's weather propagated out of `dispatch()` and out of `advance()`
with it: the pull requests behind that one in the list got no dispatch on that
push, nothing rebased a conflicting branch and nothing re-delivered a verdict
until the next push found them, and the sweep was red while claiming to have
read every open pull request (solorepo's DR-238, solorepo's #655). Established:
the read happens once for each pull request an arm could act on, inside a `try`,
and a refusal is appended to what the pull requests reported so the sweep goes
on to the ones behind it.

Evidence: `.meta/checks/probes/loops/dispatch.py::dispatch_probes`

### A stranded review request the sweep could not re-request, reported green

Narrowing the dispatch arms left the other write the sweep makes on a pull
request's behalf where it was. `dispatch()` and `advance_stack()` re-request a review
whose `reviewer` check failed without a verdict or was dropped during a stack advance
(solorepo's DR-178, solorepo's DR-243), and every refusal of `request_review` went
to the printed list — including the one from `pr edit`, which needs the repository
write and which a rotated credential loses for every pull request in the sweep at
once. The repair solorepo's DR-178 put in the sweep because nothing else notices a
stranded request would have stopped running while the sweep stayed green (solorepo's #656).
Unlike the dispatch, this call has refusals a pull request does cause — a non-open state,
its branch conflicting, GitHub not showing the request after the write — so the arm
is narrowed to the write rather than to the verb: `request_review` raises
`RequestRefused` from a refused `pr edit` that wrote nothing, and the reads and
partial writes around it keep exiting as they did. Established: the sweep's exit names
a stranded or stack-dropped request it could not re-request, and still names each pull
request's own weather (including merged/closed states and non-sticking re-requests) in
the printed report.

Evidence: `.meta/checks/probes/loops/dispatch.py::dispatch_probes`, `.meta/checks/probes/loops/advance.py::advance_probes`

### An unlabelled Issue had no channel verb to move onto the roadmap

An Issue opened outside the issue form or channel arrived unlabelled, and the
channel had no verb to apply `roadmap` to an existing Issue (solorepo's #421).
Established: `roadmap()` moves an open Issue onto the roadmap, applying `roadmap`
and stripping `challenge` and difficulty labels symmetrically with `triage()`.

Evidence: `.meta/lib/move/challenges.py::roadmap`

### Advance sweep failures invisible in green CI run logs

Individual pull request advance failures were suppressed from sweep exit codes to
keep CI runs green (solorepo's DR-238), but without notification, persistent failures
(such as rebase conflicts or mergeability timeouts) remained unread by authors,
loops, and maintainers in GitHub Actions logs until someone opened the log
(solorepo's DR-255, solorepo's #646). Established: `reconcile_advance_notice()`
manages an in-place signed notice comment on the failing pull request (identified by
`<!-- solorepo:advance-finding -->`), updating it in place when error messages change
and deleting it when the branch cleanly advances. Paired with this, the Local Operator
Plane (`just sweep` and `just next`) detects and surfaces standing advance notices
prominently during local review.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### Opportunistic finish-line merge races invalidated in-flight pull requests on contested files

Opportunistic finish-line merges repeatedly invalidated in-flight pull requests on
contested files (solorepo's #652, solorepo's #721). When newer pull requests landed on
trunk ahead of older active branches sharing modified paths, the synthetic merge ref
of the in-flight pull requests was broken mid-cycle, forcing repeated rebases, CI
churn, and review starvation (solorepo's DR-258). Established: `merge_manager`
implements contention-aware queueing. An older pull request actively undergoing review
or status checks holds an active reservation window. Candidate pull requests sharing
modified files are deferred behind the active reservation, while disjoint pull
requests (`files(A) ∩ files(B) == ∅`) bypass the queue cleanly without conflict risk.
Stalled autonomous loop pull requests are demoted to draft to prevent head-of-line
blocking, and queue congestion is surfaced in `just next`.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### A squash merge GitHub had accepted but not yet shown, judged as one that failed

GitHub processes a squash merge asynchronously, so a `pr view` issued immediately
after the merge call could still answer `state: OPEN` for a merge GitHub had
already taken — observed on run 35609888922, over solorepo's #757's stack merge,
where every layer landed and the Job exited non-zero on the read-back
(solorepo's DR-158, solorepo's #773). The sibling of the `update-branch` entry above, on the
same asynchrony one endpoint over. Established: `merge()` reads the post-merge
state through `settled()` under `SETTLES` rather than through a single read, and
waits on the merge commit beside the state, since the line that reports the merge
consumes both; a merge GitHub never lands still reads `OPEN` once the wait runs
out, which the refusal below the read-back reports as it always has.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### One candidate that could not merge stranded the whole queue

`merge_manager` called `merge` on the winning candidate with nothing between
them, so a `SystemExit` from that call ended the run before `advance_stranded`
swept the other open pull requests. A candidate that never settles refuses
identically on every pass, so the queue stalled on it: solorepo's #757 held the
merge queue across sixteen consecutive scheduled runs of `merge.yml` (runs
35574165608 through 35609888922) on 2026-09-21, each one red and none of them
advancing anything else (solorepo's #776). Established: the winner's `merge` is
called inside a `try`, the refusal is printed, `advance_stranded` runs when
`stranded`, and the merge's own code is then re-raised through `sys.exit` so the
scheduled run stays red — the isolation is of the queue from the candidate, not
of the operator from the failure.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### A mergeability read that cost a cycle, and a wait that settled half of it

`check_mergeable_clean` read `pull.get("mergeable")` off the merge manager's one
`pr list` and refused a candidate answering `UNKNOWN` as though a semaphore had
failed. `UNKNOWN` is what GitHub answers while it computes the value in the
background, and `merge.yml` runs on `workflow_run` completion — seconds after the
push that invalidated every cached answer — so an approved, green candidate was
refused for the cycle and waited on the next `workflow_run` or the fifteen-minute
cron, the log naming it ineligible when it was only unread. Found reviewing
solorepo's #781 on 2026-09-21, which names the read among nine read-after-write
sites (solorepo's #784). Routing that one read through `mergeability` then broke a
second way, caught in review before it landed: the wait renewed `mergeable` and
left `mergeStateStatus` at the value of the read it was entered on, and GitHub
computes the pair together, so a branch the same push to trunk had just put behind
its base cleared the `BEHIND` refusal on a stale `UNKNOWN` and returned `mergeable
clean` — which `advance_stranded` never rebases, since it decides on a reason list
of exactly `[BEHIND_BASE]`, and which the merge manager could instead arm on an
out-of-date head. Established: `ADVANCE` names `mergeStateStatus`, `mergeability`
settles it onto the caller's pull request beside `mergeable` from the read that
answered, and `check_mergeable_clean` reads both through it — so every refusal in
that function reads two values GitHub computed at one moment, and a value still
`UNKNOWN` once the wait is spent is refused in words that say it was waited for.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### A stack merge that exited zero, merged nothing, and said so to no one

`merge()` called `gh stack merge <pr> --squash --yes` through `channel.gh` and
read the result back off GitHub, so the only account of what the call did was
`settled()`'s verdict that the pull request was still open — which is also what
a merge GitHub has not finished processing looks like. The call had in fact
been consumed by the CLI's install of the `gh stack` extension, and said so on
a stream nothing read (solorepo's #797). Established: the stack call passes
`echo=True`, so its exit status and both of its streams reach standard error
before the read-back runs, and a merge that exits 0 having merged nothing is
read off its own words.

Evidence: `.meta/checks/probes/channel/extension.py::gh_stack_extension_probes`

### A scheduled reconciler pass cancelled by the merge traffic it shared a group with

`reconcile.yml` declared `concurrency: group: merge`, the group `merge.yml`
declares, because both run the merge manager and two merges in quick succession
must serialize. GitHub holds at most one pending run per concurrency group and
cancels the waiting one when a third arrives, so the group bought that exclusion
by throwing runs away. On 2026-09-22 the reconciler's 21:38 pass, run
35787817254, was cancelled with no job started while solorepo's #828 was landing,
and `merge.yml` fired four more times between 21:40 and 21:43. What the
cancellation dropped was not a merge, which the next push brings round anyway,
but every act the reading pass performs — a rebase dispatched, a review requested
again, a dead claim released — and it dropped them silently, a run cancelled
before any job starts printing nothing (solorepo's #850). Established: the two
workflows are in concurrency groups of their own, and the exclusion the shared
group was providing is a lock the manager takes for itself on
`refs/tags/merge-manager-lock`, created with the compare-and-set `move mint`
reserves a Decision number with (solorepo's DR-267). A manager meeting a held
lock declines rather than waits, and a lock whose holder has stopped is broken by
a delete and that same create rather than by a force-`PATCH` read back
afterwards, which is no compare-and-set at all. The break is not one either,
GitHub offering a precondition on neither operation: it leaves the ordering in
which one breaker's delete lands after another's create, which is stated wherever
the break is described rather than asserted away.

Evidence: `.meta/checks/probes/loops/merge_lock.py::merge_lock_probes`

### Unmergeable pull requests blocked queue throughput on merge refusal

`merge_manager` caught a winning candidate's `merge` failure and advanced
stranded branches, but left the failed candidate open and in ready state on
GitHub with no diagnostic comment on the conversation timeline (solorepo's #776).
Because approved pull requests were exempt from changes-requested stall eviction
under solorepo's DR-258 and the candidate remained green, subsequent cycles
repeatedly re-selected it as the highest-leverage candidate, producing
head-of-line blocking across scheduled runs until a human intervened (solorepo's #780).
Established: pre-merge read inspection via `pull_requests.stacked` runs outside
the mutation `try` block so transient GitHub API read errors are never treated as
merge refusals. When `pull_requests.merge()` refuses a candidate or raises
`SystemExit`, `merge_manager` catches the exit, reconciles an in-place failure
diagnosis notice on the pull request conversation via `advance.reconcile_notice`
(solorepo's DR-255), pruning surplus notice comments to enforce the single standing
notice invariant while scanning all comments across the conversation in
`find_active_merge_refusal`. Because repeating a squash-merge
against an unchanged head commit cannot succeed at the final gate and blocks queue
throughput across cycles, autonomous loop candidates demote to draft status via
`demote_to_draft`, and their Challenge is handed back to `human` via `move stop`
under an attributable signed trailer (solorepo's DR-112, solorepo's DR-233,
solorepo's DR-258) to alert a maintainer rather than silently stranding the draft.
Active merge refusal notices suppress draft restoration until a new commit changes
`headRefOid`, while surfacing standing refusal notices prominently across the Local
Operator Plane in `just next` and `just sweep` (solorepo's DR-255). Remaining
candidates are swept via `advance_stranded()`, and the refusal exit code is re-raised
so the workflow run surfaces the failure.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### Branch behind its base with a refused replay owed a rebase by no reader

`gh pr update-branch --rebase` can be refused on a branch GitHub still reports
as `mergeable: MERGEABLE`: the mergeability answers whether the head merges
into the base, while the update replays the branch's commits onto it, and the
two can disagree. Nothing read the difference. The merge manager called the
pull request ineligible on `mergeStateStatus: BEHIND`, `advance` reported the
refusal in a notice nobody else read, and the reconciler's rebase arm turned
on `CONFLICTING` alone — so the branch was owed a pass by no reader and stood
until it was rebased by hand (solorepo's #805, behind solorepo's #853).
Established: `advance.stalled_behind` is the one reading, taken off the pull
request as the listing already holds it — `mergeStateStatus: BEHIND` beside a
standing advance notice tagged `replay-refused head:<oid>` against the current
`headRefOid`. The tag is what narrows the marker to the state the predicate is
named for: a sweep posts one notice per pull request for whatever it reported,
and only the head that did not move within the wait and the head still behind
after the update are a refused replay — from `_advance_single_pull` for a
branch advancing on its own and from `pull_requests.advance_stack` for a layer
advancing with its stack, so a stalled layer above a clean root is admitted
too. A refused mergeability read, an arming lost after a successful update and
a `gh stack` sequence that raised are not. `reconcile._owed_stalled`
owes that branch the coder's rebase pass, held above a conflicting lower layer
on solorepo's DR-133's terms, and `move dispatch --task rebase` admits it by
hand beside a conflicting one. `RECONCILE_FIELDS` and `dispatch_pass` both
carry `comments`, which `pr list` answers for every pull request at once, so
the reading costs no read of its own.

Evidence: `.meta/checks/probes/loops/reconcile.py::reconcile_probes`

### A pending review request asked again, starting a second run on the head one already stood on

`review.yml` runs on `synchronize` while a review request is pending, and PR
First tells the coder to request review after a push, so the push starts one
run and the re-request seconds later starts another. The concurrency group
cancels an in-progress run only on `synchronize`, so the second is not
cancelled: it waits the first out and then reviews the same commit, holding a
self-hosted runner (solorepo's DR-137) to post a verdict saying nothing had
changed since the last one. That is what happened on solorepo's #934 at head
`f46a2df`, where three runs answered one request (solorepo's #950).
Established: `pull_requests.reviewing` reads what already answers a standing
request before `request_review` withdraws and re-adds it — a `review.yml` run
listed on the current head that has not completed, or one that has, with the
Role's verdict standing at that head, which is read from the reviews endpoint
because `pr view --json reviews` carries no commit. Either leaves the request
as GitHub holds it. A request nothing answers is stale rather than pending —
the run at this head finished without that verdict, or the push moved the head
off the run that ran — and so is a listing GitHub refuses, since a duplicate
run costs a runner and a review never delivered costs the branch. What
`is_verdict` drops is dropped here too: GitHub wraps every raise and every
reply in a bodiless review carrying the head's commit (solorepo's DR-118), so a
run that raised threads and died before its verdict would otherwise read as one
that gave it.

Evidence: `.meta/checks/probes/loops/handoff.py::handoff_probes`

### A wrapped `**Waits on.**` line left its remainder standing beside its replacement

The line is one line in the form and several in a body an editor wrapped, and
`WAITS_LINE` read only as far as the first newline. `move waits` rewrote that
first physical line and left the rest of the paragraph where it was, so
`**Waits on.** #2 and\n#3.` under `--off 3` became a line citing `#2` with `#3.`
standing under it, citing a blocker the relationship no longer held
(solorepo's #957). Established: `WAITS_LINE` runs to the blank line, the next
bold heading or the end of the body, every terminator admitting a carriage
return, and `common.cited_waits` reads the citations off that same span, so the
guard in `file_issue` that refuses a citation `--blocked-by` omits reads the
text the rewrite will replace rather than its first line.

Evidence: `.meta/checks/probes/channel/waits.py::waits_probes`

### A clause refusal raised where there was no sentence to sever and no rewrite to make

`retarget_waits` refused any line whose prose opened with one of
`CLAUSE_OPENERS`, which holds ordinary sentence openers — `all`, `both`, `each`,
`when` — so `**Waits on.** All three seed repositories being migrated` was
refused as a severed clause on a line citing nothing, the free-standing prose
blocker solorepo's DR-170 preserves. The same refusal exited before `waits`
reached its no-op short-circuit, so repeating a call that had already settled
both records failed instead of reporting them settled, which is the recovery
`channel.act`'s read-back of both records exists for.
Established: `common.severed_clauses` reads no clause on a paragraph citing no
Issue, `retarget_waits` rewrites and refuses nothing, and each caller refuses in
its own words after testing what its own call would change — `file_issue`
naming the body on stdin, since at filing there is no Issue to revise.

Evidence: `.meta/checks/probes/channel/waits.py::waits_probes`

### A continuation clause read as a blocker because its first word was not on a list

`severed_clause` called a `**Waits on.**` comma segment a continuation of the
citations beside it only where the segment opened with one of the twenty-one
words in `CLAUSE_OPENERS`, or cited an Issue of its own. A segment doing
neither read as a free-standing prose blocker and was re-emitted ahead of the
citations it explained, which is the reordering solorepo's #957 exists to stop:
`**Waits on.** #950, open until the schema lands` under `--on 950,952` became
`**Waits on.** open until the schema lands, #950, #952`, the citations reading
as an afterthought to a sentence fragment they began. No list closes this,
since the next word it lacks is the next line someone writes.
Established: the reading is structural. `waits_line` renders prose ahead of the
citations however the source line ordered them, so `severed_clause` takes where
the segment stands — a segment after a citation is a continuation whatever its
first word — and `CLAUSE_OPENERS` is gone with the lexical reading. Prose
standing *before* every citation and carrying none is a blocker of its own,
which is the free-standing `Decision DR-041, #2` solorepo's DR-170 preserves,
and the paragraph citing nothing at all needs no exception to be admitted. One
carrying a citation is severed wherever it stands, since the rewrite renders
that citation a second time from the relationship.

Evidence: `.meta/checks/probes/channel/waits.py::waits_probes`

### A draft rebased by advance, its Seed Commit replayed away

`_is_advance_candidate` read a pull request as a candidate whenever it was
armed or approved, and said nothing about drafts. A plan-only draft changes no
file against its base, so the server-side rebase replayed its Seed Commit away
and left GitHub nothing ahead of the base, which closed the pull request:
solorepo's #974 went that way on Challenge solorepo's #967, taking with it the
reviewer's approval of the plan, the second of the two gates a `hard` Challenge
passes before any code (solorepo's DR-273, solorepo's #998). Established: the
draft is refused ahead of every other arm of the filter, so a sweep passes it
over and reports nothing; and `_no_candidate_reason` refuses a named draft in
words of its own, because the general sentence — nothing has asked it to land —
is false about a draft the reviewer approved and names a remedy already taken.
The carve-out is the filter's alone: a draft that is a layer of a stack still
moves with the stack, and `advance(pr, held=True)` skips the filter outright.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### An approved loop pull request refused rebase or held because its challenge was handed back

When a coder agent stopped work on a Challenge due to an external blocker (`move stop`),
the Challenge was demoted to `human` (`IssueState.HANDED_BACK`). Even after the blocker
resolved and the pull request on that loop branch was reviewed and approved
(`standing_verdict: APPROVED`), the advance sweep (`_is_autonomous_challenge`) and
reconciler (`owed_by_pull`, `_held_above`) checked whether the Challenge was `RESUMABLE`
(solorepo's #1019). Because the Challenge remained labeled `human`, `_dispatch_conflicting`
refused to trigger coder rebase passes (`left #<pr> alone: #<issue> is at a level no loop takes`)
and `reconcile` held the pull request as the solo's.
Established: an approved pull request has completed its creative authoring phase.
Mechanical maintenance (rebasing against trunk under `NEEDS_REBASE` or `READY_TO_MERGE`) is
admitted as loop agency in `_is_autonomous_challenge`, `owed_by_pull`, and `_held_above`
even when its parent Challenge is in the hand-back state (`HANDED_BACK`).

Evidence: `.meta/checks/probes/loops/dispatch.py::dispatch_probes`

### Conflicting pull request dispatched for coder rebase without returning to draft

When an open pull request conflicted with its base, the reconciler and advance sweep
dispatched coder rebase passes while leaving the pull request ready for merge (solorepo's #1024).
Because `.github/workflows/review.yml` is guarded to run only on draft pull requests,
the coder's subsequent push resolving conflicts bypassed reviewer triggering, stranding
the review semaphore and risking unreviewed rebased code progressing toward merge in violation
of solorepo's DR-273.
Established: conflicting pull requests are demoted to draft via `manager.demote_to_draft`
prior to coder rebase dispatch in `_dispatch_conflicting`, `dispatch_pass`, and
`reconcile.perform`, while non-conflict maintenance rebases retain their state.

Evidence: `.meta/checks/probes/loops/advance.py::advance_probes`

### Reviewer approval validity across clean rebases

`check_reviewer_approval` in `.meta/lib/move/manager/ranking.py` accepted an `APPROVED`
review regardless of head commit, merging pull request solorepo's #905 on an approval
given prior to two rebases (solorepo's DR-288, solorepo's #948). Established: a clean
rebase onto trunk preserves standing `APPROVED` verdicts so long as the branch remains clean
and passes required gate status checks, avoiding review churn and merge-queue starvation.

Evidence: `.meta/checks/probes/loops/merge_manager.py::merge_manager_probes`

### A draft layer in an advancing stack preserved its Seed Commit

The candidate filter held out individual draft pull requests from server-side
rebase, but a draft that was a layer of a stack was still reached when trunk
moved because `gh stack rebase --upstack` operates across the stack unfiltered:
the rebase could replay a zero-diff Seed Commit away, closing the draft pull
request and losing reviewer approval of the plan (solorepo's DR-273,
solorepo's #1006). Option A settled the trade: `channel.gh` sets
`rebase.empty = keep` in the git environment for `gh stack rebase` calls,
so cascading stack rebases preserve empty Seed Commits across draft layers
and allow the entire stack to advance cleanly.

Evidence: `.meta/checks/probes/channel/extension.py::gh_stack_extension_probes`

### Opening a pull request did not request review automatically

Opening a pull request with `move open` created the pull request without
requesting review, requiring authors to run `move request-review` as a separate
command to signal handoff (solorepo's #1042). Established: `open_pull_request`
atomically requests review from the reviewer role upon creation.

Evidence: `.meta/checks/probes/loops/handoff.py::handoff_probes`


