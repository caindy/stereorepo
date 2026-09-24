"""The boundary an unpromoted thread may not cross, at every door of `post`
that could close one (solorepo's Article 16, solorepo's DR-224).

`probes/channel/filing.py` reads the *promoted* thread: what `promote` files,
what its reply says, and what each verb does once the link is on the thread.
This module reads the other side of the same boundary — the thread with no link
on it — and the three functions the boundary is computed from, `sole_author`,
`promotes` and `comment_party`, called directly rather than through a verb,
since a verb can only show one of their answers at a time.

`channel.graphql` is what stands in here, rather than `post.thread_comments` and
`post.thread_nodes` as `filing.py` stands in: the three GraphQL documents are
the whole of what these verbs say to GitHub, so a fake answering them reads the
reply and the resolve as writes that did or did not happen rather than as
functions that were or were not called.

One module for one probe, so a history log's Evidence names the file holding it
(solorepo's DR-209).
"""
from types import ModuleType
from typing import Any

from checks.collect import check
from checks.probes.harness import environment, exit_of, load_channel, stood_in, unanswered

ISSUE_LINK = "https://github.com/o/r/issues/900"
"""An Issue URL of the shape `promote` writes, under a repository no citation
check reads (solorepo's DR-124)."""

HASH = "#"
"""The number sign, spelled rather than typed beside digits: `#` and a number in
a file a portfolio inherits is a citation as far as `inherited citations` is
concerned, and the one below is a fixture (solorepo's DR-124)."""

TITLE = "A Challenge a promotion filed"
BODY = "**Waits on.** Nothing.\n\nWhat was noticed.\n"

MISSING = "PRRT_kwDOnothing"
"""A thread node id GitHub answers `null` for, which is a thread deleted or never held."""

THREAD = "PRRT_kwDOholds"
"""The thread node id every case here names, so a refusal is read for the id it was given."""

MINE = "Actor: gha-1\nAgent: probe"
"""The Trailer `channel.trailers()` composes under this module's environment."""

THEIRS = "Actor: gha-2\nAgent: probe"
"""A second Job's Trailer under the same login, which is the only way two
parties differ here (solorepo's DR-068)."""

CODER = "caindy-solorepo-coder"
"""The login every comment on this repository carries, whichever Job wrote it
(solorepo's DR-068)."""


