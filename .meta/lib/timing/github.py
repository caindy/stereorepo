"""What the screen reads off GitHub: the workflows it reports, the runs and jobs of each, and the one `gh` call that degrades when the token cannot list them (solorepo's DR-153).
"""
import json
import subprocess
import sys
from typing import Any

# The same four `next.py` reads, and for the same reason: they are the
# workflows a portfolio inherits or writes its own of. `gate.yml` is not in
# Specialization's copied set — a portfolio writes one whose jobs are its own
# Projects' — so it is named here rather than discovered, and a portfolio's
# own gate keeps the name.
WORKFLOWS = ("gate.yml", "coder.yml", "review.yml", "merge.yml", "advance.yml")
# A run GitHub never started costs nothing and would drag every percentile
# toward zero. `skipped` is the common one: `coder.yml` and `review.yml` skip
# far more deliveries than they take.
NOT_RUN = {"skipped", "cancelled", ""}
RUN_FIELDS = "databaseId,createdAt,startedAt,updatedAt,conclusion,event,status,headBranch,headSha,displayTitle"


# "No default was given", as a value no caller can pass. `None` cannot serve:
# the one caller that most needs to degrade — `runs_of`, on the token with no
# Actions scope this whole program is shaped around — wants `None` *as* its
# default, and a sentinel of `None` cannot tell that apart from asking to die.
# Written with `default=None` it did die, and the branch that reports an
# unreadable workflow was unreachable.
UNSET = object()


def gh(*args: str, default: Any = UNSET) -> Any:
    """Executes a GitHub CLI command and parses its JSON output.

    Args:
        *args: Command arguments passed to gh.
        default: Fallback value returned if the command fails.

    Returns:
        Any: Parsed JSON data or default value on error.
    """
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode:
        if default is not UNSET:
            return default
        sys.exit(f"gh {' '.join(args[:2])}: {out.stderr.strip()}")
    return json.loads(out.stdout or "null")


def runs_of(workflow: str, limit: int) -> list[dict[str, Any]] | None:
    """Fetches completed workflow runs, filtering out skipped or cancelled deliveries.

    Args:
        workflow: Workflow filename (e.g. 'gate.yml').
        limit: Maximum number of runs to retrieve.

    Returns:
        list[dict] | None: List of completed run dictionaries, or None on fetch failure.
    """
    found = gh("run", "list", "--workflow", workflow, "--limit", str(limit),
               "--json", RUN_FIELDS, default=None)
    if found is None:
        return None
    return [r for r in found
            if r["status"] == "completed" and (r["conclusion"] or "").lower() not in NOT_RUN]


def jobs_of(run_id: int | str) -> list[dict[str, Any]]:
    """Fetches job definitions and step timings for a specific workflow run.

    Args:
        run_id: GitHub Actions workflow run database ID.

    Returns:
        list[dict]: List of job dictionaries including step timing metadata.
    """
    found = gh("run", "view", str(run_id), "--json", "jobs", default={})
    return list(found.get("jobs") or [])
