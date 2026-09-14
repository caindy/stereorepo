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
import re
import subprocess
import sys
from datetime import UTC, datetime

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


def gh(*args, default=UNSET):
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


def runs_of(workflow, limit):
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


def jobs_of(run_id):
    """Fetches job definitions and step timings for a specific workflow run.

    Args:
        run_id: GitHub Actions workflow run database ID.

    Returns:
        list[dict]: List of job dictionaries including step timing metadata.
    """
    found = gh("run", "view", str(run_id), "--json", "jobs", default={})
    return found.get("jobs") or []


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


BOUNDARY_PATTERN = re.compile(
    r"^(\.meta/say|\.meta/hooks/|\.meta/check_pr\.py|\.claude/|\.github/workflows/)"
)
DIFFICULTY_CACHE = {}


def model_of(run):
    """Infers the model family ('opus' vs 'sonnet') used for a review workflow run.

    Args:
        run: Workflow run dictionary containing headSha commit ref.

    Returns:
        str: 'opus', 'sonnet', or 'unknown'.
    """
    sha = run.get("headSha")
    if not sha:
        return "unknown"
    res = subprocess.run(["git", "diff", "--name-only", f"origin/main...{sha}"],
                         capture_output=True, text=True)
    if res.returncode != 0 or not res.stdout.strip():
        res = subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
                             capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        if any(BOUNDARY_PATTERN.search(f) for f in res.stdout.splitlines()):
            return "opus"
        return "sonnet"
    return "unknown"


ISSUE_DIFF_BY_NUM = {}
ISSUE_DIFF_BY_TITLE = {}
ISSUES_FETCHED = False


def _ensure_issues_loaded():
    global ISSUES_FETCHED
    if ISSUES_FETCHED:
        return
    res = subprocess.run(["gh", "issue", "list", "--state", "all", "--limit", "300", "--json", "number,title,labels"],
                         capture_output=True, text=True)
    if res.returncode == 0:
        try:
            for item in json.loads(res.stdout):
                diff = "unknown"
                for lbl in item.get("labels", []):
                    if lbl.get("name") in ("easy", "medium", "hard", "human"):
                        diff = lbl["name"]
                        break
                ISSUE_DIFF_BY_NUM[str(item["number"])] = diff
                ISSUE_DIFF_BY_TITLE[item.get("title", "").strip().lower()] = diff
        except Exception:
            pass
    ISSUES_FETCHED = True


def difficulty_of(run):
    """Determines challenge difficulty label associated with a workflow run.

    Args:
        run: Workflow run dictionary.

    Returns:
        str: Difficulty label ('easy', 'medium', 'hard', 'human', or 'unknown').

    The run's head branch names its Issue, and the label is read from there. A
    run whose head branch is `main` — an `issues: labeled` trigger, or a
    `workflow_dispatch` — names no Issue that way, so the number is taken from
    its display title instead, and failing that the title is matched against
    the Issue titles the run listing carries.
    """
    branch = run.get("headBranch") or ""
    m = re.search(r"issue-(\d+)", branch)
    if m:
        issue_num = m.group(1)
        if issue_num in DIFFICULTY_CACHE:
            return DIFFICULTY_CACHE[issue_num]
        _ensure_issues_loaded()
        diff = ISSUE_DIFF_BY_NUM.get(issue_num)
        if not diff or diff == "unknown":
            res = subprocess.run(["gh", "issue", "view", issue_num, "--json", "labels"],
                                 capture_output=True, text=True)
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    labels = {lbl.get("name") for lbl in data.get("labels", [])}
                    for cand in ("easy", "medium", "hard", "human"):
                        if cand in labels:
                            diff = cand
                            break
                except Exception:
                    pass
        diff = diff or "unknown"
        DIFFICULTY_CACHE[issue_num] = diff
        return diff

    title = (run.get("displayTitle") or "").strip()
    if title:
        m = re.search(r"#(\d+)", title)
        if m:
            return difficulty_of({"headBranch": f"claude/issue-{m.group(1)}"})
        _ensure_issues_loaded()
        if title.lower() in ISSUE_DIFF_BY_TITLE:
            return ISSUE_DIFF_BY_TITLE[title.lower()]

    return "unknown"


