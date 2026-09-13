# PR First

**PR First** is the discipline that organizes all changes as an open pull request
from inception, advancing through autonomous review, automated testing, and
auto-merge loops.

Rather than developing features in private long-lived branches and opening a
pull request only when finished, work is visible to the harness from the moment
it begins. The pull request acts as an active semaphore coordinating the solo,
background coder loops, and automated reviewer passes.

## The Loop Machinery

Work flows through a series of specialized loop workflows triggered by GitHub
events:

1. **Coder Pass:** Dispatched to implement a Challenge or respond to reviewer
   feedback, operating under the `coder` role.
2. **Reviewer Pass:** Performs independent verification of diffs against
   repository disciplines, operating under the `reviewer` role.
3. **Advance & Merge:** Automatically rebases clean branches onto `main`, verifies
   gates, and completes squash-merges once approved.
4. **Sweep:** Detects and reports residue branches whose remote heads have merged
   or closed.

## Persistent Monitoring

A pull request opened in an interactive session is watched until it closes. The
operator surface `just watch <n>` maintains an active subscription: waking the
session when actionable feedback lands so that reviews are answered
immediately rather than after an arbitrary delay (solorepo's DR-102, solorepo's DR-138).

---

**See also:** [Knowledge Management](knowledge-management.md), [Ubiquitous Language](ubiquitous-language.md), solorepo's DR-062, solorepo's DR-117, solorepo's DR-184.
