---
difficulty: developer
---

# Keep gpg from hanging a seat's signed commit in the sandbox

`seat-git-signature-check-hangs` (done) turns off signature display for the
seats, through a `GIT_CONFIG_COUNT` entry that `confinement` in
`pair/seats.py` sets, so `git show` and `git log` stop verifying signatures.
A seat can still start a verify on purpose (`git log --show-signature`,
`git verify-commit`). That issue does not cover two more things seen on
2026-10-01 with the seats in the sandbox (DR-302).

## What happened

- **A signed commit hung.** At 13:24, in the in-progress stage of
  `specialized-portfolio-gate`, the primary seat's
  `git add -A && git commit -q -m ...` ran past the Bash tool's 600-second
  timeout. Its output shows the commit was made (`3409f48`) before the
  command was killed. Other signed commits in the sandbox that day took
  seconds.
- **Stuck `gpg --verify` processes outlived their turns.** Each hung
  `git show` left a `gpg --keyid-format=long --status-fd=1 --verify` process
  behind. Its parent git process had gone, so launchd had adopted it, and it
  waited on a unix socket, probably the gpg agent's or `keyboxd`'s. Thirteen
  of them, started between 12:18 and 13:35, were still running at 13:46,
  when the developer had them stopped.

One explanation, not confirmed: a stuck verify holds a gpg lock or a
connection that a signing `gpg` then waits on. The sandbox denies writes to
`~/.gnupg/trustdb.gpg` and `pubring.kbx`, which gpg may try to update when it
verifies. On the developer's machine, `~/.gnupg/common.conf` routes public
keys through `keyboxd` (`public-keys.d/`, no `pubring.kbx`), and
`trustdb.gpg` is the only key file at the root. A second explanation to rule
in or out: a killed gpg leaves a `*.lock` file at the root of the GnuPG home
(the sandbox allows the `.#lk*` files gpg's dotlock creates), and the next
gpg waits on it. `confinement` denies every entry already at the root when
the seat starts except `S.*` and `.#lk*`, then takes every `*.lock` back out
of that list, so a seat can remove a lock left from before its start. A
third: when no `gpg-agent` or `keyboxd` is running, a seat's `gpg` starts one, and that
daemon inherits the sandbox, outlives the turn, and cannot write
`public-keys.d/` or `trustdb.gpg`; every later gpg, the loop's included,
then talks to a confined daemon.

`seat-background-work-outlives-turn` (done) makes a turn wait for the
background tasks the seat's session tracks. It does not stop a process that
has left its parent and been adopted by launchd, as these verifies were.

## How to reproduce

In a seat session started with the command line `command` in `pair/seats.py`
builds, in a repository whose commits are signed, run
`git -c log.showSignature=true show --stat HEAD` a few times in the
background, then `git commit --allow-empty -m probe`. Check from outside
the sandbox with `pgrep -fl "status-fd=1 --verify"` that verifies are left
running; inside it, `pgrep` cannot list processes.

## Wanted

- Find why a verify hangs in the sandbox and why a signing commit can wait,
  and record the cause in this file and in the docstring of whatever in
  `pair/seats.py` changes.
- Fix the cause in how a seat is started (its sandbox settings, its
  environment, or the git configuration it sees), not by changing the
  developer's GnuPG home.
- A seat's signed commit finishes within seconds, whatever verifies have run
  before it.
- No gpg process a seat starts outlives the seat's turn.

## Out of scope

- Signature display in `git show` and `git log`, which
  `seat-git-signature-check-hangs` handles.
- Turning commit signing off, or letting a seat write the developer's keys,
  trust database or GnuPG configuration.
- Hangs in the loop's own git commands, which run outside the sandbox.

## Done when

- The reproduction above finishes its commit within seconds, and leaves no
  `gpg --verify` running once the seat's turn ends. The developer checks this
  by hand at the desk check, since it depends on their gpg setup.
- A test in `pair/test_pair.py` asserts the mechanism of the fix, for
  instance the setting or environment entry that `confinement` or the seat's
  command line now carries, without needing gpg.
- The cause found is written under a `## Cause` heading in this file.

## The plan

### What planning found

Probes run on 2026-10-01 in a session started with the seat sandbox (gpg
2.5, keys in `keyboxd`), each bounded by a Perl `alarm`:

- `gpg --verify` reaches `SIG_ID`, prints
  `gpg: Fatal: can't open '~/.gnupg/trustdb.gpg': Operation not permitted`,
  and then never exits. It holds a unix socket open, by its path the agent's
  or `keyboxd`'s. The trust models `pgp`, `classic` and `direct` all fail
  the same way, as does `--no-auto-check-trustdb`.
- With `--trust-model always`, the same verify prints `GOODSIG` and
  `VALIDSIG` and exits 0 in 20 ms. It reports the key as `[unknown]`, so
  git shows `%G?` as `U` rather than `G`. A seat never decides on trust, so
  this costs nothing.
- Signing (`gpg -bsau <key>`) takes about 0.17 s alone, with one verify
  hanging, and with 13 hanging. So the stuck verifies do not block a signature
  directly, and the first explanation above is not borne out. The second does
  not apply, because no lock file is involved. The third is unconfirmed:
  the agent and `keyboxd` were already running.
- The repository has no hooks. The session log of the hung commit is gone:
  `.pair/primary.jsonl` now holds a later session. So why `3409f48`'s
  command waited after the commit was made is still unexplained.

The verify hang has a cause: gpg opens `trustdb.gpg` for writing, the
sandbox refuses, and gpg's fatal exit then blocks. Killing a hung `git show`
leaves its gpg behind, adopted by launchd. If no verify hangs, none is left
behind.

### Change

1. **`pair/seat-gpg`**, a new executable shell script:
   `exec "${PAIR_SEAT_GPG:?}" --trust-model always "$@"`. Its docstring-style
   header comment states the cause above. It lives beside `seats.py` and is
   referenced through `Path(__file__)`, so a seat's edits to its worktree
   copy never change the program the seat runs.
2. **`confinement` in `pair/seats.py`** builds `Confinement.gitconfig`, the
   text of a global git config file. It includes the developer's own global
   files (`$GIT_CONFIG_GLOBAL` if set, else `$XDG_CONFIG_HOME/git/config`
   and `~/.gitconfig`, in git's order), then sets `log.showSignature =
   false` and `gpg.program` and `gpg.openpgp.program` to the script.
   `PAIR_SEAT_GPG` in `env` names the real gpg (`real_gpg`). git reads
   `gpg.openpgp.program` and `gpg.program` into one setting, and the last one
   read wins, so the file sets both, and the real gpg is the last line of
   `git config --get-regexp '^gpg\.(openpgp\.)?program$'` in `cwd`, else
   `shutil.which("gpg")`. If that is the script itself (a seat started by a
   seat), the outer seat's `PAIR_SEAT_GPG` is taken. The gpg entries are
   added only when a gpg is found, whether or not the repository signs,
   because a commit signed elsewhere hangs a verify just the same. The
   `GIT_CONFIG_COUNT` entry for `log.showSignature` is gone (see Notes).
3. **`ClaudeSeat`** writes `gitconfig` to `<role>.gitconfig` in the log
   directory, which is in the developer's checkout and outside the seat's
   writable area, and points the seat's `GIT_CONFIG_GLOBAL` at it.
4. **The issue file** gets the `## Cause` heading.

### Tests (`pair/test_pair.py`)

In `ConfinementTest`, each test sets the developer's global config to a file
of its own (`GIT_CONFIG_GLOBAL`, with `GIT_CONFIG_NOSYSTEM=1`), so neither
the developer's `~/.gitconfig` nor an installed gpg decides the outcome.

- `test_signature_display_is_off_and_the_developers_settings_are_kept`: with
  `log.showSignature = true` and `core.abbrev = 12` in the developer's file,
  git under the seat's config reads `false` and `12`.
- `test_the_seats_git_runs_seat_gpg_in_front_of_the_gpg_git_would_run`:
  with `gpg.program` and then `gpg.openpgp.program` set, `PAIR_SEAT_GPG`
  takes the second, and both keys read the script's path; in the other
  order, it takes `gpg.program`.
- `test_a_seat_started_by_a_seat_keeps_the_real_gpg`.
- `test_a_relative_global_config_is_still_included`: a relative
  `GIT_CONFIG_GLOBAL` is included by its absolute path, since git resolves
  a relative `include.path` against the including file. The test runs from
  a directory one level below the test's root, because a long relative
  path from the repository climbs to `/` and resolves the same either way.
- `test_without_a_gpg_the_seat_gets_no_gpg_program`: `shutil.which`
  patched to `None`, no `gpg.program`.
- `test_seat_gpg_runs_the_real_gpg_with_the_always_trust_model`: against a
  stand-in that echoes its arguments; without `PAIR_SEAT_GPG` it exits
  non-zero.

In `ClaudeSeatTest`, `test_the_seat_reads_its_git_config_from_a_file_outside_the_worktree`
has the stand-in `claude` report its `GIT_CONFIG_GLOBAL` (a new `env` step),
which is `<log>/primary.gitconfig` and turns signature display off.

### By hand, at the desk check

`just pair` runs `pair/pair.py` from the main checkout, so `Path(__file__)`
resolves outside every seat's writable area, but it also means a seat
started by the loop before this lands does not carry the change. The
developer runs the reproduction in a session built from this worktree's
`pair/seats.py`.

The reproduction in this file, run in a seat session: the
`git -c log.showSignature=true show` calls finish at once, the commit takes
seconds, and `pgrep -fl "status-fd=1 --verify"` run outside the sandbox
shows nothing.

### Risks

- A gpg that a seat runs directly and that consults the trust database
  (`gpg --verify`, `gpg --list-keys`) still hangs. Only git's calls go
  through the script. A `gpg` earlier on the seat's `PATH` would cover direct
  calls too, but it would wrap the developer's tooling more widely than the
  issue asks. Left out; the `SEAT_GPG` docstring says so.
- A repository's own `gpg.program` or `log.showSignature` outranks a global
  file, so it would win over the seat's. None is set in stereorepo.
- `--trust-model always` on a signing call is harmless, since signing does
  not consult trust, but it is checked by hand at the desk check through the
  reproduction's commit.
- If the commit hang has a cause other than verifies, this does not fix it.
  The desk check is where that would show, and a new backlog Issue would
  then record it.

## Cause

In the seat's sandbox, `~/.gnupg/trustdb.gpg` is read-only. `gpg --verify`
opens it for writing under every trust model that consults it, prints
`Fatal: can't open '…/trustdb.gpg': Operation not permitted`, and then
never exits, holding a socket to the agent or `keyboxd`. A `git show` or
`git log` that shows signatures waits on it. When the Bash tool kills git at
its timeout, launchd adopts the gpg, which goes on waiting: those were the
thirteen verifies. Under `--trust-model always`, gpg does not open the trust
database, and the verify ends in milliseconds.

The signed commit that hung at 13:24 is not explained. Signing took about
0.17 s alone and with 13 verifies hanging, and the session log that would
show what the command waited on is gone.

## Notes

- **The plan changed: a global config file, not `GIT_CONFIG_COUNT`
  entries.** In this seat's Bash, `GIT_CONFIG_COUNT` was `4`, with four
  `safe.directory` entries and no `log.showSignature`, although the loop
  that started the seat sets that entry (it was restarted after
  `seat-git-signature-check-hangs` landed at 13:54, and its other
  environment, such as `UV_TOOL_DIR`, does reach Bash). Claude Code's
  sandboxed Bash writes its own `GIT_CONFIG_*` entries from index 0, so the
  seat's were never seen there. That issue's override never took effect in
  a seat's shell; this one replaces it. `GIT_CONFIG_GLOBAL` is not one the
  sandbox sets, so it passes through as `UV_TOOL_DIR` does; the desk check
  confirms it in a real seat. The price is precedence: a global file is
  outranked by the repository's own config, where the env entry would have
  outranked everything.
- **Checked live in this seat's sandbox**, with the config file
  `confinement` writes for this worktree: `git -c log.showSignature=true
  show --stat HEAD` printed a good signature and exited in 0.02 s, and
  `git log --format=%G?` showed `U` for the signed commits. The same verify
  through the plain gpg hung until killed. Signing through `pair/seat-gpg`
  (`-bsau <key>`) printed `SIG_CREATED` at once.
- The developer's checkout has no `~/.config/git/config`. An `include.path`
  to a missing file is ignored by git, so the file names it anyway.
- For the desk check: the loop runs from the main checkout, so seats started
  before this lands still have the old environment. After landing, the next
  seat's `GIT_CONFIG_GLOBAL` should read `.pair/<role>.gitconfig`.
