# History

Each account names the symbol by the module of `.meta/lib/worktree_only/` that holds it
(solorepo's DR-217); the hook at `.meta/hooks/worktree_only.py` is the entry.

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Evidence: `<path>::<symbol>`
-->

### Command line token blocklist allowed shell operator escapes

Scanning command lines for prohibited tokens failed because bash syntax encompasses
abbreviated options, command substitution, process substitution, and semicolons
glued to words (solorepo's #87). Established: replaced the token blocklist with a positive grammar
of allowed commands and exact per-subcommand option tables (solorepo's DR-110).

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### Review subagent scratch files blocked outside the worktree

Blocking all paths outside the repository root prevented review subagents from
reading tool outputs and scratch results written under the harness's project
directory, causing reviews to stall (solorepo's #99). Established: `paths.outside()` explicitly permits
reads within the harness project directory (`~/.claude/projects/`) while continuing
to guard `~/.config` and `.git/`.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### Subcommand option leakage across git subcommands

Options valid for one subcommand (such as `-C` context in `git grep`) were at
risk of being accepted for subcommands where they had dangerous side effects
(such as `git -C <dir>` repointing the working tree). Established: options are
declared and validated per subcommand via `grammar.GIT` and `grammar.TAKES_VALUE`.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### Double-quoted regex patterns and escape sequences failed grammar

Reviewers frequently typed double-quoted arguments (such as `"a|b"` or `"\s+"`)
containing characters bash does not expand in double quotes, leading to generic
refusals across review runs (solorepo's #117, solorepo's #197, solorepo's #242). Established: `shell.words_of()` distinguishes
literal quote contents from active expansions, and `grammar.plain_form()` derives valid
single-quoted alternatives.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### Redirection file descriptors corrupted nearest-command suggestions

Cutting commands at redirection operators (`>`) left preceding file descriptor
digits attached to arguments (e.g. `git show x:y 2>/dev/null` produced `git show x:y 2`),
yielding valid but semantically unintended command suggestions (solorepo's #117, solorepo's #146, solorepo's #197).
Established: `shell.before_operator()` strips attached file descriptor digits when truncating
at redirection boundaries.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### Generic refusals caused multi-turn reviewer command guessing

Refusing non-conforming commands without suggesting the conforming alternative
caused autonomous reviewers to spend multiple turns guessing acceptable syntax
(solorepo's #144). Established: `grammar.plain_form()` deterministically computes and derives the
nearest conforming command by stripping unauthorized options, normalizing quotes, and
dropping operators.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### Nearest-command offers that were a different command from the one refused

On solorepo's #146 the refusal's nearest command was twice well-formed, accepted
by the hook, and a different command from the one refused: the channel reached
with an operator (`.meta/say/post --role reviewer review 146 --approve < body.md`),
cut at the operator, was offered as the review without its body; and a command
holding a character that expands inside an argument rather than ending it
(`git show HEAD~1:.meta/hooks/worktree_only.py`, `git log HEAD~5..HEAD`), cut at
the `~`, was offered with the argument truncated. Established: `grammar.plain_form()`
offers nothing for a channel program, whose options are its own, and nothing for
a command `shell.words_of()` refuses on a character inside a word, so an offer is only
ever the refused command with an operator's tail or an option off the list
removed and its words respelled by `shell.requote`, in single quotes where a word needs
quoting at all (solorepo's #144, solorepo's #242).

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### Programs off the list refused without naming the tool in their place

A program off the list has no nearest command, so its refusal offered nothing,
and on solorepo's #117 the reviewer reached for `grep` and `wc` seven times to
search and count a file before turning to the tools that do (solorepo's #144,
solorepo's #197). Established: `grammar.INSTEAD` maps `python3 .meta/check.py`, `grep`
and `wc` to where what each wanted is — the gate's result at `gh pr checks`, the
Grep tool for a search of the worktree, the Read tool for a file and a count —
and `grammar.command_allowed()` appends it to the refusal.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### A reader input the hook did not recognise was a permit

On solorepo's #452 `paths.targets()` answered `["."]` — the worktree — for a reader
input naming none of the keys it knew, so `glob` carrying only `pattern` was
allowed whatever the pattern said, `~/.gemini/oauth_creds.json` among them, the
file the boundary exists to keep out. The same default made every future
spelling a permit: `google-github-actions/run-gemini-cli@v0` floats, so a
renamed or added path argument reopened the boundary with no symptom, and no
probe could notice, every row being written in the spellings the hook already
checked. Established: `paths.READERS` names `pattern` and pairs each key with the tool
that sends it, and a reader naming none of its keys is refused rather than
resolved to the worktree — `paths.SEARCHES` is the one exception, a search with no
path searching the worktree the bound permits anyway.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### A glob pattern was resolved as the path it is not

`paths.outside()` handed a pattern to `pathlib`, where every matcher metacharacter is
an inert literal component, so on solorepo's #452 an `include` of
`**/.git/config` passed both clauses: the literal `**` stood between the root
and `.git`, while a matcher for which `**` spans no directory reads
`.git/config`. Established: `paths.outside_pattern()` bounds a pattern by the
components before its first metacharacter — the deepest directory every match
lies under — and refuses a component named `.git` outright.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### A working directory was checked by the predicate written for reads

The `dir_path` check reused `paths.outside()` on solorepo's #452, so it carried two
clauses a working directory has no business with: a command ran in a harness
scratch directory while the refusal beside it said the reviewer runs its
commands in the worktree and nowhere else, and a `dir_path` of `.git` was
refused for holding a token the allowed grammar reads nothing of from there.
Established: `paths.elsewhere()` is the working directory's own predicate — inside the
root, no scratch exemption, no `.git` clause.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`

### A pattern beginning with a metacharacter was bounded by nothing

The prefix rule stops at the first component holding a metacharacter, so on
solorepo's #452 a pattern whose *first* component held one had an empty literal
prefix, which `paths.outside(".")` read as the worktree and allowed whatever followed:
an `include` of `**/../../etc/passwd` on `read_many_files`, and a `pattern` of
`{/etc,.}/passwd` on `glob`, one of whose alternatives is a root of its own. The
prose said the same gap — the components before the first metacharacter are "the
deepest directory every match lies under", which for `**/../x` is no directory at
all. Established: what the prefix rule cannot see past is refused wherever it
appears, as `.git` already was — a component that can match `..` (`paths.ascends`,
which reads the wildcard spellings `..*` and `.?` as the ascent they can match),
and brace alternation, whose grammar this hook does not hold.

Evidence: `.meta/checks/probes/git/step.py::hook_probes`
