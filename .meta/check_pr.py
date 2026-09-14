#!/usr/bin/env python3
"""The GitHub half of the gate: A15, held against a live pull request, and the
quarter of A12 whose target is an Issue rather than a file.

`check.py` reads files and this repository's own commits, and reaches the remote
for one thing only — which Decision numbers are reserved, and only when the
record has a hole to explain (solorepo's DR-128). History in check_pr.history.md (solorepo's DR-171).
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
the branch edits while settling it (solorepo's DR-175).
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
    """Strip code fences and inline backtick spans from text.

    Parameters:
        text (str): Raw markdown text.

    Returns:
        str: Text with markdown code blocks and inline code spans removed.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def sections(body):
    """Splits pull request markdown body text at bold section headings.

    Args:
        body: Raw markdown body string.

    Returns:
        dict[str, str]: Mapping of heading names to their corresponding body text.
    """
    marks = list(HEADING.finditer(body))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out[m.group(1)] = body[m.end():end].strip()
    return out


def check(title, body):
    """Validates pull request title and body against template requirements.

    Args:
        title: Pull request title string.
        body: Pull request markdown body string.

    Returns:
        list[str]: Validation error messages.

    Four things are asked of a body, in order. Every heading the form declares
    is present and not blank. No placeholder the form spells in angle brackets
    survives into the title or the body. Each item under **What it closes**
    carries a closing keyword, so the merge closes the Issue and nobody has to
    remember to (solorepo's DR-089). And each item under **What was noticed and
    not done** is a link, which is Article 15 itself: everything before it is
    the form being present, and this is the rule the form exists to carry.
    """
    problems = []
    required = [m.group(1) for m in HEADING.finditer(fence(FORM))]
    found = sections(body)

    for heading in required:
        if heading not in found:
            problems.append(f"missing section: **{heading}.**")
        elif not found[heading]:
            problems.append(f"empty section: **{heading}.** — the form was submitted blank")

    form = fence(FORM)
    literal = set(PLACEHOLDER.findall(form)) | set(re.findall(r"<[^<>\s]+>", form))
    for where, raw in (("title", title), ("body", body)):
        text = uncoded(raw)
        seen = set(PLACEHOLDER.findall(text)) | (literal & set(re.findall(r"<[^<>\s]+>", text)))
        for m in sorted(seen):
            problems.append(f"unfilled placeholder in {where}: {m}")

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
    """Validates that every commit on the pull request contains an Actor trailer.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        list[str]: Validation messages for commits missing an Actor trailer.
    """
    commits = gh("pr", "view", ref, "--json", "commits")["commits"]
    return [f"{c['oid'][:8]} names no Actor: {c['messageHeadline'][:60]}"
            for c in commits
            if not ACTOR.search(c.get("messageBody") or "")]


def pull(ref):
    """Fetches all review threads and reviews for a pull request via GraphQL.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        dict: Pull request GraphQL node containing reviewThreads and reviews.
    """
    owner, name = gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"].split("/")
    number = gh("pr", "view", ref, "--json", "number")["number"]
    data = gh("api", "graphql", "-f", f"query={THREADS}",
              "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}")
    return data["data"]["repository"]["pullRequest"]


def threads(ref):
    """Fetches all review thread nodes for a pull request.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        list[dict]: Review thread nodes from GraphQL.
    """
    return pull(ref)["reviewThreads"]["nodes"]


def checks_of(node):
    """Extracts status check contexts from a pull request commit GraphQL node.

    Args:
        node: Pull request dictionary containing commits nodes.

    Returns:
        list[dict]: Flattened check run or status check context dictionaries.
    """
    commits = (node.get("commits") or {}).get("nodes") or []
    if not commits:
        return []
    rollup = commits[0]["commit"].get("statusCheckRollup") or {}
    return (rollup.get("contexts") or {}).get("nodes") or []


def rollup_of(number):
    """Fetches status check contexts for the head commit of a specific pull request.

    Args:
        number: Pull request number.

    Returns:
        list[dict]: Check run or status context nodes.
    """
    owner, name = repo().split("/")
    data = gh("api", "graphql", "-f", f"query={ROLLUP_ONE}",
              "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}")
    return checks_of(data["data"]["repository"]["pullRequest"])


