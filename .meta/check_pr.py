#!/usr/bin/env python3
"""The GitHub half of the gate: A15, held against a live pull request.

`check.py` reads files and needs no network. This reads GitHub, so it is a
separate command with a separate lifecycle — it runs when a pull request opens
or changes, and there is nothing for it to say the rest of the time.

    python .meta/check_pr.py 12          # what CI runs
    python .meta/check_pr.py --file b.md # a body on disk, for watching it fail
    python .meta/check_pr.py 12 --watch  # one line per change, until it closes

What a body must contain is **derived from the form**, never listed here. The
headings come out of the fence in `.meta/templates/pull-request.md`, which is
the same text GitHub renders into `.github/PULL_REQUEST_TEMPLATE.md`. Adding a
heading to the form makes it required by that act alone; a checker with its own
copy of the list would drift from the form the first time either moved, and the
drift would show up as a check that had quietly stopped asking for something.

A15 is the one Article in this area that is mechanically checkable. A13 and A14
are not — reasoning in a commit message is a judgement about a paragraph, and no
length check reaches it. What is checkable is narrower and still worth having:
every item under *what was noticed and not done* is a link, so the pull request
cannot close over an observation that has nowhere to live afterwards.

The same shape holds the other direction. Every item under *what it closes*
carries one of GitHub's closing keywords, so the merge closes the Challenge the
pull request finished and no one has to remember a second act (DR-089).
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

META = pathlib.Path(__file__).parent
FORM = META / "templates" / "pull-request.md"
# A promotion, in the only form that can be checked: a link to the Issue the
# thread became. Bare "#12" is deliberately not enough — it is what someone
# types when referring to an Issue, not when filing one.
# A parked item announces itself, so a thread deliberately held open until merge
# is not confused with one owed an answer. Same trick as the handoff note's
# heading: a convention a machine can see, rather than a guess from who opened it.
# Who wrote a comment, when the GitHub login cannot say. Every comment an agent
# posts here is authored by the solo's account, so a genuine exchange between the
# solo and an agent is indistinguishable from one party talking to itself. The
# trailer is what separates them — the same one the commits carry.
ACTOR = re.compile(r"^Actor:\s*(\S+)", re.M)
NOTICED = re.compile(r"^\W*\*\*Noticed and not done\.?\*\*", re.M)
PROMOTED = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/issues/\d+")
HEADING = re.compile(r"^\*\*(.+?)\.\*\*", re.M)
PLACEHOLDER = re.compile(r"<[^<>\n]*\s[^<>\n]*>")
LINK = re.compile(r"(#\d+|https?://\S+)")
BULLET = re.compile(r"^\s*[-*]\s+(.*)$", re.M)
NONE = re.compile(r"^\s*(none|nothing)\b", re.I)
DEFERRED = "What was noticed and not done"
CLOSES = "What it closes"
# GitHub's closing keywords, followed by the reference GitHub accepts — a bare
# number, owner/repo#n, or the Issue's URL. Anything else under this heading
# names an Issue the merge will leave open.
KEYWORD = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+"
                     r"(?:#\d+|[\w.-]+/[\w.-]+#\d+|https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)", re.I)


def fence(path):
    return path.read_text().split("```markdown\n", 1)[1].split("\n```", 1)[0]


def uncoded(text):
    """The text with code fences and inline spans removed.

    `Map<K, V>` is a generic, not an unfilled slot, and a placeholder rule that
    flagged it in a repository with a Rust bootstrap would be switched off within
    a week — which Ratchet says is the worse outcome. Code belongs in backticks,
    so dropping what is in backticks costs nothing and buys the rule its life.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def sections(body):
    """Body text split at each `**Heading.**`, in order, as {heading: text}."""
    marks = list(HEADING.finditer(body))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out[m.group(1)] = body[m.end():end].strip()
    return out