def stratify_run(workflow, run, stratify):
    """Categorizes a workflow run by model or difficulty when requested.

    Args:
        workflow: Workflow filename.
        run: Workflow run dictionary.
        stratify: Grouping dimension ('model' or 'difficulty').

    Returns:
        str | None: Category tag or None.
    """
    if stratify == "model" and workflow == "review.yml":
        return model_of(run)
    if stratify == "difficulty" and workflow in ("review.yml", "coder.yml"):
        return difficulty_of(run)
    return None


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
    found = runs_of(workflow, limit)
    if found is None:
        return None, []
    opened = []
    for run in found[:deep]:
        jobs = jobs_of(run["databaseId"])
        if not jobs:
            continue
        w, x = critical(run, jobs)
        opened.append((run, jobs, w, x))

    valid_runs = [(r, w, x) for r, _, w, x in opened if w is not None and x is not None]
    if deep > 0 and valid_runs:
        total = [span(r["createdAt"], r["updatedAt"]) for r, _, _ in valid_runs]
        waits = [w for _, w, _ in valid_runs]
        works = [x for _, _, x in valid_runs]
        n = len(valid_runs)
    elif deep > 0 and opened:
        total = [span(r["createdAt"], r["updatedAt"]) for r, _, _, _ in opened]
        waits = [w for _, _, w, _ in opened if w is not None]
        works = [x for _, _, _, x in opened if x is not None]
        n = len(opened)
    else:
        total = [span(r["createdAt"], r["updatedAt"]) for r in found]
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
            tag = stratify_run(workflow, run, stratify)
            if tag:
                t = span(run["createdAt"], run["updatedAt"])
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
            f"{clock(pick(seen['total'], 0.5))} {clock(pick(seen['total'], 0.95))} "
            f"{clock(max(seen['total']) if seen['total'] else None)}  "
            f"{clock(pick(seen['waiting'], 0.5))} {clock(pick(seen['waiting'], 0.95))}  "
            f"{clock(pick(seen['running'], 0.5))} {clock(pick(seen['running'], 0.95))}")


def subrow(tag, seen):
    """Formats a stratified breakdown subrow under a workflow row."""
    label = f"  {tag}"
    return (f"  {label:<9} {seen['n']:>3}  "
            f"{clock(pick(seen['total'], 0.5))} {clock(pick(seen['total'], 0.95))} "
            f"{clock(max(seen['total']) if seen['total'] else None)}  "
            f"{clock(pick(seen['waiting'], 0.5))} {clock(pick(seen['waiting'], 0.95))}  "
            f"{clock(pick(seen['running'], 0.5))} {clock(pick(seen['running'], 0.95))}")


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


def main():
    """Parses arguments and outputs workflow timing statistics."""
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("workflow", nargs="*", default=None,
                   help="which workflows, by file name; all four by default")
    p.add_argument("--limit", type=int, default=20,
                   help="runs per workflow to summarise (default 20)")
    p.add_argument("--deep", default="5",
                   help="how many of those to open for the wait/run split (default 5, or 'all')")
    p.add_argument("--by", choices=["model", "difficulty"], default=None,
                   help="break down runs by 'model' (opus/sonnet) or 'difficulty' (hard/medium/easy)")
    p.add_argument("--by-model", action="store_const", dest="by", const="model",
                   help="shortcut for --by model")
    p.add_argument("--by-difficulty", action="store_const", dest="by", const="difficulty",
                   help="shortcut for --by difficulty")
    p.add_argument("--steps", action="store_true",
                   help="also the slowest steps across the runs opened")
    p.add_argument("--show", type=int, default=15,
                   help="how many steps to list with --steps (default 15)")
    args = p.parse_args()
    names = args.workflow or list(WORKFLOWS)
    names = [n if n.endswith(".yml") else f"{n}.yml" for n in names]
    if args.deep == "all":
        deep = args.limit
    else:
        try:
            deep = max(0, int(args.deep))
        except ValueError:
            p.error(f"invalid --deep value: {args.deep!r}")
    screen(names, args.limit, deep, args.show, args.steps, stratify=args.by)


if __name__ == "__main__":
    main()