def rollups():
    """Fetches status check contexts across all open pull requests in a single GraphQL query.

    Returns:
        dict[int, list[dict]]: Mapping of pull request numbers to their check context lists.
    """
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
    """Format a review thread for display with identifier, location, and comments.

    Parameters:
        thread (dict): Thread node payload from GitHub GraphQL query.
        where (str): Human-readable location description.
        limit (int, optional): Maximum characters per comment, or None for full text.

    Returns:
        str: Formatted multi-line thread summary.
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
    """Format resolved review threads for reviewer re-inspection.

    Parameters:
        nodes (list[dict]): Review thread nodes from GitHub.
        limit (int, optional): Maximum characters per comment, or None for full text.

    Returns:
        list[str]: Formatted summaries of resolved threads with resolver logins.
    """
    out = []
    for t in nodes:
        if not t["isResolved"]:
            continue
        by = (t.get("resolvedBy") or {}).get("login", "someone")
        out.append(shown(t, where_of(t, owed=False) + f" — resolved by {by}", limit=limit))
    return out


def verdicts(reviews):
    """Format review verdicts in reverse chronological order against head commits.

    Parameters:
        reviews (list[dict]): Review nodes from GitHub GraphQL query (solorepo's DR-118).

    Returns:
        list[str]: Formatted review verdicts with author, state, commit SHA, and timestamp.
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
    """Identify the pull request associated with the current branch or list open ones.

    Returns:
        tuple[str, list[tuple[int, str, list[str] | None]]]: Current branch name and
            list of tuples containing PR number, title, and unaddressed thread summaries.
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
    """Identifies local branches and worktrees whose remote tracking branches are gone.

    Returns:
        list[str]: Descriptions and git cleanup commands for orphaned branches and worktrees.
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
    """Verifies that the working tree has no uncommitted changes and all commits are pushed.

    Returns:
        list[str]: Validation error messages for uncommitted or unpushed modifications.
    """
    def git(*args):
        """Executes a git command and returns its status code, stdout, and stderr.

        Returns:
            tuple[int, str, str]: Return code, stripped stdout, and stripped stderr.
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
    """Executes a git command in ROOT, returning its return code and stdout.

    Args:
        *args: Command arguments passed to git.

    Returns:
        tuple[int, str]: Git return code and raw standard output string.
    """
    out = subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT)
    return out.returncode, out.stdout


def git_text(*args, default=""):
    """Executes a git command in ROOT, returning stdout on success or default on failure.

    Args:
        *args: Command arguments passed to git.
        default: Fallback string to return if the command exits non-zero.

    Returns:
        str: Output text on success, or the default fallback string.
    """
    code, out = git_read(*args)
    return default if code else out


def touched(base):
    """Returns all paths modified on this branch against the merge base, including untracked files.

    Args:
        base: Target branch or commit ref to compute the merge base against.

    Returns:
        list[str] | None: Unique relative paths modified or added, or None if git diff failed.
    """
    merge = git_text("merge-base", "HEAD", base).strip() or base
    code, diffed = git_read("diff", "--name-only", merge)
    if code:
        return None
    named = diffed.split()
    named += git_text("ls-files", "--others", "--exclude-standard").split()
    return list(dict.fromkeys(named))


def artifacts():
    """Extracts declared artifact paths from structure assertions.

    Returns:
        set[str]: Set of artifact path strings declared in structure assertions.
    """
    found = set()
    for rel in ("assertions/structure.yaml", "assertions/imported/structure.yaml"):
        path = META / rel
        if path.is_file():
            found |= set(ARTIFACT.findall(path.read_text()))
    return found


def accounted():
    """Maps artifact file paths to the set of decision numbers that enact them.

    Returns:
        dict[str, set[int]]: Mapping of artifact file paths to decision ID numbers.
    """
    path = ROOT / INDEX
    if not path.is_file():
        return {}
    return {file: {int(n) for n in DR.findall(entries)}
            for file, entries in ROW.findall(path.read_text())}


def unrendered():
    """Checks whether generated documentation pages match their source assertions.

    Returns:
        tuple[list[str] | None, list[str] | None, str]: A 3-tuple containing:
            - stale: Names of pages differing from rendered output, or None on failure.
            - unrendered: Names of pages missing generated output, or None on failure.
            - error: Descriptive error message if the render command could not run.
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


def artifact_map():
    """Maps artifact IDs (e.g. 'work:artifact/meta-charter') to their declared paths.

    Returns a dictionary (`dict[str, str]`) mapping these artifact ID strings to
    their declared file paths relative to the workspace root.
    """
    mapping = {}
    for rel in ("assertions/structure.yaml", "assertions/imported/structure.yaml"):
        path = META / rel
        if not path.is_file():
            continue
        curr_id = None
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("- id:"):
                curr_id = stripped.split(":", 1)[1].strip()
            elif curr_id and stripped.startswith("path:"):
                p = stripped.split(":", 1)[1].strip().strip('"\'')
                mapping[curr_id] = p
                curr_id = None
    return mapping


def parse_decision_yaml(path):
    """Parses a decision yaml file, returning its status and the list of enacted_in artifact ids.

    The `path` parameter expects a `pathlib.Path` instance pointing to the YAML
    decision file. Returns a tuple of `(status, enacted_in)` consisting of
    `status` (a string or None) and `enacted_in` (a list of artifact ID strings).
    """
    status = None
    enacted_in = []

    lines = path.read_text().splitlines()
    in_enacted_in = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("status:"):
            status = stripped.split(":", 1)[1].strip().strip('"\'')
        elif stripped.startswith("enacted_in:"):
            in_enacted_in = True
            continue
        elif in_enacted_in:
            if stripped.startswith("-"):
                art = stripped.removeprefix("-").strip().strip('"\'')
                enacted_in.append(art)
            elif line.startswith("  ") and not stripped:
                continue
            elif stripped and not stripped.startswith("-") and ":" in stripped:
                in_enacted_in = False

    return status, enacted_in


RECORD = (".meta/assertions/decisions/", ".meta/decisions.md")


def unenacted(base):
    """Verifies that every adopted decision settled on this branch enacts non-record artifacts.

    Args:
        base: Git ref string to compare against (e.g. 'origin/main').

    Returns:
        tuple[list[str] | None, str]: Problem descriptions (or None if base cannot resolve)
            and a summary note string.
    """
    changed = touched(base)
    if changed is None:
        return None, f"{base} did not resolve, so what this branch changed is unread"
    settled = sorted({int(m.group(1)) for p in changed if (m := ENTRY_FILE.match(p))})
    if not settled:
        return [], "this branch settles no decision"

    amap = artifact_map()
    problems = []

    for n in settled:
        path = ROOT / f".meta/assertions/decisions/DR-{n:03d}.yaml"
        if not path.is_file():
            continue

        status, enacted_in = parse_decision_yaml(path)
        if status == "ADOPTED":
            valid_paths = []
            for art_id in enacted_in:
                p = amap.get(art_id)
                if p and not any(p.startswith(r) for r in RECORD):
                    valid_paths.append(p)
            if not valid_paths:
                problems.append(
                    f"DR-{n:03d}: is adopted and names no Artifact carrying its rule "
                    f"under enacted_in — name at least one non-record Artifact carrying its rule"
                )

    shown = ", ".join(f"DR-{n:03d}" for n in settled)
    return problems, f"{len(settled)} decision(s) settled on this branch ({shown})"


def handoff(base):
    """Executes handoff validation checking unpushed commits, stale renders, and enacted artifacts.

    Args:
        base: Git ref (e.g. 'origin/main') to evaluate branch changes against.

    Returns:
        int: 0 if all handoff checks pass; 1 if any check fails.

    The render names a page relative to `.meta/`, which is how the Artifact
    asserting its prose is found too, so a name the render answered with is
    turned back into the repository-relative path the record's table and this
    file's own reads are keyed on.
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
    """Formats pull request status, check rollups, reviews, and unaddressed threads for resuming work.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        str: Formatted briefing summary of pull request state.
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
    pr = gh("pr", "view", ref, "--json", "number,state,comments,reviews,mergeable")
    comments = {c["id"]: c for c in pr["comments"]}
    reviews = {r["id"]: r for r in pr["reviews"]}
    threads_ = {t["id"]: t for t in threads(ref)}
    sorted_checks = deduplicate_checks(rollup_of(pr["number"]))
    checks = {c.get("name") or c.get("context"):
              (c.get("conclusion") or c.get("state") or c.get("status") or "PENDING",
               c.get("detailsUrl") or c.get("targetUrl"))
              for c in sorted_checks}
    return (pr["number"], pr["state"], comments, reviews, threads_, checks,
            pr.get("mergeable") or "UNKNOWN")


def mine(body):
    """Determines whether a comment was authored by the current session.

    Args:
        body: Text content of the comment or review.

    Returns:
        bool: True if the comment trailer matches the active session identifier.
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
                if not mine(r.get("body", "")):
                    print(f"review by {r['author']['login']}: {r['state']} {said(r.get('body', ''))}",
                          flush=True)
                    actionable.append(f"review by {r['author']['login']} ({r['state']})")
            for tid in threads_.keys() - p_threads.keys():
                t = threads_[tid]
                where = (t["path"] or "the pull request") + (f":{t['line']}" if t.get("line") else "")
                first_author = (t["comments"]["nodes"][0]["author"] or {}).get("login", "someone") if t["comments"]["nodes"] else "someone"
                first_body = t["comments"]["nodes"][0]["body"] if t["comments"]["nodes"] else ""
                print(f"new thread on {where} by {first_author}: {said(first_body)}", flush=True)
                actionable.append(f"new thread on {where}")
            for tid, t in threads_.items():
                where = (t["path"] or "the pull request") + (f":{t['line']}" if t.get("line") else "")
                before = p_threads.get(tid)
                nodes = t["comments"]["nodes"]
                before_len = len(before["comments"]["nodes"]) if before else 0
                if before is None or len(nodes) > before_len:
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
    """Identifies resolved review threads that lack an answer from a distinct participant.

    Args:
        ref: Pull request number, URL, or head branch reference.
        thread_nodes: Optional pre-fetched review thread dictionaries.

    Returns:
        list[str]: Validation error messages for threads resolved without independent response.
    """
    return unanswered(threads(ref) if thread_nodes is None else thread_nodes)


def parties(thread):
    """Extracts the set of distinct participants in a review thread.

    Args:
        thread: Review thread dictionary containing comments and optional resolution metadata.

    Returns:
        set[str]: Set of participant identifiers (logins or actor trailers).
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
    """Validates that issue references in assertions resolve to existing GitHub issues or PRs.

    Scans YAML assertion files for bare and solorepo-qualified issue citations and
    queries GitHub to ensure they exist.

    Returns:
        list[str]: Validation error messages for non-existent cited issue numbers.
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
    """Verifies that gate workflow jobs produce every status check required by main.

    Returns:
        list[str]: Descriptions of required status checks missing from workflow definitions.
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
    """Executes gate checks on a pull request: title/body form, threads, signoffs, and contexts.

    Args:
        ref: Pull request number, URL, or head branch reference.
        thread_nodes: Optional pre-fetched review thread dictionaries.

    Returns:
        list[str]: Problem descriptions across all gate checks.
    """
    title, body = from_github(ref)
    return (check(title, body) + resolved_without_an_answer(ref, thread_nodes=thread_nodes)
            + unsigned_commits(ref) + required_contexts() + cited_issues())


CONTEXT = "pull request"


def publish(number, head, problems):
    """Publishes gate validation results as a completed GitHub check run.

    Args:
        number: Pull request number.
        head: Commit SHA of the pull request head.
        problems: List of problem descriptions; empty indicates success.
    """
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
    """Reads the maximum job timeout in minutes configured for the coder workflow.

    Returns:
        int | None: Configured timeout in minutes, or None if unreadable.
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
    """Provides pull request status metrics for challenge hand-back automation.

    Args:
        issue: Challenge issue number string or integer.

    Returns:
        dict[str, Any]: Status summary containing handed, green, conflicting, number, base.
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
    """Identifies open pull requests lacking an active owner, review request, or remediation.

    Args:
        prs: Sequence of pull request metadata dictionaries from GitHub.
        minutes: Inactivity threshold in minutes before flagging unheld work.
        clean: Set of pull request numbers verified as passing gate checks in the current run.
        unresolved: Optional mapping of pull request numbers to unresolved review threads.
        reviewer_login: Optional reviewer handle; defaults to the configured reviewer role.

    Returns:
        list[str]: Remediation messages for each unheld or stalled pull request.

    Each shape reported here is one a webhook should have carried and did not:
    the event was spent, or the run that took it ended without answering. A
    review requested of the reviewer whose check failed with no verdict
    (solorepo's DR-178); a request for changes nobody is answering; an approved
    pull request whose checks are red; and one that is green with nobody
    holding it. Every one is qualified by `minutes` of silence, so a pass that
    is merely still running is not mistaken for one that stopped.
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
        if reviewer_login in asked and not pr["isDraft"] and pr.get("mergeable") != "CONFLICTING" and branch and idle >= minutes:
            contexts = deduplicate_checks(pr.get("statusCheckRollup") or [])
            reviewer_check = next((c for c in contexts if c.get("name") == "reviewer"), None)
            if reviewer_check and (reviewer_check.get("conclusion") or "").upper() == "FAILURE":
                out.append(f"#{pr['number']} {pr['title'][:60]} — review requested of {reviewer_login}, "
                           f"but reviewer check failed without a verdict: no run is answering it and "
                           f"nothing has moved on it for {int(idle)} minutes. Re-request review with "
                           f".meta/say/move request-review {pr['number']}")
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
    """Evaluates gate checks and ownership across all open pull requests.

    Args:
        publishing: Whether to publish check runs to GitHub for each pull request.

    Returns:
        int: 0 if all checks succeed or no PRs are open; 1 if any check or fetch failed.

    A pull request GitHub would not answer for — the listing that failed, or
    the one missing from the rollup — is reported as unread and keeps the
    verdict its last push left. It is not passed on to `unheld`, where an empty
    check suite is indistinguishable from a green one, and a run that could not
    ask would otherwise report the whole tree as clean.
    """
    try:
        found = gh("pr", "list", "--state", "open", "--json", SWEEP_FIELDS)
        rolled = rollups()
    except SystemExit as unreachable:
        print("x  sweep — could not ask GitHub for the open pull requests, so no "
              "verdict was published and every one keeps the verdict its last "
              f"push left: {unreachable.code}")
        return 1
    if not found:
        print("ok sweep — no open pull requests")
        return 0
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
