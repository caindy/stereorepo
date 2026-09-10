#!/usr/bin/env python3
"""What to work on next, on one screen, read from GitHub (solorepo's DR-114).

The question opens most sessions, and answering it by hand meant reading
eleven Issue bodies to learn four things: what waits on what, whether the
loops are busy, which Milestone is next, and what the coder has queued. Each
of those is a field a listing can read, so this reads them and prints one
screen. It decides nothing: which ripe Issue to take is the solo's.

    python3 .meta/next.py            # the screen
    python3 .meta/next.py --check    # the sweep: fail on a Challenge with no difficulty

What it reads, and from where:

- **Waits on.** The first line of both Issue forms. `#<n>` per blocker, or
  `Nothing`. A blocker that is closed no longer blocks, and a blocker written
  as prose — a Decision, an account — keeps the Issue waiting until somebody
  rewrites the line. An Issue with no such line is shown as `?`, which is the
  form asking for it.
- **Difficulty.** The label solorepo's DR-112 made the raiser's estimate. A Challenge
  without one is invisible to the coder, and `--check` refuses that so the
  queue cannot empty without anyone noticing.
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
from datetime import datetime, timezone

DIFFICULTY = ("easy", "medium", "hard", "human")
LOOPS = ("coder.yml", "review.yml", "advance.yml", "gate.yml")

WAITS = re.compile(r"^\*\*Waits on\.\*\*\s*(.*?)\s*$", re.M)
OLD_WAITS = re.compile(r"\*\*What it waits on\.\*\*\s*(.*?)(?:\n\s*\n|\Z)", re.S)
REF = re.compile(r"#(\d+)")


def gh(*args, default=None):
    """One `gh` call, parsed. A read that fails degrades to `default` rather
    than taking the screen down: the sweep's token cannot list runs, and the
    screen is still worth printing without that section."""
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode:
        if default is not None:
            return default
        sys.exit(f"gh {' '.join(args[:2])}: {out.stderr.strip()}")
    return json.loads(out.stdout) if out.stdout.strip() else default


def waits_on(body):
    """The blockers an Issue declares: a list of numbers, or a string when the
    line names something that is not an Issue, or None when there is no line.

    The roadmap form carried the same fact as a paragraph before solorepo's DR-114, so
    that paragraph is read too, for the Issues filed under it."""
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
    """Where an Issue sits: what blocks it, whether an open pull request
    already closes it, and otherwise whether it is ripe."""
    labels = {l["name"] for l in issue["labels"]}
    level = next((d for d in DIFFICULTY if d in labels), None)
    waits = waits_on(issue["body"])
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
    }


def row(i):
    level = i["level"] or ("roadmap" if i["kind"] == "roadmap" else "untriaged")
    return f"  #{i['number']:<4} {level:<10} {i['note']:<24} {i['title'][:70]}"


def issues(closing=None):
    found = gh("issue", "list", "--state", "open", "--limit", "200",
               "--json", "number,title,labels,body,milestone", default=[])
    numbers = {i["number"] for i in found}
    return sorted((classify(i, numbers, closing or {}) for i in found),
                  key=lambda i: i["number"])


def untriaged(rows):
    """A Challenge with no difficulty: the coder cannot see it, so nobody can
    tell an empty queue from an untriaged one."""
    return [i for i in rows if i["kind"] == "challenge" and not i["level"]]


def pull_requests():
    """Print the open pull requests, and return which Issues they close:
    Issue number to pull request number, read from the closing keywords
    GitHub resolved in each body."""
    prs = gh("pr", "list", "--state", "open", "--json",
             "number,title,autoMergeRequest,mergeStateStatus,reviewDecision,isDraft,headRefName,"
             "closingIssuesReferences",
             default=[])
    print("pull requests — the loops' work in progress, not what is next")
    if not prs:
        print("  none open")
    for pr in prs:
        armed = "armed" if pr.get("autoMergeRequest") else "draft" if pr["isDraft"] else "open"
        state = (pr.get("mergeStateStatus") or "").lower()
        review = (pr.get("reviewDecision") or "").lower().replace("_", " ")
        print(f"  #{pr['number']:<4} {armed:<7} {state:<9} {review:<17} {pr['title'][:60]}")
    print()
    return {ref["number"]: pr["number"]
            for pr in prs for ref in pr.get("closingIssuesReferences") or []}


def loops():
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
    print()


def milestones(rows):
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
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
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
    missing = untriaged(rows)
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
    section("untriaged — a Challenge with no difficulty; the sweep fails on these", missing)
    section("roadmap — deferred by definition, never queued", roadmap)


def check():
    missing = untriaged(issues())
    if missing:
        print(f"x  triage — {len(missing)} Challenge(s) carry no difficulty; "
              "the coder cannot see them (solorepo's DR-112)")
        for i in missing:
            print(row(i))
        return 1
    print("ok triage — every Challenge carries a difficulty")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on a Challenge with no difficulty label, one line each")
    args = ap.parse_args()
    sys.exit(check() if args.check else screen())