def check(title, body):
    problems = []
    required = [m.group(1) for m in HEADING.finditer(fence(FORM))]
    found = sections(body)

    for heading in required:
        if heading not in found:
            problems.append(f"missing section: **{heading}.**")
        elif not found[heading]:
            problems.append(f"empty section: **{heading}.** — the form was submitted blank")

    # `.meta/templates/` fills with <angle brackets>, so one surviving in a
    # submitted body is the form itself showing through. The form's own
    # placeholders are matched exactly, because `<details>` and `<br>` are
    # legitimate in a body and a rule that flagged them would be switched off.
    # Anything bracketing a phrase is caught too — that shape is never markup.
    form = fence(FORM)
    literal = set(PLACEHOLDER.findall(form)) | set(re.findall(r"<[^<>\s]+>", form))
    for where, raw in (("title", title), ("body", body)):
        text = uncoded(raw)
        seen = set(PLACEHOLDER.findall(text)) | (literal & set(re.findall(r"<[^<>\s]+>", text)))
        for m in sorted(seen):
            problems.append(f"unfilled placeholder in {where}: {m}")

    # What the merge closes. The heading's items carry a closing keyword or the
    # Issue stays open after the pull request that finished it has merged —
    # which is how #26 sat open until a verb was written to close it (DR-089).
    closing = found.get(CLOSES, "")
    if closing and not NONE.match(closing):
        items = [m.group(1).strip() for m in BULLET.finditer(closing)]
        if not items:
            problems.append(
                f"**{CLOSES}.** is prose. It takes one `Closes #n` per item, or "
                "an explicit 'None.'")
        for item in items:
            if not KEYWORD.search(item):
                problems.append(f"no closing keyword, so the merge leaves it open: {item}")

    # A15 proper. Everything else above is the form being present; this is the
    # rule the form exists to carry.
    deferred = found.get(DEFERRED, "")
    if deferred and not NONE.match(deferred):
        items = [m.group(1).strip() for m in BULLET.finditer(deferred)]
        if not items:
            problems.append(
                f"**{DEFERRED}.** is prose. It takes one link per item, or "
                "an explicit 'None.'")
        for item in items:
            if not LINK.search(item):
                problems.append(f"not a link, so it closes with this pull request: {item}")
    return problems


