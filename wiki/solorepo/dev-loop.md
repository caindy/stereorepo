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

It is the operational engine realizing the [[pr-first]] discipline. Rather than relying on interactive hand-offs, manual review coordination, or continuous human intervention, the development loop orchestrates autonomous agents across GitHub webhook events. The repository itself acts as the single source of truth, using open pull requests, review verdicts, and branch naming conventions as stateful coordination semaphores.

## The Decoupled Pass Lifecycle

Work progresses through four specialized, asynchronous passes triggered by repository events:

1. **Coder Pass:** Activated when an [[issue]] is labeled with an autonomous difficulty (`easy` or `medium`), or when a pull request review requests changes (solorepo's DR-112). The coder role claims the [[challenge]], creates or updates the working branch, drives quality checks to green, records changes via signed channel commits, and requests review.
2. **Reviewer Pass:** Activated when a pull request review is requested (solorepo's DR-109). The reviewer role performs an independent verification of the diff against repository disciplines, assertions, and conventions. The review depth pipeline dynamically calculates model capacity, extended thinking depth, and agent fan-out ceiling based on touched paths (solorepo's DR-188).
3. **Advance & Merge Manager Pass:** Continuously evaluates open pull requests when `main` moves or auto-merge conditions are met. It automatically rebases clean branches onto updated trunk heads (solorepo's DR-133) and squashes and merges approved candidates in order of structural leverage (solorepo's DR-161).
4. **Sweep Pass:** Periodically scans the repository for residue branches whose remote heads have merged or closed, reporting cleanup commands to preserve repository hygiene.

## Coordination via Branch Prefixes and Semaphores

The development loop operates without a centralized orchestrator database. State is tracked deterministically in git and GitHub metadata:

- **Durable Harness Memory:** Working branches follow the canonical naming pattern `<harness>/issue-<n>` (for example, `claude/issue-414` or `gemini/issue-414`). Embedding the originating harness into the branch name provides durable, stateless memory in git. When a downstream pass wakes to rebase a branch or answer reviewer comments, it reads the branch ref directly to preserve harness stickiness across webhook boundaries without external state storage.
- **Loop vs. Human Demarcation:** The branch prefix distinguishes autonomous loop work from human maintenance branches. When a reviewer requests changes on a `(claude|gemini|codex)/issue-*` branch, the verdict acts as an operational semaphore that automatically awakes the coder pass to remediate the diff. On human branches, the verdict remains an advisory review informing the author.
- **Challenge Recovery for Hand-Back:** Embedding `issue-<n>` into the branch ref guarantees that if an autonomous pass cannot complete its remit, it can reliably extract the originating [[challenge]] number from the git ref and execute the hand-back protocol.

## Multi-Harness Agnosticism and Resilient Fallback

Solorepo decouples engineering disciplines from any specific model vendor (solorepo's DR-111). A Role is a repository account and credential boundary (solorepo's DR-107), while a harness (Claude Code, Gemini CLI, OpenAI Codex) is the interchangeable execution container running inside the workflow.

Because external model APIs suffer transient rate limits, weekly quota exhaustion, and unhandled container terminations, the development loop enforces multi-harness self-healing (solorepo's DR-178):

- **Decoupled Execution:** Workflows dispatch to the harness declared by issue labels (`harness:gemini`), branch prefixes, or manual workflow inputs.
- **Automated Fallback:** When a primary harness encounters unrecoverable execution failures or quota limits (such as HTTP 429), the workflow catches the termination, records the fallback transition in the workload identity [[trailer]] (`AI_AGENT`), and transparently re-engages the secondary harness (such as Gemini CLI) to finish the pass.
- **Single Source of Truth:** Implementation mechanics are maintained directly in workflow definitions ([`.github/workflows/coder.yml`](../../.github/workflows/coder.yml), [`.github/workflows/review.yml`](../../.github/workflows/review.yml)) rather than duplicated across documentation.

## The Graceful Hand-Back Invariant

An autonomous loop must never silently abandon work or loop indefinitely when blocked (solorepo's DR-112). 

When a coder pass encounters conditions beyond its capability—such as an architectural decision requiring human judgement, a quality gate check that refuses to pass, or complex merge conflicts on rebase—it must stand down gracefully. The loop relabels the [[challenge]] as `human`, posts a diagnostic explanation to the pull request thread describing the obstacle encountered, and terminates execution. This leaves the pull request open and cleanly documented for the solo maintainer to resume.

---

**See also:** [[pr-first]], [[knowledge-management]], [[ubiquitous-language]], [[challenge]], solorepo's DR-107, solorepo's DR-111, solorepo's DR-112, solorepo's DR-133, solorepo's DR-161, solorepo's DR-178, solorepo's DR-188.
