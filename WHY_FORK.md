# Why solorepo forks

This document explains why solorepo is being forked and what the fork is for.
It records why PR First, the delivery discipline, is being abandoned, and the
reasoning behind the local pair-programming loop that replaces it. It also
records what a later cross-repository "cockpit" must do, and what was learned
from surveying other meta-harnesses.

It is written out of band on purpose. It is not a Decision Record or a wiki
page, and it follows none of the conventions PR First imposed. In the fork,
solorepo's own disciplines turn its content into proper artifacts: Decision
Records, wiki pages under the Diátaxis compass, and Ubiquitous Language
entries.

## 1. Why fork

The fork gives permission to remove PR First completely: its verbs, its
vocabulary, its Decision Records, its workflows, and the instructions that
dominate `AGENTS.md`. Superseding it here, one Decision Record at a time,
would carry its history into every page that mentions delivery, and every
reader would keep paying for that history.

This repository stays as the historical record. The fork keeps no account of
PR First, not even as history. It starts from this document and from the
findings of the booktutor spike (section 8).

## 2. Why PR First has to die

### How it worked

PR First ran as a **choreography**: nothing coordinated the parts; each part
reacted to events on GitHub. Seven GitHub Actions workflows acted as "doors":

| Workflow | Fired on | What it did |
|---|---|---|
| `coder.yml` | difficulty labels, a request for changes, a comment reading `Approve decomposition` | started a coder agent |
| `review.yml` | a review request on a draft pull request | started a reviewer agent |
| `triage.yml` | a label added or removed | started the reviewer to read a Challenge |
| `reconcile.yml` | a cron every 15 minutes | re-delivered events GitHub had dropped |
| `advance.yml` | a push to `main` | rebased pull requests that had fallen behind |
| `merge.yml` | a push to `main`, a finished gate or review | ran the merge manager |
| `gate.yml` | pull request events, and a cron every 30 minutes | ran checks and published pull request status |

Each door started an agent from cold on a self-hosted runner pool (Actions
Runner Controller, 0 to 12 runners). Every run did the following:

- checked out the repository;
- ran `apm --reconcile`;
- rendered a prompt from a template;
- chose a harness from a fallback chain;
- passed through "before", "between" and "after" door scripts.

The state of the work lived in GitHub labels, assignees, review requests and
review threads. The `.meta/say/move` program changed that state (about 25
verbs), and `.meta/say/post` spoke on GitHub (about 10 verbs). A session
waited on its pull request by polling GitHub every 60 seconds
(`check_pr --watch`).

### What it cost

- **A cold start on every hand-off.** Each turn of work was a new process on a
  new runner, with a new prompt, so each one discarded the prompt cache.
- **GitHub round-trips and polling** on every transition.
- **A reviewer who wrote English instead of code.** It described fixes that the
  coder then had to understand and make in a separate run.
- **Rebases and answers to review as separate runs,** each with its own cold start.
- **A signed-channel hook that blocked even read-only `gh` calls.** During the
  analysis behind this document, it stopped both a research agent and the main
  session from reading a GitHub repository.

### The deeper failure

In a choreography the participants must know the state machine and drive it
themselves. The agents were expected to set labels, request reviews, answer
and resolve threads, mark drafts ready, and cite a mandate before setting a
difficulty. They got stuck on protocol state that should never have been part
of the model:

- decisions that waited for approval;
- semaphore labels;
- difficulty mandates;
- plan gates on empty pull requests;
- review requests that had gone stale.

Whenever an agent failed to follow an instruction, the work stalled.

The record shows the pattern. Each of these Decision Records patched the
mechanics after one more failure:

- solorepo's DR-112 (A difficulty label is the raiser's estimate, one workflow takes an Issue by it, and a loop that cannot finish hands it to the solo)
- solorepo's DR-148 (A session's claim on an Issue a loop takes is refused, and the refusal names the move to `hard` that takes the Challenge)
- solorepo's DR-214 (Coordination is what GitHub records, not what git history carries)
- solorepo's DR-226 (A difficulty label routes an Issue to whoever answers it, and a Job may hand a Challenge back at any point)
- solorepo's DR-230 (The reviewer reads every Challenge before a coder takes it, and its verdict is the difficulty label)
- solorepo's DR-235 (A run lands no level on a Challenge but `human`, and `move reread` takes a level off one)
- solorepo's DR-236 (A mechanical fix within the branch's reach is an Incidental Commit, not an Issue)
- solorepo's DR-248 (Formalize pull request state machine and watch handoff semaphore)
- solorepo's DR-249 (Settle the approach before code on hard and human Challenges, with diff review for easy and medium)
- solorepo's DR-265 (Read a comment verdict with a thread owed an answer as a request for changes)
- solorepo's DR-269 (Prohibit pre-PR implementation edits on hard and human Challenges and codify seed commits)
- solorepo's DR-273 (A plan passes two gates, on a draft that nothing lifts while it changes no file)
- solorepo's DR-278 (A level a session lands is refused unless `--mandate` quotes the solo asking for it)
- solorepo's DR-286 (A comment already said is corrected or withdrawn by the account that said it, and no body may type a Trailer of its own)
- solorepo's DR-287 (A pull request stays draft until its final reviewer approval)
- solorepo's DR-289 (A promoted thread may be resolved by the same Actor session via its promotion link)
- solorepo's DR-291 (Move open omits automatic review requests on easy Challenges, and the reviewer reviews whenever requested)
- solorepo's DR-292 (Every hard Challenge is decomposed into reviewer-triaged child Challenges before autonomous execution)
- solorepo's DR-296 (Reviewer approval on a draft settles a leaf plan without obligatory solo approval in session)

### The taxonomy of work

The ontology of work (Actor, Agency, Job, Role, Capability, Challenge and
related classes) was an attempt to build a meta-harness from first
principles, out of familiar paradigms. It failed together with PR First. The
vocabulary it produced is now clutter that every reader of `AGENTS.md` has to
work through: Door, Choreography, Dev-loop, Seed Commit, Handoff, Claim,
Incidental Commit.

## 3. What survives

These parts of solorepo work, and the fork keeps them:

- **The Diátaxis compass and knowledge management:** the `wiki/` and the routing
  of each kind of prose to its proper home.
- **The Ubiquitous Language,** with one wiki page for every term.
- **Technical writing and literate programming.**
- **The `wikisplain` and `search` tools.**
- **The gate contract.** solorepo's Article 21 says a gate reports each step in
  one shape (`ok`, `x` or `?`, then the step, then what it covered, found, or
  could not do), so that anyone who can read one Project's gate can read
  every other's.
- **The bootstraps.**
- **Distribution through APM,** solorepo's DR-206 (Solorepo packages its
  cognitive layer for APM distribution via GitHub Releases).

Consistent quality across the bootstraps still matters, but it helps
brownfield products more as a **reference and an audit** than as something
imposed. The audit compares an existing product with the reference, and each
gap it finds becomes a backlog item. A greenfield product still gets a gate
on its first day from a bootstrap.

## 4. The new delivery paradigm

**A repository is the unit of parallelism.** Within a repository, work is
serial, one issue at a time. Parallel work happens across repositories.

**Pair programming, not a coder and a reviewer.** Two long-lived harness
sessions (the *seats*) take one issue from the backlog to `main`, taking
turns. Both seats write code. When the second seat finds a problem, it fixes
it rather than describing it.

**The seats do not know a protocol exists.** On each turn a seat is told
three things: the issue file, what the other seat changed, and what the
current stage is for. It sets no flag, runs no hand-off command, and asks
nobody for approval. A deterministic program, the *supervisor*, works out
every transition from facts it can observe for itself:

- which directory holds the issue file;
- `git status` and `HEAD`;
- the exit code of the gate.

This answers section 2 directly: an agent that ignores an instruction can no
longer stall the state machine, because the state machine asks nothing of it.

**Agreement is a quiet turn.** A *quiet turn* is one that changes nothing.
When a quiet turn follows a turn that did change something, the second seat
has seen the change and let it stand. The stage then advances if its
requirement holds: a difficulty is set, a plan is written, or the gate
passes.

**Sending an issue back is a consequence, not a verdict.** If a seat judges
that the issue cannot be done as written, it adds a "Needs elaboration"
section saying why, and the supervisor moves the file back to the roadmap.
Nobody rules on the other seat's work.

**The board is a set of directories, and `git mv` moves issues between
them.** The board lives in `issues/` at the repository root, and its
directories are `issues/roadmap/`, `issues/backlog/`, `issues/todo/`,
`issues/in-progress/`, `issues/desk-check/` and `issues/done/`. The buckets are
worth having from the first day, because moving a file with `git mv` keeps the
board and the history consistent. (The booktutor spike first called the
top-level directory `work/`. It was renamed because everything else already
called the unit an *issue*.)

- **Adding to the backlog never interrupts anything.** Each issue is its own
  file, and its filename slug is its id, so no number has to be reserved. The
  loop reads the backlog from the `main` ref, so an item exists once it is
  committed there.
