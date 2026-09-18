#!/usr/bin/env python3
"""What to work on next, on one screen, read from GitHub (solorepo's DR-114).

The question opens most sessions, and answering it by hand meant reading
eleven Issue bodies to learn four things: what waits on what, whether the
loops are busy, which Milestone is next, and what the coder has queued. Each
of those is a field a listing can read, so this reads them and prints one
screen. It decides nothing: which ripe Issue to take is the solo's.

    python3 .meta/next.py            # the screen
    python3 .meta/next.py --check    # the sweep: fail on a Challenge the reviewer's door did not read

What it reads, and from where:

- **Waits on.** The first line of both Issue forms, and GitHub's native
  `blockedBy` relationship (solorepo's DR-170). `#<n>` per blocker seeds the
  native relationship on GitHub, or `Nothing`. A blocker that is closed no
  longer blocks, and a blocker written as prose — a Decision, an account —
  keeps the Issue waiting until somebody rewrites the line. An Issue with no
  such line is shown as `?`, which is the form asking for it.
- **Difficulty.** The label the reviewer's verdict lands after reading the
  Challenge (solorepo's DR-230), or the solo's mandate given with the filing. A
  Challenge without one is unread and waits for the reviewer; `--check` asks
  whether the reviewer's door fired, from `triage.yml`'s runs, and refuses one
  with no run an hour after its filing or whose latest run ended red, so the
  queue cannot stall without anyone noticing. Where the runs cannot be listed,
  the hour is measured from the filing alone, since `updatedAt` moves on any
  touch and would let a comment silence the check.
- **Milestone.** GitHub's, with the lowest number next. The priority is
  written once there rather than inferred per session from which Issues
  happen to cite it.
- **Pull requests and loops.** What is open, whether the merge is armed and
  whether it fell behind main; and the last run of each loop workflow, so
  "idle" is a fact and not an impression. An open pull request is the loops'
  work in progress, not an answer to what is next: the answer is an Issue,
  and the pull request is shown so that its being worked is a fact too.
  An Issue an open pull request closes is that pull request's work, so it is
  listed as **in progress** and not as ripe: a screen that offered it again
  would hand the solo a Challenge a loop already holds.

Reads only, through `gh`, which the hook permits. Nothing here writes.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

from lib.timing.github import NOT_RUN

DIFFICULTY = ("easy", "medium", "hard", "human")
UNREAD = timedelta(hours=1)
"""How long after its filing a Challenge may carry no level with no triage run before `--check` reports it as stalled (solorepo's DR-230)."""
RUN_ISSUE = re.compile(r"#(\d+)")
"""The Issue number in a triage run's name, which `triage.yml` writes as `triage-issue-#<n>`."""
LOOPS = ("coder.yml", "review.yml", "merge.yml", "advance.yml", "gate.yml")

WAITS = re.compile(r"^\*\*Waits on\.\*\*\s*(.*?)\s*$", re.M)
OLD_WAITS = re.compile(r"\*\*What it waits on\.\*\*\s*(.*?)(?:\n\s*\n|\Z)", re.S)
REF = re.compile(r"#(\d+)")


def gh(*args: str, default: Any = None) -> Any:
    """Executes a GitHub CLI command and parses its JSON output.

    Args:
        *args: Command arguments passed to gh.
        default: Fallback value returned if the command fails.

    Returns:
        Any: Parsed JSON data or default value on error.
    """
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode:
        if default is not None:
            return default
        sys.exit(f"gh {' '.join(args[:2])}: {out.stderr.strip()}")
    return json.loads(out.stdout) if out.stdout.strip() else default


def waits_on(issue):
    """Extracts blocker issue numbers declared by an issue.

    Inspects GitHub's native `blockedBy` relation (solorepo's DR-170) before
    falling back to markdown regex parsing.

    Args:
        issue: Issue dictionary or raw markdown body string.

    Returns:
        list[int] | str | None: List of blocker issue numbers, prose explanation string,
            or None if no blocker section is declared.
    """
    native = [n["number"] for n in (issue.get("blockedBy") or {}).get("nodes", []) if "number" in n] if isinstance(issue, dict) else []
    if native:
        return native
    body = issue.get("body") if isinstance(issue, dict) else issue
    m = WAITS.search(body or "") or OLD_WAITS.search(body or "")
    if not m:
        return None
    text = m.group(1).strip()
    refs = [int(n) for n in REF.findall(text)]
    if refs:
        return refs
    if text.lower().rstrip(".") in ("nothing", "none", ""):
        return []
    return text


def classify(issue, open_numbers, closing):
    """Classifies an issue by blocker status, in-progress state, and difficulty level.

    Args:
        issue: Issue dictionary from GitHub API.
        open_numbers: Set of currently open issue numbers.
        closing: Mapping of issue numbers to PR numbers closing them.

    Returns:
        dict[str, Any]: Classified issue metadata dictionary.
    """
    labels = {lbl["name"] for lbl in issue["labels"]}
    level = next((d for d in DIFFICULTY if d in labels), None)
    waits = waits_on(issue)
    taken = closing.get(issue["number"])
    if taken:
        blocked, note = True, f"in #{taken}"
    elif waits is None:
        blocked, note = None, "?"
    elif isinstance(waits, str):
        blocked, note = True, "waits, see body"
    else:
        live = [n for n in waits if n in open_numbers]
        blocked = bool(live)
        note = "waits on " + ", ".join(f"#{n}" for n in live) if live else "ripe"
    return {
        "number": issue["number"],
        "title": issue["title"],
        "kind": "challenge" if "challenge" in labels else "roadmap" if "roadmap" in labels else "-",
        "level": level,
        "blocked": blocked,
        "note": note,
        "milestone": (issue.get("milestone") or {}).get("title"),
        "taken": taken,
        "created": datetime.fromisoformat(issue.get("createdAt", "1970-01-01T00:00:00Z").replace("Z", "+00:00")),
    }


def row(i: dict[str, Any]) -> str:
    """Formats one issue summary line for the next screen."""
    level = i["level"] or ("roadmap" if i["kind"] == "roadmap" else "unread")
    return f"  #{i['number']:<4} {level:<10} {i['note']:<24} {i['title'][:70]}"


def issues(closing=None):
    """Lists open issues and classifies each by blocker state and in-progress assignment."""
    found = gh("issue", "list", "--state", "open", "--limit", "200",
               "--json", "number,title,labels,body,milestone,blockedBy,createdAt", default=[])
    numbers = {i["number"] for i in found}
    return sorted((classify(i, numbers, closing or {}) for i in found),
                  key=lambda i: i["number"])


def unread(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filters Challenges carrying no difficulty label: filed, and waiting for the reviewer's verdict.

    Args:
        rows: Sequence of classified issue dictionaries.

    Returns:
        list[dict[str, Any]]: Unread Challenges.
    """
    return [i for i in rows if i["kind"] == "challenge" and not i["level"]]


def pull_requests():
    """Prints open pull requests and returns mapping of closed issue numbers to PR numbers.

    Returns:
        dict[int, int]: Mapping of closed issue numbers to closing pull request numbers.
    """
    prs = gh("pr", "list", "--state", "open", "--json",
             "number,title,autoMergeRequest,mergeStateStatus,reviewDecision,latestReviews,reviewRequests,isDraft,headRefName,"
             "closingIssuesReferences",
             default=[])
    print("pull requests — the loops' work in progress, not what is next")
    if not prs:
        print("  none open")
    for pr in prs:
        armed = "armed" if pr.get("autoMergeRequest") else "draft" if pr["isDraft"] else "open"
        state = (pr.get("mergeStateStatus") or "").lower()
        review = (pr.get("reviewDecision") or "").lower().replace("_", " ")
        if not review:
            revs = [r for r in pr.get("latestReviews") or []
                    if (r.get("author") or {}).get("login", "").endswith("-reviewer")]
            if revs:
                review = revs[-1].get("state", "").lower().replace("_", " ")
            elif pr.get("reviewRequests"):
                review = "requested"
        print(f"  #{pr['number']:<4} {armed:<7} {state:<9} {review:<17} {pr['title'][:60]}")
    print()
    return {ref["number"]: pr["number"]
            for pr in prs for ref in pr.get("closingIssuesReferences") or []}


def loops():
    """Prints the status and timestamp of the most recent run for each loop workflow."""
    print("loops — last run of each")
    for wf in LOOPS:
        runs = gh("run", "list", "--workflow", wf, "--limit", "1",
                  "--json", "status,conclusion,createdAt,displayTitle,event", default=[])
        if not runs:
            print(f"  {wf[:-4]:<9} no run listed (or no permission to list runs)")
            continue
        r = runs[0]
        when = r["createdAt"][:16].replace("T", " ")
        verdict = r["conclusion"] or r["status"]
        print(f"  {wf[:-4]:<9} {verdict:<10} {when}  {r['event']:<9} {r['displayTitle'][:50]}")
    sweep_row()
    print()


def sweep_row():
    """Prints status and timestamps for the last scheduled and last successful gate sweep runs."""
    runs = gh("run", "list", "--workflow", "gate.yml", "--event", "schedule",
              "--limit", "50", "--json", "status,conclusion,createdAt", default=[])
    if not runs:
        print(f"  {'sweep':<9} no scheduled run listed (or no permission to list runs)")
        return
    last = runs[0]
    when = last["createdAt"][:16].replace("T", " ")
    verdict = last["conclusion"] or last["status"]
    ok = next((r for r in runs if r["conclusion"] == "success"), None)
    ok_when = ok["createdAt"][:16].replace("T", " ") if ok else f"none in last {len(runs)}"
    print(f"  {'sweep':<9} {verdict:<10} {when}  last ok  {ok_when}")


def milestones(rows):
    """Prints open milestones in ascending numerical order along with their associated issues.

    Args:
        rows: Sequence of classified issue dictionaries.
    """
    found = gh("api", "repos/{owner}/{repo}/milestones?state=open&per_page=20", default=[])
    print("milestones — the lowest number is next")
    if not found:
        print("  none open")
    for m in sorted(found, key=lambda m: m["number"]):
        print(f"  {m['title']}  ({m['open_issues']} open, {m['closed_issues']} closed)")
        for i in rows:
            if i["milestone"] == m["title"]:
                print(row(i))
    print()


def screen():
    """Renders the comprehensive next-actions overview screen."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    print(f"next — {now}\n")
    closing = pull_requests()
    loops()
    rows = issues(closing)
    milestones(rows)

    challenges = [i for i in rows if i["kind"] == "challenge"]
    taken = [i for i in challenges if i["taken"]]
    ripe = [i for i in challenges if i["level"] and i["blocked"] is False]
    waiting = [i for i in challenges if i["level"] and i["blocked"] and not i["taken"]]
    unknown = [i for i in challenges if i["level"] and i["blocked"] is None]
    missing = unread(rows)
    roadmap = [i for i in rows if i["kind"] == "roadmap"]

    def section(name, items, empty="  none"):
        print(name)
        for i in items:
            print(row(i))
        if not items:
            print(empty)
        print()

    section("in progress — an open pull request closes these; they are its, not next", taken)
    section("ripe — a Challenge with a difficulty and no open blocker; "
            "easy and medium are the coder's the moment they are labelled", ripe)
    section("waiting", waiting + unknown)
    section("unread — a Challenge with no difficulty, waiting for the reviewer's verdict; "
            "the sweep fails on one untouched for an hour", missing)
    section("roadmap — deferred by definition, never queued", roadmap)


def triage_runs() -> dict[int, dict[str, Any]] | None:
    """The latest `triage.yml` run whose job ran, per Issue number, or None where the runs cannot be listed.

    Every label change on an Issue creates a run named for it, and the job
    declines all but the two deliveries that read; a completed run whose
    conclusion is in `NOT_RUN` is one the job declined or one displaced before
    it started, and is passed over so the run read is one that owed a reading.

    Returns:
        dict[int, dict[str, Any]] | None: The newest run for each Issue a run names,
            or None when the listing failed, which a token without `actions: read`
            looks like.
    """
    runs = gh("run", "list", "--workflow", "triage.yml", "--limit", "100",
              "--json", "displayTitle,status,conclusion,createdAt", default=None)
    if runs is None:
        return None
    latest: dict[int, dict[str, Any]] = {}
    for r in runs:
        if r.get("status") == "completed" and (r.get("conclusion") or "") in NOT_RUN:
            continue
        m = RUN_ISSUE.search(r.get("displayTitle") or "")
        if m and int(m.group(1)) not in latest:
            latest[int(m.group(1))] = r
    return latest


def stalled(rows: list[dict[str, Any]], runs: dict[int, dict[str, Any]] | None,
            now: datetime) -> list[tuple[dict[str, Any], str]]:
    """The unread Challenges the reviewer's door did not read, each with why.

    Args:
        rows: Classified issue dictionaries.
        runs: The latest triage run per Issue, or None where runs cannot be listed.
        now: The moment the check is made.

    Returns:
        list[tuple[dict[str, Any], str]]: Each stalled Challenge and the reason.
    """
    found: list[tuple[dict[str, Any], str]] = []
    for i in unread(rows):
        run = None if runs is None else runs.get(i["number"])
        if run is None:
            if i["created"] < now - UNREAD:
                found.append((i, "no triage run" if runs is not None else "runs not listable"))
        elif run["status"] == "completed" and run["conclusion"] != "success":
            found.append((i, f"its triage run ended {run['conclusion']}"))
    return found


def check() -> int:
    """Verifies that the reviewer's door read every open Challenge carrying no level."""
    found = stalled(issues(), triage_runs(), datetime.now(UTC))
    if found:
        print(f"x  triage — {len(found)} Challenge(s) carry no difficulty and the reviewer's "
              "door did not read them (solorepo's DR-230)")
        for i, why in found:
            print(row(i) + f"  ({why})")
        return 1
    print("ok triage — every Challenge carries a difficulty, or its triage run is under way")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on a Challenge the reviewer's door did not read, one line each")
    args = ap.parse_args()
    sys.exit(check() if args.check else screen())
