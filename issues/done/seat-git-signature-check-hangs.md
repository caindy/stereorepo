---
difficulty: easy
---

# Keep a seat's `git show` and `git log` from hanging in the sandbox

Since `seat-sandbox-permissions` landed (DR-302), a seat's `git show` or
`git log` never finishes. The developer's `~/.gitconfig` sets
`log.showSignature = true`, so both commands verify each commit's gpg
signature, and that verification hangs inside the seat sandbox, as
`git verify-commit` does. Claude Code gives up after its 120-second Bash
timeout and moves the command to the background, where it keeps running
after the turn ends.

## What happened

On 2026-10-01, in the backlog stage of `gate-failure-goes-to-primary` and of
`specialized-portfolio-gate`, the secondary seat's first command was
`cat <issue>; git show --stat HEAD; ...`. Both times it came back as "Command
did not complete within its 120s timeout". Those turns took 263 and 266
seconds of wall time against 22 and 25 seconds of model time. The median
backlog-stage turn went from 21 seconds before the sandbox to 209 seconds
after. The turns are in `.pair/turns.jsonl` and the seat logs in
`.pair/secondary.jsonl`, in the developer's checkout.

## How to reproduce

Start a seat session with the command line `command` in `pair/seats.py`
builds, in a repository whose commits are gpg-signed, with
`log.showSignature = true` in the global git config, and run
`git show --stat HEAD`.

## Wanted

A seat's `git show` and `git log` return promptly in the sandbox, whatever
the developer's own git config says. `confinement` in `pair/seats.py` adds to
`Confinement.env` a `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n`
entry setting `log.showSignature=false`, which overrides every config file
for the seat's processes only. If the loop's own environment already carries
`GIT_CONFIG_COUNT` entries, the new entry is appended after them rather than
replacing them. The `confinement` docstring says why the entry is there.

A signed `git commit` still works in the sandbox: only display of signatures
changes, not `commit.gpgsign`.

## Out of scope

Making signature verification itself (`git verify-commit`,
`git log --show-signature`) work in the sandbox, and changing the
developer's own git config.

## Done when

- A test in `pair/test_pair.py` builds a `Confinement` for a worktree whose
  repository has `log.showSignature = true` in its config, and asserts that
  `git config --bool log.showSignature`, run in that worktree with
  `confined.env` added to the environment, prints `false`.
- A test asserts that when the environment already holds a
  `GIT_CONFIG_COUNT=1` pair, `confined.env` keeps that pair and adds the
  override as index 1 with `GIT_CONFIG_COUNT=2`.
- At a turn of the next run, a seat's `git show --stat HEAD` returns within
  seconds; the developer sees this in `.pair/turns.jsonl`, but it does not
  hold the Issue back from `main`.

## The plan

One seam: `confinement` in `pair/seats.py`, which already fills
`Confinement.env` (with `UV_TOOL_DIR`). `ClaudeSeat.__init__` copies
`os.environ` and then applies `confined.env`, so the override reaches the
`claude` process and every shell it starts. `command` and `ClaudeSeat` need
no change.

1. In `confinement`, after `env = {}`, read `n = int(os.environ.get("GIT_CONFIG_COUNT", "0"))`
   and set `env["GIT_CONFIG_KEY_{n}"] = "log.showSignature"`,
   `env["GIT_CONFIG_VALUE_{n}"] = "false"` and
   `env["GIT_CONFIG_COUNT"] = str(n + 1)`. The existing pairs stay in the
   copied `os.environ`, so they are kept without being repeated in `env`.
2. Add a paragraph to the `confinement` docstring: the developer's git config
   can set `log.showSignature`, signature verification hangs in the sandbox,
   and the override turns only the display off, so `commit.gpgsign` and a
   signed commit are untouched.
3. Add two tests to `ConfinementTest` in `pair/test_pair.py`:
   - `test_signature_display_is_off_for_the_seat`: set
     `log.showSignature true` in `self.repo`, build `confinement(self.wt)`,
     run `git config --bool log.showSignature` in `self.wt` with
     `{**os.environ, **confined.env}`, and assert it prints `false`.
   - `test_existing_git_config_overrides_are_kept`: set
     `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=core.abbrev`,
     `GIT_CONFIG_VALUE_0=12` in `os.environ` inside
     `unittest.mock.patch.dict(os.environ, ...)`, which restores whatever was
     there before, then assert
     `confined.env` holds `GIT_CONFIG_COUNT=2` and the override at index 1,
     and that `git config core.abbrev` with the merged environment still
     prints `12`.

### Risks

- A malformed `GIT_CONFIG_COUNT` in the loop's environment would raise in
  `int()`. Git itself refuses to run with one, so letting it raise is
  acceptable; no special handling.
- Once this lands, a seat that runs the tests does so with
  `GIT_CONFIG_COUNT=1` and `GIT_CONFIG_KEY_0=log.showSignature` already in
  its environment. So the second test must restore the previous values, not
  pop them (popping, the idiom the gnupg test uses for `GNUPGHOME`, would
  remove the seat's own override for every later test in that process).
  `patch.dict` does this. The first test must not assume the override lands
  at index 0. It checks what git reports, not the index, so it passes either
  way.
- Whether Claude Code's sandboxed Bash passes `GIT_CONFIG_*` through to the
  command is not testable here; the developer's check at the next run's turn
  covers it.

## Notes

Implemented as planned. The override is in `confinement`'s `env`, so it also
reaches anything else built from a `Confinement`; today that is only
`ClaudeSeat`. Inside a seat the tests run with the seat's own override
already at index 0, so the first test's `confinement` writes it again at
index 1; git takes the last value, and the test checks git's answer, not the
index.

The second test also sets `log.showSignature = true` in the repository and
checks that git still reports `false` with the earlier pair in place, and
that `confined.env` leaves index 0 alone. Without the first check, a version
that wrote the key at index 1 but left the count at 1 would have passed.