- **A `human` item gets a desk check.** An item at difficulty `human` waits for
  the solo to check it before it merges.
- **A `hard` item is split by the pair.** The pair writes the child items as new
  files. There is no approval step.

**Front matter holds only what cannot be observed or derived:**
`difficulty`, and optionally `waits_on` and `parent`. The directory gives the
state. Git gives the round count, the branch, and the commit that landed the
issue.

**The seats run the vendors' own harness CLIs.** A CLI draws on a
subscription rather than API billing, and it brings the prompts and tooling
each vendor has built into its harness.

- Claude Code comes first.
- Antigravity (`agy`) is a later target.
- Gemini CLI is excluded, because it does not draw on subscription tokens.
- Each harness has its own adapter, and one adapter can switch between a
  headless stream and a terminal pane without affecting the others.

**Sessions persist so the prompt cache stays warm.** Each seat is a single
process for the whole issue. Every issue starts from the same stable prefix.

**Both seats share one worktree.** The work is serial, so there is nothing to
synchronise between turns.

**Work lands by a local squash-merge to `main`.** There are no pull requests,
and GitHub Issues will be retired.

**No agent sits at the top.** The supervisor is a program, not a model.

**DR-214's objections are met.** solorepo's DR-214 (Coordination is what
GitHub records, not what git history carries) rejected a local supervisor
over a filesystem queue on two grounds:

- *Workers are early-bound.* In this design the seat is chosen for each issue.
- *The supervisor owns the queue and the human becomes an audience.* Here the
  queue is files in git. The supervisor holds nothing but a lock and its
  process handles, and the solo can edit any file at any time.

## 5. Alternatives considered and rejected

- **An explicit hand-off command run by the seat** (`just pair hand <next>`). A
  seat that forgets to run it stalls the loop. The supervisor must decide
  whose turn it is.
- **A `verdict:` field.** It reinstates a coder and a reviewer, which is what
  pair programming does away with.
- **OKF's `verified` fields as a semaphore.** Any semaphore is protocol for the
  agents to carry. The Open Knowledge Format (OKF v0.2) was also considered as
  the issue file format. Its one required field, `type`, costs little, but its
  generated `index.md` and `log.md` files would conflict between `main` and an
  issue branch. The spike does not use OKF. Conformance can be added later if
  it proves useful.
- **Redundant front matter:** `state`, `phase`, `round`, `landed`, `branch`, and
  numeric ids. Each can be derived from the directory or from git.
- **An agent SDK in place of the harness CLIs.** It gives up subscription
  billing and the work the vendors put into their harnesses.
- **Deleting solorepo's choreography before the spike.** The fork makes this
  unnecessary.

## 6. The meta-harness survey

### Three ways to hold a session

- **Terminal multiplexer and injected keystrokes.** The harness runs in a tmux
  or herdr pane, and messages are typed into it with `send-keys`. The cache
  stays warm and a human can take over trivially. The end of a turn, though,
  can only be guessed at, and injecting text is fragile.
- **Relaunch every turn with `--resume`.** Each turn is a clean process, but
  every turn pays for a process start, and the cache misses whenever the
  prefix drifts.
- **A long-lived structured stream:** Claude's `stream-json` mode, Codex's
  `app-server`, or the Agent Client Protocol (ACP). Turn boundaries are
  explicit and the cache stays warm. To take over, the solo pauses the stream
  and resumes the same session interactively.

The spike uses the structured stream for Claude. The multiplexer is the
fallback, and relaunching with `--resume` is how the solo takes over a seat.

### Tool by tool

