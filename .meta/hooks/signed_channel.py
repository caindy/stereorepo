#!/usr/bin/env python3
"""Refuse any path to GitHub that does not sign what it posts (solorepo's DR-069).

A PreToolUse hook, so the harness runs it rather than the agent remembering to.
`.claude/settings.json` denies `gh`'s writing verbs and permits its read-only
ones; this catches everything else that can reach the same endpoint — `curl`, `python`, `wget`, a language's
HTTP client — because a deny list over one binary is not a boundary.

It is a string match over a command line, and string matches lose eventually.
What it buys is that the cheap paths are shut and the remaining ones are
deliberate. The boundary that would actually hold is the credential: a token
reachable only by `.meta/say/` makes the channel the only path by construction rather
than by inspection. That is solorepo's #21 (solorepo's DR-174), and this stands in until it is built.

    echo '{"tool_name":"Bash","tool_input":{"command":"..."}}' | .meta/hooks/signed_channel.py

Exit 2 blocks the call and shows the message to the agent. The predicate is
separate from the plumbing so it can be watched failing without a harness.
"""
import json
import re
import sys

# The endpoint, however it is spelled, and the writing verbs of the CLI that
# wraps it. Reading is not the concern: an unsigned `gh pr view` costs nothing.
#
# `merge` and `close` are here although neither posts text. They are acts by an
# Actor, and GitHub records who performed them — so they go through the channel
# for the same reason a comment does, which is that the record should say which
# Role did it rather than which human owns the credential. `update-branch` is
# the same kind and one further: by hand it defaults to a merge commit GitHub
# authors, which names no Actor at all and fails A19 on the branch it moved
# (solorepo's DR-113). The stack extension's verbs that write — link, merge, submit and
# the rest — are acts of the same kind (solorepo's DR-100); `submit` also opens pull
# requests unsigned. Its views stay open.
#
# `workflow run` is the newest of them and the same kind again: it starts a Job,
# which GitHub records as dispatched by an account, and the Job then writes with
# a credential of its own. `.meta/say/move dispatch` is the verb for it
# (solorepo's DR-151), and the refusal of the raw spelling is the other half of
# that pattern — a verb supplied while the raw path stays one keystroke away
# leaves the act attributable to whoever holds `gh`. `gh run list` and
# `gh workflow view` read and stay open.
ENDPOINT = re.compile(r"api\.github\.com|graphql\.github\.com")
GH_WRITES = re.compile(r"\bgh\s+(api|pr\s+(comment|review|create|edit|merge|close|update-branch)"
                       r"|issue\s+(create|comment|edit|close)"
                       r"|workflow\s+run"
                       r"|stack\s+(link|merge|submit|unstack|delete|push|sync|rebase))\b")
# The channel is a directory of programs over one signing primitive (solorepo's DR-117),
# so what is sanctioned is the directory: a program added beside `post` and
# `move` is sanctioned by where it lives, not by a name added here.
SANCTIONED = re.compile(r"\.meta/(say/|check_pr\.py\b)")

WHY = ("Blocked: this reaches GitHub without signing what it posts.\n"
       "Use the channel — .meta/say/post to say something, .meta/say/move to change "
       "state — which appends the Actor Trailer from the environment, which is what "
       "makes a comment attributable at all when every login here is the solo's. "
       "Your reading of PR First lists your verbs; a program's --help lists its own. "
       "Reading is fine through "
       "`.meta/check_pr.py --threads|--resume|--sweep`.")


def blocked(command):
    """The predicate: does this command reach GitHub outside the signed channel?"""
    if SANCTIONED.search(command):
        return None
    if ENDPOINT.search(command) or GH_WRITES.search(command):
        return WHY
    return None


def main():
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    problem = blocked(event.get("tool_input", {}).get("command", ""))
    if problem:
        print(problem, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
