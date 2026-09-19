#!/usr/bin/env python3
"""Worktree containment and reviewer command confinement hook (solorepo's DR-110).

Before-tool hook for the reviewer role container in `.github/workflows/review.yml`,
registered on Claude Code's `PreToolUse` event and on Gemini CLI's `BeforeTool`.
Enforces two isolation boundaries before tool execution: filesystem
containment, which `lib.worktree_only.paths` decides, and command confinement,
which `lib.worktree_only.grammar` decides over the lexing in
`lib.worktree_only.shell`; `lib.worktree_only.verdict` composes the two into the
decision and writes the refusal, with the nearest conforming command where one
is derivable (solorepo's DR-175). Each module's docstring carries the why of its
boundary; this file is the contract a harness invokes.

Input/Output Contract:
    Reads a before-tool event JSON object from stdin. Both harnesses carry the
    same two fields, so one reader serves each:
        {"tool_name": "Bash", "tool_input": {"command": "..."}}
    Exits with code 0 to permit execution.
    Exits with code 2 and writes an explanatory refusal message to stderr to block
    execution; Claude Code and Gemini CLI both read code 2 as a block and stderr
    as the reason given to the agent. A payload that is not a readable event —
    bytes that are not JSON, JSON that is not an object, or a stdin that cannot
    be read — is blocked in the same way, because both harnesses read any other
    exit code as a non-blocking error and run the tool anyway.
    Appends one line of Evidence, `<UTC timestamp, seconds> <tool>
    permit|refuse`, to the file `SOLOREPO_HOOK_EVIDENCE` names, where the run
    set it, so that a session this hook never confined is a run that can be told
    apart from a confined one (solorepo's #645).

History in worktree_only.history.md (solorepo's DR-171).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from lib.worktree_only import ROOT, grammar, paths, shell, verdict
from lib.worktree_only.grammar import (
    GIT,
    INSTEAD,
    NUMBER,
    PROGRAMS,
    TAKES_VALUE,
    command_allowed,
    form_of,
    options_allowed,
    plain_form,
    refused_option,
)
from lib.worktree_only.paths import (
    ALTERNATION,
    GLOBBY,
    HARNESS,
    PATH,
    PATTERN,
    READERS,
    SEARCHES,
    TOOLS,
    ascends,
    elsewhere,
    outside,
    outside_pattern,
    targets,
)
from lib.worktree_only.shell import (
    CHAINS,
    DESCRIPTOR,
    ESCAPES,
    EXPANDS,
    QUOTES,
    SHELL,
    SUBSTITUTES,
    before_operator,
    partition_unquoted,
    requote,
    unquoted,
    words_of,
)
from lib.worktree_only.verdict import (
    blocked,
    main,
    record_evidence,
)

__all__ = [
    "ALTERNATION",
    "CHAINS",
    "DESCRIPTOR",
    "ESCAPES",
    "EXPANDS",
    "GIT",
    "GLOBBY",
    "HARNESS",
    "INSTEAD",
    "NUMBER",
    "PATH",
    "PATTERN",
    "PROGRAMS",
    "QUOTES",
    "READERS",
    "ROOT",
    "SEARCHES",
    "SHELL",
    "SUBSTITUTES",
    "TAKES_VALUE",
    "TOOLS",
    "ascends",
    "before_operator",
    "blocked",
    "command_allowed",
    "elsewhere",
    "form_of",
    "grammar",
    "main",
    "options_allowed",
    "outside",
    "outside_pattern",
    "partition_unquoted",
    "paths",
    "plain_form",
    "record_evidence",
    "refused_option",
    "requote",
    "shell",
    "targets",
    "unquoted",
    "verdict",
    "words_of",
]
"""The hook's whole surface: every public name of the package, and the four modules beside them.

`hook_probes` in `.meta/checks/probes/git/step.py` loads this file by path and reads
`blocked`, `command_allowed`, `plain_form` and `main` off it. The modules are
exported so a probe can stand a collaborator in at the module that defines it,
`worktree_only.paths.ROOT` rather than a name rebound here that nothing reads
(solorepo's DR-217)."""

if __name__ == "__main__":
    sys.exit(verdict.main())
