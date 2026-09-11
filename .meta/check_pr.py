#!/usr/bin/env python3
"""The GitHub half of the gate: A15, held against a live pull request, and the
quarter of A12 whose target is an Issue rather than a file.

`check.py` reads files and this repository's own commits, and reaches the remote
for one thing only — which Decision numbers are reserved, and only when the
record has a hole to explain (solorepo's DR-128). This reads GitHub for
everything it does, so it is a separate command with a separate lifecycle — it
runs when a pull request opens or changes, and there is nothing for it to say
the rest of the time.

    python .meta/check_pr.py 12          # what CI runs
    python .meta/check_pr.py --file b.md # a body on disk, for watching it fail
    python .meta/check_pr.py 12 --watch  # one line per change, exiting on actionable events or when it closes

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
pull request finished and no one has to remember a second act (solorepo's DR-089).

`--all`, the sweep the gate workflow runs on the clock, asks one more thing that
is not the body's: who takes each open pull request next (solorepo's DR-129). A
handoff here is a review request, which GitHub holds and reports — so a pull
request with no request on it, and a request no workflow can answer, are the two
states nothing reports and nothing wakes on.
"""
import argparse
import datetime
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
    # which is how solorepo's #26 sat open until a verb was written to close it (solorepo's DR-089).
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
      reviews(last: 100) {
        nodes { author { login } state submittedAt commit { abbreviatedOid } body }
      }
    }
  }
}
"""

# The check states on a pull request's head, asked for by name, per
# solorepo's DR-153. `gh --json statusCheckRollup` answers the same question,
# but the CLI's own GraphQL for that field traverses `checkSuite.workflowRun`
# — an Actions resource — and the gate's token holds no `actions` scope, so the
# whole query fails rather than returning the field null. Every reader takes a
# name and a state, and the watcher takes the run's url and when it started;
# nothing here wants a workflow run. Written out, the fetch names its own
# fields, as `THREADS` above already does.
ROLLUP = """
      commits(last: 1) { nodes { commit { statusCheckRollup {
        contexts(first: 100) { nodes {
          ... on CheckRun { name status conclusion startedAt completedAt detailsUrl }
          ... on StatusContext { context state createdAt targetUrl }
        } }
      } } } }
"""

ROLLUP_ONE = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {%s}
  }
}
""" % ROLLUP

