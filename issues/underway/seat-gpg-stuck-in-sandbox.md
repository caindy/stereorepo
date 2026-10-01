# Keep gpg from hanging a seat's signed commit in the sandbox

`seat-git-signature-check-hangs` turns off signature display for the seats,
so `git show` and `git log` stop verifying signatures. It does not cover two
more things seen on 2026-10-01 with the seats in the sandbox (DR-302).

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
verifies.

## How to reproduce

In a seat session started with the command line `command` in `pair/seats.py`
builds, in a repository whose commits are signed, run
`git -c log.showSignature=true show --stat HEAD` a few times in the
background, then `git commit --allow-empty -m probe`. Check with
`pgrep -fl "status-fd=1 --verify"` that verifies are left running.

## Wanted

- Find why a verify hangs in the sandbox and why a signing commit can wait.
- A seat's signed commit finishes within seconds, whatever verifies have run
  before it.
- No gpg process a seat starts outlives the seat's turn.

## Out of scope

Signature display in `git show` and `git log`, which
`seat-git-signature-check-hangs` handles, and turning commit signing off.

## Done when

The reproduction above finishes its commit within seconds, and leaves no
`gpg --verify` running. The developer checks this by hand at the desk check,
since it depends on their gpg setup.
