"""What each harness's own settings JSON in `review.yml` registers for the worktree hook: the matcher and the command line, per harness (solorepo's #456).

Neither `hook_probes`' `EVENTS` table nor `gemini_core_matches_hook_matcher` in
`checks.files.workflows` runs the string this file writes into
`.claude/settings.json` or `.gemini/settings.json`: the first calls
`worktree_only.main()` in-process, standing in for the envelope a harness
sends but not for the registration that gets it there; the second compares
tool-name sets by regex, without ever resolving or executing the `command`
either path names. A hook that is missing, unreadable, or refused by a shell
that cannot expand `$CLAUDE_PROJECT_DIR` does not block — solorepo's #454 found
exactly that state on the Gemini path, with every other check green — so this
table is read against a real subprocess: the registered path is resolved with
the harness's own project-directory variable, and the registered matcher is
checked against the tool name each harness's own before-tool envelope would
carry, before either amounts to nothing.
"""
import re

REGISTRATIONS = (
    ("Claude Code", "CLAUDE_PROJECT_DIR",
     re.compile(r'"PreToolUse":\s*\[\{"matcher":\s*"([^"]+)",\s*'
                r'"hooks":\s*\[\{"type":\s*"command",\s*"command":\s*"([^"]+)"', re.DOTALL),
     {"session_id": "s", "transcript_path": "/tmp/session.json", "hook_event_name": "PreToolUse",
      "tool_name": "Bash", "tool_input": {"command": "cat /etc/passwd"}},
     {"session_id": "s", "transcript_path": "/tmp/session.json", "hook_event_name": "PreToolUse",
      "tool_name": "Bash", "tool_input": {"command": "git status --porcelain"}}),
    ("Gemini CLI", "GEMINI_PROJECT_DIR",
     re.compile(r'"BeforeTool":\s*\[\s*\{\s*"matcher":\s*"([^"]+)",\s*'
                r'"hooks":\s*\[\s*\{\s*"type":\s*"command",\s*"name":\s*"[^"]*",\s*"command":\s*"([^"]+)"', re.DOTALL),
     {"session_id": "s", "transcript_path": "/tmp/session.json", "hook_event_name": "BeforeTool",
      "timestamp": "2026-09-15T00:00:00Z", "tool_name": "run_shell_command",
      "tool_input": {"command": "cat /etc/passwd"}},
     {"session_id": "s", "transcript_path": "/tmp/session.json", "hook_event_name": "BeforeTool",
      "timestamp": "2026-09-15T00:00:00Z", "tool_name": "run_shell_command",
      "tool_input": {"command": "git status --porcelain"}}),
)
"""Each harness's `(name, project-dir variable, registration pattern, refuse event, allow event)`.

The pattern's two groups are the registered `matcher` and `command`, read
straight from `review.yml`'s own settings JSON rather than restated by hand,
so a rewritten registration is what this table follows and not what it drifts
from. The events are what that harness's own before-tool payload carries for
the one call every registration guards in common — a shell command — so the
matcher is checked against the tool name the harness itself would send, and
the command against a call the hook must refuse and one it must allow.
"""