# Every open pull request's head, the first hundred most recently touched.
# Which hundred those are is not necessarily the hundred `gh pr list` returns:
# that call takes its own default limit and orders by whatever the CLI orders
# by, which is a fact about `gh` this file would have to assert and cannot
# cite — and resting the sweep on what the CLI does on its behalf is the thing
# solorepo's DR-153 is about. So `sweep_all` pairs the two by number and names
# what this query did not answer for, rather than needing the two to agree.
ROLLUP_ALL = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 100,
                 orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes { number %s }
    }
  }
}
""" % ROLLUP


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


def pull(ref):
    """Every review thread and every review on a pull request, fetched once.

    Split from the readers below because the fetch is the slow, networked,
    untestable half and no predicate should own it. It is also what makes
    the threads readable at all: A16 only ever answered pass or fail, so the
    thing that knows how to ask GitHub what was said could not be asked to say
    it. The reviews ride in the same query because a verdict is the other half
    of what was said, and the one half that names a head (solorepo's DR-118).
    """
    owner, name = gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"].split("/")
    number = gh("pr", "view", ref, "--json", "number")["number"]
    data = gh("api", "graphql", "-f", f"query={THREADS}",
              "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}")
    return data["data"]["repository"]["pullRequest"]


def threads(ref):
    """Every review thread on a pull request."""
    return pull(ref)["reviewThreads"]["nodes"]


def checks_of(node):
    """A pull request's rollup contexts, flattened as the readers expect them.

    `ROLLUP` reaches the rollup where GitHub keeps it — on the head commit —
    and the readers want the list of contexts, which is what `gh --json
    statusCheckRollup` used to hand them. An empty list is a real answer: a
    head with no checks on it yet.
    """
    commits = (node.get("commits") or {}).get("nodes") or []
    if not commits:
        return []
    rollup = commits[0]["commit"].get("statusCheckRollup") or {}
    return (rollup.get("contexts") or {}).get("nodes") or []


def rollup_of(number):
    """The check states on one pull request's head."""
    owner, name = repo().split("/")
    data = gh("api", "graphql", "-f", f"query={ROLLUP_ONE}",
              "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}")
    return checks_of(data["data"]["repository"]["pullRequest"])


def rollups():
    """The check states on every open pull request's head, by number, in one
    query — which is what the sweep needs and what `gh pr list` was carrying."""
    owner, name = repo().split("/")
    data = gh("api", "graphql", "-f", f"query={ROLLUP_ALL}",
              "-F", f"owner={owner}", "-F", f"name={name}")
    return {pr["number"]: checks_of(pr)
            for pr in data["data"]["repository"]["pullRequests"]["nodes"]}


def where_of(thread, owed=True):
    """Where a thread sits, as a reader would look for it."""
    where = thread["path"] or "the pull request"
    if thread.get("line"):
        where += f":{thread['line']}"
    if thread["isOutdated"]:
        where += " (outdated — answer it anyway)" if owed else " (outdated)"
    return where


def shown(thread, where, limit=600):
    """A thread as the listing prints it: its id, where it sits, who said what.

    `limit` cuts each comment at that many characters; `None` prints it whole.
    The sweep's per-item line stays cut — its job is to say a thread is owed,
    not to be read — but `--threads` and `--resume`, which are how a thread
    gets read and answered, pass `None`: a comment cut mid-point reads as the
    whole of it, and a reader who trusts that has answered half a point (solorepo's #126).
    """
    spoke = []
    for c in thread["comments"]["nodes"]:
        who = (c["author"] or {}).get("login", "someone")
        body = " ".join((c["body"] or "").split())
        spoke.append(f"    {who}: " + (body if limit is None else body[:limit]))
    return f"  {thread['id']}\n  {where}\n" + "\n".join(spoke)


def unaddressed(nodes, parked=False, limit=600):
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

    An outdated thread is still unaddressed (solorepo's DR-057) and is marked rather than
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
        out.append(shown(t, where_of(t), limit=limit))
    return out


def settled(nodes, limit=600):
    """What was answered and resolved, in the shape of what is owed.

    `unaddressed` hides these on purpose: unresolved is the test, and a
    listing that counted the resolved would wake someone for nothing. Hidden
    from an arriving reviewer they cost a full review (solorepo's #122): its reading says
    a re-review reads each answer against the diff it claims, and a listing
    that shows only what is unresolved shows a re-review nothing, so every
    pass on solorepo's #117 ran the whole review again. So they are printed, after what
    is owed and apart from it, with who resolved each; nothing counts them.
    """
    out = []
    for t in nodes:
        if not t["isResolved"]:
            continue
        by = (t.get("resolvedBy") or {}).get("login", "someone")
        out.append(shown(t, where_of(t, owed=False) + f" — resolved by {by}", limit=limit))
    return out


def verdicts(reviews):
    """Each verdict, newest first, on the head GitHub recorded it against.

    A body that says which head it reviewed is a convention the next run has
    to trust; the commit a review was submitted on is a fact GitHub holds, and
    it is what a re-review reads to know what it has already seen (solorepo's DR-118).
    The review a `raise` posts under — no verdict, no body — says nothing and
    is left out; there is one per raise and per reply, which is why the query
    asks for the newest hundred and not the oldest (solorepo's #123). Newest first, and
    printed before everything else, so the verdict a re-review needs is inside
    the 2 KB preview a long listing is cut to; the owed section alone on solorepo's #117
    was 2.7 KB. The login is on each line and nothing here says whose Role a
    verdict is: the reader knows its own login, and the solo's approval and a
    dismissed verdict print as what they are.
    """
    out = []
    for r in reversed(reviews):
        body = said(r.get("body"), 600)
        if r["state"] == "COMMENTED" and not body:
            continue
        who = (r["author"] or {}).get("login", "someone")
        sha = (r.get("commit") or {}).get("abbreviatedOid") or "no head"
        when = (r.get("submittedAt") or "")[:16].replace("T", " ")
        out.append(f"  {who} {r['state']} on {sha} at {when}" + (f"\n    {body}" if body else ""))
    return out


def owned_and_open():
    """The pull request this worktree is working on, and what it still owes.

    Resolved by **branch**, because the branch is where the Job already is: one
    branch, one pull request, by construction, and it is what an agent wakes up
    on — whoever authored it. Authorship cannot do this job — since solorepo's DR-107 a
    pull request is authored by the Role's account, not the solo's, so
    `--author @me` only narrows to this Role's own pull requests and says
    nothing about which one this thread is answerable for.

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


def residue():
    """Local branches that outlived their pull request, and the worktrees on them.

    GitHub deletes a merged branch and nothing deletes the local one, so every
    checkout accumulates them (solorepo's DR-108): a branch per pull request, a worktree
    per session, and a listing the next Job reads through before finding its
    own. The predicate is the remote being gone after a prune — a branch that
    was never pushed is work in progress and is not named here.

    Naming is this tool's whole part. Removing is one command per branch, and
    it is printed rather than run, because a worktree may be the one this
    process stands in, or another session's.
    """
    def git(*args):
        return subprocess.run(["git", *args], capture_output=True, text=True).stdout
    git("fetch", "--prune", "--quiet", "origin")
    gone = [line.split()[0] for line in
            git("for-each-ref", "--format=%(refname:short) %(upstream:track,nobracket)",
                "refs/heads/").splitlines()
            if line.endswith(" gone")]
    if not gone:
        return []
    worktrees, path = {}, None
    for line in git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/"):
            worktrees[line[len("branch refs/heads/"):]] = path
    here = git("rev-parse", "--show-toplevel").strip()
    out = []
    for branch in gone:
        found = gh("pr", "list", "--head", branch, "--state", "all", "--json", "number,state")
        state = f"#{found[0]['number']} {found[0]['state'].lower()}" if found else "no pull request"
        tree = worktrees.get(branch)
        out.append(f"  {branch} — {state}" + (f"; worktree {tree}" if tree else ""))
        if tree == here:
            out.append("    this worktree stands on it: remove it from the main checkout, "
                       "or let the harness at exit")
            continue
        if tree:
            out.append(f"    git worktree remove {tree}")
        out.append(f"    git branch -D {branch}")
    return out


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
    pr = gh("pr", "view", ref, "--json", "number,title,body,headRefName")
    out = [f"#{pr['number']} {pr['title']}",
           f"branch: {pr['headRefName']}", "", "--- body ---", pr["body"] or "(empty)", ""]
    states = {c.get("name") or c.get("context"): c.get("conclusion") or c.get("state")
              for c in rollup_of(pr["number"])}
    out.append("checks: " + (", ".join(f"{k}={v}" for k, v in states.items()) or "none"))
    held = pull(ref)
    given = verdicts(held["reviews"]["nodes"])
    if given:
        out.append(f"--- {len(given)} verdict(s), newest first, each on the head GitHub recorded it against ---")
        out += given
    owed = unaddressed(held["reviewThreads"]["nodes"], limit=None)
    out.append(f"--- {len(owed)} thread(s) owed an answer ---")
    out += owed
    return "\n".join(out)


# A check that has concluded and did not fail. GitHub reports a check that has
# not finished with no conclusion at all, and pending is not green: PR First
# stops a handoff at green, and a pull request whose gate has not answered yet
# is not one whose gate passed.
GREEN = {"SUCCESS", "NEUTRAL", "SKIPPED"}
# Check status/state values that mean the check is still running and has not yet concluded.
UNCONCLUDED = {"PENDING", "IN_PROGRESS", "QUEUED", "WAITING", "REQUESTED", "EXPECTED"}


def snapshot(ref):
    """Everything on a pull request that a watcher compares between polls.

    Keyed so that a change is a set difference and not a diff of text: a
    comment or review by its id, a thread by its id and how many comments it
    holds, a check by its name and state. The keys are what GitHub already
    holds, so nothing is written locally and a watch restarted from scratch
    reports the same events a continuous one would have.
    """
    pr = gh("pr", "view", ref, "--json", "number,state,comments,reviews")
    comments = {c["id"]: c for c in pr["comments"]}
    reviews = {r["id"]: r for r in pr["reviews"]}
    threads_ = {t["id"]: t for t in threads(ref)}
    # When multiple check runs share a name (e.g. repeated dispatches or cancelled runs),
    # order by startedAt so the latest run wins.
    sorted_checks = sorted(rollup_of(pr["number"]),
                           key=lambda c: c.get("startedAt") or c.get("completedAt") or "")
    # A check still running has no conclusion; its status says so, which reads
    # better than a `None` beside a result and is a change worth a line. The
    # run's url rides beside the verdict: a re-run that ends where it started
    # is the same verdict from a different run, and keyed on the verdict alone
    # it was invisible (solorepo's #79).
    checks = {c.get("name") or c.get("context"):
              (c.get("conclusion") or c.get("state") or c.get("status") or "PENDING",
               c.get("detailsUrl") or c.get("targetUrl"))
              for c in sorted_checks}
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
    """One line per change on a pull request, exiting on actionable events or when it closes.

    PR First's fourteenth step is to stay subscribed, and until this existed it
    was the one step in the skill with no command behind it — so a session
    improvised a poll, or reported that it could not hold one without having
    tried (solorepo's DR-102). This is the subscription. Keeping it running is the
    harness's business: it is a process that prints, and any harness that can
    keep a process alive and be woken by a line it prints can hold it.

    It polls, because GitHub pushes nothing to a session without a webhook and
    a webhook needs somewhere to land. The interval is a minute, which is the
    rate limit's comfort and well inside "a review lands minutes after a push".

    Each line is one event. Nothing is emitted for the first poll except a
    heading, so a watch started on a busy pull request does not replay it; a
    poll that fails is skipped and the next one compares against the last that
    did not, so nothing is lost across a transient failure. Exits 0 when the
    subscription ends (the pull request merges or closes) or when an actionable
    event arrives (a new review from another author, a new unaddressed comment or
    thread, or a check failure). Exiting on actionable events completes the
    background process, waking any harness that resumes on command completion
    (solorepo's DR-138).
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
                  + ", ".join(f"{k}={v}" for k, (v, _) in checks.items()), flush=True)
        else:
            _, _, p_comments, p_reviews, p_threads, p_checks = previous
            actionable = []
            for cid in comments.keys() - p_comments.keys():
                c = comments[cid]
                if not mine(c["body"]):
                    print(f"comment by {c['author']['login']}: {said(c['body'])}", flush=True)
                    actionable.append(f"comment by {c['author']['login']}")
            for rid in reviews.keys() - p_reviews.keys():
                r = reviews[rid]
                if not mine(r["body"]):
                    print(f"review by {r['author']['login']}: {r['state']} {said(r['body'])}",
                          flush=True)
                    actionable.append(f"review by {r['author']['login']} ({r['state']})")
            for tid, t in threads_.items():
                where = (t["path"] or "the pull request") + (f":{t['line']}" if t.get("line") else "")
                before = p_threads.get(tid)
                nodes = t["comments"]["nodes"]
                if before is None or len(nodes) > len(before["comments"]["nodes"]):
                    last = nodes[-1] if nodes else None
                    if last and not mine(last["body"]):
                        who = (last["author"] or {}).get("login", "someone")
                        print(f"thread {tid} on {where} by {who}: {said(last['body'])}", flush=True)
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
            if actionable:
                print(f"watch exiting on #{number}: " + ", ".join(actionable), flush=True)
                return
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
    sole author of. Each Role has an account (solorepo's DR-066, DR-107), so `resolvedBy`
    tells a Role from the solo and from another Role; within one Role two Jobs
    share a login and only the Trailer tells them apart, which is why the
    channel refuses on the Trailer rather than the login.

    A16 asks for a second party. Every comment an agent writes is posted under
    its Role's account, so a login shows a Role and never a Job — and the
    Article would be unsatisfiable exactly where it matters, between two Jobs of
    one Role. An unsigned comment is the human; a signed one is the Job that
    signed it.
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


ASSERTIONS = META / "assertions"
FENCED = re.compile(r"```.*?```|`[^`\n]*`", re.S)
# What an Issue citation is, for both halves of A12's fourth quarter: the owner,
# which `check.py`'s `inherited citations` holds over the copy set, and the
# number, which this file resolves. One predicate, because a string the form
# check passes over and this one resolves is the two gates disagreeing about
# what a citation is (solorepo's DR-132). It lives here, of the two files, because
# this one is stdlib alone and so is the one either side can import; `check.py`
# reads it from here and defines none of its own.
#
# Not `#abc123`, which is a fragment or a colour, and not the tail of a longer
# number. Not a number in quotes either: `"#7"` in a probe is the string it
# greps its own output for, and a citation is not made by showing one.
ISSUE = re.compile(r"(?<![\w#&\"'])#(\d{1,4})(?!\d)")
# A citation of solorepo's Issues, in the form `cited decisions` has the
# inherited material write one of solorepo's record: the possessive, then a run,
# so `solorepo's #11, #21` names two.
FOREIGN = re.compile(r"solorepo's #\d{1,4}\b(?:(?:,| and|, and) #\d{1,4}\b)*")
# This Portfolio is solorepo, read off the identity its assertions declare.
# `cited decisions` asks its index; a checker with no YAML parser asks for the
# line, which is the same answer by a string search.
SCAFFOLD = re.compile(r"^\s*id:\s*work:portfolio/solorepo\s*$", re.M)
LIMIT = 1000


def cited_issues():
    """A12: every `#<n>` in an assertion resolves to an Issue (solorepo's DR-130).

    An Issue number is the one citation form here whose target is not in the
    repository. A `DR-nnn` resolves against the record and an `A<n>` against
    the Charter, both of which `check.py` reads off disk; a number GitHub never
    issued reads in a paragraph exactly like one it did, and nothing looked. So
    this quarter of A12 lives with the half of the gate that reads GitHub, and
    the other three-quarters are in `check.py`, which reads files and needs no
    network.

    Issues and pull requests share one sequence and the prose here cites both —
    a Challenge by its Issue, a precedent by the pull request that set it — so
    the two lists are read as one set.

    The assertions and no wider, which is where solorepo's #147 scopes it and as far as a
    glob reaches. The set `check.py` scans is read out of the Specialization
    step that lists what a portfolio inherits, and reading that here would put
    a YAML parser into a checker that is stdlib only and stays that way.

    Whose Issues. `.meta/assertions/imported/` is copied into every portfolio
    and cites solorepo's Issues; a portfolio's own sequence starts again at one,
    so a number cited bare there comes to mean an Issue of the portfolio's — the
    citation the Charter holds worse than one that dangles. That half of the
    rule is not held here. It is `check.py`'s `inherited citations`, over the
    whole copy list rather than the single entry of it that is an assertion, and
    this check held a second copy of it for as long as it took solorepo's #160 to
    draw the seam: one bare number in an imported assertion, reported twice, by
    two gates (solorepo's DR-132). What is left here is the number, which is the
    half only GitHub can answer. `solorepo's #11` resolves against this
    repository's lists only where this repository is solorepo, and is passed
    over where it is not, since the Issues it names are not there to resolve
    against — `cited decisions`'s answer to solorepo's #114, over the other
    sequence.

    `gh` answers newest first, so a list that comes back at the limit is
    truncated at the bottom and says nothing about the numbers below it. Those
    are passed over rather than reported: "cited and does not exist" has to
    keep its one meaning.
    """
    bare, foreign, problems, home = {}, {}, [], False
    for path in sorted(ASSERTIONS.rglob("*.yaml")):
        try:
            text = FENCED.sub("", path.read_text())
        except (UnicodeDecodeError, OSError):
            continue
        where = str(path.relative_to(META.parent))
        home = home or bool(SCAFFOLD.search(text))
        for m in FOREIGN.finditer(text):
            for number in ISSUE.findall(m.group()):
                foreign.setdefault(int(number), set()).add(where)
        plain = {int(m.group(1)) for m in ISSUE.finditer(FOREIGN.sub("", text))}
        for number in sorted(plain):
            bare.setdefault(number, set()).add(where)
    if not (bare or foreign):
        return problems
    known, floor = set(), 0
    for kind in ("issue", "pr"):
        try:
            found = gh(kind, "list", "--state", "all", "--limit", str(LIMIT), "--json", "number")
        except SystemExit:
            print(f"?  the {kind} list is not readable from here; cited issues unchecked")
            return problems
        known |= {item["number"] for item in found}
        if len(found) == LIMIT:
            floor = max(floor, min(item["number"] for item in found))
    if home:
        problems += [f"{where}: solorepo's #{number} is cited and is no Issue"
                     for number in sorted(foreign) if number not in known and number > floor
                     for where in sorted(foreign[number])]
    return problems + [f"{where}: #{number} is cited and is no Issue"
                       for number in sorted(bare) if number not in known and number > floor
                       for where in sorted(bare[number])]


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
    on the push, and on the clock (solorepo's DR-105) — and two copies would be two gates."""
    title, body = from_github(ref)
    return (check(title, body) + resolved_without_an_answer(ref)
            + unsigned_commits(ref) + required_contexts() + cited_issues())


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


CODER = META.parent / ".github" / "workflows" / "coder.yml"
LOOPS_BRANCH = re.compile(r"^claude/issue-(\d+)$")
# The difficulties a loop takes, which is what makes a Challenge a loop's and
# not the solo's. `human` and `hard` are the solo's, and so is a pull request
# on their Challenge.
TAKEN = ("easy", "medium")
# The fields the hand-off reader needs, added to the sweep's own list so that
# one fetch answers both. The rollup is not among them: `gh` answers that one
# field with a query the gate's token cannot run, so it is fetched by name
# alongside (solorepo's DR-153).
SWEEP_FIELDS = ("number,title,headRefOid,headRefName,baseRefName,isDraft,updatedAt,"
                "reviewRequests,autoMergeRequest,mergeable")


def longest_run():
    """How long a loop's run may hold a pull request without touching it.

    The coder job's own `timeout-minutes`, read rather than copied. A run that
    is working pushes and comments, and GitHub moves `updatedAt` when it does;
    one that has not moved for longer than a run may last has no run standing
    on it. A number restated here would drift the first time the budget moved,
    and the drift reads either as a sweep that had quietly stopped noticing or
    as one that names a pull request somebody is in the middle of.

    Loud and unmarked when it cannot be read, like `required_contexts`: a
    checkout without the workflow is told so rather than passed. Absent is one
    of the ways it cannot be read, and the likeliest one — `check_pr.py` and
    `.github/workflows/` are separate lines in Specialization's copy step, so a
    portfolio that took one and not the other gets this line rather than a
    traceback out of its gate every half hour.
    """
    if not CODER.exists():
        print(f"?  no {CODER.name} in this checkout; who holds each pull request is unchecked")
        return None
    found = re.search(r"^    timeout-minutes: (\d+)\s*$", CODER.read_text(), re.M)
    if not found:
        print(f"?  no job timeout in {CODER.name}; who holds each pull request is unchecked")
        return None
    return int(found.group(1))


def asked_of(pr):
    return [r.get("login") or r.get("name") or "someone" for r in pr["reviewRequests"]]


def green(pr):
    """Whether every check on the head has concluded and none of them failed."""
    states = [c.get("conclusion") or c.get("state") or c.get("status")
              for c in pr.get("statusCheckRollup") or []]
    return bool(states) and all(s in GREEN for s in states)


def unheld(prs, minutes, clean):
    """Pull requests nobody holds, and requests nobody can answer (solorepo's #154).

    A handoff here is a semaphore: GitHub holds a review request and reports
    it, and an arriving Job finds its work by asking what has been requested of
    its login. That makes two states invisible to everyone, because nothing
    about either is a fact GitHub reports.

    The first is a pull request that names no successor at all. A run that dies
    at its budget with the work pushed and green has not reached the step that
    requests review, so no Job's question — what has been requested of me —
    ever has this pull request as its answer, and no event fires to ask it
    again. `coder.yml` now hands off from its own hand-back handler, which
    covers the deaths GitHub reports as failures; a run whose turn cap ends it
    reports success, so the handler never runs, and this is what is left to
    catch that. Four conditions, and each one is a way somebody *does* hold it:
    a review requested, a merge armed, checks that are not green — a red gate
    is not a handoff but a mess, and the mess is the solo's — and a head that
    has moved recently enough that a run may still be standing on it. Greenness
    is read twice over: the rollup GitHub reported before this sweep began, and
    `clean`, the pull requests this same sweep found nothing on. The second is
    this run's verdict rather than the last one's, and without it a sweep can
    mark a head red on its gate line and then, three lines later, prescribe a
    handoff onto it. Only a loop's branch is read: `claude/issue-<n>` is a
    Challenge a loop took, and the solo's own pull request is held by the solo
    whatever it looks like from here. Only while the Challenge is still a
    loop's, too — one handed back sits at `human`, which is the solo holding
    it, and a sweep that named it every half hour until they acted would be
    switched off inside a week.

    What a candidate is owed is not always the request. A branch GitHub reports
    as `CONFLICTING` is one no review can be requested on, for the reason the
    second half of this reader exists, so naming it and prescribing
    `request-review` would prescribe the act that creates the other finding:
    the next sweep would print the same pull request as a request nobody can
    answer. It is still nobody's — the sweep says so — but what it needs first
    is the rebase. Onto its base and not onto trunk: PR First's twelfth step
    makes a layer its own branch and pull request based on the layer below, so
    a `claude/issue-<n>` branch is not always cut from `main`, and rebasing a
    layer onto trunk while the layer below is open drops that layer's commits
    off the head and shows its work as a removal. `mergeable` is computed
    against the base, so the branch the remedy names is the one the finding was
    read against.

    The second is a request that exists and cannot be answered. GitHub builds
    no merge ref for a branch that conflicts, and the review workflow runs on
    `pull_request`, so there is nothing for it to check out and no run is
    created; GitHub reports the request as outstanding and says nothing about
    its being unanswerable. solorepo's #141 sat that way for three hours. This one is read
    on every open pull request, whoever opened it: a request pending on a
    conflicting branch is unanswerable by whoever it names.

    The Challenge behind a candidate is read here rather than fetched with the
    rest, because only a candidate needs it — the read is the judgement's, not
    the sweep's, and on a quiet sweep there are none to make.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for pr in prs:
        asked = asked_of(pr)
        if asked and pr.get("mergeable") == "CONFLICTING":
            out.append(f"#{pr['number']} {pr['title'][:60]} — requested of "
                       f"{', '.join(asked)}, on a branch that conflicts: GitHub builds no "
                       f"merge ref, so the review workflow has nothing to check out and the "
                       f"request cannot be answered. Rebase {pr['headRefName']} onto "
                       f"{pr['baseRefName']}")
        if asked or pr.get("autoMergeRequest") or pr["isDraft"] or not green(pr):
            continue
        if pr["number"] not in clean:
            continue
        branch = LOOPS_BRANCH.match(pr["headRefName"])
        if not branch:
            continue
        moved = datetime.datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))
        idle = (now - moved).total_seconds() / 60
        if idle < minutes:
            continue
        issue = gh("issue", "view", branch.group(1), "--json", "state,labels")
        level = next((l["name"] for l in issue["labels"] if l["name"] in TAKEN), None)
        if issue["state"] != "OPEN" or not level:
            continue
        if pr.get("mergeable") == "CONFLICTING":
            remedy = (f"and its branch conflicts, so a review requested on it now could not "
                      f"be answered: rebase {pr['headRefName']} onto "
                      f"{pr['baseRefName']}, then "
                      f".meta/say/move request-review {pr['number']}")
        else:
            remedy = f"and nobody has: .meta/say/move request-review {pr['number']}"
        out.append(f"#{pr['number']} {pr['title'][:60]} — green, and nobody holds it: "
                   f"no review requested, no merge armed, and nothing has moved on it for "
                   f"{int(idle)} minutes, while #{branch.group(1)} is still {level}. "
                   f"A run ended without handing it over, {remedy}")
    return out


def sweep_all(publishing):
    """A16 between the last push and the merge (solorepo's #5). Resolving a thread fires
    no event, so the check that ran on the push is stale the moment one is
    resolved, and a schedule is the only thing left to run it. Every open pull
    request, one line each in A21's shape, and the result published as the
    check when asked.

    Then who holds each one, which is the same question asked of the handoff
    rather than of the body. It is printed as its own step and is never
    published: the finding *is* that the checks are green, so folding it into
    the check the ruleset waits on would turn every pull request it named red
    and unname it (solorepo's #154).

    The pull requests this loop found nothing on are carried into that reader.
    The rollup it would otherwise trust was fetched before the loop ran, so it
    is the last sweep's `pull request` check and not this one's, and a head
    whose gate has just gone red — a closing keyword edited out of the body, a
    job renamed on `main` under `required_contexts` — would be marked `x` above
    and then handed over below, which is the handoff onto a red gate that the
    reader exists to refuse.
    """
    try:
        found = gh("pr", "list", "--state", "open", "--json", SWEEP_FIELDS)
        rolled = rollups()
    except SystemExit as unreachable:
        # A sweep that could not fetch and a sweep that found nothing to say
        # read the same everywhere downstream: no verdict is published either
        # way, and every open pull request keeps the one its last push left.
        # So the fetch says which it was, in the sweep's own voice rather than
        # as a `gh` error the job's tail then prints `ok triage` over
        # (solorepo's #229). Still red — but red here now names a broken
        # checker rather than the queue state the job's other findings are.
        print("x  sweep — could not ask GitHub for the open pull requests, so no "
              "verdict was published and every one keeps the verdict its last "
              f"push left: {unreachable.code}")
        return 1
    if not found:
        print("ok sweep — no open pull requests")
        return 0
    # A pull request `gh pr list` returned that the rollup query did not answer
    # for is a fetch that did not happen, and `rolled.get(n, [])` would hand it
    # to `green` as a head with no checks on it: not green, so `unheld` passes
    # over it without a word and its line above says nothing either. That is
    # the collapse the failure path just above refuses, kept for one pull
    # request instead of for the run, so it is named in the same voice and
    # carried no further. It bites only past a hundred open pull requests,
    # where the two calls need not have taken the same ones.
    unfetched = [pr for pr in found if pr["number"] not in rolled]
    if unfetched:
        print(f"x  sweep — GitHub answered for {len(rolled)} open pull request(s) "
              "and not for "
              + ", ".join(f"#{pr['number']}" for pr in unfetched)
              + ", which are left unread and keep the verdict their last push left")
    found = [pr for pr in found if pr["number"] in rolled]
    for pr in found:
        pr["statusCheckRollup"] = rolled[pr["number"]]
    failed = bool(unfetched)
    clean = set()
    for pr in found:
        number = str(pr["number"])
        problems = gate(number)
        print(f"{'x  ' if problems else 'ok '}#{number} {pr['title'][:60]}"
              + (f" ({len(problems)})" if problems else ""))
        for p in problems:
            print(f"     {p}")
        if publishing:
            publish(number, pr["headRefOid"], problems)
        if not problems:
            clean.add(pr["number"])
        failed |= bool(problems)

    minutes = longest_run()
    if minutes is not None:
        owed = unheld(found, minutes, clean)
        print(f"{'x  ' if owed else 'ok '}hand-off — "
              + (f"{len(owed)} pull request(s) nobody can take up"
                 if owed else "every open pull request names who takes it next"))
        for o in owed:
            print(f"     {o}")
        failed |= bool(owed)
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pr", nargs="?", help="pull request number, URL or branch")
    ap.add_argument("--file", help="read a body from disk instead of GitHub")
    ap.add_argument("--title", default="a real title", help="title to use with --file")
    ap.add_argument("--threads", action="store_true",
                    help="print the threads owed, held, and answered, and each verdict "
                         "with the head it was given on; check nothing")
    ap.add_argument("--resume", action="store_true",
                    help="what an arriving Job needs, read from GitHub")
    ap.add_argument("--handoff", action="store_true",
                    help="A18: refuse to hand off work the successor cannot see")
    ap.add_argument("--sweep", action="store_true",
                    help="every open pull request you own, and what each still owes")
    ap.add_argument("--watch", action="store_true",
                    help="one line per change on the pull request, exiting on actionable events or when it closes")
    ap.add_argument("--every", type=int, default=60, help="seconds between polls under --watch")
    ap.add_argument("--all", action="store_true",
                    help="the check on every open pull request, one line each, and who "
                         "holds each one next")
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
        left = residue()
        if left:
            print(f"\n--- residue: {sum(1 for l in left if not l.startswith('    '))} "
                  "branch(es) outlived their pull request ---")
            print("\n".join(left))
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
        held = pull(args.pr)
        nodes = held["reviewThreads"]["nodes"]
        owed, parked, done = (unaddressed(nodes, limit=None),
                               unaddressed(nodes, parked=True, limit=None),
                               settled(nodes, limit=None))
        given = verdicts(held["reviews"]["nodes"])
        if given:
            print(f"--- {len(given)} verdict(s), newest first, each on the head GitHub recorded it against ---")
            print("\n".join(given))
            print()
        print("\n".join(owed) if owed else "nothing unaddressed")
        if parked:
            print(f"\n--- {len(parked)} noticed and not done, held for promotion at merge ---")
            print("\n".join(parked))
        if done:
            print(f"\n--- {len(done)} answered and resolved: a re-review reads each answer against the diff it claims ---")
            print("\n".join(done))
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
