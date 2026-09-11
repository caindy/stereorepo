#!/usr/bin/env python3
"""What the workflows cost in time, on one screen, read from GitHub (solorepo's DR-157).

`just next`'s `loops()` answers whether a loop is idle. This answers what it
costs, which is the question nobody asks until they are waiting — and by then
the increment that caused it is several weeks back and inside the noise of the
one before.

    python3 .meta/timing.py              # every workflow, the last 20 runs each
    python3 .meta/timing.py gate.yml     # one workflow
    python3 .meta/timing.py --steps      # the slowest steps, and what they wait on

Two costs, reported apart, because they move for different reasons and only
one of them is the repository's to fix:

- **waiting** is what the run spent getting a runner: GitHub finding one, and
  for `arc-runner-set` a pod being scheduled and pulling its image. A change
  to this repository's own files does not move it; a change to the runner
  image or the scale set's ceiling does.
- **running** is what it spent working once it had one, which is what a step
  added to a workflow moves.

Both are read off the job that finished last, so they add up to the run —
see `critical`, which is where the arithmetic that looks obvious is wrong.

Reported together they are one number that goes up for two unrelated reasons,
which is the shape that gets attributed to whatever landed most recently.

**Read locally, never by CI.** This is an Actions read, and solorepo's DR-153 refused
`actions: read` in the gate workflows on the ground that a scaffold hands a
fresh clone whatever scope its gate declares. So this is a command the solo
runs with the solo's own token, and no workflow calls it. `next.py` already
degrades when its token cannot list runs; this would have nothing left to
print, so it says so rather than printing zeros.

**The figures are this repository's.** solorepo's runs on `arc-runner-set` and a
portfolio's on `ubuntu-latest` (Specialization's second step retargets every
`runs-on:`), so a number measured here means nothing there. Nothing here
carries a threshold for that reason: it reports, and what is too slow is read
by someone who knows what the work was.
"""
import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone

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
RUN_FIELDS = "databaseId,createdAt,startedAt,updatedAt,conclusion,event,status"


# "No default was given", as a value no caller can pass. `None` cannot serve:
# the one caller that most needs to degrade — `runs_of`, on the token with no
# Actions scope this whole program is shaped around — wants `None` *as* its
# default, and a sentinel of `None` cannot tell that apart from asking to die.
# Written with `default=None` it did die, and the branch that reports an
# unreadable workflow was unreachable.
UNSET = object()


def gh(*args, default=UNSET):
    """One `gh` call, parsed. A read that fails degrades to `default` rather
    than taking the screen down — the same bargain `next.py` makes, for the
    same token."""
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode:
        if default is not UNSET:
            return default
        sys.exit(f"gh {' '.join(args[:2])}: {out.stderr.strip()}")
    return json.loads(out.stdout or "null")


def at(stamp):
    """GitHub's timestamps, as an aware datetime. An absent one is `None`: a
    step that never ran has no start, and the caller decides what that means
    rather than getting an epoch that sorts first."""
    if not stamp:
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def span(start, end):
    """Seconds between two of GitHub's timestamps, or `None` where either is
    missing. Negative is possible and is GitHub's clock, not an error worth
    dying on — it is clamped, so a skew cannot make a step look instant."""
    a, b = at(start), at(end)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds())


def clock(seconds):
    """`3m12s`, `42s`, `1h04m`. Read down a column, so the unit is always
    present and the field is a fixed width."""
    if seconds is None:
        return "     —"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds:>6}s"
    if seconds < 3600:
        return f"{seconds // 60:>3}m{seconds % 60:02d}s"
    return f"{seconds // 3600:>3}h{(seconds % 3600) // 60:02d}m"


def pick(values, fraction):
    """The nearest-rank percentile, which is a value that actually occurred.

    Interpolating between two runs would report a duration no run had, and the
    reason to read this is to go and look at the run — so every figure printed
    is one there is a run to open.
    """
    if not values:
        return None
    ordered = sorted(values)
    # `ceil`, which is the nearest-rank formula, and not `round`, which is not.
    # Python rounds halves to even, so `round(0.5 * 5)` is 2 and the median of
    # five runs was the second smallest. The tie lands whenever the product is
    # a half with an even integer part — five runs, nine, thirteen — and five
    # is `--deep`'s default, so it was the ordinary reading and not an edge.
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def runs_of(workflow, limit):
    """Completed runs of one workflow, newest first, with the ones GitHub
    never started removed."""
    found = gh("run", "list", "--workflow", workflow, "--limit", str(limit),
               "--json", RUN_FIELDS, default=None)
    if found is None:
        return None
    return [r for r in found
            if r["status"] == "completed" and (r["conclusion"] or "").lower() not in NOT_RUN]


def jobs_of(run_id):
    """Every job of one run, with its steps. One call per run, which is why
    the step report is opt-in and samples fewer runs than the summary."""
    found = gh("run", "view", str(run_id), "--json", "jobs", default={})
    return found.get("jobs") or []


