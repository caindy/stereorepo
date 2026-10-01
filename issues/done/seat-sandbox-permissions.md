---
difficulty: developer
---

# Run the seats in a sandbox confined to the worktree

The seats run with a prefix allow-list (`ALLOWED` and `DISALLOWED` in
`pair/seats.py`). In the booktutor spike (hypothesis H9) it produced 75
permission denials in 81 turns, none of which blocked anything dangerous: 62
were compound shell commands built from allowed parts, which prefix rules
cannot express, and 6 were the secondary seat deliberately breaking code to
check that a test fails without the fix. The guarantees that mattered were
held by the loop's own checks after each turn, not by permissions.

## Wanted

- Replace the `Bash(...)` entries of `ALLOWED` with a sandbox, so that any
  shell command runs without a permission prompt and its file writes are
  confined to:
  - the seat's working directory (the pair worktree, taken from where the seat
    runs, not a hard-coded `worktrees/pair`);
  - the parts of the repository's git common directory
    (`git rev-parse --git-common-dir`) that `git commit` in a worktree writes:
    objects, the worktree's own git directory (index and HEAD), and the refs and
    reflogs under `pair/`. Not the whole directory: `hooks/`, `config` and
    `refs/heads/main` stay read-only, because the loop runs git there outside
    the sandbox;
  - the system temporary directory;
  - the caches the gate's tools write to (at least `uv`'s and `cargo`'s), found
    by running `just gate` inside a seat session.
- Network stays allowed.
- Claude Code's sandbox confines Bash only. Keep the non-Bash tools allowed
  (Read, Edit, Write, WebFetch, WebSearch and the rest), and confirm that
  Edit and Write outside the working directory are still refused under the
  permission mode the seat uses.
- `command()` takes no working directory today. Give it what it needs to
  name the write locations (the working directory, or the paths themselves)
  rather than reading the process's own `cwd`, so the test can pass them in.
- Keep `DISALLOWED` as it is: what the loop owns (push, merge, rebase, switch,
  checkout, reset, branch, worktree, mv, stash). Confirm the deny list still
  applies under the permission mode the sandbox uses, including to a deny-listed
  command inside a compound one (`cd pair && git push`).
