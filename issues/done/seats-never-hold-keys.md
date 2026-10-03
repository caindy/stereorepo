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
  main checkout and of every worktree of the repository, the seat's own
  included. The roots come from `git worktree list --porcelain`:
  `confinement()` enumerates the worktrees' git directories under
  `<common>/worktrees/`, not their roots. Bash is denied them through the
  sandbox's `filesystem.denyRead`, alongside `denyWrite` in `command()`.
  The read tools (Read, Grep, Glob) are denied them through `Read(//<path>)`
  rules in `permissions.deny` in the same `--settings`, since the sandbox
  does not govern them. The denials name the files that exist, found when
  the seat starts (`confinement()` runs then), as literal paths resolved
  with `Path.resolve()` so that `/tmp` and `/private/tmp` agree on macOS;
  no glob reaches the sandbox, whose glob support is not established.
- The seat's environment carries none of the variables those files name:
  `ClaudeSeat` reads the names (never acting on the values) from each such
  file and drops them from the environment it passes, as it drops
  `ANTHROPIC_API_KEY` today. A name is the text before the first `=` on a
  line, less a leading `export ` and surrounding whitespace; blank lines and
  lines starting with `#` name nothing.
- A portfolio with no `.env` behaves exactly as today.

## Out of scope

- Loading keys into the landing gate (`landing-gate-reads-declared-keys`).
- Narrowing the network allowlist, a separate decision from DR-302.
- A `.env` created while a seat is running: it is denied from the seat's
  next start, not before.

## Done when

- A test over a temporary repository with a `.env` at the root and in a
  worktree: the seat's command line denies reading both paths, and denies
  them to the read tools, and denies the seat's own worktree's `.env` as
  well.
- A test over a temporary repository whose root holds `.env.local` as well
  as `.env`: both are denied, to Bash and to the read tools.
- A test with a `.env` naming `SOME_KEY` (written as `export SOME_KEY=x`,
  after a comment line), and `SOME_KEY` and `OTHER` set in the loop's
  environment: the environment `ClaudeSeat` starts the seat with lacks
  `SOME_KEY` and keeps `OTHER`.
- A test with no `.env`: the command line and environment are as today.

## The plan

All of it is in `pair/seats.py` and `pair/test_pair.py`.

1. **`Confinement` gains two fields**, both defaulting to empty so that
   `SeatCommandTest.CONFINED` and every other caller is unchanged:
   `unreadable: list[Path]`, the key files, and `withheld: set[str]`, the
   names they hold. The class docstring says what each becomes.
2. **A helper `env_names(path) -> set[str]`** parses one file by the rule in
   Wanted: per line, strip it, skip a blank line or one starting with `#`,
   drop a leading `export `, and take the text before the first `=`,
   stripped. A line without `=` names nothing. Values are never kept. It
   reads with `errors="replace"`, so a binary `.env.*` (an encrypted
   `.env.gpg`, say) names nothing much rather than raising
   `UnicodeDecodeError` and stopping the seat from starting.
3. **`confinement()` fills them.** It reads `git worktree list --porcelain`
   (through its `out()` helper) and takes each `worktree <path>` line, the
   main checkout first; a root that no longer exists (a prunable worktree)
   is skipped. A second helper, `key_files(roots)`, globs `.env` and
   `.env.*` in each root (resolved first) and keeps regular files
   (`is_file()` follows a symlink). A file that is a symlink is listed both
   as itself and as its `Path.resolve()` target, since whether the Read
   tool's rules match a link by its target is not established.
   `unreadable` is those paths, deduplicated and sorted, and `withheld` the
   union of `env_names` over them. The docstring's summary line stops
   calling it only the write confinement, and it gains a paragraph on why:
   the seat's sandbox confines writes, not reads, and a portfolio's
   worktree sits inside its tree.
