# PR First

**PR First** is the discipline that organizes all changes as an open pull request
from inception, advancing through autonomous review, automated testing, and
auto-merge loops (solorepo's DR-184, solorepo's DR-185).

Rather than developing features in private long-lived branches and opening a
pull request only when finished, work is visible to the harness from the moment
it begins. The pull request acts as an active semaphore coordinating the solo,
background coder loops, and automated reviewer passes.

## The Loop Machinery

Work flows through the [[dev-loop]], a series of specialized loop workflows triggered by GitHub
events:

1. **Coder Pass:** Dispatched to implement a Challenge or respond to reviewer
   feedback, operating under the `coder` role.
2. **Reviewer Pass:** Performs independent verification of diffs against
   repository disciplines, operating under the `reviewer` role.
3. **Advance & Merge:** Automatically rebases clean branches onto `main`, verifies
   gates, and completes squash-merges once approved.
4. **Sweep:** Detects and reports residue branches whose remote heads have merged
   or closed.

## Reviewer Depth & Concurrency

The reviewer pass determines review intensity using a 4-layer template method
pipeline (solorepo's DR-188) executed by [`.meta/depth.py`](../../.meta/depth.py):
- **Scaffold Security Invariants:** Modifications affecting scaffold control
  surfaces (`.meta/say/`, `.meta/hooks/`, `.claude/`, `.github/workflows/`,
  `.meta/check_pr.py`) mandate deep auditing (`claude-opus-5`, high effort,
  3 concurrent subagents, 45 minutes).
- **Declarative Critical Paths:** Paths matching `critical_paths` globs declared
  on Projects in `assertions/structure.yaml` automatically trigger deep auditing.
- **Programmatic Hooks:** Specialized portfolios can provide
  `.meta/hooks/depth.py` (scaffolded from `.meta/hooks/depth.py.example`) to
  execute dynamic heuristics based on PR metadata, touched paths, or full diff patches.
- **Standard Baseline:** Diffs that do not touch critical boundaries default to
  standard review depth (`claude-sonnet-5`, medium effort, 1 agent, 15 minutes).

When multiple review dimensions are evaluated on the deep path, subagents are
dispatched concurrently in a single turn to execute in parallel rather than
accumulating sequential turn delays (solorepo's DR-189).

## Persistent Monitoring

A pull request opened in an interactive session is watched until it closes. The
operator surface `just watch <n>` maintains an active subscription: waking the
session when actionable feedback lands so that reviews are answered
immediately rather than after an arbitrary delay (solorepo's DR-102, solorepo's DR-138).

---

**See also:** [[dev-loop]], [[knowledge-management]], [[ubiquitous-language]], solorepo's DR-062, solorepo's DR-117, solorepo's DR-184, solorepo's DR-185, solorepo's DR-188, solorepo's DR-189.
