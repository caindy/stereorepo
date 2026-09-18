"""The screen: one row per workflow, its sub-rows by stratum, and the slowest steps under `--steps`.
"""
from datetime import UTC, datetime

from lib.timing import arithmetic, github, routing


def summarise(workflow, limit, deep, stratify=None):
    """Aggregates runtime and wait percentiles across workflow runs.

    Args:
        workflow: Workflow filename.
        limit: Number of recent runs to inspect.
        deep: Number of recent runs to open for job-level wait and runtime analysis.
        stratify: Optional grouping dimension ('model' or 'difficulty').

    Returns:
        tuple[dict | None, list]: Aggregate statistics dictionary and list of opened run tuples.

    The three series — total, waiting and running — are drawn from one sample,
    preferring the opened runs whose wait and work could both be determined.
    Drawn from three samples the percentiles do not compose: a total taken over
    runs a wait was never read for is not the sum of the other two.
    """
    found = github.runs_of(workflow, limit)
    if found is None:
        return None, []
    opened = []
    for run in found[:deep]:
        jobs = github.jobs_of(run["databaseId"])
        if not jobs:
            continue
        w, x = arithmetic.critical(run, jobs)
        opened.append((run, jobs, w, x))

    valid_runs = [(r, w, x) for r, _, w, x in opened if w is not None and x is not None]
    if deep > 0 and valid_runs:
        total = [arithmetic.span(r["createdAt"], r["updatedAt"]) for r, _, _ in valid_runs]
        waits = [w for _, w, _ in valid_runs]
        works = [x for _, _, x in valid_runs]
        n = len(valid_runs)
    elif deep > 0 and opened:
        total = [arithmetic.span(r["createdAt"], r["updatedAt"]) for r, _, _, _ in opened]
        waits = [w for _, _, w, _ in opened if w is not None]
        works = [x for _, _, _, x in opened if x is not None]
        n = len(opened)
    else:
        total = [arithmetic.span(r["createdAt"], r["updatedAt"]) for r in found]
        waits = []
        works = []
        n = len(found)
    total = [s for s in total if s is not None]

    result = {
        "n": n,
        "available": len(found),
        "total": total,
        "waiting": waits,
        "running": works,
    }

    if stratify and opened:
        groups = {}
        for run, _, w, x in opened:
            tag = routing.stratify_run(workflow, run, stratify)
            if tag:
                t = arithmetic.span(run["createdAt"], run["updatedAt"])
                g = groups.setdefault(tag, {"n": 0, "total": [], "waiting": [], "running": []})
                if w is not None and x is not None and t is not None:
                    g["n"] += 1
                    g["total"].append(t)
                    g["waiting"].append(w)
                    g["running"].append(x)
        result["groups"] = groups

    return result, opened


def row(name, seen):
    """Formats one workflow summary row displaying runtime and wait percentiles."""
    return (f"  {name[:-4]:<9} {seen['n']:>3}  "
            f"{arithmetic.clock(arithmetic.pick(seen['total'], 0.5))} {arithmetic.clock(arithmetic.pick(seen['total'], 0.95))} "
            f"{arithmetic.clock(max(seen['total']) if seen['total'] else None)}  "
            f"{arithmetic.clock(arithmetic.pick(seen['waiting'], 0.5))} {arithmetic.clock(arithmetic.pick(seen['waiting'], 0.95))}  "
            f"{arithmetic.clock(arithmetic.pick(seen['running'], 0.5))} {arithmetic.clock(arithmetic.pick(seen['running'], 0.95))}")


def subrow(tag, seen):
    """Formats a stratified breakdown subrow under a workflow row."""
    label = f"  {tag}"
    return (f"  {label:<9} {seen['n']:>3}  "
            f"{arithmetic.clock(arithmetic.pick(seen['total'], 0.5))} {arithmetic.clock(arithmetic.pick(seen['total'], 0.95))} "
            f"{arithmetic.clock(max(seen['total']) if seen['total'] else None)}  "
            f"{arithmetic.clock(arithmetic.pick(seen['waiting'], 0.5))} {arithmetic.clock(arithmetic.pick(seen['waiting'], 0.95))}  "
            f"{arithmetic.clock(arithmetic.pick(seen['running'], 0.5))} {arithmetic.clock(arithmetic.pick(seen['running'], 0.95))}")


def steps(opened, show):
    """Identifies and displays the slowest workflow steps across opened runs.

    Args:
        opened: Sequence of opened run tuples containing job step timings.
        show: Maximum number of slowest steps to display.
    """
    seen = {}
    for _, jobs, *_ in opened:
        for job in jobs:
            for step in job.get("steps") or []:
                cost = arithmetic.span(step.get("startedAt"), step.get("completedAt"))
                if cost is not None:
                    seen.setdefault((job["name"], step["name"]), []).append(cost)
    if not seen:
        print("  no step timing (no run was opened, or none had jobs to read)")
        return
    ranked = sorted(seen.items(), key=lambda kv: arithmetic.pick(kv[1], 0.5) or 0, reverse=True)
    for (job, step), costs in ranked[:show]:
        print(f"  {arithmetic.clock(arithmetic.pick(costs, 0.5))} {arithmetic.clock(arithmetic.pick(costs, 0.95))} n={len(costs):<3} "
              f"{job} / {step[:58]}")


def screen(names, limit, deep, show, want_steps, stratify=None):
    """Renders the workflow timing summary screen."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\nworkflow runtimes — {now}, last {limit} completed runs each\n")
    print(f"  {'workflow':<9} {'n':>3}  {'total':>7} {'p95':>7} {'max':>7}  "
          f"{'wait':>7} {'p95':>7}  {'run':>7} {'p95':>7}")
    print(f"  {'':<9} {'':>3}  {'p50':>7} {'':>7} {'':>7}  {'p50':>7} {'':>7}  {'p50':>7} {'':>7}")
    unreadable, everything = [], []
    for name in names:
        seen, opened = summarise(name, limit, deep, stratify=stratify)
        everything += opened
        if seen is None:
            unreadable.append(name)
        elif seen["n"]:
            print(row(name, seen))
            if "groups" in seen:
                for tag in sorted(seen["groups"].keys()):
                    print(subrow(tag, seen["groups"][tag]))
        else:
            print(f"  {name[:-4]:<9}   0  no completed run in the last {limit}")
    if unreadable:
        print(f"\n  could not list runs for {', '.join(unreadable)} — this token has no "
              "Actions read, which is solorepo's DR-153's refusal and correct in CI; run it locally")
    print("\n  total is the whole run, wall clock. wait is what it spent getting a"
          "\n  runner — for arc-runner-set, a pod being scheduled and pulling its image."
          "\n  run is what it spent working once it had one, which is what a step added"
          "\n  to a workflow moves. Both are read off the job that finished last, so"
          "\n  they add across the row.")
    if deep > 0:
        print(f"  All three are read from the {deep} most recent runs of each.")
    else:
        print(f"  total is read from the {limit} most recent runs of each.")
    if want_steps:
        print(f"\nslowest steps — across the {len(everything)} run(s) opened above\n")
        steps(everything, show)
    print()
