---
difficulty: medium
parent: keys-reach-the-landing-gate-not-the-seats
---

# Keep a portfolio's keys out of the seats' reach

Part of `keys-reach-the-landing-gate-not-the-seats`. The seats' sandbox
confines writes, not reads (DR-302): `command()` in `pair/seats.py` sets
`filesystem.allowWrite` and `denyWrite` only, and `network.allowedDomains`
is `["*"]`. A portfolio's loop worktree sits inside its tree, so a seat can
read `../../.env`, and a key it reads can leave through the network, its
transcript under `.pair/`, a file or a commit. `ClaudeSeat` passes the
loop's whole environment to the seat except `ANTHROPIC_API_KEY`.

## Wanted

- The seat's sandbox denies reading `.env` and `.env.*` at the root of the
  main checkout and of every worktree of the repository (the same worktrees
  `confinement()` already enumerates), through the sandbox's read-deny
  setting alongside `denyWrite`. Read tools (Read, Grep, Glob) are held to
  the same paths through the permission settings the seat is started with,
  since the Bash sandbox does not govern them.
- The seat's environment carries none of the variables those files name:
  `ClaudeSeat` reads the names (never acting on the values) from each such
  file that exists and drops them from the environment it passes, as it
  drops `ANTHROPIC_API_KEY` today.
- A portfolio with no `.env` behaves exactly as today.

## Out of scope

- Loading keys into the landing gate (`landing-gate-reads-declared-keys`).
- Narrowing the network allowlist, a separate decision from DR-302.

## Done when

- A test over a temporary repository with a `.env` at the root and in a
  worktree: the seat's command line denies reading both paths, and denies
  them to the read tools.
- A test with a `.env` naming `SOME_KEY`, and `SOME_KEY` set in the loop's
  environment: the environment `ClaudeSeat` starts the seat with lacks it.
- A test with no `.env`: the command line and environment are as today.
