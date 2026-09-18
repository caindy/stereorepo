# History

Each account names the symbol by the module of `.meta/lib/signed_channel/` that holds it
(solorepo's DR-217); the hook at `.meta/hooks/signed_channel.py` is the entry.

<!--
### <what failed, as a heading somebody would search for>

<What was observed, and what the change established. Not what changed; the
diff has that.>

Receipt: `<path>::<symbol>`
-->

### One regex over one flat command line was wrong in both directions

The predicate swept substrings over the raw command line with no notion of shell
syntax, so a word being searched for read as a word being run and a word being
mentioned read as a permit (solorepo's #463). `tables.GH_WRITES` matched the `gh api`
inside a quoted `grep` pattern and refused a read that reached nothing; and
`tables.SANCTIONED` cleared the whole line wherever `.meta/say/` or
`.meta/check_pr.py` appeared in it, so `echo "use .meta/say/post instead" &&
curl -X POST <endpoint>` posted unsigned, as did anything after a `&&` whose
first segment happened to run the channel. Established: the line is split on the
shell's own separators, each segment is lexed with `shlex` and judged on its own
by the program it runs, and a segment being sanctioned says nothing about its
neighbours.

Receipt: `.meta/checks/probes/git/step.py::hook_probes`

### A heredoc body was read as the commands its lines spell

Splitting a command line on its separators makes every line of a heredoc body a
segment, and a body the channel carries is prose: a sentence naming the endpoint
became a call to it, and an apostrophe became an unclosed quote
(solorepo's #463). Established: `shell.without_heredocs()` lifts each body out before
the line is split and hands it to the segment that opened it as text that
segment carries, so a body the channel is given is data and a body piped into
`curl` is still that call's.

Receipt: `.meta/checks/probes/git/step.py::hook_probes`
