---
slug: mergeability-refresh-commit
context: solorepo
minted: 2026-09-24
---

# Mergeability Refresh Commit

**Mergeability Refresh Commit** is an empty commit force-pushed to a branch already current with its base to clear a stuck CONFLICTING state in GitHub's mergeable cache.

## Overview

A Mergeability Refresh Commit is an empty commit authored specifically to force GitHub's backend to recalculate a pull request's `mergeable` status. When a branch is already current with its base but GitHub caches its status as `CONFLICTING`, a zero-diff commit pushed to the branch clears the cache without modifying the tree.

Unlike a Seed Commit, which records an initial plan before work begins, the Mergeability Refresh Commit is purely infrastructural. Its subject is fixed to `Mergeability Refresh Commit` to distinguish it from deliberate changes.

## Invariants

1. **Per-Branch Bound:** A branch must receive no more than one Mergeability Refresh Commit for its whole life (not one per stranding). The rebase pass checks the branch tip's subject; if it is already `Mergeability Refresh Commit`, the pass stops. A second stranding on an already-refreshed branch is routed to the solo deliberately.
2. **Subject Exact Match:** The commit subject is precisely `Mergeability Refresh Commit`, without any prefix.
3. **No Diff:** The commit must be empty (`--allow-empty`).

---

**See also:** [[knowledge-management]], [[ubiquitous-language]], [[pr-first]]
