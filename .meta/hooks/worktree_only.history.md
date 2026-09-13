# History

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Receipt: `<path>::<symbol>`
-->

### Command line token blocklist allowed shell operator escapes

Scanning command lines for prohibited tokens failed because bash syntax encompasses
abbreviated options, command substitution, process substitution, and semicolons
glued to words (solorepo's #87). Established: replaced the token blocklist with a positive grammar
of allowed commands and exact per-subcommand option tables (solorepo's DR-110).

Receipt: `.meta/checks/probes.py::hook_probes`

### Review subagent scratch files blocked outside the worktree

Blocking all paths outside the repository root prevented review subagents from
reading tool outputs and scratch results written under the harness's project
directory, causing reviews to stall (solorepo's #99). Established: `outside()` explicitly permits
reads within the harness project directory (`~/.claude/projects/`) while continuing
to guard `~/.config` and `.git/`.

Receipt: `.meta/checks/probes.py::hook_probes`

### Subcommand option leakage across git subcommands

Options valid for one subcommand (such as `-C` context in `git grep`) were at
risk of being accepted for subcommands where they had dangerous side effects
(such as `git -C <dir>` repointing the working tree). Established: options are
declared and validated per subcommand via `GIT` and `TAKES_VALUE`.

Receipt: `.meta/checks/probes.py::hook_probes`

### Double-quoted regex patterns and escape sequences failed grammar

Reviewers frequently typed double-quoted arguments (such as `"a|b"` or `"\s+"`)
containing characters bash does not expand in double quotes, leading to generic
refusals across review runs (solorepo's #117, solorepo's #197, solorepo's #242). Established: `words_of()` distinguishes
literal quote contents from active expansions, and `plain_form()` derives valid
single-quoted alternatives.

Receipt: `.meta/checks/probes.py::hook_probes`

### Redirection file descriptors corrupted nearest-command suggestions

Cutting commands at redirection operators (`>`) left preceding file descriptor
digits attached to arguments (e.g. `git show x:y 2>/dev/null` produced `git show x:y 2`),
yielding valid but semantically unintended command suggestions (solorepo's #117, solorepo's #146, solorepo's #197).
Established: `before_operator()` strips attached file descriptor digits when truncating
at redirection boundaries.

Receipt: `.meta/checks/probes.py::hook_probes`

### Generic refusals caused multi-turn reviewer command guessing

Refusing non-conforming commands without suggesting the conforming alternative
caused autonomous reviewers to spend multiple turns guessing acceptable syntax
(solorepo's #144). Established: `plain_form()` deterministically computes and derives the
nearest conforming command by stripping unauthorized options, normalizing quotes, and
dropping operators.

Receipt: `.meta/checks/probes.py::hook_probes`