4. **`command()` passes them on, only when there are any**, so that with no
   `.env` the `--settings` JSON is byte-for-byte today's:
   `sandbox.filesystem.denyRead` lists the paths, and a top-level
   `permissions.deny` lists `Read(/<path>)` for each (an absolute path
   already starts with `/`, which gives Claude Code's `//` form). The
   docstring says the read tools are held by the permission rules and Bash
   by the sandbox.
5. **`ClaudeSeat.__init__`** drops `confined.withheld` from the environment
   in the same comprehension that drops `ANTHROPIC_API_KEY`, before
   `confined.env` is applied.

### Tests

- In `ConfinementTest`, whose `setUp` already has a main checkout (`repo`),
  the seat's worktree (`wt`) and another worktree (`other`): write `.env`
  in `repo`, `other` and `wt`, and `.env.local` in `repo`; assert all four
  are in `confinement(self.wt).unreadable`, and that `command("p", it)`
  lists each in `denyRead` and as `Read(//…)` in `permissions.deny`. A
  `.env` directory, or a file named `env`, is not listed. A `.env.link`
  symlink in `other` pointing at a file under `self.tmp` lists both the
  link and the target.
- A unit test of `env_names` over `# c\n\nexport SOME_KEY=x\nB = y=z\nnoeq\n`
  gives `{"SOME_KEY", "B"}`, and over bytes that are not UTF-8 it returns
  without raising.
- In `ClaudeSeatTest`, using the `Popen` interception of
  `test_a_seat_given_no_program_starts_claude` but keeping `kwargs["env"]`:
  with `wt/.env` holding `# c\nexport SOME_KEY=x\n` and `SOME_KEY` and
  `OTHER` patched into `os.environ`, the seat's environment lacks
  `SOME_KEY` and has `OTHER`.
- No `.env`: `confinement(self.wt)` has empty `unreadable` and `withheld`,
  and in `SeatCommandTest` the settings carry no `permissions` key and no
  `denyRead`.

### Risks

- Whether Claude Code's Grep and Glob honour a `Read(...)` deny when they
  search a directory that holds the file, rather than name it, is not
  something a unit test can show; the tests prove the rules are passed,
  not obeyed. Bash's `rg` and `cat` are held by the sandbox regardless.
- The project's `.claude/settings.json` is still loaded
  (`--setting-sources project`); its `permissions.deny` merges with the one
  passed here rather than being replaced, which is the behaviour wanted.
- `.env.*` also matches a committed `.env.example`, which a seat can then
  neither read nor edit. Accepted as written; no portfolio here has one.

## Pair notes

> **primary, backlog turn 1**
>
> The issue was already close to ready to plan. I checked it against `pair/seats.py`, fixed one wrong statement, and made the read denials concrete. It stays at `difficulty: medium`.
>
> - **The wrong statement:** the issue said to deny `.env` in "the same worktrees `confinement()` already enumerates". But `confinement()` lists each worktree's git directory under `<common>/worktrees/`, not the worktree's root folder, which is where a `.env` sits. The issue now says to get the roots from `git worktree list --porcelain`, and says the seat's own worktree is included.
> - **The read denials:** Bash is denied through `filesystem.denyRead`, next to `denyWrite` in `command()`. The read tools (Read, Grep, Glob) are denied through `Read(//<path>)` rules in `permissions.deny`, passed in the same `--settings`. The Bash sandbox doesn't cover those tools.
> - **Done when:** the first test now also checks that the seat's own worktree's `.env` is denied.
>
> The scope, what's out of scope and the other two tests are unchanged. The change is committed as `9bd2691e`.

> **secondary, backlog turn 2**
>
> I checked the issue against `pair/seats.py`. My partner's fixes hold up: worktree roots come from `git worktree list --porcelain`, and the read tools are denied through `permissions.deny`. I filled in three gaps the plan would have run into, and left `difficulty: medium` as it was. Committed as `ffaceb92`.
>
> - **Which paths get denied:** only `.env` files that exist when the seat starts. Each is passed to the sandbox as a full path with symlinks resolved, so `/tmp` and `/private/tmp` agree on macOS. No glob patterns, since we don't know whether the sandbox handles them. This keeps a portfolio with no `.env` exactly as it is today.
> - **How variable names are read from `.env`:** a name is the text before the first `=`, with any leading `export ` removed. Blank lines and lines starting with `#` name nothing. A file created while a seat is running is now listed as out of scope: it is denied from the seat's next start.
> - **Tests:** one new test checks that a `.env.local` next to `.env` is denied too. The environment test now writes the key as `export SOME_KEY=x` after a comment line, and checks that an unrelated variable, `OTHER`, is still passed through.

> **primary, backlog turn 3**
>
> I'm leaving the issue as it is. It's ready to plan, and `difficulty: medium` still fits.
>
> My partner's changes hold up:
>
> - **Which files are denied:** only `.env` files that exist when the seat starts, each passed as a full path. That is what keeps a portfolio with no `.env` behaving exactly as today. No glob patterns are sent, because we don't know whether the sandbox supports them.
> - **How names are read from `.env`:** the rule is clear and the environment test exercises it.
> - **New tests:** the `.env.local` test and the check that an unrelated variable (`OTHER`) still reaches the seat close the gaps a plan would have hit.
>
> One open point, not worth an edit now: `.env.*` also matches a committed template such as `.env.example`, so a seat couldn't read it. This repository has no tracked `.env` files, so nothing here is affected. The planner can carve the template out if a portfolio needs it.

> **primary, todo turn 1**
>
> I added `## The plan` to `issues/todo/seats-never-hold-keys.md` and committed it as `96080277`. The issue can be done as written. The change stays in `pair/seats.py` and `pair/test_pair.py`.
>
> **Steps, in order:**
> 1. `Confinement` gets two new fields that default to empty: `unreadable` (the `.env` files) and `withheld` (the variable names they contain). Existing callers don't change.
> 2. A new helper, `env_names()`, reads the variable names from one file using the rule the issue gives, and never keeps the values.
> 3. `confinement()` gets each worktree root from `git worktree list --porcelain`, skipping any root that no longer exists. It collects the `.env` and `.env.*` files there, with symlinks resolved.
> 4. `command()` adds `filesystem.denyRead` and `permissions.deny` `Read(//…)` rules only when there is at least one such file. With no `.env`, the settings are exactly the same as today.
> 5. `ClaudeSeat` drops the withheld names from the seat's environment, in the same step that drops `ANTHROPIC_API_KEY`.
>
> **Tests:**
> - A repository with `.env` in the main checkout, the seat's worktree and a second worktree, plus a `.env.local`: all four are listed in `confinement()` and denied in the command line.
> - A unit test of `env_names()`.
> - A seat-environment test that catches the `Popen` call, the same way an existing test does: `SOME_KEY` is dropped and `OTHER` is kept.
> - A no-`.env` test: the settings have no `permissions` key and no `denyRead`.
>
> **Risks:**
> - The tests show the `Read(...)` deny rules are passed to the seat, not that Grep and Glob obey them when searching a directory that holds a `.env`. Bash is held by the sandbox either way.
> - The project's own `permissions.deny` settings merge with the ones passed here rather than being replaced. That is the wanted behaviour.
> - A committed `.env.example` would become unreadable to the seats. This is accepted as written, since no portfolio here has one.

> **secondary, todo turn 2**
>
> I checked my partner's plan against `pair/seats.py` and `pair/test_pair.py`, and the code matches what it assumes. The `out()` helper is inside `confinement()`. `ConfinementTest` already sets up the three checkouts the tests need. `SeatCommandTest.CONFINED` keeps working because the new fields default to empty. And `--setting-sources project` means the project's own deny rules are merged with ours, not replaced.
>
> I made four changes to the plan and committed them as `2f26625e`:
>
> - **Binary key files:** a `.env.*` file can be binary, such as an encrypted `.env.gpg`. Reading it as text would raise `UnicodeDecodeError` and stop the seat from starting. `env_names()` now reads with `errors="replace"`, and its unit test now feeds it bytes that aren't valid UTF-8.
> - **Symlinked key files:** a `.env` that is a symlink is now denied both under its own path and under the file it points to, since we don't know whether the Read tool's rules follow a link to its target. Worktree roots are resolved before the search. A new test case covers a `.env.link` symlink.
> - **Docstring:** step 3 now says the summary line of `confinement()`'s docstring must stop calling it only the write confinement, since it will deny reads too.
>
> The issue can be done as written, so I added no `# Needs elaboration` section.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is. My partner's four changes hold up against the code:
>
> - **Binary key files:** reading with `errors="replace"` means a binary `.env.*` file can't stop the seat from starting.
> - **Symlinked key files:** denying a symlinked `.env` under both its own path and its target covers us while we don't know whether the Read tool's rules follow links. This also denies the target when it lies outside every worktree, which is what we want.
> - **Worktree roots:** resolving each root before the search keeps paths consistent with the rest of the plan.
> - **Docstring:** the summary line of `confinement()`'s docstring will stop calling it only the write confinement.
>
> The new test cases fit the existing `ConfinementTest` setup. The issue can still be done as written, so it needs no `# Needs elaboration` section.

> **primary, in-progress turn 1**
>
> I implemented the plan in `pair/seats.py` and `pair/test_pair.py`. `just gate pair` and `just gate meta` pass.
>
> - **What changed from the plan:** the file search became its own helper, `key_files(roots)`, next to `env_names(path)`, so that `confinement()` only gathers the worktree roots and calls it. Step 3 of the plan now says so.
> - **Tests added:** `test_key_files_in_every_checkout_are_denied_reading` and `test_with_no_key_files_nothing_is_withheld` in `ConfinementTest`; `test_with_no_key_files_nothing_is_denied_reading` and `test_env_names_takes_the_names_and_never_the_values` in `SeatCommandTest`; and `test_a_seat_starts_without_the_variables_its_key_files_name` in `ClaudeSeatTest`, which catches the seat's `Popen` and reads its `env`.
> - **Still unproven:** whether a real Claude Code seat's Grep and Glob obey the `Read(//…)` rules when searching a directory, as the plan's Risks section says. The tests show only that the rules are passed.

> **primary, in-progress turn 1**
>
> The seats can no longer read a portfolio's `.env` files or inherit the variables those files set. `just gate pair` (248 tests) and `just gate meta` both pass, and the change is committed as `d4da9a4a`.
>
> What the change does, all in `pair/seats.py`:
> - **Finding the files:** when a seat starts, `confinement()` asks `git worktree list --porcelain` for the main checkout and every worktree. A new helper, `key_files()`, collects the `.env` and `.env.*` files at each root. A symlinked key file is denied under both its own path and the file it points to.
> - **Reading the names:** another new helper, `env_names()`, reads only the variable names from each file, never the values. A binary file such as an encrypted `.env.gpg` can't stop the seat from starting.
> - **Denying the reads:** `command()` passes the files to the sandbox's `filesystem.denyRead`, which covers Bash, and as `Read(//…)` rules in `permissions.deny`, which cover the read tools. With no key files, the settings are exactly the same as before.
> - **Cleaning the environment:** `ClaudeSeat` drops the names it found from the seat's environment, along with `ANTHROPIC_API_KEY` as before.
>
> There are five new tests:
> - **Every checkout:** key files in all three checkouts, plus a `.env.local` and a symlink, are all denied, while a `.env.d` directory and a file named `env` are not.
> - **No key files:** the settings and the seat's environment are the same as before.
> - **Name parsing:** `env_names()` returns only the names and doesn't crash on bytes that aren't valid UTF-8.
> - **The seat's environment:** with `SOME_KEY` named in a `.env`, the environment a seat starts with lacks `SOME_KEY` and still has `OTHER`.
>
> One thing is still unproven: whether a real seat's Grep and Glob obey the `Read(//…)` rules when they search a whole directory. The tests only show the rules are passed in. Bash is blocked by the sandbox either way.
>
> The only change from the plan is that the file search became its own helper, and the plan now says so. No wiki page covers the seat sandbox, so no other documents needed updating. I left a note for the next reader in the issue file.

> **secondary, in-progress turn 2**
>
> I reviewed my partner's implementation against the plan and it holds up. Seats are now denied reading `.env` files in the main checkout and every worktree, and the variables those files set are removed from the seat's environment.
>
> I made one fix. If the loop itself couldn't read a key file (permissions set to `000`, or owned by another user), `env_names()` in `pair/seats.py` raised an error and the seat failed to start. Now such a file gives no variable names, but it is still denied to the seat. The test `test_env_names_takes_the_names_and_never_the_values` covers this, except when the tests run as root, which can read the file anyway; that check is skipped there.
>
> `just gate pair` (248 tests) and `just gate meta` both pass. The change is committed as `7f5c8d49`, with a note in the issue file.
>
> One thing is still untested: whether a real seat's Grep and Glob tools obey the `Read(//…)` deny rules when they search a whole folder rather than open the file by name. The tests only show the rules are passed to the seat. Bash can't read the files either way, because the sandbox blocks it.

> **primary, in-progress turn 3**
>
> I'm keeping my partner's fix. If the loop itself can't read a key file, `env_names()` now finds no variable names in it instead of crashing, so the seat still starts and the file is still denied to it. The new test can't check this when it runs as root, because root can read the file anyway.
>
> The only thing I changed was the issue file: it had two copies of my partner's note, so I removed the shorter one. `just gate meta` and `just gate pair` (248 tests) both pass, and that edit is committed as `b3bb31a2`.

> **secondary, in-progress turn 4**
>
> I'm changing nothing this turn. Since my last turn, my partner only edited the issue file: they removed a duplicate of my note and added their own. The note that remains still describes my fix, where a key file the loop can't read gives no variable names but is still denied to the seat. The implementation is unchanged since `just gate pair` (248 tests) and `just gate meta` passed on my last turn, and the issue is done as planned.