class FakeThread:
    """GitHub answering the three GraphQL documents `post` sends about a review thread.

    Holds what the documents were asked to write, so a case reads the reply and
    the resolve as writes rather than as calls.

    Attributes:
        nodes: The comment nodes the thread query answers, or None for a thread
            GitHub does not hold.
        reads: How many times the thread was queried.
        replies: The body of each reply posted, in order.
        resolves: The thread id of each resolve performed, in order.
    """

    def __init__(self, nodes: list[dict[str, Any]] | None) -> None:
        self.nodes = nodes
        self.reads = 0
        self.replies: list[str] = []
        self.resolves: list[str] = []

    def graphql(self, query: str, **variables: Any) -> Any:
        """The document in `query` answered as GitHub answers it, its write recorded.

        Raises:
            AssertionError: For a document this fake does not model, named in
                the message so the report says what it was asked.
        """
        if "resolveReviewThread" in query:
            self.resolves.append(str(variables["t"]))
            return {"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}}
        if "addPullRequestReviewThreadReply" in query:
            self.replies.append(str(variables["b"]))
            return {"data": {"addPullRequestReviewThreadReply":
                             {"comment": {"url": "https://github.com/o/r/pull/7#discussion_r1"}}}}
        if "PullRequestReviewThread" in query:
            self.reads += 1
            if self.nodes is None:
                return {"data": {"node": None}}
            return {"data": {"node": {"comments": {"nodes": self.nodes}}}}
        raise unanswered((query, variables), "the thread")

    def gh(self, *args: Any, **keywords: Any) -> Any:
        """Any `gh` call these verbs make outside the three documents, which is none.

        Raises:
            AssertionError: Always, naming the call.
        """
        raise unanswered(args, "GitHub")


class Filer:
    """`move` as `promote` reaches it: `file_issue` recording its call rather than filing.

    Attributes:
        filed: One entry per call, as `(title, level, blockers)`.
    """

    def __init__(self) -> None:
        self.filed: list[tuple[str, str | None, list[int]]] = []

    def file_issue(self, title: str, body: str, level: str | None = None, roadmap: bool = False,
                   blocked_by: list[int] | None = None) -> tuple[str, str]:
        """The call recorded, answered with a number and URL as the real one answers."""
        self.filed.append((title, level, list(blocked_by or ())))
        return "900", ISSUE_LINK


def comment(body: str, login: str = CODER) -> dict[str, Any]:
    """One comment node of the shape the thread query answers."""
    return {"body": body, "author": {"login": login}}


def voiced(text: str, trailer: str) -> str:
    """A comment body ending in `trailer`, which is what `sole_author` reads."""
    return f"{text}\n\n{trailer}"


@check("resolution probes", pre=True)
def resolution_probes() -> list[str]:
    """Every door of `post` that could close an unpromoted thread, and the three
    functions the boundary is computed from (solorepo's Article 16, solorepo's DR-224).

    The hazard solorepo's #967 opens is a review point silenced with no tracker
    item behind it, and the shape of that mistake is a door that reads a thread
    as promoted when nothing was filed. So the cases here are the ones where the
    link is absent or is not a link: a thread whose only voice is the caller's
    and carries no Issue URL, a thread with one voice that is not the caller's, a
    reply naming an Issue by number rather than by URL, and a thread GitHub does
    not hold at all.

    Each is stated in the function that carries it. What is *not* here is the
    promoted thread, which `probes/channel/filing.py` holds in
    `sole_author_probes` and `multi_voice_probes`, and the level a promotion
    files at, which `probes/channel/level.py` holds.

    A refusal's text is read and not just its presence: `exit_of` reports an
    exception as text rather than raising it, so a truthy answer alone cannot
    tell the refusal from the fake being asked a document it has no answer for.
    """
    channel, _, programs = load_channel()
    post = programs["post"]
    return (boundary_probes(post) + party_probes(post)
            + unpromoted_probes(channel, post) + missing_probes(channel, post))


def boundary_probes(post: ModuleType) -> list[str]:
    """`sole_author` and `promotes`, called for the answers no single verb run shows.

    `sole_author` over an empty thread is False, so a thread with no comments
    falls to `resolve_verb`'s party test rather than being refused as
    sole-authored — a distinction no verb can show, since a thread GitHub holds
    always has the comment that opened it. It is False too where a body ends in
    prose after the Trailer, which is the reply solorepo's DR-224 asks for the
    other way round: `filing.py` reads the marker's replies for the Trailer
    coming last, and this is the reading that makes that requirement matter.

    `promotes` is the whole of what separates a promotion from a reply. An Issue
    named by number is not one, and neither is a pull request URL: both are what
    a coder writes when it means to say it filed something and did not, which is
    the silencing solorepo's #967 risks. `promotes` is deliberately wide enough
    to match an Issue URL the argument merely cites; `filing.py` states why that
    is the right width and probes it through `promote`.
    """
    problems = []
    trailing = f"{voiced('my notice', MINE)}\n\nand one more thing"
    with environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"):
        readings = {
            "an empty thread": ([], False),
            "one voice, the caller's": ([voiced("my notice", MINE)], True),
            "one voice, a second Job's": ([voiced("a point", THEIRS)], False),
            "a Trailer with prose after it": ([trailing], False),
            "an unsigned comment beside the caller's":
                ([voiced("my notice", MINE), "a point"], False),
            "both voices": ([voiced("my notice", MINE), voiced("a reply", THEIRS)], False),
        }
        for what, (bodies, expected) in readings.items():
            found = post.sole_author(bodies)
            if found is not expected:
                problems.append(f"resolution: `sole_author` read {what} as {found!r}, "
                                f"and {expected!r} is what A16 counts")

    links = {
        f"Promoted to {ISSUE_LINK}.": True,
        f"Promoted to {HASH}900.": False,
        "Promoted to issue 900.": False,
        "See https://github.com/o/r/pull/900 for the fix.": False,
    }
    for body, expected in links.items():
        if post.promotes(body) is not expected:
            problems.append(f"resolution: `promotes` read {body!r} as {post.promotes(body)!r}, "
                            f"and {expected!r} is what a promotion link is")
    return problems


def party_probes(post: ModuleType) -> list[str]:
    """`comment_party`, which is what `resolve_verb` counts when there is no link.

    Every comment on this repository carries one login, so the Trailer is the
    whole of the difference between two parties and one (solorepo's DR-068): two
    comments under that login with differing `Actor:` lines are two parties, and
    two with none are one. A comment GitHub answers no author for is `someone`,
    which counts as a party rather than crashing the read — a resolve refused
    because GitHub omitted an author would be the wrong failure.
    """
    problems = []
    readings = {
        "a signed comment": (comment(voiced("my notice", MINE)), f"{CODER}/gha-1"),
        "a second Job's under the same login":
            (comment(voiced("a reply", THEIRS)), f"{CODER}/gha-2"),
        "an unsigned comment": (comment("a point"), CODER),
        "a comment with no author": ({"body": "a point", "author": None}, "someone"),
    }
    for what, (node, expected) in readings.items():
        found = post.comment_party(node)
        if found != expected:
            problems.append(f"resolution: `comment_party` read {what} as {found!r}, "
                            f"and {expected!r} is the party A16 counts")
    return problems


def unpromoted_probes(channel: ModuleType, post: ModuleType) -> list[str]:
    """`post answer` and `post resolve` across the boundary the promotion link
    draws (solorepo's DR-224).

    The cases. `post answer` on a thread whose only voice is the caller's
    refuses before it writes anything, and the refusal names the promotion that
    would stand aside from the rule — a coder told only that it may not reply is
    left with a notice and no act. `post resolve` on a thread with one party
    that is *not* the caller's refuses too, naming A16: the caller's own Trailer
    is not what the rule turns on, so a thread nobody has answered stays open
    whoever raised it. `post resolve` on a thread with one party and a link
    resolves, which is the limb the link buys and the one a mistake in
    solorepo's #967's work would widen to the unlinked case above.

    Every refusal is read for the thread having been queried once and for the
    reply and the resolve never being sent, since a verb that refuses after
    posting has refused nothing.
    """
    problems = []

    def answered_over(nodes: list[dict[str, Any]],
                      text: str) -> tuple[str | None, FakeThread]:
        """One `post answer` of `text` over a thread holding `nodes`, as
        `(what it exited with, the fake)`."""
        fake = FakeThread(nodes)
        with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"),
              stood_in(channel, graphql=fake.graphql, gh=fake.gh)):
            return exit_of(lambda: post.answer(THREAD, text)), fake

    def resolved_over(nodes: list[dict[str, Any]]) -> tuple[str | None, FakeThread]:
        """One `post resolve` over a thread holding `nodes`, as
        `(what it exited with, the fake)`."""
        fake = FakeThread(nodes)
        with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"),
              stood_in(channel, graphql=fake.graphql, gh=fake.gh)):
            return exit_of(lambda: post.resolve_verb(THREAD)), fake

    said, fake = answered_over([comment(voiced("my notice", MINE))], "the point is met.")
    if (not said or "sole author" not in said or "Promote it" not in said
            or fake.replies or fake.resolves or fake.reads != 1):
        problems.append(f"resolution: answering an unpromoted thread with one voice, the "
                        f"caller's, was told {said!r}, replied {fake.replies!r}, resolved "
                        f"{fake.resolves!r} and read the thread {fake.reads} time(s)")

    said, fake = resolved_over([comment(voiced("a point", THEIRS))])
    if not said or "A16" not in said or fake.resolves or fake.reads != 1:
        problems.append(f"resolution: resolving an unpromoted thread with one party, not the "
                        f"caller's, was told {said!r}, resolved {fake.resolves!r} and read the "
                        f"thread {fake.reads} time(s)")

    said, fake = resolved_over([comment(voiced(f"Promoted to {ISSUE_LINK}.", THEIRS))])
    if said or fake.resolves != [THREAD]:
        problems.append(f"resolution: resolving a promoted thread with one party, not the "
                        f"caller's, said {said!r} and resolved {fake.resolves!r}")

    return problems