| Tool | What it is | What we borrow | Why we do not adopt it |
|---|---|---|---|
| firstmate (kunchenguid/firstmate) | A "captain" agent that supervises a crew. Runs in tmux, herdr or Zellij; sends briefs with `send-keys`; keeps status files and inbox/outbox directories; a watcher script that costs no tokens; Stop hooks. | The zero-token watcher that wakes only on change. The Stop hook as a turn-end signal. Append-only status files. | An agent sits at the top. Crew members are started fresh for each task, which throws away the cache. The human talks only to the captain. |
| SwarmForge (unclebob/swarm-forge) | A fixed set of role agents in tmux, a `handoffd` daemon, hand-offs as git commits plus inbox/outbox queues, and a web dashboard. | Persistent role seats. Git commits as the hand-off medium. A daemon that only wakes things up. | One worktree per role, which adds a sync step to every turn. A queue protocol the agents must follow. Written in Babashka. |
| OpenRig (mvschwarz/openrig) | Teams declared in YAML; a daemon, CLI, MCP server and web UI on top of tmux; seats that can be snapshotted and restored. | Seats declared in configuration. Resuming a seat from its session id. A shared terminal view. | Agents manage their own team through 17 MCP tools, which is a protocol to carry. Heavy. A recorded failure on `send-keys` payloads over 128 KB. |
| herdr | A terminal multiplexer, written in Rust, that shows whether each agent is working, blocked or idle, with a socket API. | A possible base for the cockpit. | Unverified: its reported star count looks implausible, and which repository is the real one is unclear. |
| Claude Code agent teams | Experimental: a lead session with teammates, JSON mailboxes, and `TeammateIdle` and `TaskCompleted` hooks. | Hooks as the signal that an agent is idle. | Experimental and interactive only; teammates cannot be resumed; the lead is an agent at the top; Claude only. |
| vibe-kanban | A kanban board that launches agents over `stream-json`, `app-server` and ACP. Being wound down. | One structured-protocol adapter per harness. | Being wound down. Its issue #2993 shows that sessions are keyed by folder path, so the worktree path must stay stable. |
| Backlog.md (MrLesk/Backlog.md) | One Markdown file per task, with front matter, and a board view. | A Markdown file per task. A board view. | It keeps state in a `status` field. Directories and `git mv` do that job here. |
| claude-squad, uzi | Parallel agent sessions in tmux. | Pausing and resuming one instance. A "checkpoint" as a rebase onto `main`. | Parallel within one repository, and no hand-off between agents. |
| Crystal, Conductor, Polygraph | A desktop app that relaunches per turn (deprecated); a closed desktop app; a largely hosted service for cross-repository memory. | Crystal's cost of relaunching per turn, as a lesson. | Deprecated, closed, or hosted. |

### Why we do not adopt any of them

- Most put an agent at the top: a captain, a lead, or agents managing
  themselves through MCP tools.
- Several make the agents follow a messaging protocol. That is PR First's
  failure mode again.
- Their main value is parallel work within a repository. Here, work within a
  repository is serial.
- Several start a new session for each task, or a new process for each turn.
- Several are closed, deprecated, or being wound down.
- They keep their state in databases and daemons, not in git.
- None of them runs a pair in which both seats write code and agreement is
  observed rather than declared.

## 7. What the cockpit must do

The cockpit comes later; the spike runs in one repository only. When it
comes, it must meet these requirements:

- **One view across repositories.** For each repository: the issue in flight,
  its stage, its round, and whether it needs the solo.
- **One queue of what needs the solo, across repositories.** It includes desk
  checks, issues sent back to the roadmap, seats that crashed twice, and
  merges that `--ff-only` refused.
- **Notifications,** on the desktop first and on the phone later.
- **Deterministic and zero-token.** No agent at the top. It wakes only when
  something changes, as firstmate's watcher does.
- **Take over any seat, then give it back:** resume the seat's session
  interactively, and let the supervisor carry on afterwards.
- **Add to any repository's backlog without switching context.** An ordinary
  interactive session with filesystem access writes the backlog files. That
  is the captain's job, done with no captain.
- **A read-only projection of files and git,** so that several cockpits can be
  tried side by side: herdr panes, a status command, a web page. Each
  repository's supervisor publishes its status by a shared convention, for
  example `~/.pairs/<repo>.json`.
- **Work that spans repositories is split per repository** and linked through
  `waits_on`, for example `waits_on: [otherrepo:slug]`.

## 8. What the spike must answer

The spike runs the loop in booktutor (`caindy/booktutor`), with the loop
living inside that repository for now. It has to answer:

1. **Do headless `stream-json` seats behave like interactive sessions?** That
   covers skills, hooks, `CLAUDE.md`, and the subscription login.
2. **How many tokens does each turn read from the cache,** and does that
   number rise across a seat's turns?
3. **How reliably can the end of a turn be detected?**
4. **How well does taking over a seat and handing it back work?**
5. **Does quiet-turn agreement settle naturally?** Or does it rubber-stamp, or
   never settle at all?
6. **Which set of tool permissions works?**

## 9. What happens next

1. Run the spike in booktutor and record its answers.
2. Fork solorepo.
3. In the fork, remove PR First, the choreography, and the taxonomy of work.
   Write the new delivery discipline from this document and the spike's
   findings, using solorepo's disciplines.
4. Publish an APM package that carries the disciplines without any delivery
   machinery.
5. Move booktutor onto that package and remove the spike's tooling from it.
