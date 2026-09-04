#!/usr/bin/env python3
"""Refuse any path to GitHub that does not sign what it posts.

A PreToolUse hook, so the harness runs it rather than the agent remembering to.
`.claude/settings.json` denies `gh`'s writing verbs and permits its read-only
ones; this catches everything else that can reach the same endpoint — `curl`, `python`, `wget`, a language's
HTTP client — because a deny list over one binary is not a boundary.

It is a string match over a command line, and string matches lose eventually.
What it buys is that the cheap paths are shut and the remaining ones are
deliberate. The boundary that would actually hold is the credential: a token
reachable only by `.meta/say` makes `say` the only path by construction rather
than by inspection. That is DR-066's open question, and this stands in until it
is answered.

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
# Role did it rather than which human owns the credential.
ENDPOINT = re.compile(r"api\.github\.com|graphql\.github\.com")
GH_WRITES = re.compile(r"\bgh\s+(api|pr\s+(comment|review|create|edit|merge|close)"
                       r"|issue\s+(create|comment|edit|close))\b")
SANCTIONED = re.compile(r"\.meta/(say|check_pr\.py)\b")

WHY = ("Blocked: this reaches GitHub without signing what it posts.\n"
       "Use .meta/say — it appends the Actor Trailer from the environment, which is "
       "what makes a comment attributable at all when every login here is the solo's. "
       "`.meta/say --help` lists the verbs. Reading is fine through "
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
