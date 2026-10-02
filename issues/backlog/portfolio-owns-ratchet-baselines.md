---
difficulty: medium
parent: onboard-fitch-mvp
---

# A sync never overwrites a portfolio's ratchet baselines

`.meta/checks/*.baseline.yaml` sit inside `.meta/checks/`, a managed
directory of `.meta/bundle.yaml`. Each sync of fitch-mvp overwrote its
comment baseline (418 existing comments across 27 files) with stereorepo's,
and the developer had to restore it from git each time. An adopted codebase
depends on its baselines from its first gate, so the baselines belong to the
portfolio, not the bundle.

## Done when

- Copying the managed items into a portfolio leaves its baselines as they
  were. The baselines can move out of the managed directory, or the bundle
  can mark them as the portfolio's.
- A specialized portfolio starts with baselines its own gate accepts.
- A test copies the managed items over a portfolio whose baseline differs
  from stereorepo's and finds the portfolio's baseline unchanged.
