# Run the seats in a sandbox confined to the worktree

The seats run with a prefix allow-list (`ALLOWED` and `DISALLOWED` in
`pair/seats.py`). In the booktutor spike (hypothesis H9) it produced 75
permission denials in 81 turns, none of which blocked anything dangerous: 62
were compound shell commands built from allowed parts, which prefix rules
cannot express, and 6 were the secondary seat deliberately breaking code to
check that a test fails without the fix. The guarantees that mattered were held
by the loop's own checks after each turn, not by permissions.

Replace the allow-list with a sandbox confined to the worktree: file writes
limited to `worktrees/pair` and `.pair/`, network allowed for package managers,
and permissions otherwise bypassed. Keep a short deny list for what the loop
owns: `git push`, `git merge`, `git rebase`, `git switch`, `git worktree`, and
deleting branches. Which mechanism to use — Claude Code's own sandboxing or an
OS-level one — is open; the spike did not test one.

Done when a seat can run compound shell commands in the worktree without a
denial, cannot write outside it, cannot run the loop's git verbs, and the pair
tests cover the command line `ClaudeSeat` builds.