def critical(run, jobs):
    """The job the run actually waited on, and its two costs.

    Not the earliest job and not the sum. The jobs of one run neither start
    together nor run together: on run 34561479681 `python seed` had a runner
    five seconds in while `files` and `rust seed` waited two minutes
    forty-nine for a pod, and the run was not over until those finished. The
    earliest start reports the luckiest job and hides exactly the cost that
    made the run long; the sum reports a wall clock nobody waited.

    So the run is decomposed along the job that finished last: its wait is
    what the run spent getting a runner, and its duration is what the run
    spent working. Those two add up to the run, which is the property that
    makes the columns readable across a row.

    A job GitHub never ran is skipped rather than clamped. Its timestamps are
    not merely absent: a skipped job carries a `completedAt` *before* its
    `startedAt` — `sweep` on that run completed at 04:14:46 having started at
    04:17:30 — so it is excluded by having no first step rather than by
    arithmetic that would quietly call it instant.
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


def summarise(workflow, limit, deep):
    """One row per workflow: how many runs, and what they cost.

    `deep` is how many of those runs to open for the waiting/running split.
    Zero reads none, and the row then carries total wall clock only — one call
    per workflow instead of one per run.
    """
    found = runs_of(workflow, limit)
    if found is None:
        return None, []
    total = [span(r["createdAt"], r["updatedAt"]) for r in found]
    total = [s for s in total if s is not None]
    waits, works, opened = [], [], []
    for run in found[:deep]:
        jobs = jobs_of(run["databaseId"])
        if not jobs:
            continue
        opened.append((run, jobs))
        w, x = critical(run, jobs)
        if w is not None:
            waits.append(w)
        if x is not None:
            works.append(x)
    return {"n": len(found), "total": total, "waiting": waits, "running": works}, opened


def row(name, seen):
    return (f"  {name[:-4]:<9} {seen['n']:>3}  "
            f"{clock(pick(seen['total'], 0.5))} {clock(pick(seen['total'], 0.95))} "
            f"{clock(max(seen['total']) if seen['total'] else None)}  "
            f"{clock(pick(seen['waiting'], 0.5))} {clock(pick(seen['waiting'], 0.95))}  "
            f"{clock(pick(seen['running'], 0.5))} {clock(pick(seen['running'], 0.95))}")


def steps(opened, show):
    """The slowest steps across the runs that were opened.

    Keyed by job and step name together, because the same step name appears in
    several jobs — `Set up job` is in all of them — and a figure that averaged
    those would describe no step anybody could go and look at.
    """
    seen = {}
    for _, jobs in opened:
        for job in jobs:
            for step in job.get("steps") or []:
                cost = span(step.get("startedAt"), step.get("completedAt"))
                if cost is not None:
                    seen.setdefault((job["name"], step["name"]), []).append(cost)
    if not seen:
        print("  no step timing (no run was opened, or none had jobs to read)")
        return
    ranked = sorted(seen.items(), key=lambda kv: pick(kv[1], 0.5) or 0, reverse=True)
    for (job, step), costs in ranked[:show]:
        print(f"  {clock(pick(costs, 0.5))} {clock(pick(costs, 0.95))} n={len(costs):<3} "
              f"{job} / {step[:58]}")


def screen(names, limit, deep, show, want_steps):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\nworkflow runtimes — {now}, last {limit} completed runs each\n")
    print(f"  {'workflow':<9} {'n':>3}  {'total':>7} {'p95':>7} {'max':>7}  "
          f"{'wait':>7} {'p95':>7}  {'run':>7} {'p95':>7}")
    print(f"  {'':<9} {'':>3}  {'p50':>7} {'':>7} {'':>7}  {'p50':>7} {'':>7}  {'p50':>7} {'':>7}")
    unreadable, everything = [], []
    for name in names:
        seen, opened = summarise(name, limit, deep)
        everything += opened
        if seen is None:
            unreadable.append(name)
        elif seen["n"]:
            print(row(name, seen))
        else:
            print(f"  {name[:-4]:<9}   0  no completed run in the last {limit}")
    if unreadable:
        print(f"\n  could not list runs for {', '.join(unreadable)} — this token has no "
              "Actions read, which is solorepo's DR-153's refusal and correct in CI; run it locally")
    print("\n  total is the whole run, wall clock. wait is what it spent getting a"
          "\n  runner — for arc-runner-set, a pod being scheduled and pulling its image."
          "\n  run is what it spent working once it had one, which is what a step added"
          "\n  to a workflow moves. Both are read off the job that finished last, so"
          "\n  they add across the row."
          f"\n  wait and run are read from the {deep} most recent runs of each; total"
          "\n  from all of them.")
    if want_steps:
        print(f"\nslowest steps — across the {len(everything)} run(s) opened above\n")
        steps(everything, show)
    print()


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("workflow", nargs="*", default=None,
                   help="which workflows, by file name; all four by default")
    p.add_argument("--limit", type=int, default=20,
                   help="runs per workflow to summarise (default 20)")
    p.add_argument("--deep", type=int, default=5,
                   help="how many of those to open for the wait/run split, one call "
                        "each (default 5)")
    p.add_argument("--steps", action="store_true",
                   help="also the slowest steps across the runs opened")
    p.add_argument("--show", type=int, default=15,
                   help="how many steps to list with --steps (default 15)")
    args = p.parse_args()
    names = args.workflow or list(WORKFLOWS)
    names = [n if n.endswith(".yml") else f"{n}.yml" for n in names]
    screen(names, args.limit, max(0, args.deep), args.show, args.steps)


if __name__ == "__main__":
    main()
