"""What the screen reads off GitHub: the workflows it reports, the runs and jobs of each, and the one `gh` call that degrades when the token cannot list them (solorepo's DR-153).

History in github.history.md (solorepo's DR-171).
"""
import subprocess
from typing import Any

from lib import gh as lib_gh

# The same four `next.py` reads, and for the same reason: they are the
# workflows a portfolio inherits or writes its own of. `gate.yml` is not in
# Specialization's copied set — a portfolio writes one whose jobs are its own
# Projects' — so it is named here rather than discovered, and a portfolio's
# own gate keeps the name.
WORKFLOWS = ("gate.yml", "coder.yml", "review.yml", "merge.yml", "advance.yml", "reconcile.yml")
# A run GitHub never started costs nothing and would drag every percentile
# toward zero. `skipped` is the common one: `coder.yml` and `review.yml` skip
# far more deliveries than they take.
NOT_RUN = {"skipped", "cancelled", ""}
RUN_FIELDS = "databaseId,createdAt,startedAt,updatedAt,conclusion,event,status,headBranch,headSha,displayTitle"


UNSET = lib_gh.UNSET


def gh(*args: str, default: Any = UNSET) -> Any:
    """Executes a GitHub CLI command and parses its JSON output.

    The read is unbounded, which is `timeout=None` here and was the absence of
    a `timeout` argument before the runner was shared: `.meta/lib/gh.py` raises
    `GhTimeout` without consulting `default`, so a bound would take the whole
    timing screen on a slow `gh run list` where `screen.py` is built to report
    the one workflow it could not read (solorepo's DR-153).

    Parameters:
        *args: Command arguments passed to gh.
        default: Fallback value returned if the command fails, prints nothing,
            or prints output that is not JSON. If default is omitted, any of
            the three exits the process.

    Returns:
        Any: Parsed JSON data or the fallback.

    Raises:
        SystemExit: If the read fails and no fallback was given.
    """
    return lib_gh.gh(*args, default=default, timeout=None, subprocess_module=subprocess)


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
