# What bounds every agent on this review

This is the reviewer's container on pull request #<number>
of <repository>, filled by the review door before the session started
(solorepo's DR-264). Everything here holds for the reviewer's own session and
for every agent the review spawns.

**The diff is a file.** `.review/diff.patch` is this pull request's
whole diff, written before the session started. Read it with the Read
tool, which takes an offset and a limit. `gh pr diff` says the same
thing and arrives as its first 2 KB and a path when the diff is large.

**<count> paths in the worktree are trunk's, not this pull request's:**
<paths>. They were replaced with `origin/main`'s
copies before the session, so that what runs here is trunk's. You run
and read them as trunk's; you do not review them by reading them.
`git status` and `git diff` show nothing for a change the pull request
makes to them; a file the pull request adds under them shows as a
staged deletion, which is the restore and not the pull request.
Nothing else under `.meta/lib/` is trunk's: a package the pull request
adds or changes for any other script is in the worktree as the pull
request wrote it, and is reviewed by reading it there.

**The pull request's version of those trunk paths is under `.review/head/`,**
at the same path: `.review/head/.meta/say/post` is what this pull
request's `post` says. That copy is read and never run, and it is the
version to review. `git show <head>:<path>`
says the same thing and costs a turn for each file.

**The shell runs one plain command at a time and nothing else:**
`git log|show|diff|status|grep|ls-files|ls-tree` with plain options,
`gh pr view|diff|checks`, `python3 .meta/check_pr.py`, or
`.meta/say/post` and `.meta/say/move` with their heredoc. No pipes,
redirects or chaining, and nothing the shell would expand: a `$`, a
backtick, a bare glob. Quoting is what stops it, either pair — a
pattern or a glob goes inside one, single quotes where it holds a
`$`, a backtick, a `\` or a `!`, the four a double quote does not
stop here. A regex usually holds the `\` — `\s`, `\b`, `\.` — so
`git grep -n -E '^\s*def blocked' -- .meta` is the pair that is taken
and the same words in a double quote are refused. List the
worktree's files with the Glob tool and a commit's with
`git ls-tree -r --name-only <sha>`, read them with the Read tool and
search with Grep. A refusal names the nearest command it would have
taken, where the one refused has one; that is the command to type
next, rather than a guess at another.

**A Grep of `.review/` needs `path`.** Grep is ripgrep and ripgrep
honours `.gitignore`, which holds `.review/`: a Grep from the root
finds nothing there, including in this file. Pass `.review` or
`.review/head` as Grep's `path` to search the diff or the head's
copies, and read a hit in the worktree as trunk's until you have
checked `.review/head/` for the same path.

**Only the session the review was requested of posts.** An agent hands
its findings back to the session that spawned it; it does not run
`.meta/say/post`, and it resolves no thread.

**An agent reviews the dimension it was given and no other.** The
pass is scoped before it is spawned (solorepo's DR-166): the session
has read the diff itself and named the dimensions it holds, and each
agent has one of them. A sweep for everything, done by an agent asked
for one thing, is the same diff read again for what the session or
another agent already holds — and every agent here runs in the
foreground, so the run waits on it while it does.

**The Technical Writer pass holds prose to the Literate Programming register.**
When the diff touches documentation, docstrings, Decision Records, or markdown
artifacts, evaluate them under `work:personality/technical-writer` and the
Literate Programming rubric (solorepo's DR-175, solorepo's DR-176):
- Spelled out and self-contained. Every citation dereferenced.
- Assume a reader who was not in the conversation and arrives by search years later.
- Apply the reader's test: could someone use this item from its docstring alone
  without reading the argument for it?
- Verify that item docstrings state what to do and invariants without litigating
  against a reviewer, why belonging in module docstrings or Decision Records
  (solorepo's DR-175), and that past incident narratives are in
  `<module>.history.md` (solorepo's DR-171).
