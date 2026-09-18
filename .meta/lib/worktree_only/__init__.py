"""The body of `.meta/hooks/worktree_only.py`: the reviewer's worktree containment and command confinement (solorepo's DR-110).

In dependency order. `paths` decides whether a path a tool reads lies inside
the worktree, and draws only `ROOT` from the package; `shell` lexes a command
line as the shell would, and draws nothing. `grammar` holds the commands a reviewer may run and
their options, and draws on `shell`. `verdict` composes `paths` and `grammar`
into the hook's decision and its entry.
"""
import os
import pathlib

ROOT = pathlib.Path(
    os.environ.get("CLAUDE_PROJECT_DIR")
    or os.environ.get("GEMINI_PROJECT_DIR")
    or pathlib.Path.cwd()
).resolve()
"""The worktree the hook confines the reviewer to: the harness's project directory, or the
current directory where no harness names one."""
