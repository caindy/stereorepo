"""What has happened on a pull request since: continuously under `watch`, once under `resume`.

`watch` prints one line per change and exits on an actionable event or when
the pull request closes. `resume` reads what GitHub holds once and prints the
briefing an arriving Job needs. A snapshot keys checks by name, reduced to the
latest run of each, so a re-run concluding as its predecessor did is still a
change. A third mode answering the same question belongs here.
"""
import sys

from lib.check_pr import github, review

# A check that has concluded and did not fail. GitHub reports a check that has
# not finished with no conclusion at all, and pending is not green: PR First
# stops a handoff at green, and a pull request whose gate has not answered yet
# is not one whose gate passed.
GREEN = {"SUCCESS", "NEUTRAL", "SKIPPED"}

# Check status/state values that mean the check is still running and has not yet concluded.
UNCONCLUDED = {"PENDING", "IN_PROGRESS", "QUEUED", "WAITING", "REQUESTED", "EXPECTED"}


def deduplicate_checks(contexts):
    """When multiple check runs share a name (e.g. repeated runs or body revisions),
    keep only the latest entry by startedAt / completedAt / createdAt."""
    def timestamp(c):
        completed = c.get("completedAt") or ""
        if completed.startswith("0001"):
            completed = ""
        return c.get("startedAt") or completed or c.get("createdAt") or ""
    deduped = {}
    for c in sorted(contexts, key=timestamp):
        name = c.get("name") or c.get("context") or "check"
        deduped[name] = c
    return list(deduped.values())


def snapshot(ref):
    """Queries pull request metadata, comments, reviews, threads, and check rollups.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        tuple: (number, state, comments_dict, reviews_dict, threads_dict, checks_dict, mergeable).

    Checks are keyed by name, so the several runs a name accumulates — a
    repeated dispatch, a cancelled run — are reduced to the latest by
    `deduplicate_checks` before the key is taken. Each answers with its
    conclusion and the URL of the run that reached it: a rerun concluding as
    its predecessor did is otherwise indistinguishable from no rerun at all,
    and the watcher would sit on it.
    """
    pr = github.gh("pr", "view", ref, "--json", "number,state,comments,reviews,mergeable")
    comments = {c["id"]: c for c in pr["comments"]}
    reviews = {r["id"]: r for r in pr["reviews"]}
    threads_ = {t["id"]: t for t in github.threads(ref)}
    sorted_checks = deduplicate_checks(github.rollup_of(pr["number"]))
    checks = {c.get("name") or c.get("context"):
              (c.get("conclusion") or c.get("state") or c.get("status") or "PENDING",
               c.get("detailsUrl") or c.get("targetUrl"))
              for c in sorted_checks}
    return (pr["number"], pr["state"], comments, reviews, threads_, checks,
            pr.get("mergeable") or "UNKNOWN")


