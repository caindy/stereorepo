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

## Desk-check brief

Both children have landed on `main`: `seats-never-hold-keys` and
`landing-gate-reads-declared-keys`. A portfolio's keys now reach the landing
gate by name, and a seat can neither read them nor inherit them.

**What was delivered**

- **Seats never hold keys.** When a seat starts, `confinement()` in
  `pair/seats.py` finds every `.env` and `.env.*` file at the root of the main
  checkout and of each worktree, the seat's own included (`key_files`). It
  denies them to Bash through the sandbox's `filesystem.denyRead`, and to the
  Read, Grep and Glob tools through `Read(//…)` rules in `permissions.deny`.
  `ClaudeSeat` drops every variable those files name (`env_names`) from the
  seat's environment, as it already dropped `ANTHROPIC_API_KEY`. With no
  `.env`, the seat's settings are the same as before, byte for byte.
- **The landing gate gets the keys a portfolio declares.** A portfolio lists
  variable names, never values, under `portfolio.gate_keys` in
  `.meta/assertions/structure.yaml`; the slot is in the schema in
  `.meta/work/structure.yaml`. `Loop.gate_env` in `pair/loop.py` reads that
  list from `main`, not from the branch, so a seat cannot widen it. It takes
  the values from the `.env` at the main checkout's root, and `gate` in
  `pair/pair.py` adds them to the gate's process only. Before the gate's
  output reaches a seat, `redact` replaces each declared value in it with
  the variable's name in angle brackets, such as `<GEMINI_API_KEY>`.
- **The rule is recorded.** DR-357 states it: keys reach the supervisor's
  gate and never a seat. It also says that an Issue whose work is itself a
  live run stays a `developer` Issue, and it names what stays open.
  `pair/README.md`, under the gating step, describes the behaviour.
- **Nothing changes for the developer.** `just gate` in the developer's own
  checkout is untouched.

**Where to see it**

- `GateKeysTest` in `pair/test_pair.py`. It checks that the gate gets the
  declared key and not the undeclared one, that a portfolio declaring nothing
  gives the gate nothing, that a key declared only on the branch is not
  given, and that a printed key is redacted in both a failing and a `?` gate.
- In `ConfinementTest`: `test_key_files_in_every_checkout_are_denied_reading`
  and `test_with_no_key_files_nothing_is_withheld`. In `ClaudeSeatTest`:
  `test_a_seat_starts_without_the_variables_its_key_files_name`.
- I ran these, with the `SeatCommandTest` cases, on this branch at `main`'s
  code: 31 tests, all passing.

**Worth trying**

- In fitch-mvp, add `gate_keys: [GEMINI_API_KEY]` under `portfolio:` in its
  `structure.yaml` on `main`, and let `live-generation-run`'s test reach the
  landing gate. It should run rather than report `?`.
- In a live seat, ask it to `cat ../../.env`, and to Grep the repository root
  for a value in `.env`. The tests show the deny rules are passed to the
  seat, not that Grep and Glob obey them when they search a whole directory.
  That is the one part nobody has seen working.
- Weigh the openings DR-357 leaves: code on the branch runs with the declared
  keys, and a test that writes its key to a file in `worktrees/pair` leaves
  it where the next seat can read it. Also, `.env.*` matches a committed
  `.env.example`, which the seats then can neither read nor edit.

## Pair notes

> **primary, flight-check turn 1**
>
> I found no gaps in the Flight, so I added a `## Desk-check brief` to `issues/underway/keys-reach-the-landing-gate-not-the-seats.md` and committed it as `5e14355e`. The Flight goes to your desk check.
>
> The developer hadn't sent the Flight back: there is no `## Desk-check notes` section. I checked each "How anyone will know it is done" item against the code on this branch, which is `main` plus the Flight's start commit:
>
> - **Declared key versus undeclared key:** `GateKeysTest` in `pair/test_pair.py` covers this. The gate's process gets only the declared key, and only from `main`'s list, so a branch can't add keys. A key the gate prints is replaced by its name before a seat sees it.
> - **Seats can't read `.env`:** `ConfinementTest` shows the seat's settings deny reading `.env` and `.env.*` in the main checkout, in other worktrees and in the seat's own worktree.
> - **The seat's environment holds neither variable:** `ClaudeSeatTest` shows a seat starts without any variable that a `.env` file names.
> - **A portfolio that declares nothing behaves as today:** tests cover this for both the gate and the seats.
> - **The decision record:** DR-357 states the rule that keys reach the gate and never a seat. It also says a live-run Issue stays with you.
>
> I ran those test groups and they passed: 31 tests, all OK.
>
> The brief suggests three things to try:
> - **fitch-mvp:** declare `GEMINI_API_KEY` under `portfolio.gate_keys` on its `main`. Its `live-generation-run` test should then pass the landing gate instead of reporting `?`.
> - **A live seat:** the tests show the deny rules are given to the seat, not that its Grep and Glob tools obey them when searching a whole folder. Asking a real seat to read `.env` is the only way to see that.
> - **What DR-357 leaves open:**
>   - Code on the branch runs with the keys you declare.
>   - A test that writes its key to a file in the worktree leaves it where the next seat can read it.
>   - A committed `.env.example` would become unreadable to the seats.

> **secondary, flight-check turn 2**
>
> I changed nothing. My partner's desk-check brief for the Flight is accurate, and I found no gap that needs a new backlog Issue.
>
> The developer hasn't sent the Flight back, since there is no `## Desk-check notes` section. So the brief's claims were what needed checking, and each one matches the code:
>
> - **Seats can't read keys.** `key_files` and `env_names` in `pair/seats.py` find each `.env` file and the variables it sets. `confinement()` denies reading those files through the sandbox's `filesystem.denyRead` and the `Read` rules in `permissions.deny`.
> - **The landing gate gets only declared keys.** `Loop.gate_env` in `pair/loop.py` reads `portfolio.gate_keys` from `main`'s structure, not the branch's, and takes the values from the main checkout's `.env`. `gate` in `pair/pair.py` adds them to the gate's own process only. `redact` replaces each value with its variable's name before the gate's output reaches a seat.
> - **The schema and the rule are in place.** The `gate_keys` slot is in `.meta/work/structure.yaml`, and DR-357 states the rule that keys reach the gate and never a seat.
> - **The tests the brief cites exist.** They are `GateKeysTest`, and the `ConfinementTest` and `ClaudeSeatTest` cases it names, all in `pair/test_pair.py`.
>
> I didn't rerun those tests: my attempt failed because this shell has no `timeout` command. The pass count is my partner's: 31 tests, all passing.
>
> The brief already flags the one thing nobody has seen working: whether a live seat's Grep and Glob obey the deny rules when they search a whole directory. That can only be tried by hand, so it belongs in the developer's desk check rather than in a new Issue.
