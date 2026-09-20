"""The arithmetic over a run: timestamps, spans, the clock a span prints as, the nearest-rank percentile, and the critical path through the job that finished last.
"""
import math
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any


def at(stamp: str | None) -> datetime | None:
    """Parses an ISO 8601 UTC timestamp string into a timezone-aware datetime object.

    Args:
        stamp: ISO 8601 timestamp string or None.

    Returns:
        datetime | None: Timezone-aware datetime in UTC, or None if stamp is missing.
    """
    if not stamp:
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def span(start: str | None, end: str | None) -> float | None:
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


def clock(seconds: float | None) -> str:
    """Formats a duration in seconds into human-readable fixed-width units.

    Args:
        seconds: Duration in seconds, or None.

    Returns:
        str: Formatted duration string (e.g. ' 42s', ' 3m12s', ' 1h04m', or ' —').
    """
    if seconds is None:
        return "     —"
    sec = round(seconds)
    if sec < 60:
        return f"{sec:>6}s"
    if sec < 3600:
        return f"{sec // 60:>3}m{sec % 60:02d}s"
    return f"{sec // 3600:>3}h{(sec % 3600) // 60:02d}m"


def pick(values: Sequence[float], fraction: float) -> float | None:
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


def critical(run: dict[str, Any], jobs: Sequence[dict[str, Any]]) -> tuple[float | None, float | None]:
    """Determines the critical-path job for a run and calculates queue wait and active work duration.

    Args:
        run: Workflow run dictionary containing createdAt timestamp.
        jobs: List of job dictionaries associated with the run.

    Returns:
        tuple[float | None, float | None]: Queue wait duration and active execution duration in seconds.
    """
    created = at(run.get("createdAt"))
    if created is None:
        return None, None
    ran_at_all: list[dict[str, Any]] = []
    for j in jobs:
        if not (j.get("startedAt") and j.get("completedAt") and (j.get("steps") or [])):
            continue
        c_at, s_at = at(j.get("completedAt")), at(j.get("startedAt"))
        if c_at is not None and s_at is not None and c_at >= s_at:
            ran_at_all.append(j)
    if not ran_at_all:
        return None, None
    min_time = datetime.min.replace(tzinfo=UTC)
    last = max(ran_at_all, key=lambda j: at(j.get("completedAt")) or min_time)
    s_last = at(last.get("startedAt"))
    if s_last is None:
        return None, None
    wait = max(0.0, (s_last - created).total_seconds())
    return wait, span(last.get("startedAt"), last.get("completedAt"))
