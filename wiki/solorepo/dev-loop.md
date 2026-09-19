---
slug: dev-loop
context: solorepo
synonyms:
  - development loop
  - autonomous loop
  - loop machinery
minted: 2026-09-14
---

# Dev Loop

**Dev Loop** is the event-driven autonomous execution cycle that advances a [[challenge]] from triage to merged pull request through decoupled coder, reviewer, and merge manager passes without continuous human supervision (solorepo's Article 15, solorepo's DR-111, solorepo's DR-112, solorepo's DR-178).

It is the operational engine realizing the [[pr-first]] discipline. Rather than relying on interactive hand-offs, manual review coordination, or continuous human intervention, the development loop advances work through autonomous agents that each react to GitHub webhook events under their own rules, with no coordinator holding the process (solorepo's DR-214). The repository itself acts as the single source of truth, using open pull requests, review verdicts, and branch naming conventions as stateful coordination semaphores.

## The Decoupled Pass Lifecycle

Work progresses through five specialized, asynchronous passes triggered by repository events:

0. **Triage Pass:** Activated when `challenge` lands on an [[issue]] carrying no difficulty, or a difficulty is taken off one (solorepo's DR-230). The reviewer role reads the [[challenge]] against the form and the tree, posts a verdict naming what it checked, and lands the difficulty, which is the label the Coder Pass fires on. A level landed with the filing is the solo's verdict given in advance and skips this pass.
1. **Coder Pass:** Activated when an [[issue]] is labeled with an autonomous difficulty (`easy` or `medium`), or when a pull request review requests changes (solorepo's DR-112). The coder role claims the [[challenge]], creates or updates the working branch, drives quality checks to green, records changes via signed channel commits, and requests review.
2. **Reviewer Pass:** Activated when a pull request review is requested (solorepo's DR-109). The reviewer role performs an independent verification of the diff against repository disciplines, assertions, and conventions. The review depth pipeline dynamically calculates model capacity, extended thinking depth, and agent fan-out ceiling based on touched paths (solorepo's DR-188).
3. **Advance & Merge Manager Pass:** Continuously evaluates open pull requests when `main` moves or auto-merge conditions are met. It automatically rebases clean branches onto updated trunk heads (solorepo's DR-133) and squashes and merges approved candidates in order of structural leverage (solorepo's DR-161).
4. **Sweep Pass:** Periodically scans the repository for residue branches whose remote heads have merged or closed, reporting cleanup commands to preserve repository hygiene.

## Coordination via Branch Prefixes and Semaphores

The development loop operates without a centralized orchestrator database. State is tracked deterministically in git and GitHub metadata:

- **Branch Names Reflect Chosen Harnesses:** Working branches created by the loop follow the canonical naming pattern `<harness>/issue-<n>` (for example, `claude/issue-414` or `codex/issue-414`). Rather than reading the branch name to select a harness (solorepo's DR-242), the coder workflow determines the harness exclusively from explicit pull request labels (`harness:<harness>`) or manual dispatch inputs, defaulting to Claude Code, and then records the selected harness as the branch prefix.
- **Loop vs. Human Demarcation:** The branch prefix distinguishes autonomous loop work from human maintenance branches. When a reviewer requests changes on a `(claude|codex)/issue-*` branch, the verdict acts as an operational semaphore that automatically awakes the coder pass to remediate the diff. On human branches, the verdict remains an advisory review informing the author.
- **Challenge Recovery for Hand-Back:** Embedding `issue-<n>` into the branch ref guarantees that if an autonomous pass cannot complete its remit, it can reliably extract the originating [[challenge]] number from the git ref and execute the hand-back protocol.

## Concurrency Keys and What They Hold

Each loop workflow declares a `concurrency` group, and the group's expression
decides which deliveries of an event may run beside each other and which are
dropped. GitHub settles the group and the cancellation from the `github`,
`inputs` and `vars` contexts — the only ones the expression may use — and admits
one running and one pending run per group:

> This means that there can be at most one running job or workflow in a
> concurrency group at any time. When a concurrent job or workflow is queued, if
> another job or workflow using the same concurrency group in the repository is
> in progress, the queued job or workflow will be `pending`. By default, any
> existing `pending` job or workflow in the same concurrency group will be
> canceled and the new queued job or workflow will take its place.
>
> — GitHub, [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency)

A key is therefore a statement about what the loop may lose. Losing the wrong
delivery is silent: a dropped verdict produces no failure, no red check and no
notification, so the loop simply stops and the solo finds out by looking. That
is what solorepo's #102 was.

### The Coder Key

[`.github/workflows/coder.yml`](../../.github/workflows/coder.yml) groups on a
subject and a shape, and cancels nothing that is already running:

```yaml
group: coder-${{ github.event.issue.number || github.event.pull_request.number || inputs.pull_request }}-${{ github.event.review.state || (inputs.task == 'rebase' && 'rebase') || (inputs.pull_request && 'changes_requested') || 'take' }}
cancel-in-progress: false
```

**The invariant: no delivery is dropped while the work it carries is undone.**
The key names the pass a delivery would run — the [[challenge]] or
[[pull-request]] it would act on, and which of the four passes it would be — and
that naming buys two properties:

1. **Separation.** Two deliveries that would run different passes never share a
   group, so neither can displace the other.
2. **Coalescence.** Two deliveries that would run the same pass on the same
   subject do share a group, and the survivor does the dropped delivery's work,
   because each pass reads the state that holds when it runs rather than the
   payload frozen at delivery. A difficulty moved while a run waits is the level
   the run takes (solorepo's #117); a rebase pass reads `origin/<base>` when it
   starts; an answering pass reads the threads that are unanswered then.

Because `cancel-in-progress` is `false`, the only delivery the key ever drops is
a *pending* one, and only for a newer delivery of the same shape on the same
subject. What the invariant excludes is solorepo's #102's shape: a verdict
cancelled while pending by a delivery that will not answer it, leaving a request
for changes standing with no [[job]] to take it.

The claim is about drops and not about mutual exclusion. Separation lets two
different passes on one pull request run at the same time — an approval's
promotion beside a dispatched answer, say — and the key neither excludes that
nor pretends to. What it excludes is one pass cancelling another.

### The Event Shapes That Reach the Coder

Three triggers reach the workflow, and the subject segment resolves to whichever
of its three operands the payload populates. A repository issues Challenge and
pull request numbers from one run of numbers — solorepo's #470, #471 and #472
are Challenges where solorepo's #467 and #475 are pull requests — so a subject
segment names one subject and never two.

| Delivery | What the payload carries | Branch of the shape chain | Group | The pass it runs |
|---|---|---|---|---|
| `issues`, `labeled` | `github.event.issue`, `github.event.label`; no `pull_request`; no `inputs` | fourth, the literal `take` | `coder-<issue>-take` | take the Issue |
| `pull_request_review`, `submitted`, state `approved` | `github.event.review`, `github.event.pull_request`; no `inputs` | first | `coder-<pr>-approved` | promote on approval (solorepo's DR-159) |
| `pull_request_review`, `submitted`, state `changes_requested` | as above | first | `coder-<pr>-changes_requested` | answer the review (solorepo's DR-112) |
| `pull_request_review`, `submitted`, state `commented` | as above | first | `coder-<pr>-commented` | none: the job admits only `changes_requested` and `approved` |
| `workflow_dispatch`, `task: review` | `inputs.pull_request`, `inputs.task`; no `review` | third | `coder-<n>-changes_requested` | answer the review |
| `workflow_dispatch`, `task: rebase` | as above | second | `coder-<n>-rebase` | rebase onto the base (solorepo's DR-133) |

Four facts about GitHub settle that table.

- **The `inputs` context does not exist on the other two triggers.** It "is only
  available in a reusable workflow or in a workflow triggered by the
  `workflow_dispatch` event"
  ([Contexts reference](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#inputs-context)),
  so an `issues` or `pull_request_review` delivery cannot take the second or
  third branch whatever a dispatch would have put there.
- **`&&` and `||` yield an operand, not a boolean.** GitHub writes the same form
  in its own reference — `image: ${{ options.nginx == true && 'nginx' || '' }}`
  — and documents `group: ${{ github.head_ref || github.run_id }}` as the
  fallback for a property "only defined on `pull_request` events". Falsy values
  are "`false`, `0`, `-0`, `""`, `''`, `null`"
  ([Expressions reference](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions)),
  so an absent property falls through and `(inputs.task == 'rebase' &&
  'rebase')` contributes a falsy `false` whenever the task is not a rebase. The
  chain's last operand is a literal, so the shape segment is never empty.
- **Case does not enter the key.** The review state reaches the group exactly as
  the payload spells it, and both readings of it are case-blind: "GitHub ignores
  case when comparing strings" (Expressions reference), and "The concurrency
  group name is case insensitive. For example, `prod` and `Prod` will be treated
  as the same concurrency group" (Workflow syntax reference).
- **A reply on a [[review-thread]] is a submitted review too**, carrying the
  state `commented` and no verdict, which is why the state is in the key at all.
  Evidence: the ten answers posted to the pull request at solorepo's #467 on 2026-09-17 produced
  ten `pull_request_review` deliveries between 14:28:02Z and 14:28:33Z (runs
  `35233746673` through `35233808445`), each creating a coder run whose job
  declined and none cancelling a verdict. Keyed by number alone, each of those
  replies would have shared a group with a verdict on the same pull request.

Which copy of the workflow decides the key differs by trigger, because
`GITHUB_REF` does. On `pull_request_review` GitHub gives `GITHUB_REF` as "PR
merge branch `refs/pull/PULL_REQUEST_NUMBER/merge`" and `GITHUB_SHA` as "Last
merge commit on the `GITHUB_REF` branch", so a verdict is keyed by the pull
request's own copy of the file and a change to the key governs the first verdict
on the pull request that makes it. On `issues` the values are "Last commit on
default branch" and "Default branch", and the event "will only trigger a
workflow run if the workflow file exists on the default branch"; on
`workflow_dispatch` they are "Last commit on the `GITHUB_REF` branch or tag" and
"Branch or tag that received dispatch"
([Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)).
A change to the take key is therefore in force only once it has landed on trunk.

### The Review Key

[`.github/workflows/review.yml`](../../.github/workflows/review.yml) groups on
the pull request alone and puts its variation in the cancellation:

```yaml
group: review-${{ github.event.pull_request.number }}
cancel-in-progress: ${{ github.event.action == 'synchronize' && github.actor != format('{0}-{1}-reviewer', github.repository_owner, github.event.repository.name) }}
```

**The invariant: a review run is alive exactly while the question it was asked
is still the current one.** One run reviews one pull request, and it ends early
only when the head under it moves by an act that is not the reviewer's own. The
key needs no shape segment because the workflow runs one pass; the shape
question it does face is not *which* pass but *whether an arrival invalidates
the pass in flight*, and that is what the conditional answers.

| Delivery | `cancel-in-progress` | What happens to a run in flight | The job's own condition |
|---|---|---|---|
| `review_requested` naming the reviewer's account | `false` | left alone; the arrival waits behind it | runs |
| `review_requested` naming any other account | `false` | left alone | declines |
| `synchronize` by any account but the reviewer's | `true` | cancelled; the arrival reviews the new head | runs if a request of the reviewer is still outstanding |
| `synchronize` by the reviewer's account | `false` | left alone | runs if outstanding |

The condition sits on `cancel-in-progress` rather than in the job because
cancellation is settled without reference to any job: the expression may read
only `github`, `inputs` and `vars`, none of which can see a job's outcome, and a
delivery whose job will decline has already acted on the group by the time it
declines. An unconditional `cancel-in-progress: true` would let a review request
naming the solo kill the review it then declines to be. The actor is the right
test for "whose doing": `github.actor` is "the username of the user that
triggered the initial workflow run" (Contexts reference), which on a
`synchronize` is the account that pushed.

Two further facts of the substrate shape this pass. Workflows "will not run on
`pull_request` activity if the pull request has a merge conflict", so a request
outstanding on a conflicting branch is answerable by nobody until a rebase moves
the branch — which is the whole reason `.meta/say/move advance` dispatches the
rebase pass (solorepo's DR-133). And a `pull_request` run reads the workflow
file from the merge ref, so a review runs under the pull request's own copy of
`review.yml`.

### Residuals

The first two are judgements about what is acceptable to lose rather than
defects. The third is a case the expressions do not cover, found while writing
this account.

1. **A third rebase dispatch cancels the one waiting.** Two merges on the base
   in quick succession dispatch twice, leaving one run standing and one pending;
   a third replaces the pending one. Nothing is lost, because a rebase pass
   reads `origin/<base>` when it starts rather than the base as of its dispatch,
   so the survivor moves the branch onto everything the dropped deliveries would
   have moved it onto, and a branch already current is one the pass leaves
   alone.
2. **A `raise` in the cancellation window anchors to the head it finds.** A
   review comment posted between a head move and the runner acting on the cancel
   hangs on the new head although the run read the old one. What is lost is not
   a verdict but the guarantee that a posted point was read against the head it
   anchors to, and the window is the seconds between a push and a cancellation.
3. **The take shape does not separate a delivery that takes from one that
   declines.** Unlike the two above, this one the comments do not record.
   `take` is the chain's default, so *every* `issues` delivery lands on it,
   including deliveries for labels the job declines — `challenge`, `roadmap`, a
   `harness:` label. One pending slot per group then admits a loss the other
   shapes cannot reach: where a declining delivery arrives while a sibling
   delivery's run is still in progress and a difficulty delivery is pending
   behind it, the difficulty delivery is cancelled and replaced by one that
   skips, and nothing takes the [[challenge]] until a label moves again. Two
   labels in one act cannot reach it, because the second delivery has nothing
   behind it to displace; three can, and GitHub orders them only loosely —
   "ordering is not guaranteed". How close such deliveries land is visible in
   the Challenge at solorepo's #473, whose two `labeled` deliveries created runs `35242844586` and
   `35242844314` in the same second. Whether to close this or accept it belongs
   to solorepo's #472, which holds the change to these expressions.

## Harness Agnosticism and Subscription Economics

Solorepo decouples engineering disciplines from any specific model vendor (solorepo's DR-111). A Role is a dedicated machine account with its login and credential file derived from the Role name (solorepo's DR-107), while a harness (Claude Code, OpenAI Codex) is the interchangeable execution container running inside the workflow.

While multi-harness fallback to Gemini CLI was adopted to heal transient Claude Code crashes (solorepo's DR-178), differing authentication models introduced severe economic hazards: Claude Code authenticates via personal flat-rate user subscriptions (`CLAUDE_CODE_OAUTH_TOKEN`), whereas headless Gemini CLI required a utility-metered `GEMINI_API_KEY`, routing deep multi-turn loop sessions to unexpected Google Cloud pay-as-you-go bills. After initially gating fallback behind an opt-in toggle (solorepo's DR-240), Gemini CLI and secondary fallback steps were excised from autonomous workflows (solorepo's DR-242).

Autonomous loops execute on subscription-backed Claude Code, with OpenAI Codex available by explicit label. Re-introducing Gemini is deferred until personal subscription credentials can be mounted directly into self-hosted Actions Runner Controller (ARC) runner pods to drive the containerized Google Antigravity command-line interface without pay-as-you-go API keys (solorepo's DR-242).

## The Graceful Hand-Back Invariant

An autonomous loop must never silently abandon work or loop indefinitely when blocked (solorepo's DR-112). 

When a coder pass encounters conditions beyond its capability—such as an architectural decision requiring human judgement, a quality gate check that refuses to pass, or complex merge conflicts on rebase—it must stand down gracefully. The loop relabels the [[challenge]] as `human`, posts a diagnostic explanation to the pull request thread describing the obstacle encountered, and terminates execution. This leaves the pull request open and cleanly documented for the solo maintainer to resume.

---

**See also:** [[pr-first]], [[knowledge-management]], [[ubiquitous-language]], [[challenge]], solorepo's DR-107, solorepo's DR-111, solorepo's DR-112, solorepo's DR-133, solorepo's DR-161, solorepo's DR-178, solorepo's DR-188, solorepo's DR-214, solorepo's DR-240, solorepo's DR-242.
