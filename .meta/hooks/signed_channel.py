#!/usr/bin/env python3
"""Refuse any path to GitHub that does not sign what it posts (solorepo's DR-069).

A PreToolUse hook, so the harness runs it rather than the agent remembering to.
`.claude/settings.json` denies `gh`'s writing verbs and permits its read-only
ones; this catches everything else that can reach the same endpoint — `curl`, `python`, `wget`, a language's
HTTP client — because a deny list over one binary is not a boundary.

Inspects commands before execution and blocks unsanctioned access to GitHub
endpoints, ensuring operations route through the signing channel until credential-level
isolation is enforced (solorepo's DR-174, solorepo's DR-175).

    echo '{"tool_name":"Bash","tool_input":{"command":"..."}}' | .meta/hooks/signed_channel.py

Exit 2 blocks the call and shows the message to the agent. The predicate is
separate from the plumbing so it can be watched failing without a harness.
"""
import json
import re
import sys

# The endpoint, however it is spelled, and the writing verbs of the CLI that
# wraps it. Reading is permitted; mutating actions must pass through the channel:
# - merge, close, update-branch: mutating operations that record an actor and require
#   proper attribution (solorepo's DR-113).
# - stack commands (link, merge, submit): commands that create or mutate pull requests (solorepo's DR-100).
# - workflow run: dispatches GitHub Actions jobs; must use .meta/say/move dispatch (solorepo's DR-151).
# Read-only operations (such as gh run list and gh workflow view) remain open.
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
    """Validates incoming pre-tool-use events to ensure mutating GitHub calls route through the signed channel."""
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
