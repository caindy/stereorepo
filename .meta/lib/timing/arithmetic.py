"""The arithmetic over a run: timestamps, spans, the clock a span prints as, the nearest-rank percentile, and the critical path through the job that finished last.
"""
import math
from datetime import datetime


def at(stamp):
    """Parses an ISO 8601 UTC timestamp string into a timezone-aware datetime object.

    Args:
        stamp: ISO 8601 timestamp string or None.

    Returns:
        datetime | None: Timezone-aware datetime in UTC, or None if stamp is missing.
    """
    if not stamp:
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def span(start, end):
    """Computes the elapsed time in seconds between two ISO 8601 timestamps.

    Args:
        start: Beginning timestamp string.
        end: Ending timestamp string.

    Returns:
        float | None: Non-negative elapsed seconds, or None if either timestamp is missing.
    """
    a, b = at(start), at(end)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds())


def clock(seconds):
    """Formats a duration in seconds into human-readable fixed-width units.

    Args:
        seconds: Duration in seconds, or None.

    Returns:
        str: Formatted duration string (e.g. ' 42s', ' 3m12s', ' 1h04m', or ' —').
    """
    if seconds is None:
        return "     —"
    seconds = round(seconds)
    if seconds < 60:
        return f"{seconds:>6}s"
    if seconds < 3600:
        return f"{seconds // 60:>3}m{seconds % 60:02d}s"
    return f"{seconds // 3600:>3}h{(seconds % 3600) // 60:02d}m"


def pick(values, fraction):
    """Calculates the nearest-rank percentile value from a sequence of numbers.

    Args:
        values: Sequence of numeric values.
        fraction: Percentile fraction between 0.0 and 1.0 (e.g. 0.5 for median).

    Returns:
        float | int | None: Nearest-rank percentile value, or None if values is empty.
    """
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def critical(run, jobs):
    """Determines the critical-path job for a run and calculates queue wait and active work duration.

    Args:
        run: Workflow run dictionary containing createdAt timestamp.
        jobs: List of job dictionaries associated with the run.

    Returns:
        tuple[float | None, float | None]: Queue wait duration and active execution duration in seconds.
    """
    created = at(run["createdAt"])
    if created is None:
        return None, None
    ran_at_all = [j for j in jobs
                  if j.get("startedAt") and j.get("completedAt")
                  and (j.get("steps") or [])
                  and at(j["completedAt"]) >= at(j["startedAt"])]
    if not ran_at_all:
        return None, None
    last = max(ran_at_all, key=lambda j: at(j["completedAt"]))
    wait = max(0.0, (at(last["startedAt"]) - created).total_seconds())
    return wait, span(last["startedAt"], last["completedAt"])
