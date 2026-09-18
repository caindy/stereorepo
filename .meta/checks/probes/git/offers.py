"""What a refusal offers instead: the nearest conforming command `worktree_only` derives, and the tool it names when a command belongs to another.
"""

OFFERS = (
    ("an operator or an option off the list has a nearest command the hook would have taken "
     "(solorepo's #144)", (
        ("gh pr diff 86 | head", "gh pr diff 86"),
        ("gh pr diff 86 > .meta/say", "gh pr diff 86"),
        ("git status;git -c core.pager=id log -1", "git status"),
        ("git log -1&&git -c core.pager=id log", "git log -1"),
        ("git log -1 --output=.meta/say", "git log -1"),
        ("gh pr view 87 --repo other/repo --json body", "gh pr view 87 --json body"),
        ("git grep -rn 'authority.yaml' 0123abc -- .meta/", "git grep authority.yaml 0123abc -- .meta/"),
        ("python3 .meta/check_pr.py 87 --watch", "python3 .meta/check_pr.py 87"),
        ("git grep -n 'a.*' -- README.md | wc -l", "git grep -n 'a.*' -- README.md"),
    )),
    ("a program off the list, a heredoc, a git that never reached a subcommand, the channel reached "
     "with an operator, and a command cut inside an argument have no nearest command (solorepo's #146)", (
        ("python3 .meta/check.py", None),
        ("true", None),
        ("curl https://example.com", None),
        ("git -c core.pager=id log -1", None),
        ("git clone --upload-pack='sh -c id' /some/repo /tmp/out", None),
        (".meta/say/post raise 1 x 2 <<EOF\nbody\nEOF", None),
        (".meta/say/post --role reviewer review 146 --approve < body.md", None),
        ("git show HEAD~1:.meta/hooks/worktree_only.py", None),
        ("git log HEAD~5..HEAD", None),
    )),
    ("a redirect's file descriptor goes with the redirect; a blank before the digits makes them an "
     "argument again, and `-n 2` is a count that stays (solorepo's #197)", (
        ("git show main:.meta/say 2>/dev/null", "git show main:.meta/say"),
        ("gh pr view 117 --json files,commits 2>&1 | head -100", "gh pr view 117 --json files,commits"),
        ("git log -n 2 > /tmp/out", "git log -n 2"),
        ("git ls-files .meta | head -30", "git ls-files .meta"),
    )),
    ("a word carrying a single quote has no offer rather than a mangled one", (
        ('git grep -n "it\'s" -- README.md | wc -l', None),
    )),
    ("a refusal about the pair and not the pattern offers the same words in the pair that is taken "
     "(solorepo's #242)", (
        ('git grep -n -E "^\\s*def blocked" -- .meta',
         "git grep -n -E '^\\s*def blocked' -- .meta"),
        ('git grep -n -E "\\bdef\\b" HEAD -- .meta | head -20',
         "git grep -n -E '\\bdef\\b' HEAD -- .meta"),
        ('git log --grep="fix!" -1', "git log '--grep=fix!' -1"),
    )),
    ("an escape inside double quotes is read, so the offer is the word bash would have made", (
        ('git grep -n "a\\$b" -- README.md', "git grep -n 'a$b' -- README.md"),
        ('git grep -n "a\\"b" -- README.md', 'git grep -n \'a"b\' -- README.md'),
    )),
    ("an unescaped `$` or backtick has no offer: what bash puts there is the output of something", (
        ('git grep -n "$(id)" -- README.md', None),
        ('git grep -n "`id`" -- README.md', None),
    )),
)
"""Each refused command with the nearest command its refusal names, or `None` where none is derivable (solorepo's #144).

A group is `(name, rows)` and a row is `(command, offer)`. An operator or an
option off the list has a nearest command the hook would have taken. A program
off the list, a heredoc, and a git that never reached a subcommand have none,
and offering one would be the guess the offer replaces; so has the channel
reached with any operator, and so has a command cut at a character that
expands inside an argument rather than ending it. A redirect's file descriptor
is the redirect's, so it goes with it, while a blank before the digits makes
them an argument again: the `2` of `2>/dev/null` is dropped with the redirect,
and the `2` of `-n 2` is a count that stays.

A word carrying a single quote has only `requote`'s single quotes to be
spelled with, so it has no offer rather than a mangled one. A refusal on a
character a double quote does not stop is about the pair and not the pattern,
so the offer is the same words in the pair that is taken (solorepo's #242), and
`\\` is the one this happens on, because it is what a regex is made of: `\\s`,
`\\b`, `\\.`. What is offered is the word bash would have made, which is why an
escape is read rather than passed through: `"a\\$b"` is `a$b`, and the hook
would take `'a\\$b'` just as readily while asking for something else; single
quotes either way, since a quoted `"` is a character of the word and single
quotes are where it needs no escape at all. A `$` or a backtick that is not
escaped has no offer: what bash puts there is the output of something, and no
spelling of those characters in single quotes asks for it. Every offer must
itself pass `command_allowed`, or the refusal sends the reviewer to a second
refusal.
"""


INSTEAD = (
    ("python3 .meta/check.py", "gh pr checks"),
    ("grep -n x README.md", "Grep"),
    ("wc -l README.md", "Read"),
)
"""Each program off the list with the tool its refusal names in its place (solorepo's #144, solorepo's #197).

A row is `(command, name)`. A program off the list has no nearest command, so
its refusal says where what it wanted is instead: the gate's result at `gh pr
checks`, the Grep tool for a search of the worktree, and the Read tool for a
file and a count.
"""
