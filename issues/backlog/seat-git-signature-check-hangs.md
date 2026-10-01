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
the developer's own git config says. One way: the seat's environment sets
`GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=log.showSignature` and
`GIT_CONFIG_VALUE_0=false`, which overrides the setting for the seats only.
A signed `git commit` still works in the sandbox.

## Out of scope

Making signature verification itself work in the sandbox, and changing the
developer's own git config.

## Done when

A test in `pair/test_pair.py` asserts that a seat's environment turns
signature display off, and the developer finds at a turn of the next run
that a seat's `git show --stat HEAD` returns within seconds.