def watch(ref, every=60):
    """Monitors a pull request for changes, printing events and exiting on actionable signals.

    Args:
        ref: Pull request number, URL, or head branch reference.
        every: Polling frequency in seconds (default: 60).

    Returns:
        int: Exit status code (0 on actionable completion or closure, non-zero on error).

    Mergeability is remembered as the last answer GitHub gave, apart from the
    snapshot, because `UNKNOWN` is not a state of the branch but GitHub
    computing one and every push sets it: compared snapshot to snapshot, a push
    would report `UNKNOWN` and then the value the branch already had, which is
    two lines for no change. Nothing said yet — including by the heading — is
    a change from nothing, and is printed.

    A conflicting branch is reported and not exited on. It is what the coder's
    rebase pass is dispatched for, and a watcher that exited would stop
    watching the branch about to move under it.
    """
    import time
    previous = None
    merges = None
    while True:
        try:
            current = snapshot(ref)
        except SystemExit as e:
            print(f"? poll skipped: {e}", file=sys.stderr)
            time.sleep(every)
            continue
        number, state, comments, reviews, threads_, checks, mergeable = current
        if previous is None:
            owed = len(review.unaddressed(list(threads_.values())))
            print(f"watching #{number}: {owed} thread(s) owed an answer, mergeable={mergeable}, "
                  + ", ".join(f"{k}={v}" for k, (v, _) in checks.items()), flush=True)
        else:
            _, _, p_comments, p_reviews, p_threads, p_checks, _ = previous
            actionable = []
            for cid in comments.keys() - p_comments.keys():
                c = comments[cid]
                if not review.mine(c["body"]):
                    print(f"comment by {c['author']['login']}: {review.said(c['body'])}", flush=True)
                    actionable.append(f"comment by {c['author']['login']}")
            for rid in reviews.keys() - p_reviews.keys():
                r = reviews[rid]
                if not review.mine(r.get("body", "")):
                    print(f"review by {r['author']['login']}: {r['state']} {review.said(r.get('body', ''))}",
                          flush=True)
                    actionable.append(f"review by {r['author']['login']} ({r['state']})")
            for tid in threads_.keys() - p_threads.keys():
                t = threads_[tid]
                where = (t["path"] or "the pull request") + (f":{t['line']}" if t.get("line") else "")
                first_author = (t["comments"]["nodes"][0]["author"] or {}).get("login", "someone") if t["comments"]["nodes"] else "someone"
                first_body = t["comments"]["nodes"][0]["body"] if t["comments"]["nodes"] else ""
                print(f"new thread on {where} by {first_author}: {review.said(first_body)}", flush=True)
                actionable.append(f"new thread on {where}")
            for tid, t in threads_.items():
                where = (t["path"] or "the pull request") + (f":{t['line']}" if t.get("line") else "")
                before = p_threads.get(tid)
                nodes = t["comments"]["nodes"]
                before_len = len(before["comments"]["nodes"]) if before else 0
                if before is None or len(nodes) > before_len:
                    last = nodes[-1] if nodes else None
                    if last and not review.mine(last["body"]):
                        who = (last["author"] or {}).get("login", "someone")
                        print(f"thread {tid} on {where} by {who}: {review.said(last['body'])}", flush=True)
                        actionable.append(f"thread comment by {who}")
                if before is not None and t["isResolved"] and not before["isResolved"]:
                    by = (t.get("resolvedBy") or {}).get("login", "someone")
                    print(f"thread {tid} on {where} resolved by {by}", flush=True)
            for name, (value, run) in checks.items():
                before = p_checks.get(name)
                is_failure = (value not in GREEN and value not in UNCONCLUDED
                              and value != "CANCELLED")
                if before is None or before[0] != value:
                    print(f"check {name}: {value}", flush=True)
                    if is_failure:
                        actionable.append(f"check {name} ({value})")
                elif before[1] != run:
                    print(f"check {name}: {value} again, from a re-run", flush=True)
                    if is_failure:
                        actionable.append(f"check {name} ({value})")
            if mergeable != "UNKNOWN" and mergeable != merges:
                print(f"mergeable: {mergeable}" + (
                    " — GitHub builds no merge ref for a branch that conflicts, so no review "
                    "of this head can run" if mergeable == "CONFLICTING" else ""), flush=True)
            if actionable:
                print(f"watch exiting on #{number}: " + ", ".join(actionable), flush=True)
                return
        if state in ("MERGED", "CLOSED"):
            print(f"pr {state}", flush=True)
            return
        if mergeable != "UNKNOWN":
            merges = mergeable
        previous = current
        time.sleep(every)


def resume(ref):
    """Formats pull request status, check rollups, reviews, and unaddressed threads for resuming work.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        str: Formatted briefing summary of pull request state.
    """
    pr = github.gh("pr", "view", ref, "--json", "number,title,body,headRefName")
    out = [f"#{pr['number']} {pr['title']}",
           f"branch: {pr['headRefName']}", "", "--- body ---", pr["body"] or "(empty)", ""]
    states = {c.get("name") or c.get("context"): c.get("conclusion") or c.get("state")
              for c in github.rollup_of(pr["number"])}
    out.append("checks: " + (", ".join(f"{k}={v}" for k, v in states.items()) or "none"))
    held = github.pull(ref)
    given = review.verdicts(held["reviews"]["nodes"])
    if given:
        out.append(f"--- {len(given)} verdict(s), newest first, each on the head GitHub recorded it against ---")
        out += given
    owed = review.unaddressed(held["reviewThreads"]["nodes"], limit=None)
    out.append(f"--- {len(owed)} thread(s) owed an answer ---")
    out += owed
    return "\n".join(out)
