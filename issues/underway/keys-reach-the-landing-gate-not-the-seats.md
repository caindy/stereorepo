---
difficulty: hard
---

# Give the landing gate a portfolio's keys, and keep them from the seats

A product often has tests that need a key, such as an API token, which the
developer keeps in a gitignored `.env` at the repository root. Today the pair
loop handles that in neither direction:

- **The landing gate cannot run them.** `run_gate` in `pair/loop.py` runs the
  gate in `worktrees/pair`, which has no `.env`, because git does not check
  out an ignored file. A test that needs the key either fails there or
  reports `?`, which since `landing-gate-holds-on-could-not-run` holds the
  landing for good.
- **The seats can read the key anyway.** The seats' sandbox confines writes,
  not reads (DR-302). A portfolio's loop worktree sits inside its tree, so a
  seat can read `../../.env`. Its network allows every domain
  (`allowedDomains: ["*"]`), so a seat steered by text it reads could send the
  key anywhere. A key in a seat's context can also reach its transcript under
  `.pair/`, a file it writes, or a commit.

fitch-mvp found this. Its `live-generation-run` needs a Gemini key from its
`.env`, and its seats reported that they could not reach it.

## Wanted

- **Seats never hold keys.** A seat's sandbox denies reading a portfolio's
  `.env` and its variants (`.env.*`), in the main checkout and in every
  worktree. The seat's environment carries none of the variables they hold.
  A test that needs a missing key reports `?`, as a test that needs a missing
  database does (fitch-mvp's DR-004), so a seat's targeted gate still passes.
- **The landing gate gets the keys a portfolio declares.** A portfolio names,
  in its assertions, the variables from its root `.env` that its gate may
  read. Naming only the variables, never their values, keeps them auditable
  in git. `run_gate` loads only those, and only into the gate's process,
  which runs outside the seats' sandbox. The landing hold then guarantees that
  nothing lands with a key-dependent step unrun.
- **Nothing else changes for the developer.** `just gate` in the developer's
  own checkout reads `.env` as the product already does.
- A coding decision record in stereorepo states the rule: keys reach the
  supervisor's gate and never a seat. An Issue whose work is itself a live run
  stays a `developer` Issue: the developer runs it, and the pair records what
  it found.

## How anyone will know it is done

- A test over a temporary portfolio whose `.env` holds a declared variable
  and an undeclared one: the landing gate's process sees the declared
  variable only, and a seat's settings deny reading `.env` at the root and in
  the worktree.
- A seat's environment holds neither variable.
- A portfolio that declares nothing behaves as today.

## Out of scope

- Narrowing the seats' network allowlist, which is a separate decision from
  DR-302.
- Secret managers or keychains: `.env` is the developer's convention.

## Split

This is two pieces of work, each of which stands alone:

1. `seats-never-hold-keys`: the seats' sandbox denies reading `.env` files
   and their environment carries none of the variables they hold.
2. `landing-gate-reads-declared-keys`: a portfolio declares the variables
   its gate may read, `run_gate` loads only those, and the decision record
   states the rule. It waits on the first, so the record describes both
   halves as built.
