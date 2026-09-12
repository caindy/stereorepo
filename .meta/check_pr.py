#!/usr/bin/env python3
"""The GitHub half of the gate: A15, held against a live pull request, and the
quarter of A12 whose target is an Issue rather than a file.

`check.py` reads files and this repository's own commits, and reaches the remote
for one thing only — which Decision numbers are reserved, and only when the
record has a hole to explain (solorepo's DR-128). History in check_pr.history.md.
This reads GitHub for everything it does, so it is a separate command with a
separate lifecycle — it runs when a pull request opens or changes, and there is
nothing for it to say the rest of the time.

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

`--hand-back` answers that same question from the other side, for a run that is
about to die: whether anybody holds this Challenge's pull request yet, and
whether what is there is worth requesting a review of. Its reader is
`coder.yml`'s hand-back step, so the predicate lives here and not in that
step's shell (solorepo's DR-155).

`--handoff` is the one mode that reads the tree rather than GitHub, because what
it holds is about the branch: A18, and what a branch that changes the record owes
along with it — a render that is current, and a decision that names the artifacts
the branch edits while settling it. Both are deterministic, both were costing
review rounds that found them by reading, and a review round is the most expensive
place to discover either (solorepo's #302).
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time

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
# What a workflow writes into `ACTOR_SESSION` and nothing else does
# (`channel.py`'s `RUN_MARK`, solorepo's DR-148); `mine()` below resolves the
# session the same way `channel.actor()` does, so the two never disagree
# about which id the Trailer signed with.
def _load_run_mark():
    import importlib.util
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("channel", str(pathlib.Path(__file__).resolve().parent / "say" / "channel.py"))
    spec = importlib.util.spec_from_loader("channel", loader)
    channel = importlib.util.module_from_spec(spec)
    loader.exec_module(channel)
    return channel.RUN_MARK


RUN_MARK = _load_run_mark()
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

ROOT = META.resolve().parent
# The record's own rendered index. Every branch that settles a decision rewrites
# it and no entry names it, so the step below passes over it — the exclusion A20
# already makes, for the reason it gives: naming the record itself would satisfy
# the letter and defeat the point.
INDEX = ".meta/decisions.md"
# An entry of the record, by the file it is written in.
ENTRY_FILE = re.compile(r"^\.meta/assertions/decisions/DR-(\d+)\.yaml$")
# An Artifact's path, as the two files that declare one write it: four spaces,
# because an Artifact is an item of a single list in each file and `path` is its
# slot. Read with a regex rather than parsed, because `check_pr.py` is run with
# bare `python3` everywhere it runs — CI, `just pr`, the reviewer's tool list —
# and so holds to the standard library and has no YAML reader to reach for.
ARTIFACT = re.compile(r"^    path: (\S+)$", re.M)
# A row of `decisions.md`'s by-artifact table: the file, then the entries naming
# it. The record's other tables key on an entry rather than on a backticked
# path, so none of them match.
ROW = re.compile(r"^\| \[`([^`]+)`\][^|]*\|([^|]*)\|", re.M)
DR = re.compile(r"DR-(\d+)")
# The render, invoked as `just render` invokes it. Naming what it is run with is
# this file's only choice: it needs PyYAML and this one does not have it.
RENDER = ["uvx", "--with", "pyyaml", "python", str(META.resolve() / "render.py"), "--check"]


def fence(path):
    """Extracts markdown body content from the first code block fence in a template file."""
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
    """Validates a pull request title and body against the required form sections."""
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
""" % ROLLUP  # noqa: UP031  # reason: GraphQL query templates have literal curly braces

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
""" % ROLLUP  # noqa: UP031  # reason: GraphQL query templates have literal curly braces


def _role_token():
    for role in ("reviewer.env", "coder.env"):
        p = pathlib.Path("~/.config/solorepo").expanduser() / role
        if p.exists():
            try:
                for line in p.read_text().splitlines():
                    line = line.strip().removeprefix("export ").strip()
                    if line.startswith("GH_TOKEN="):
                        return line.split("=", 1)[1].strip("\"'")
            except Exception:
                pass
    return None


def gh(*args):
    """Invokes the GitHub CLI with the role credential and parses JSON output."""
    env = None
    if "GH_TOKEN" not in os.environ:
        token = _role_token()
        if token:
            env = dict(os.environ, GH_TOKEN=token)
    out = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
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
        return [*problems, f"git rev-list failed, so pushed state is unknown: {err}"]
    if ahead:
        problems.append(f"{len(ahead.splitlines())} commit(s) not pushed; the branch is the handoff")
    return problems


def git_read(*args):
    """git, as an exit code beside what it printed.

    Whether a failure is a finding is the caller's to say, and both answers are
    wanted below, so the two are kept apart here rather than collapsed into one
    of them. `unpushed` above keeps its own for the same reason it always did.
    """
    out = subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT)
    return out.returncode, out.stdout


def git_text(*args, default=""):
    """git, as text, with a failure answered rather than raised.

    For the reads that have somewhere to go when the command fails: a branch
    with no merge base is read against its base, and a tree with no untracked
    files is read as having none. The read that has nowhere to go — the diff the
    whole `enacted` step turns on — takes `git_read` instead.
    """
    code, out = git_read(*args)
    return default if code else out


def touched(base):
    """Every path this branch changed, committed or not; or why git could not say.

    Against the merge base and not against the base's head: a landing on the
    trunk while this branch was open is not this branch's work, and reading it
    as such would name files nobody here edited. The same scope
    `dereference.py` takes, for the same reason, and read the same way.

    Uncommitted and untracked alike. A decision entry is a new file, and a
    handoff check that read only what git had already been told about would pass
    over the file the branch exists to add — which is the one file both steps
    below turn on.

    A base git cannot resolve returns `None` rather than an empty list, because
    those are different answers and the step below reports the emptier one. The
    first version swallowed the diff's exit code: `merge-base` failed, `merge`
    fell back to the literal `base`, `git diff` against it failed too, and a
    branch that settles a decision and edits an Artifact read as one that
    settles none. The `--base` flag's own help invites the ref that does it —
    a bare `claude/issue-nnn` resolves for neither command in a checkout
    holding only the remote-tracking form — and the default does the same
    wherever `origin/main` is absent, which is any `--single-branch` clone.
    """
    merge = git_text("merge-base", "HEAD", base).strip() or base
    code, diffed = git_read("diff", "--name-only", merge)
    if code:
        return None
    named = diffed.split()
    named += git_text("ls-files", "--others", "--exclude-standard").split()
    return list(dict.fromkeys(named))


def artifacts():
    """The paths that are Artifacts, from the two files that declare one.

    `assertions/structure.yaml` says what an Artifact is for: the things a
    Decision names under `enacted_in`, and nothing else. So the set of them is
    the universe the step below asks its question over, and a file that is not
    one is not a file an entry could name.
    """
    found = set()
    for rel in ("assertions/structure.yaml", "assertions/imported/structure.yaml"):
        path = META / rel
        if path.is_file():
            found |= set(ARTIFACT.findall(path.read_text()))
    return found


def accounted():
    """Which entries name each file under `enacted_in`, read from the record's index.

    `decisions.md`'s by-artifact table is `enacted_in` rendered the other way
    round — "which entries account for a file", as the page says of itself — and
    the step before this one holds the page current. So the record is read here
    through its own render, rather than through a second reader of the entries
    that would drift from the first the day either moved.
    """
    path = ROOT / INDEX
    if not path.is_file():
        return {}
    return {file: {int(n) for n in DR.findall(entries)}
            for file, entries in ROW.findall(path.read_text())}


def unrendered():
    """Whether every generated page is the render of what this branch now asserts.

    The render's own answer, asked of it. `render.py --check` compares each
    target against a fresh render and names what differs, which is the same
    question `check.py`'s `rendered prose` step asks; asking it again here is
    not a second copy of the rule but the same command, run where the coder is
    rather than where the gate is.

    It is asked at the handoff because that is where it is cheap. A stale
    `decisions.md` is a page asserting something the assertions no longer say,
    and every reader of it downstream — a reviewer, and the step below — is
    reading the record as it was before this branch touched it.

    Three answers, and the third is why this returns what it does: a `None` is
    "the render could not run", which is neither green nor a finding about the
    tree (A6). `uvx` is how the render is invoked everywhere, and a machine
    without it can still hand off — with this unread and saying so.

    The render itself has two findings, not one, and they are kept apart here
    because their repairs differ and the step after this one asks which page
    each names. A page that differs from its render is made current by running
    the render; a page no target renders at all is not, and `just render`
    writes nothing for it. Read under a single prefix, the second arrived as a
    sentence rather than a name — a finding whose named repair could not work,
    and one that could never match `INDEX`, so the one page whose freshness the
    render had just said it could not establish was the one the step below read
    on anyway. Not reachable on this tree, where every target renders; reachable
    in a portfolio that keeps a generated page after dropping the assertions it
    came from, and `check_pr.py` is in the copy set Specialization's step two
    names.

    The pages are returned by the names the render gives them, rather than as
    sentences about them, because the step after this one asks which page went
    stale and not how many.
    """
    try:
        out = subprocess.run(RENDER, capture_output=True, text=True, cwd=ROOT)
    except OSError as missing:
        return None, None, f"{RENDER[0]} could not be run — {missing}"
    said = out.stdout.strip()
    if out.returncode == 0 and said == "up to date":
        return [], [], ""
    named = {}
    for line in said.splitlines():
        prefix, colon, rest = line.partition(":")
        if colon:
            named[prefix.strip()] = [n.strip() for n in rest.split(",") if n.strip()]
    if out.returncode == 1 and named and set(named) <= {"stale", "unrendered"}:
        return named.get("stale", []), named.get("unrendered", []), ""
    return None, None, ("render.py --check answered neither: "
                        + (said or out.stderr.strip() or f"exit {out.returncode}"))


def unenacted(base):
    """Artifacts this branch edits that no decision it settles names (A20, solorepo's DR-131).

    `enacted_in` says where a rule lives, and a change that settles a decision is
    the change that puts the rule where it now lives. So an artifact edited by
    that change and named by none of its entries is one of two things, and both
    are worth stopping for: a rule put somewhere the record does not point at, or
    a file edited on a branch that is not about it.

    This is the reviewer's standard, read at the handoff instead of in a review
    round. On solorepo's #265 it took four of them — a verdict at a time, each
    naming one more artifact the branch edited and `enacted_in` did not, the last
    approving on "every artifact this branch edits is named in it, which was the
    whole ask". Nothing about that reading needs a reader: what the branch edited
    is in git and what the entry names is in the record, and the comparison is
    the two of them.

    The universe is the Artifacts, because `enacted_in` names those and nothing
    else, so a file that is not one cannot be named without being declared first
    — which is a judgement, and this is not where it is made. The record's own
    index is passed over for A20's reason. What this is blind to is therefore
    the file no `artifacts:` list declares, and the repair for it is one an
    entry's own author is better placed to see than a check is.

    Two repairs, and the failure names both. Name the Artifact under
    `enacted_in`, where the entry's rule does live in that file; or leave the
    file out of this branch, where it does not — one commit per settled decision
    is the convention that makes the second answer available at all.

    Three answers, as the render's reader has: a `None` is "what this branch
    changed went unread", which is neither green nor a finding about the tree
    (A6), and is what a base git cannot resolve produces.
    """
    changed = touched(base)
    if changed is None:
        return None, f"{base} did not resolve, so what this branch changed is unread"
    settled = sorted({int(m.group(1)) for p in changed if (m := ENTRY_FILE.match(p))})
    if not settled:
        return [], "this branch settles no decision"
    shown = ", ".join(f"DR-{n:03d}" for n in settled)
    named, declared = accounted(), artifacts()
    edited = [p for p in changed if p in declared and p != INDEX]
    return ([f"{p}: this branch edits it, and none of the entries it settles "
             f"({shown}) names it under enacted_in — name the Artifact at that "
             f"path there, or leave the file to the change that carries its rule"
             for p in edited if not named.get(p, set()) & set(settled)],
            f"{len(edited)} artifact(s) edited, each named in {shown}")


def handoff(base):
    """A18, and what a branch that changes the record owes along with it.

    Three steps, each a line in A21's shape and each refusing the handoff on its
    own. They are ordered so that a reader repairs them in the order that works:
    a push is what makes the branch the handoff at all, a render is what makes
    the record's index readable, and the index is what the third step reads.

    So the third runs only where its source is known current, and otherwise says
    it did not. Read against a stale index it would ask what names each file of a
    page written before this branch existed, and answer with findings about
    entries the branch has already added — a step that is wrong rather than
    silent when its source is, which is the failure A6 asks a step not to have.
    An unread index is that same failure and not a milder one: a render that
    could not run leaves the page's freshness unknown, and a step that reports
    `ok` over an unknown says it checked something it did not. A page nothing
    renders is the same unknown by a different road, and counts alike. Only that
    page, though: a stale `justfile` says nothing about what an entry names, and
    skipping the third step over it would withhold a reading that is sound.

    The third step has the same three answers for the same reason, and its own
    unknown is a base git cannot resolve. `ok` over that would be `ok` over a
    diff nobody read.
    """
    def mark(label, problems, note=""):
        for p in problems:
            print(f"x  {p}")
        print(("x  " if problems else "ok ") + label
              + (f" — {note}" if note and not problems else ""))
        return bool(problems)

    failed = mark("handoff", unpushed())
    stale, orphans, unread = unrendered()
    if stale is None:
        print(f"?  rendered — {unread}")
    else:
        failed |= mark("rendered",
                       [f"{name} is stale; re-render with `just render` and commit it"
                        for name in stale]
                       + [f"{name} is on disk and no target renders it; `just render` writes "
                          f"nothing for it — restore the target, or drop the page"
                          for name in orphans],
                       "every generated page is the render of what it asserts")
    # The render names a page relative to `.meta/`, which is how the Artifact
    # that asserts its prose is found too; here it is turned back into the path
    # the record's table and this file's own reads are keyed on.
    unnamed = [] if stale is None else stale + orphans
    unsure = stale is None or INDEX in {
        (pathlib.Path(".meta") / name).as_posix() for name in unnamed}
    if unsure:
        print(f"?  enacted — {INDEX} is "
              + ("unread, " if stale is None else "a page the render could not call current, ")
              + "and what names each file is read from it")
    else:
        problems, note = unenacted(base)
        if problems is None:
            print(f"?  enacted — {note}")
        else:
            failed |= mark("enacted", problems, note)
    return 1 if failed else 0


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
    """Everything on a pull request that a watcher compares between polls.

    Keyed so that a change is a set difference and not a diff of text: a
    comment or review by its id, a thread by its id and how many comments it
    holds, a check by its name and state. The keys are what GitHub already
    holds, so nothing is written locally and a watch restarted from scratch
    reports the same events a continuous one would have.

    `mergeable` rides along because a branch that goes conflicting under a
    standing review request is a change on the pull request that produces no
    thread, no review and no check, and so was the one thing a watch could not
    see (solorepo's #192).
    """
    pr = gh("pr", "view", ref, "--json", "number,state,comments,reviews,mergeable")
    comments = {c["id"]: c for c in pr["comments"]}
    reviews = {r["id"]: r for r in pr["reviews"]}
    threads_ = {t["id"]: t for t in threads(ref)}
    # When multiple check runs share a name (e.g. repeated dispatches or cancelled runs),
    # order by startedAt so the latest run wins.
    sorted_checks = deduplicate_checks(rollup_of(pr["number"]))
    # A check still running has no conclusion; its status says so, which reads
    # better than a `None` beside a result and is a change worth a line. The
    # run's url rides beside the verdict: a re-run that ends where it started
    # is the same verdict from a different run, and keyed on the verdict alone
    # it was invisible (solorepo's #79).
    checks = {c.get("name") or c.get("context"):
              (c.get("conclusion") or c.get("state") or c.get("status") or "PENDING",
               c.get("detailsUrl") or c.get("targetUrl"))
              for c in sorted_checks}
    return (pr["number"], pr["state"], comments, reviews, threads_, checks,
            pr.get("mergeable") or "UNKNOWN")


def mine(body):
    """Whether this session wrote a comment, read from the Trailer it carries.

    A watch that reported the watcher's own comments back to it would wake a
    conversation for every line it posted. The login cannot say — every agent
    posts under one account — but the channel signs each comment with the
    session's id, and that is what is compared.

    Resolved the same way `channel.actor()` resolves it: `ACTOR_SESSION` wins
    when it carries the run's mark (`gha-`), since inside a container run
    `CLAUDE_CODE_SESSION_ID` is also set and is not what the Trailer signed
    with. Otherwise the first of the two sets `me`.
    """
    run_session = os.environ.get("ACTOR_SESSION", "")
    me = (run_session if run_session.startswith(RUN_MARK) else
          next((os.environ[k] for k in ("CLAUDE_CODE_SESSION_ID", "ACTOR_SESSION")
                if os.environ.get(k)), None))
    found = ACTOR.search(body or "")
    return bool(me and found and found.group(1) == me)


def said(body, limit=300):
    """Truncates and collapses whitespace in a comment or text string for display."""
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

    Each line is one event, a change in whether GitHub can still merge the
    branch among them (solorepo's DR-145): a merge on the base while a review
    is requested makes the request unanswerable, and that produces no thread,
    no review and no check, so the silence read as a review in progress
    (solorepo's #192). The
    heading carries the state a watch starts on, since a branch already
    conflicting when the watch begins never changes into it — and when the
    watch begins while GitHub is still computing one, the heading carries
    `UNKNOWN` and the first answer that follows is printed instead, since a
    state never said is not one a reader can be left to infer. Nothing else is
    emitted for the first poll, so a watch started on a busy pull request does
    not replay it; a poll that fails is skipped and the next one compares
    against the last that did not, so nothing is lost across a transient
    failure. Exits 0 when the
    subscription ends (the pull request merges or closes) or when an actionable
    event arrives (a new review from another author, a new unaddressed comment or
    thread, or a check failure). Exiting on actionable events completes the
    background process, waking any harness that resumes on command completion
    (solorepo's DR-138).
    """
    import time
    previous = None
    # The last thing GitHub said about merging this branch that was an answer.
    # Held apart from the snapshot because `UNKNOWN` is not a state of the
    # branch but GitHub computing one, and every push sets it: compared
    # snapshot to snapshot, a push would report `UNKNOWN` and then the value it
    # already had, which is two lines for no change. `None` means nothing has
    # been said yet, including by the heading, so the first answer is a change
    # from nothing and is printed.
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
            owed = len(unaddressed(list(threads_.values())))
            print(f"watching #{number}: {owed} thread(s) owed an answer, mergeable={mergeable}, "
                  + ", ".join(f"{k}={v}" for k, (v, _) in checks.items()), flush=True)
        else:
            _, _, p_comments, p_reviews, p_threads, p_checks, _ = previous
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
            # Said and not exited on. A conflict under a standing request
            # already dispatches the coder's rebase pass off the merge that
            # caused it (solorepo's DR-133), so waking this session to rebase
            # would put two Actors on one branch; what the session watching
            # lacked was the reason the review was silent, which is the line.
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


def resolved_without_an_answer(ref, thread_nodes=None):
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
    return unanswered(threads(ref) if thread_nodes is None else thread_nodes)


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
    """Determines the current GitHub repository slug from environment, CLI, or git remote."""
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    if repo_name:
        return repo_name
    try:
        return gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    except (Exception, SystemExit):
        out = subprocess.run(["git", "remote", "get-url", "origin"],
                             capture_output=True, text=True, cwd=ROOT)
        if out.returncode == 0 and out.stdout.strip():
            url = out.stdout.strip()
            m = re.search(r"[:/]([^/:]+)/([^/:]+?)(?:\.git)?$", url)
            if m:
                return f"{m.group(1)}/{m.group(2)}"
        return "solo/repo"


def role_login(role):
    """The account a Role holds, by name and not by reading anything.

    `<owner>-<repo>-<role>` is the convention solorepo's DR-107 set.
    """
    return f"{repo().replace('/', '-')}-{role}"


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

    Status checks required by `main`'s branch ruleset are read directly to
    ensure workflow jobs produce every context `main` requires before merging.

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
    """Fetches the title and body of a pull request from GitHub."""
    data = gh("pr", "view", ref, "--json", "title,body")
    return data["title"], data["body"] or ""


def gate(ref, thread_nodes=None):
    """The pull request check, whole: the body against the form, A16, A19 and
    the required contexts. One function because it is run from two places —
    on the push, and on the clock (solorepo's DR-105) — and two copies would be two gates."""
    title, body = from_github(ref)
    return (check(title, body) + resolved_without_an_answer(ref, thread_nodes=thread_nodes)
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
LOOPS_BRANCH = re.compile(r"^(?:claude|gemini|codex)/issue-(\d+)$")
# The difficulties a loop takes, which is what makes a Challenge a loop's and
# not the solo's. `human` and `hard` are the solo's, and so is a pull request
# on their Challenge.
TAKEN = ("easy", "medium")
# The fields the hand-off reader needs, added to the sweep's own list so that
# one fetch answers both. The rollup is not among them: `gh` answers that one
# field with a query the gate's token cannot run, so it is fetched by name
# alongside (solorepo's DR-153).
SWEEP_FIELDS = ("number,title,headRefOid,headRefName,baseRefName,isDraft,updatedAt,"
                "reviewRequests,autoMergeRequest,mergeable,latestReviews")


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
    """Names or logins of reviewers currently requested on a pull request."""
    return [r.get("login") or r.get("name") or "someone" for r in pr["reviewRequests"]]


def green(pr):
    """Whether every check on the head has concluded and none of them failed."""
    contexts = deduplicate_checks(pr.get("statusCheckRollup") or [])
    states = [c.get("conclusion") or c.get("state") or c.get("status")
              for c in contexts]
    return bool(states) and all(s in GREEN for s in states)


# What the hand-back asks `gh pr list` for, which is everything except the
# rollup: those fields are a pull request's own and the step's token reads them
# at `pull-requests: read`, while the check states come through `ROLLUP` below,
# whose scope is `checks: read` and nothing wider (solorepo's DR-155).
HANDBACK_FIELDS = "number,headRefName,baseRefName,reviewRequests,autoMergeRequest,mergeable"


def wait_for_checks(pr_number, timeout=120, interval=5):
    """Wait for in-progress or queued checks on the head to conclude."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = rollup_of(pr_number)
        if not raw:
            return []
        pending = [c for c in raw if (c.get("conclusion") or c.get("state") or c.get("status") or "").upper() in UNCONCLUDED]
        if not pending:
            return raw
        time.sleep(interval)
    return rollup_of(pr_number)


def hand_back(issue):
    """What `coder.yml`'s hand-back handler needs about a Challenge's pull
    request, so that green is read here and not written out a second time.

    That step decides which verb a run killed at its budget owes its Challenge,
    and its predicate is already this file's: `green` above is the same
    question, and the step asked `gh pr list` for `statusCheckRollup` and then
    wrote `green` out again in jq beside it. The copy could not run. `gh`
    answers that field with GraphQL of its own that traverses
    `checkSuite.workflowRun`, an Actions resource, and the step's
    `permissions:` block holds no `actions` scope — so the whole query failed,
    and on `bash -e` the failed assignment took the step with it: the one
    handler written so that a dead run still names a successor named none, and
    left the pull request to nobody (solorepo's #233).

    Asked for here instead, the fetch names its own fields and the rollup
    arrives through `ROLLUP`, as it does everywhere else in this file since
    solorepo's DR-153. Three facts come back, each the reader of one
    condition the step's branches turn on:

    `handed` — somebody already holds it, by a review requested or a merge
    armed, which means the run reached its own last step and only then ran out.

    `green` — every check concluded and none failed, which is `green` above and
    so is pending-is-not-green with it.

    `conflicting` — `CONFLICTING` and not `UNKNOWN`, which is GitHub still
    computing: refusing a handoff on that would refuse it on timing. `base` is
    the pull request's own, because a layer is based on the layer below (PR
    First's twelfth step) and the rebase the step prescribes has to name the
    branch `mergeable` was computed against.

    JSON, because the reader is a shell. Scalars a step lifts out one at a
    time, with no predicate left in jq to drift from the ones here.
    """
    found = []
    for prefix in ("gemini", "claude", "codex"):
        found = gh("pr", "list", "--state", "open", "--head", f"{prefix}/issue-{issue}",
                   "--json", HANDBACK_FIELDS)
        if found:
            break
    if not found:
        return {"number": None, "branch": None, "handed": False, "green": False,
                "conflicting": False, "base": None}
    pr = found[0]
    raw_contexts = rollup_of(pr["number"])
    pending = [c for c in raw_contexts if (c.get("conclusion") or c.get("state") or c.get("status") or "").upper() in UNCONCLUDED]
    if pending:
        raw_contexts = wait_for_checks(pr["number"], timeout=120, interval=5)
    pr["statusCheckRollup"] = deduplicate_checks(raw_contexts)
    return {"number": pr["number"],
            "branch": pr.get("headRefName"),
            "handed": bool(asked_of(pr)) or pr.get("autoMergeRequest") is not None,
            "green": green(pr),
            "conflicting": pr.get("mergeable") == "CONFLICTING",
            "base": pr.get("baseRefName") or "main"}


def is_approved_pull(pr, reviewer_login=None):
    """Whether the reviewer's most recent review on this pull request is an approval."""
    if not (pr.get("latestReviews") or pr.get("reviews")):
        return False
    if reviewer_login is None:
        reviewer_login = role_login("reviewer")
    revs = [r for r in pr.get("latestReviews") or pr.get("reviews") or []
            if (r.get("author") or {}).get("login") == reviewer_login]
    return bool(revs and revs[-1].get("state") == "APPROVED")


def is_changes_requested_pull(pr, reviewer_login=None):
    """Whether the reviewer's most recent review on this pull request requests changes."""
    if not (pr.get("latestReviews") or pr.get("reviews")):
        return False
    if reviewer_login is None:
        reviewer_login = role_login("reviewer")
    revs = [r for r in pr.get("latestReviews") or pr.get("reviews") or []
            if (r.get("author") or {}).get("login") == reviewer_login]
    return bool(revs and revs[-1].get("state") == "CHANGES_REQUESTED")


def unheld(prs, minutes, clean, unresolved=None, reviewer_login=None):
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
    loop's, or when a loop handed back to `human` or `hard` while checks were
    still in flight (solorepo's DR-167). A `stop` at `human` on a broken or
    incomplete branch is the solo holding the work and passes in silence; but
    a green head left unreviewed and unrequested at `human` or `hard` is a
    handoff stall where work completed before checks settled, and the sweep
    surfaces it with the remedy to request review or return it to an agent loop.

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

    The second is a wait that cannot end, and it is one reading and not two
    (solorepo's DR-149). A request that exists and cannot be answered: GitHub
    builds no merge ref for a branch that conflicts, and the review workflow
    runs on `pull_request`, so there is nothing for it to check out and no run
    is created; GitHub reports the request as outstanding and says nothing
    about its being unanswerable. solorepo's #141 sat that way for three hours.
    And an arming that cannot be honoured, which is the same shape one
    Discipline-step later: GitHub will not merge a branch it reports as
    `CONFLICTING` and will not update one either, so an armed pull request that
    conflicts is waiting on an act nothing performs; and because arming is one
    of the four ways somebody *does* hold a pull request, the reader below
    skips it by name. On solorepo's #201 that left no line anywhere — the
    request had been answered, so no request was pending, and the arming hid it
    from the reader below — and the only sign was `advance.yml` red on every
    push to trunk. A push to trunk now dispatches the coder for it, so this is
    the floor under that and not the mechanism: what it catches is the conflict
    no push to trunk caused, the dispatch that declined, and the dispatched run
    that died with its force-push still to come.

    And an armed pull request carrying unresolved conversations: GitHub refuses
    the merge with "A conversation must be resolved before this pull request can
    be merged", and auto-merge honours the requirement, so an armed pull request
    with a noticed-and-not-done thread waits on an act no standing Job performs
    (solorepo's #232, solorepo's DR-159). Once idle for longer than a run may last,
    the reader names this rather than counting it as handled, giving the promotion
    or answering remedy, while a recently touched head is passed over in silence so
    an active promotion pass can run.

    Not the one that died after it. A rebase pass that pushes and then ends
    before it re-arms leaves a pull request neither armed nor requested and no
    longer conflicting, and this reading wants a wait, so it passes over it in
    silence; the reader below names it only once the new head is green and the
    pull request idle, and prescribes a review of a change already approved.
    Nothing else reaches it either — `advance` sweeps the armed, and a second
    dispatch declines on an empty wait. So the pass says on the pull request
    that it found the arming *before* it pushes, which is a record and not a
    floor: restoring the arming is a person's (solorepo's DR-149).

    One line whether it is waiting on one of those or on both, which is the
    same collapse `dispatch()` makes with the same words: a pull request whose
    request GitHub still shows outstanding *and* whose merge somebody has armed
    — the solo approving and arming a review requested of the reviewer's
    account — is one pull request stuck on one conflict, with one remedy, and
    the floor and the mechanism should say the same thing about it. Two lines
    would also make `len(owed)` a count of findings where the sweep prints it
    as a count of pull requests.

    This one is read on every open pull request, whoever opened it: a wait on a
    conflicting branch cannot end for whoever it names.

    The Challenge behind a candidate is read here rather than fetched with the
    rest, because only a candidate needs it — the read is the judgement's, not
    the sweep's, and on a quiet sweep there are none to make.
    """
    if reviewer_login is None:
        reviewer_login = role_login("reviewer")
    now = datetime.datetime.now(datetime.UTC)
    out = []
    for pr in prs:
        asked = asked_of(pr)
        waiting, stuck = [], []
        if asked:
            waiting.append(f"requested of {', '.join(asked)}")
            stuck.append("GitHub builds no merge ref, so the review workflow has nothing "
                         "to check out and the request cannot be answered")
        if pr.get("autoMergeRequest"):
            waiting.append("armed")
            stuck.append("GitHub will not merge it and will not update the branch, so the "
                         "arming waits on an act nothing performs")
        if is_approved_pull(pr, reviewer_login=reviewer_login):
            waiting.append("approved")
            stuck.append("GitHub will not merge it and will not update the branch, so the "
                         "approval waits on a rebase nothing performs")
        if waiting and pr.get("mergeable") == "CONFLICTING":
            hard_remedy = ""
            branch_match = LOOPS_BRANCH.match(pr["headRefName"])
            if branch_match:
                try:
                    issue = gh("issue", "view", branch_match.group(1), "--json", "state,labels")
                    level = next((lbl["name"] for lbl in issue["labels"] if lbl["name"] in ("human", "hard")), None)
                    if level:
                        hard_remedy = (f". Challenge #{branch_match.group(1)} is {level} so the loop stands down "
                                       f"(solorepo's DR-142): rebase by hand, or dispatch with "
                                       f".meta/say/move dispatch {pr['number']} --task rebase, or "
                                       f".meta/say/move difficulty {branch_match.group(1)} medium")
                except SystemExit:
                    pass
            out.append(f"#{pr['number']} {pr['title'][:60]} — {' and '.join(waiting)}, on a "
                       f"branch that conflicts: {'; and '.join(stuck)}. Rebase "
                       f"{pr['headRefName']} onto {pr['baseRefName']}{hard_remedy}")
        moved = (datetime.datetime.fromisoformat(pr["updatedAt"].replace("Z", "+00:00"))
                 if pr.get("updatedAt") else None)
        idle = (now - moved).total_seconds() / 60 if moved else float("inf")
        if pr.get("autoMergeRequest") and pr.get("mergeable") != "CONFLICTING" and idle >= minutes:
            threads_unresolved = (unresolved.get(pr["number"]) if unresolved is not None
                                  else [t for t in threads(str(pr["number"])) if not t["isResolved"]])
            if threads_unresolved:
                out.append(f"#{pr['number']} {pr['title'][:60]} — armed, with "
                           f"{len(threads_unresolved)} unresolved conversation(s): GitHub will "
                           f"not merge it while conversations are unresolved, and no Job is "
                           f"standing to resolve them (solorepo's DR-159). Promote surviving "
                           f"notices with .meta/say/post promote, resolve threads whose link or "
                           f"answer is already posted with .meta/say/post resolve, or answer with "
                           f".meta/say/post answer")
        branch = LOOPS_BRANCH.match(pr["headRefName"])
        # A review requested of reviewer where the reviewer run failed without submitting a verdict (solorepo's DR-178).
        if reviewer_login in asked and not pr["isDraft"] and pr.get("mergeable") != "CONFLICTING" and branch and idle >= minutes:
            contexts = deduplicate_checks(pr.get("statusCheckRollup") or [])
            reviewer_check = next((c for c in contexts if c.get("name") == "reviewer"), None)
            if reviewer_check and (reviewer_check.get("conclusion") or "").upper() == "FAILURE":
                out.append(f"#{pr['number']} {pr['title'][:60]} — review requested of {reviewer_login}, "
                           f"but reviewer check failed without a verdict: no run is answering it and "
                           f"nothing has moved on it for {int(idle)} minutes. Re-request review with "
                           f".meta/say/move request-review {pr['number']}")
        # An unanswered review changes request where the webhook was spent or the run crashed.
        if is_changes_requested_pull(pr, reviewer_login=reviewer_login) and not asked and branch and idle >= minutes:
            threads_unresolved = (unresolved.get(pr["number"]) if unresolved is not None
                                  else [t for t in threads(str(pr["number"])) if not t["isResolved"]])
            if threads_unresolved or not green(pr):
                issue = gh("issue", "view", branch.group(1), "--json", "state,labels")
                level = next((lbl["name"] for lbl in issue["labels"] if lbl["name"] in TAKEN), None)
                if issue["state"] == "OPEN" and level:
                    out.append(f"#{pr['number']} {pr['title'][:60]} — changes requested by "
                               f"reviewer, and unanswered: no run is answering it and nothing "
                               f"has moved on it for {int(idle)} minutes, while #{branch.group(1)} "
                               f"is still {level}. A review event was dropped or a run ended "
                               f"without answering: .meta/say/move dispatch {pr['number']} --task review")
        # An approved pull request with failing checks where the webhook was spent or the run crashed.
        if is_approved_pull(pr, reviewer_login=reviewer_login) and not asked and not pr["isDraft"] and not green(pr) and pr.get("mergeable") != "CONFLICTING" and branch and idle >= minutes:
            issue = gh("issue", "view", branch.group(1), "--json", "state,labels")
            level = next((lbl["name"] for lbl in issue["labels"] if lbl["name"] in TAKEN or lbl["name"] in ("human", "hard")), None)
            if issue["state"] == "OPEN" and level:
                if level in TAKEN:
                    remedy = f".meta/say/move dispatch {pr['number']} --task review"
                else:
                    remedy = f"fix the failing checks (or move difficulty {branch.group(1)} medium)"
                idle_mins = int(idle) if idle != float("inf") else 0
                out.append(f"#{pr['number']} {pr['title'][:60]} — approved, with failing checks: "
                           f"no review requested, no merge armed, and nothing has moved on it for "
                           f"{idle_mins} minutes, while #{branch.group(1)} is still {level}. "
                           f"A check failed after approval, and no Job is standing to fix it: {remedy}")
        if asked or pr.get("autoMergeRequest") or pr["isDraft"] or not green(pr):
            continue
        if pr["number"] not in clean:
            continue
        if not branch:
            continue
        if idle < minutes:
            continue
        issue = gh("issue", "view", branch.group(1), "--json", "state,labels")
        level = next((lbl["name"] for lbl in issue["labels"] if lbl["name"] in TAKEN or lbl["name"] in ("human", "hard")), None)
        if issue["state"] != "OPEN" or not level:
            continue
        if level in ("human", "hard"):
            if pr.get("mergeable") == "CONFLICTING":
                remedy = (f"while #{branch.group(1)} is at {level} and its branch conflicts: "
                          f"rebase {pr['headRefName']} onto {pr['baseRefName']}, then "
                          f".meta/say/move request-review {pr['number']} "
                          f"(or move difficulty {branch.group(1)} medium)")
            else:
                remedy = (f"while #{branch.group(1)} is at {level} (a run stopped before checks were green): "
                          f".meta/say/move request-review {pr['number']} "
                          f"(or move difficulty {branch.group(1)} medium)")
            out.append(f"#{pr['number']} {pr['title'][:60]} — green, and unreviewed: "
                       f"no review requested, no merge armed, and nothing has moved on it for "
                       f"{int(idle)} minutes, {remedy}")
        else:
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
    unresolved = {}
    for pr in found:
        number = str(pr["number"])
        pr_threads = threads(number)
        unresolved[pr["number"]] = [t for t in pr_threads if not t["isResolved"]]
        problems = gate(number, thread_nodes=pr_threads)
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
        reviewer = role_login("reviewer")
        owed = unheld(found, minutes, clean, unresolved, reviewer_login=reviewer)
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
                    help="A18: a dirty worktree, or a branch ahead of its remote. "
                         "Beside it: a generated page this branch left un-rendered, or "
                         "an artifact it edits that no decision it settles names")
    ap.add_argument("--base", default="origin/main",
                    help="what --handoff reads this branch against (default origin/main); "
                         "a layer of a stack is read against the layer below")
    ap.add_argument("--hand-back", metavar="ISSUE",
                    help="as JSON, what a dead run's hand-back needs about the pull "
                         "request on a Challenge's branch: whether anybody holds it, "
                         "whether it is green, and whether it conflicts")
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

    if args.hand_back:
        print(json.dumps(hand_back(args.hand_back)))
        sys.exit(0)

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
            print(f"\n--- residue: {sum(1 for line in left if not line.startswith('    '))} "
                  "branch(es) outlived their pull request ---")
            print("\n".join(left))
        sys.exit(0)

    if args.handoff:
        sys.exit(handoff(args.base))

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
            print(f"\n--- {len(parked)} noticed and not done, held for promotion at approval (solorepo's DR-159) ---")
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