- Prefer Claude Code's own sandboxing, passed on the command line `command`
  in `pair/seats.py` builds (for instance `--settings` with inline JSON, since
  `CONTEXT` loads only the project's settings), so it needs nothing installed
  on the developer's machine. Fall back to an OS-level sandbox only if Claude
  Code's cannot confine writes. Record the choice and why in a Decision Record.

## Out of scope

Other harnesses' adapters; restricting network access beyond what the chosen
sandbox does by default; changing what the loop checks after each turn.

## Done when

- `pair/test_pair.py` asserts the command line `command` builds: the sandbox
  settings with each write location above, the deny list, and an `ALLOWED`
  that holds no `Bash`, `Edit`, `Write` or `NotebookEdit` entry.
- The Decision Record exists and `just gate` passes.
- The developer checks it by hand at the desk check, since a mistake here
  widens what an unattended seat can do on their machine. In one seat session
  started with that command line: a compound shell command in the worktree runs
  without a denial; `git commit` succeeds; `just gate` runs; a write outside
  the allowed locations fails, both from Bash and with the Write tool (for
  instance to the main checkout, or to a new file directly under `$HOME`);
  `git push`, alone and inside a compound command, is refused; and a Bash
  write to the common directory's `hooks/` or `config` fails, as does
  `git update-ref refs/heads/main HEAD`, and a write to the GnuPG home's
  `gpg.conf` or `gpg.conf-2`, while a signed `git commit` still works.

## The plan

The steps below were the plan. Where the work showed it wrong, *As built*
says what changed.

Claude Code's sandbox can do this on macOS with nothing installed (Seatbelt).
The settings keys come from the Claude Code docs, as read on 2026-10-01:

- `sandbox.enabled: true` and `sandbox.autoAllowBashIfSandboxed: true` run
  every Bash command without a prompt;
- `sandbox.allowUnsandboxedCommands: false` stops a seat from retrying a
  failed command outside the sandbox (`dangerouslyDisableSandbox`);
- `sandbox.failIfUnavailable: true` makes a session fail rather than run
  unsandboxed;
- `sandbox.filesystem.allowWrite` adds write paths beyond the working
  directory and the per-user temporary directory, which the sandbox allows
  by default;
- deny rules are still honoured when sandboxed Bash is auto-allowed, and
  compound commands are split before matching, so `DISALLOWED` covers
  `cd pair && git push`;
- `--settings '<json>'` merges over the project settings that
  `--setting-sources project` loads. `.claude/settings.json` is `{}` today.

### Steps

1. **`pair/seats.py`**
   - Drop the `Bash(...)` entries from `ALLOWED`. Leave `DISALLOWED` as it is.
   - Add `writable(cwd: Path) -> list[Path]`. With `common` from
     `git rev-parse --path-format=absolute --git-common-dir` and `gitdir`
     from `git rev-parse --absolute-git-dir`, both run in `cwd`, it returns
     `common/objects`, `gitdir` (the worktree's own `worktrees/<name>/`),
     `common/refs/heads/pair` and `common/logs/refs/heads/pair`, then `uv`'s
     cache (`uv cache dir`, skipped if `uv` is not on `PATH`) and `cargo`'s
     home (`$CARGO_HOME`, or else `~/.cargo`). Never `common` itself: see
     Risks. Anything more that step 3 finds goes here too, at the narrowest
     path that works.
   - Give `command()` a required `writable: list[Path]` parameter. It adds
     `"--settings", json.dumps({"sandbox": {...}})`, with `allowWrite` holding
     those paths as strings. `command()` stays pure, so the test can pass
     paths in.
   - `ClaudeSeat.__init__` calls `command(..., writable=writable(cwd))`.
   - Give `command()`'s docstring a short note on why Bash runs in the sandbox
     instead of under an allow-list, and point it to the Decision Record.
2. **`pair/test_pair.py`, `SeatCommandTest`**
   - Pass `writable=[Path("/r/.git"), Path("/c/uv")]` and parse the JSON that
     follows `--settings`. Assert `enabled`, `autoAllowBashIfSandboxed`,
     `failIfUnavailable`, `allowUnsandboxedCommands is False`, and that `allowWrite` holds exactly
     those paths.
   - Assert that `ALLOWED` holds no entry starting `Bash(`, and that every
     `DISALLOWED` entry follows `--disallowedTools`.
   - Add one test of `writable()` on a real repository with a worktree on a
     `pair/...` branch: it holds the main repository's `.git/objects` and the
     worktree's `.git/worktrees/<name>`, and it holds neither the common
     directory itself nor anything containing `hooks` or `config`. Then, in
     that worktree, run a plain `git commit` after
     making only those paths writable (`chmod -R a-w` on the rest of the
     common directory, restored in `tearDown`), so the test shows the list
     is enough for a commit and not just plausible.
3. **Find the caches by trying them.** Start one seat session by hand with
   the new command line in `worktrees/pair`, and run `just gate`. Every
   sandbox write denial names a path; add each path to `writable()`, or
   explain in the Decision Record why it is left out.
4. **Decision Record.** Write `.meta/assertions/decisions/DR-302.yaml`,
   choosing Claude Code's sandbox over an allow-list and over an OS-level
   sandbox (`sandbox-exec` or a container). Give the H9 numbers as the context,
   and as the falsifier, a seat that writes outside the allowed paths or pushes.
   Re-render the decisions index, then run `just gate pair` and `just gate`.

### As built

- `writable()` became `confinement(cwd) -> Confinement`, with `allow`,
  `deny`, `env` and `sockets`. Claude Code's sandbox grants a worktree's git
  common directory on its own, less `hooks/` and `config`, so a narrow
  allow-list could not keep the rest read-only. `confinement` instead names
  what to deny (`filesystem.denyWrite`, which wins over an allowed path that
  holds it): every entry of the common directory except `objects`, `refs`,
  `logs` and `worktrees`; every local branch outside `pair/`; every other
  worktree.
- `Edit`, `Write` and `NotebookEdit` left `ALLOWED` too. A bare entry
  allows them anywhere, which would have undone `acceptEdits`' hold on the
  working directory.
- `uv`'s tool directory is moved into its cache with `UV_TOOL_DIR`, so a
  seat cannot change a tool the developer installed. Of `cargo`'s home, only
  `registry/` and `git/` are allowed.
- Signing works through the agent and `keyboxd` sockets
  (`network.allowUnixSockets`) and lock files in the GnuPG home's root, so
  the root is allowed and every other entry in it is denied by name.
  `gpg` also reads `gpg.conf-2`, `gpg.conf-2.5` and `gpg.conf-2.5.21`
  before `gpg.conf` (checked with gpg 2.5.21), so `versioned_gpg_conf()`
  denies those names too.
- `network.allowedDomains: ["*"]` keeps the network as open as before.
- `ps` cannot run in the sandbox, so the tests that inspect processes skip
  themselves there; the loop's own gate, outside the sandbox, runs them.
- Static analysis still refuses some commands before the sandbox sees them
  (a variable set from `$(...)`); counting those is
  `issues/backlog/seat-unanalysable-command-denials.md`.

### What the probes showed

Step 3 ran as five seat sessions started with `command()`'s own command line
(on 2026-10-01). They confirmed the following:

- A compound command runs, and `git push`, alone or after `cd`, is refused.
- The Write tool is refused outside the worktree once `ALLOWED` has no bare
  `Write`.
- Writes to the common directory's `HEAD`, `hooks/`, other branches and
  `~/.cargo/bin/` all fail.
- `git commit-tree -S` signs. Writes to `~/.gnupg/gpg-agent.conf` and
  `~/.gnupg/gpg.conf-2` fail.
- `curl https://pypi.org/simple/` answers 200.
- `just gate meta`, `just gate pair`, `just gate python-seed` and
  `just gate rust-seed` all pass in the sandbox. One meta step, *cited schema
  slots*, reported that its `git log` timed out after 30 seconds, and the
  gate counts it as a step that could not run.

`git verify-commit` hangs in the sandbox. A seat has no need of it.

Left open:

- **New worktree entries.** A seat can create a new entry under the common
  directory's `worktrees/`, because the denials name only the worktrees that
  exist when the seat starts. `git worktree prune` removes such an entry, and
  git reads no code from one, so it is not denied.
- **New branches outside `pair/`.** For the same reason, a seat can create a
  branch that did not exist when it started: the probes created
  `refs/heads/probe-sandbox`, below. Denying `refs/heads/` itself would also
  deny `refs/heads/pair/`, since a denial wins over an allowance that it
  holds. A new branch moves no branch that exists, so it is left open.
- **Probe leftovers for the developer.** The probes left four things this seat
  could not remove, because each lies outside the working directory:
  - a branch `refs/heads/probe-sandbox`;
  - a file `~/probe-write-tool.txt`;
  - an empty file `.git/worktrees/flight-probe-check`;
  - `~/.cache/uv/seat-tools`, which is harmless.

  Delete the first three with
  `git update-ref -d refs/heads/probe-sandbox`, `rm ~/probe-write-tool.txt`
  and `rm .git/worktrees/flight-probe-check`.

### Risks

- **The git common directory is a way out of the sandbox.** Its `hooks/`
  and `config` (`core.hooksPath`, `core.fsmonitor`, aliases) run code in
  every git command the loop runs outside the sandbox, and a writable
  `refs/heads/main` lets a seat move `main` with `git update-ref`, which
  `DISALLOWED` does not list. So `confinement()` denies the rest of the
  common directory by name (see *As built*). If a commit ever needs
  more (`packed-refs`, a lock file at the root), allow that one file and say
  so in the Decision Record; `git gc --auto` failing to write is harmless.
  The common directory matters beyond the loop, too: its `hooks/` and
  `config` also govern the developer's main checkout.

- **What the sandbox does not confine.** The loop runs `just gate` and
  `just deliver` in the worktree outside the sandbox (`pair/pair.py`), so
  code a seat writes there runs unsandboxed when the loop gates it. The
  sandbox confines the seat's own session, not the code it produces. That
  is the issue's scope; the Decision Record says so plainly, so that the
  sandbox is not mistaken for containment of seat-written code.

- **Signed commits.** The repository signs commits with gpg. Under the
  sandbox, `git commit` must reach the gpg agent's socket and may write to
  `~/.gnupg`. If step 3 shows signing fails, allow that socket
  (`sandbox.network.allowUnixSockets`) rather than turning signing off. That
  widens the sandbox by one known path, which the Decision Record must state.
- **Write and Edit tools.** These are confined by `acceptEdits`, not by the
  sandbox: in `-p` mode, a write outside the working directory needs a prompt,
  and a prompt is a denial. The desk check tests that this holds.
- **A gate that grows.** If a later change makes `just gate` write somewhere
  new, a seat's gate run fails with a sandbox denial. The loop's own gate
  runs outside the sandbox, so nothing lands wrongly; the seat reports the
  path, and the fix is one more entry in `confinement()`.
- **A key name that changes.** If Claude Code ignores an unknown key without
  an error, the sandbox would silently not apply. `sandbox.failIfUnavailable:
  true` makes the session fail instead of running without a sandbox; set it.
