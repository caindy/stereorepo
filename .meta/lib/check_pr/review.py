"""Review threads as the gate reads them: owed, parked, answered, and who said what.

A thread is answered when a second party spoke, when it was promoted to an
Issue, or when the solo resolved it (A16). Who spoke is read off the `Actor:`
Trailer, because every comment an agent posts is authored by the solo's account.
"""
import re
import types
from collections.abc import Sequence
from typing import Any

from lib.check_pr import META, github

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


# The channel itself, because `mine()` below asks it which session is speaking
# rather than resolving one of its own: the reader of a Trailer and the writer
# of it disagreeing inside a run is the defect solorepo's #285 fixed and
# solorepo's DR-233 keeps fixed. `RUN_MARK` — what a workflow writes into
# `ACTOR_SESSION` and nothing else does (solorepo's DR-148) — is re-exported
# from here for the same reason: one constant, in the channel.
def _load_channel() -> types.ModuleType:
    import importlib.util
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("channel", str(META / "say" / "channel.py"))
    spec = importlib.util.spec_from_loader("channel", loader)
    if spec is None:
        raise ImportError(f"no module spec for {loader.path}")
    channel = importlib.util.module_from_spec(spec)
    loader.exec_module(channel)
    return channel


CHANNEL = _load_channel()

RUN_MARK = str(CHANNEL.RUN_MARK)

NOTICED = re.compile(r"^\W*\*\*Noticed and not done\.?\*\*", re.M)

PROMOTED = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/issues/\d+")


def where_of(thread: dict[str, Any], owed: bool = True) -> str:
    """Where a thread sits, as a reader would look for it."""
    where = thread["path"] or "the pull request"
    if thread.get("line"):
        where += f":{thread['line']}"
    if thread["isOutdated"]:
        where += " (outdated — answer it anyway)" if owed else " (outdated)"
    return where


def shown(thread: dict[str, Any], where: str, limit: int | None = 600) -> str:
    """Format a review thread for display with identifier, location, and comments.

    Parameters:
        thread (dict): Thread node payload from GitHub GraphQL query.
        where (str): Human-readable location description.
        limit (int, optional): Maximum characters per comment, or None for full text.

    Returns:
        str: Formatted multi-line thread summary.
    """
    spoke: list[str] = []
    for c in thread["comments"]["nodes"]:
        who = (c["author"] or {}).get("login", "someone")
        body = " ".join((c["body"] or "").split())
        spoke.append(f"    {who}: " + (body if limit is None else body[:limit]))
    return f"  {thread['id']}\n  {where}\n" + "\n".join(spoke)


def unaddressed(nodes: Sequence[dict[str, Any]], parked: bool = False,
                limit: int | None = 600) -> list[str]:
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
    out: list[str] = []
    for t in nodes:
        if t["isResolved"]:
            continue
        comments = t["comments"]["nodes"]
        held = bool(comments) and bool(NOTICED.search(comments[-1]["body"] or ""))
        if held != parked:
            continue
        out.append(shown(t, where_of(t), limit=limit))
    return out


def settled(nodes: Sequence[dict[str, Any]], limit: int | None = 600) -> list[str]:
    """Format resolved review threads for reviewer re-inspection.

    Parameters:
        nodes (list[dict]): Review thread nodes from GitHub.
        limit (int, optional): Maximum characters per comment, or None for full text.

    Returns:
        list[str]: Formatted summaries of resolved threads with resolver logins.
    """
    out: list[str] = []
    for t in nodes:
        if not t["isResolved"]:
            continue
        by = (t.get("resolvedBy") or {}).get("login", "someone")
        out.append(shown(t, where_of(t, owed=False) + f" — resolved by {by}", limit=limit))
    return out


def verdicts(reviews: Sequence[dict[str, Any]]) -> list[str]:
    """Format review verdicts in reverse chronological order against head commits.

    Parameters:
        reviews (list[dict]): Review nodes from GitHub GraphQL query (solorepo's DR-118).

    Returns:
        list[str]: Formatted review verdicts with author, state, commit SHA, and timestamp.
    """
    out: list[str] = []
    for r in reversed(reviews):
        body = said(r.get("body"), 600)
        if r["state"] == "COMMENTED" and not body:
            continue
        who = (r["author"] or {}).get("login", "someone")
        sha = (r.get("commit") or {}).get("abbreviatedOid") or "no head"
        when = (r.get("submittedAt") or "")[:16].replace("T", " ")
        out.append(f"  {who} {r['state']} on {sha} at {when}" + (f"\n    {body}" if body else ""))
    return out


def said(body: str | None, limit: int = 300) -> str:
    """Truncates and collapses whitespace in a comment or text string for display."""
    return " ".join((body or "").split())[:limit]


def mine(body: str | None) -> bool:
    """Determines whether a comment was authored by the current session.

    Who this session is comes from `channel.speaker()`, the resolution the
    channel signs with, so a Trailer is read as this session's exactly when
    this session would have written it (solorepo's DR-233).

    Args:
        body: Text content of the comment or review.

    Returns:
        bool: True if the comment trailer matches the active session identifier.
    """
    me = CHANNEL.speaker()
    found = ACTOR.search(body or "")
    return bool(me and found and found.group(1) == me)


def parties(thread: dict[str, Any]) -> set[str]:
    """Extracts the set of distinct participants in a review thread.

    Args:
        thread: Review thread dictionary containing comments and optional resolution metadata.

    Returns:
        set[str]: Set of participant identifiers (logins or actor trailers).
    """
    seen: set[str] = set()
    resolver = (thread.get("resolvedBy") or {}).get("login")
    if resolver:
        seen.add(resolver)
    for c in thread["comments"]["nodes"]:
        login = (c["author"] or {}).get("login", "someone")
        actor = ACTOR.search(c["body"] or "")
        seen.add(f"{login}/{actor.group(1)}" if actor else login)
    return seen


def unanswered(nodes: Sequence[dict[str, Any]]) -> list[str]:
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
    problems: list[str] = []
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


def resolved_without_an_answer(
        ref: str | int,
        thread_nodes: Sequence[dict[str, Any]] | None = None) -> list[str]:
    """Identifies resolved review threads that lack an answer from a distinct participant.

    Args:
        ref: Pull request number, URL, or head branch reference.
        thread_nodes: Optional pre-fetched review thread dictionaries.

    Returns:
        list[str]: Validation error messages for threads resolved without independent response.
    """
    return unanswered(github.threads(ref) if thread_nodes is None else thread_nodes)