def missing_probes(channel: ModuleType, post: ModuleType) -> list[str]:
    """The three verbs against a thread GitHub does not hold.

    A thread id names nothing where it was mistyped, or where the pull request
    it belonged to was deleted. Each verb refuses naming the id
    it was given, so the caller can see which thread it asked about, and each
    writes nothing: `promote` in particular files no Issue, since an Issue filed
    against a thread that cannot carry the link is a promotion with nowhere to
    say so.
    """
    problems = []

    def over_nothing(call: Any) -> tuple[str | None, FakeThread, Filer]:
        """One `call` against a thread GitHub answers `null` for, as
        `(what it exited with, the fake, the filer)`."""
        fake, filer = FakeThread(None), Filer()
        with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"),
              stood_in(channel, graphql=fake.graphql, gh=fake.gh, sibling=lambda _: filer)):
            return exit_of(lambda: call(post)), fake, filer

    verbs = {
        "answer": lambda module: module.answer(MISSING, "the point is met."),
        "resolve": lambda module: module.resolve_verb(MISSING),
        "promote": lambda module: module.promote(MISSING, TITLE, BODY, None),
    }
    for verb, call in verbs.items():
        said, fake, filer = over_nothing(call)
        if not said or MISSING not in said or fake.replies or fake.resolves or filer.filed:
            problems.append(f"resolution: `post {verb}` against a thread GitHub does not hold "
                            f"was told {said!r}, replied {fake.replies!r}, resolved "
                            f"{fake.resolves!r} and filed {filer.filed!r}")
    return problems