THREADS = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          resolvedBy { login }
          isOutdated
          path
          line
          comments(first: 50) { nodes { author { login } body } }
        }
      }
    }
  }
}
"""


def gh(*args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"gh: {out.stderr.strip()}")
    return json.loads(out.stdout)


def unsigned_commits(ref):
    """A19. Every commit on the branch names the Actor that wrote it.

    The git hook appends the Trailer, and a hook lives in a worktree — so an
    agent in a fresh sandbox has none, and the one thing that cannot be forgotten
    is a check that runs on the pull request. The hook saves the trip; this is
    the guarantee.
    """
    commits = gh("pr", "view", ref, "--json", "commits")["commits"]
    return [f"{c['oid'][:8]} names no Actor: {c['messageHeadline'][:60]}"
            for c in commits
            if not ACTOR.search(c.get("messageBody") or "")]


def threads(ref):
    """Every review thread on a pull request, fetched once.

    Split from both readers below because the fetch is the slow, networked,
    untestable half and neither predicate should own it. It is also what makes
    the threads readable at all: A16 only ever answered pass or fail, so the
    thing that knows how to ask GitHub what was said could not be asked to say
    it.
    """
    owner, name = gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"].split("/")
    number = gh("pr", "view", ref, "--json", "number")["number"]
    data = gh("api", "graphql", "-f", f"query={THREADS}",
              "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}")
    return data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]


def unaddressed(nodes, parked=False):
    """What is still owed an answer, in the order a reader should take them.

    Unresolved is the test, and it now covers two different things. A review
    point is owed an answer. An item **noticed and not done** is deliberately
    held open until merge, because an unresolved thread is what stops it being
    walked past — so it is unresolved on purpose and waking someone for it is
    noise. `parked` selects which set is wanted.

    The **last** comment decides, which is the only version where both
    transitions work. Reading the first would stop a reviewer's point from ever
    becoming work for later; reading any would let a thread be parked and never
    un-parked, which is what happened the first time — a thread answered by the
    change that overtook it still read as held.

    The cost is that a parked item un-parks when anyone replies without the
    marker. That is usually right, since a reply means it is live again, and
    re-marking is one line.

    An outdated thread is still unaddressed (DR-057) and is marked rather than
    filtered: the anchor moving is the reader's context, not a reason to skip it.
    """
    out = []
    for t in nodes:
        if t["isResolved"]:
            continue
        comments = t["comments"]["nodes"]
        held = bool(comments) and bool(NOTICED.search(comments[-1]["body"] or ""))
        if held != parked:
            continue
        where = t["path"] or "the pull request"
        if t.get("line"):
            where += f":{t['line']}"
        if t["isOutdated"]:
            where += " (outdated — answer it anyway)"
        said = []
        for c in comments:
            who = (c["author"] or {}).get("login", "someone")
            said.append(f"    {who}: " + " ".join((c["body"] or "").split())[:600])
        out.append(f"  {t['id']}\n  {where}\n" + "\n".join(said))
    return out


def owned_and_open():
    """The pull request this worktree is working on, and what it still owes.

    Resolved by **branch**, because the branch is where the Job already is: one
    branch, one pull request, by construction, and it is what an agent wakes up
    on. Authorship cannot do this job — every pull request in a solorepo is the
    solo's (DR-014), so `--author @me` reconstructs a fact that was never in
    doubt and says nothing about which one this thread is answerable for.

    No local state. A background task dies with the session that started it and
    a branch note would have to be found before it could be read; the checkout
    is the token, and GitHub resolves it.

    Where the branch has no pull request, every open one is listed instead —
    without pretending that ownership was established. Which of them is this
    thread's is a question the listing cannot answer, and saying so is the
    honest output.
    """
    branch = subprocess.run(["git", "branch", "--show-current"],
                            capture_output=True, text=True).stdout.strip()
    if branch and branch != "main":
        found = gh("pr", "list", "--head", branch, "--state", "open",
                   "--json", "number,title")
        if found:
            return branch, [(p["number"], p["title"], unaddressed(threads(str(p["number"]))))
                            for p in found]
        return branch, []
    return branch, [(p["number"], p["title"], None)
                    for p in gh("pr", "list", "--state", "open", "--json", "number,title")]


def unpushed():
    """A18. Work in a worktree the successor will never see has not been done.

    Two conditions, and neither needs judgement: nothing uncommitted, and nothing
    committed that has not been pushed. It is the one step of a Handoff a machine
    can own outright, which is exactly why it is an Article and not a step
    carrying advice.
    """
    def git(*args):
        """Failure is a finding here, not a zero.

        The first version returned stdout and dropped the exit code, so
        `rev-list @{u}..HEAD` on a branch with no upstream printed nothing to
        stdout, failed, and read as "nothing ahead". A18 then passed on a branch
        that had never been pushed — which is the exact case it exists to catch,
        and the one where a silent pass costs the whole afternoon.
        """
        out = subprocess.run(["git", *args], capture_output=True, text=True)
        return out.returncode, out.stdout.strip(), out.stderr.strip()

    problems = []
    code, dirty, err = git("status", "--porcelain")
    if code:
        return [f"git status failed, so nothing here was checked: {err}"]
    if dirty:
        problems.append(f"{len(dirty.splitlines())} uncommitted change(s); a successor sees none of them")
    code, upstream, _ = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if code:
        problems.append("the branch has no upstream; push it, or there is nothing to hand over")
        return problems
    code, ahead, err = git("rev-list", f"{upstream}..HEAD")
    if code:
        return problems + [f"git rev-list failed, so pushed state is unknown: {err}"]
    if ahead:
        problems.append(f"{len(ahead.splitlines())} commit(s) not pushed; the branch is the handoff")
    return problems


def resume(ref):
    """What GitHub holds about a pull request, for an arriving Job.

    This is the whole briefing. A handoff carries no prose — it is a review
    request, which is a state rather than a message — so what an arriving Job
    knows is what GitHub holds, and there is nothing else to go stale.
    """
    pr = gh("pr", "view", ref, "--json",
            "number,title,body,headRefName,statusCheckRollup")
    out = [f"#{pr['number']} {pr['title']}",
           f"branch: {pr['headRefName']}", "", "--- body ---", pr["body"] or "(empty)", ""]
    states = {c.get("name") or c.get("context"): c.get("conclusion") or c.get("state")
              for c in pr.get("statusCheckRollup") or []}
    out.append("checks: " + (", ".join(f"{k}={v}" for k, v in states.items()) or "none"))
    owed = unaddressed(threads(ref))
    out.append(f"--- {len(owed)} thread(s) owed an answer ---")
    out += owed
    return "\n".join(out)


def snapshot(ref):
    """Everything on a pull request that a watcher compares between polls.

    Keyed so that a change is a set difference and not a diff of text: a
    comment or review by its id, a thread by its id and how many comments it
    holds, a check by its name and state. The keys are what GitHub already
    holds, so nothing is written locally and a watch restarted from scratch
    reports the same events a continuous one would have.
    """
    pr = gh("pr", "view", ref, "--json", "number,state,comments,reviews,statusCheckRollup")
    comments = {c["id"]: c for c in pr["comments"]}
    reviews = {r["id"]: r for r in pr["reviews"]}
    threads_ = {t["id"]: t for t in threads(ref)}
    # A check still running has no conclusion; its status says so, which reads
    # better than a `None` beside a result and is a change worth a line.
    checks = {c.get("name") or c.get("context"):
              c.get("conclusion") or c.get("state") or c.get("status") or "PENDING"
              for c in pr.get("statusCheckRollup") or []}
    return pr["number"], pr["state"], comments, reviews, threads_, checks


def mine(body):
    """Whether this session wrote a comment, read from the Trailer it carries.

    A watch that reported the watcher's own comments back to it would wake a
    conversation for every line it posted. The login cannot say — every agent
    posts under one account — but the channel signs each comment with the
    session's id, and that is what is compared.
    """
    me = next((os.environ[k] for k in ("CLAUDE_CODE_SESSION_ID", "ACTOR_SESSION")
               if os.environ.get(k)), None)
    found = ACTOR.search(body or "")
    return bool(me and found and found.group(1) == me)


def said(body, limit=300):
    return " ".join((body or "").split())[:limit]


def watch(ref, every=60):
    """One line per change on a pull request, until it closes.

    PR First's fourteenth step is to stay subscribed, and until this existed it
    was the one step in the skill with no command behind it — so a session
    improvised a poll, or reported that it could not hold one without having
    tried (DR-102). This is the subscription. Keeping it running is the
    harness's business: it is a process that prints, and any harness that can
    keep a process alive and be woken by a line it prints can hold it.

    It polls, because GitHub pushes nothing to a session without a webhook and
    a webhook needs somewhere to land. The interval is a minute, which is the
    rate limit's comfort and well inside "a review lands minutes after a push".

    Each line is one event. Nothing is emitted for the first poll except a
    heading, so a watch started on a busy pull request does not replay it; a
    poll that fails is skipped and the next one compares against the last that
    did not, so nothing is lost across a transient failure. Exits when the pull
    request merges or closes, which is the subscription ending.
    """
    import time
    previous = None
    while True:
        try:
            current = snapshot(ref)
        except SystemExit as e:
            print(f"? poll skipped: {e}", file=sys.stderr)
            time.sleep(every)
            continue
        number, state, comments, reviews, threads_, checks = current
        if previous is None:
            owed = len(unaddressed(list(threads_.values())))
            print(f"watching #{number}: {owed} thread(s) owed an answer, "
                  + ", ".join(f"{k}={v}" for k, v in checks.items()), flush=True)
        else:
            _, _, p_comments, p_reviews, p_threads, p_checks = previous
            for cid in comments.keys() - p_comments.keys():
                c = comments[cid]
                if not mine(c["body"]):
                    print(f"comment by {c['author']['login']}: {said(c['body'])}", flush=True)
            for rid in reviews.keys() - p_reviews.keys():
                r = reviews[rid]
                if not mine(r["body"]):
                    print(f"review by {r['author']['login']}: {r['state']} {said(r['body'])}",
                          flush=True)
            for tid, t in threads_.items():
                where = (t["path"] or "the pull request") + (f":{t['line']}" if t.get("line") else "")
                before = p_threads.get(tid)
                nodes = t["comments"]["nodes"]
                if before is None or len(nodes) > len(before["comments"]["nodes"]):
                    last = nodes[-1] if nodes else None
                    if last and not mine(last["body"]):
                        who = (last["author"] or {}).get("login", "someone")
                        print(f"thread {tid} on {where} by {who}: {said(last['body'])}", flush=True)
                if before is not None and t["isResolved"] and not before["isResolved"]:
                    by = (t.get("resolvedBy") or {}).get("login", "someone")
                    print(f"thread {tid} on {where} resolved by {by}", flush=True)
            for name, value in checks.items():
                if p_checks.get(name) != value:
                    print(f"check {name}: {value}", flush=True)
        if state in ("MERGED", "CLOSED"):
            print(f"pr {state}", flush=True)
            return
        previous = current
        time.sleep(every)


def resolved_without_an_answer(ref):
    """A16. Requiring resolution is what makes this check necessary.

    GitHub can insist every thread be resolved, and that insistence teaches
    the shortcut: resolve it and merge. A thread closed that way looks identical
    afterwards to one that was answered, which makes the merge gate a control
    whose passing carries no information — so the gate on the gate is that a
    resolved thread carries a reply from someone other than whoever opened it.

    Nothing here objects to an *unresolved* thread. The ruleset already blocks
    the merge for those, and a check saying the same thing twice is one of them
    drifting.
    """
    return unanswered(threads(ref))


def parties(thread):
    """Who took part: the login and the Actor Trailer, plus whoever resolved it.

    Resolving is an act, not a silence. A solo who reads an agent's answer and
    marks the thread resolved has taken part — that is assent, and it is what
    A16 asks for. Requiring a reply as well would make the Article cost a
    sentence of theatre per thread, which is how a rule gets routed around.

    It is trustworthy only while an agent does not resolve a thread it is the
    sole author of, because the agent and the solo share one login and
    `resolvedBy` cannot tell them apart. That is a Discipline step until DR-066
    gives each Role an account, at which point the distinction is GitHub's to
    make rather than ours to observe.

    A16 asks for a second party. In a solorepo every comment an agent writes is
    posted under the solo's account, so logins alone can never show two — and the
    Article would be unsatisfiable exactly where it matters, between the solo and
    the agent he is arguing with. An unsigned comment is the human; a signed one
    is the Job that signed it.
    """
    seen = set()
    resolver = (thread.get("resolvedBy") or {}).get("login")
    if resolver:
        seen.add(resolver)
    for c in thread["comments"]["nodes"]:
        login = (c["author"] or {}).get("login", "someone")
        actor = ACTOR.search(c["body"] or "")
        seen.add(f"{login}/{actor.group(1)}" if actor else login)
    return seen


def unanswered(nodes):
    """The predicate, apart from the fetching, so it can be watched failing.

    Three things count as an answer. A reply from someone other than whoever
    opened the thread, which is the original rule. Or a link to the Issue the
    thread became, which is what promotion looks like: work noticed and not done
    is raised here first and earns an Issue only if it survives the argument, so
    the thread that spawned one is answered by saying which.

    Or the solo resolving it, which is assent rather than silence — see
    `parties`.

    The second was added because the first cannot be satisfied by a solo working
    with agents. Every thread on a change may be opened and closed by the same
    party, and demanding a second one either manufactures a reply or teaches the
    shortcut A16 exists to catch.
    """
    problems = []
    for t in nodes:
        if not t["isResolved"]:
            continue
        comments = t["comments"]["nodes"]
        if len(parties(t)) >= 2:
            continue
        if any(PROMOTED.search(c["body"] or "") for c in comments):
            continue
        who = ", ".join(sorted(parties(t))) or "nobody"
        problems.append(
            f"resolved without an answer: {t['path'] or 'the pull request'}, "
            f"opened by {who} — answer it, or promote it to an Issue and link that")
    return problems


def repo():
    return gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]


WORKFLOW = META.parent / ".github" / "workflows" / "gate.yml"


def required_contexts():
    """The status checks `main`'s ruleset waits for, and the jobs that report them.

    A comment used to say "rename in both places or in neither", which is not a
    control: renaming a job leaves the ruleset waiting on a context nothing
    produces, and every merge blocks with no clue why. The ruleset is readable,
    so it is read.

    Loud and unmarked when it cannot run — a fork, or a token without
    `administration: read`, sees no rulesets and is told so rather than passed.
    """
    jobs = re.findall(r"^    name: (.+)$", WORKFLOW.read_text(), re.M)
    try:
        rules = gh("api", f"repos/{repo()}/rules/branches/main")
    except SystemExit:
        print("?  ruleset not readable from here; required contexts unchecked")
        return []
    contexts = sorted({c["context"]
                       for r in rules if r["type"] == "required_status_checks"
                       for c in r["parameters"]["required_status_checks"]})
    if not contexts:
        print("?  no required status checks on main; nothing to compare")
        return []
    missing = [c for c in contexts if c not in jobs]
    return [f"main requires the status check '{c}', which no job in "
            f"{WORKFLOW.name} reports" for c in missing]


def from_github(ref):
    out = subprocess.run(["gh", "pr", "view", ref, "--json", "title,body"],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"gh: {out.stderr.strip()}")
    data = json.loads(out.stdout)
    return data["title"], data["body"] or ""


def gate(ref):
    """The pull request check, whole: the body against the form, A16, A19 and
    the required contexts. One function because it is run from two places —
    on the push, and on the clock (DR-105) — and two copies would be two gates."""
    title, body = from_github(ref)
    return (check(title, body) + resolved_without_an_answer(ref)
            + unsigned_commits(ref) + required_contexts())


CONTEXT = "pull request"


def publish(number, head, problems):
    """Post the result as the check run `main`'s ruleset waits on, on the pull
    request's head commit, so a sweep's finding blocks the merge the way the
    push's did. Needs a token that can create check runs, which is the
    workflow's and not a person's — run by hand, this is where it stops."""
    summary = "\n".join(f"- {p}" for p in problems) or "nothing owed"
    gh("api", f"repos/{repo()}/check-runs",
       "-f", f"name={CONTEXT}", "-f", f"head_sha={head}", "-f", "status=completed",
       "-f", f"conclusion={'failure' if problems else 'success'}",
       "-f", f"output[title]={'x ' if problems else 'ok '}{CONTEXT}",
       "-f", f"output[summary]={summary}")


def sweep_all(publishing):
    """A16 between the last push and the merge (#5). Resolving a thread fires
    no event, so the check that ran on the push is stale the moment one is
    resolved, and a schedule is the only thing left to run it. Every open pull
    request, one line each in A21's shape, and the result published as the
    check when asked.
    """
    found = gh("pr", "list", "--state", "open", "--json", "number,title,headRefOid")
    if not found:
        print("ok sweep — no open pull requests")
        return 0
    failed = False
    for pr in found:
        number = str(pr["number"])
        problems = gate(number)
        print(f"{'x  ' if problems else 'ok '}#{number} {pr['title'][:60]}"
              + (f" ({len(problems)})" if problems else ""))
        for p in problems:
            print(f"     {p}")
        if publishing:
            publish(number, pr["headRefOid"], problems)
        failed |= bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pr", nargs="?", help="pull request number, URL or branch")
    ap.add_argument("--file", help="read a body from disk instead of GitHub")
    ap.add_argument("--title", default="a real title", help="title to use with --file")
    ap.add_argument("--threads", action="store_true",
                    help="print the threads still owed an answer, and check nothing")
    ap.add_argument("--resume", action="store_true",
                    help="what an arriving Job needs, read from GitHub")
    ap.add_argument("--handoff", action="store_true",
                    help="A18: refuse to hand off work the successor cannot see")
    ap.add_argument("--sweep", action="store_true",
                    help="every open pull request you own, and what each still owes")
    ap.add_argument("--watch", action="store_true",
                    help="one line per change on the pull request, until it closes")
    ap.add_argument("--every", type=int, default=60, help="seconds between polls under --watch")
    ap.add_argument("--all", action="store_true",
                    help="the check on every open pull request, one line each")
    ap.add_argument("--publish", action="store_true",
                    help="with --all: post each result as the required check run")
    args = ap.parse_args()

    if args.all:
        sys.exit(sweep_all(args.publish))

    if args.sweep:
        branch, found = owned_and_open()
        if not found:
            print(f"no open pull request for branch '{branch}'" if branch
                  else "no open pull requests")
        for number, title, owed in found:
            if owed is None:
                print(f"#{number} {title} — open, and not this branch's")
                continue
            print(f"#{number} {title} — {len(owed)} unaddressed")
            for item in owed:
                print(item)
        sys.exit(0)

    if args.handoff:
        problems = unpushed()
        for p in problems:
            print(f"x  {p}")
        print(("x  " if problems else "ok ") + "handoff")
        sys.exit(1 if problems else 0)

    if args.watch:
        if not args.pr:
            ap.error("--watch needs a pull request")
        watch(args.pr, args.every)
        sys.exit(0)

    if args.resume:
        if not args.pr:
            ap.error("--resume needs a pull request")
        print(resume(args.pr))
        sys.exit(0)

    if args.threads:
        if not args.pr:
            ap.error("--threads needs a pull request")
        nodes = threads(args.pr)
        owed, parked = unaddressed(nodes), unaddressed(nodes, parked=True)
        print("\n".join(owed) if owed else "nothing unaddressed")
        if parked:
            print(f"\n--- {len(parked)} noticed and not done, held for promotion at merge ---")
            print("\n".join(parked))
        sys.exit(0)

    if args.file:
        title, body = args.title, pathlib.Path(args.file).read_text()
    elif args.pr:
        title, body = from_github(args.pr)
    else:
        ap.error("give a pull request, or --file")

    problems = gate(args.pr) if args.pr else check(title, body)
    for p in problems:
        print(f"x  {p}")
    print(f"{'x  ' if problems else 'ok '}pull request"
          + (f" ({len(problems)})" if problems else ""))
    sys.exit(1 if problems else 0)
