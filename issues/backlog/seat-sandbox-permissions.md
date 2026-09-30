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

- Replace the allow-list with a sandbox: file writes confined to the
  worktree (`worktrees/pair`) and the system temporary directory, network
  allowed, and permission prompts otherwise bypassed.
- Keep a short deny list for what the loop owns: `git push`, `git merge`,
  `git rebase`, `git switch`, `git checkout` of another branch,
  `git worktree`, and deleting branches.
- Prefer Claude Code's own sandboxing, passed on the command line `command`
  in `pair/seats.py` builds, so it needs nothing installed on the developer's
  machine; fall back to an OS-level sandbox only if Claude Code's cannot
  confine writes. Record the choice and why in a Decision Record.

## Out of scope

Other harnesses' adapters, and restricting network access beyond what the
chosen sandbox does by default.

## Done when

`pair/test_pair.py` asserts the command line `command` builds (the sandbox
settings and the deny list), and `just gate` passes. The developer checks it
by hand at the desk check, since a mistake here widens what an unattended
seat can do on their machine: in one seat session started with that command
line, a compound shell command in the worktree runs without a denial, a
write outside the worktree fails, and `git push` is refused.
