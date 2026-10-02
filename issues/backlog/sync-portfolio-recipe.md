---
difficulty: hard
parent: onboard-fitch-mvp
waits_on:
  - portfolio-owns-ratchet-baselines
---

# A recipe syncs a portfolio from a stereorepo checkout

Nothing syncs a portfolio with stereorepo. fitch-mvp was synced twice by
copying `lib.bundle`'s `managed_items()` over it, which never deletes. When
DR-305 made `.meta/adapt.py`, `.meta/lib/adapt/` and
`.meta/checks/probes/tools/test_brownfield.py` scaffold-only, fitch-mvp kept
its copies, and their probe reported `?` until they were removed by hand.

## Done when

- A recipe, run in a portfolio and given a stereorepo checkout, copies the
  bundle's managed items. It removes the managed paths the bundle no longer
  lists and the scaffold-only ones (`SCAFFOLD_ONLY`), and leaves template
  items and the portfolio's own files alone.
- It never overwrites the portfolio's ratchet baselines
  (`portfolio-owns-ratchet-baselines`).
- A test syncs a specialized portfolio from a bundle that drops one managed
  path and adds another. It finds the first gone, the second present, and a
  template item and a portfolio-only file unchanged.
