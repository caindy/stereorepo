#!/usr/bin/env python3
"""The GitHub half of the gate: A15, held against a live pull request.

`check.py` reads files and needs no network. This reads GitHub, so it is a
separate command with a separate lifecycle — it runs when a pull request opens
or changes, and there is nothing for it to say the rest of the time.

    python .meta/check_pr.py 12          # what CI runs
    python .meta/check_pr.py --file b.md # a body on disk, for watching it fail

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
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

META = pathlib.Path(__file__).parent
FORM = META / "templates" / "pull-request.md"
HEADING = re.compile(r"^\*\*(.+?)\.\*\*", re.M)
PLACEHOLDER = re.compile(r"<[^<>\n]*\s[^<>\n]*>")
LINK = re.compile(r"(#\d+|https?://\S+)")
BULLET = re.compile(r"^\s*[-*]\s+(.*)$", re.M)
NONE = re.compile(r"^\s*(none|nothing)\b", re.I)
DEFERRED = "What was noticed and not done"


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


def unaddressed(nodes):
    """What is still owed an answer, in the order a reader should take them.

    Unresolved is the whole test. An outdated thread is still unaddressed —
    DR-057 — and is marked rather than filtered, because the anchor moving is
    the reader's context and not a reason to skip it.
    """
    out = []
    for t in nodes:
        if t["isResolved"]:
            continue
        where = t["path"] or "the pull request"
        if t.get("line"):
            where += f":{t['line']}"
        if t["isOutdated"]:
            where += " (outdated — answer it anyway)"
        said = []
        for c in t["comments"]["nodes"]:
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


def unanswered(nodes):
    """The predicate, apart from the fetching, so it can be watched failing."""
    problems = []
    for t in nodes:
        if not t["isResolved"]:
            continue
        authors = [c["author"]["login"] for c in t["comments"]["nodes"] if c["author"]]
        if len(set(authors)) < 2:
            who = authors[0] if authors else "nobody"
            problems.append(
                f"resolved without an answer: {t['path'] or 'the pull request'}, "
                f"opened by {who} — if it was worth mentioning it is worth answering")
    return problems


def from_github(ref):
    out = subprocess.run(["gh", "pr", "view", ref, "--json", "title,body"],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"gh: {out.stderr.strip()}")
    data = json.loads(out.stdout)
    return data["title"], data["body"] or ""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pr", nargs="?", help="pull request number, URL or branch")
    ap.add_argument("--file", help="read a body from disk instead of GitHub")
    ap.add_argument("--title", default="a real title", help="title to use with --file")
    ap.add_argument("--threads", action="store_true",
                    help="print the threads still owed an answer, and check nothing")
    ap.add_argument("--sweep", action="store_true",
                    help="every open pull request you own, and what each still owes")
    args = ap.parse_args()

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

    if args.threads:
        if not args.pr:
            ap.error("--threads needs a pull request")
        owed = unaddressed(threads(args.pr))
        print("\n".join(owed) if owed else "nothing unaddressed")
        sys.exit(0)

    if args.file:
        title, body = args.title, pathlib.Path(args.file).read_text()
    elif args.pr:
        title, body = from_github(args.pr)
    else:
        ap.error("give a pull request, or --file")

    problems = check(title, body)
    if args.pr:
        problems += resolved_without_an_answer(args.pr)
    for p in problems:
        print(f"x  {p}")
    print(f"{'x  ' if problems else 'ok '}pull request"
          + (f" ({len(problems)})" if problems else ""))
    sys.exit(1 if problems else 0)
