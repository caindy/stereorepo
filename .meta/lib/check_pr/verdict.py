"""The gate itself: every check a pull request on GitHub is held to, and the check run that publishes it.

The form (A15), the threads (A16), the commit Trailers (A19), the required
status contexts, and the Issue citations that resolve to nothing (A12). A
Concept the diff mints is not this gate's question: its say-so is the
reservation `vocabulary mints` reads, given by the solo or by the Challenge
that asked for the word (solorepo's DR-282).
"""
import re
from collections.abc import Sequence
from typing import Any

from lib.check_pr import META, form, github, review


def unsigned_commits(ref: str | int) -> list[str]:
    """Validates that every commit on the pull request contains an Actor trailer.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        list[str]: Validation messages for commits missing an Actor trailer.
    """
    commits = github.gh("pr", "view", str(ref), "--json", "commits")["commits"]
    return [f"{c['oid'][:8]} names no Actor: {c['messageHeadline'][:60]}"
            for c in commits
            if not review.ACTOR.search(c.get("messageBody") or "")]


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
# so `solorepo's #11, #21` names two, and `Solorepo's #11` names one at the
# head of a sentence.
FOREIGN = re.compile(r"[Ss]olorepo's #\d{1,4}\b(?:(?:,| and|, and) #\d{1,4}\b)*")

# This Portfolio is solorepo, read off the identity its assertions declare.
# `cited decisions` asks its index; a checker with no YAML parser asks for the
# line, which is the same answer by a string search.
SCAFFOLD = re.compile(r"^\s*id:\s*work:portfolio/solorepo\s*$", re.M)
LIMIT = 1000


def cited_issues() -> list[str]:
    """Validates that issue references in assertions resolve to existing GitHub issues or PRs.

    Scans YAML assertion files for bare and solorepo-qualified issue citations and
    queries GitHub to ensure they exist.

    Returns:
        list[str]: Validation error messages for non-existent cited issue numbers.
    """
    bare: dict[int, set[str]] = {}
    foreign: dict[int, set[str]] = {}
    problems: list[str] = []
    home = False
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
    known: set[int] = set()
    floor = 0
    for kind in ("issue", "pr"):
        try:
            found = github.gh(kind, "list", "--state", "all", "--limit", str(LIMIT), "--json", "number")
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


def required_contexts() -> list[str]:
    """Verifies that gate workflow jobs produce every status check required by main.

    Returns:
        list[str]: Descriptions of required status checks missing from workflow definitions.
    """
    jobs = re.findall(r"^    name: (.+)$", WORKFLOW.read_text(), re.M)
    try:
        rules = github.gh("api", f"repos/{github.repo()}/rules/branches/main")
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


def comment_trailers(
    ref: str | int,
    thread_nodes: Sequence[dict[str, Any]] | None = None,
) -> list[str]:
    """Validates that comments from repository Role accounts carry valid attribution trailers (solorepo's DR-260).

    Args:
        ref: Pull request number, URL, or head branch reference.
        thread_nodes: Optional pre-fetched review thread dictionaries.

    Returns:
        list[str]: Validation messages for comments with missing, duplicate, or malformed trailers.
    """
    threads = github.threads(ref) if thread_nodes is None else thread_nodes
    thread_comments = [
        c
        for t in threads
        for c in (t.get("comments") or {}).get("nodes", [])
    ]
    data = github.gh("pr", "view", str(ref), "--json", "comments")
    issue_comments = data.get("comments") or []
    role_logins = {github.role_login(role) for role in ("coder", "reviewer")}
    return review.audit_comment_trailers(thread_comments + issue_comments, role_logins)


def gate(ref: str | int,
         thread_nodes: Sequence[dict[str, Any]] | None = None) -> list[str]:
    """Executes gate checks on a pull request: title/body form, threads, signoffs, contexts, and comment trailers.

    Args:
        ref: Pull request number, URL, or head branch reference.
        thread_nodes: Optional pre-fetched review thread dictionaries.

    Returns:
        list[str]: Problem descriptions across all gate checks.
    """
    title, body = github.from_github(ref)
    return (form.check(title, body) + review.resolved_without_an_answer(ref, thread_nodes=thread_nodes)
            + unsigned_commits(ref) + comment_trailers(ref, thread_nodes=thread_nodes)
            + required_contexts() + cited_issues())


CONTEXT = "pull request"


def publish(number: str | int, head: str, problems: Sequence[str]) -> None:
    """Publishes gate validation results as a completed GitHub check run.

    Args:
        number: Pull request number.
        head: Commit SHA of the pull request head.
        problems: List of problem descriptions; empty indicates success.
    """
    summary = "\n".join(f"- {p}" for p in problems) or "nothing owed"
    github.gh("api", f"repos/{github.repo()}/check-runs",
       "-f", f"name={CONTEXT}", "-f", f"head_sha={head}", "-f", "status=completed",
       "-f", f"conclusion={'failure' if problems else 'success'}",
       "-f", f"output[title]={'x ' if problems else 'ok '}{CONTEXT}",
       "-f", f"output[summary]={summary}")
