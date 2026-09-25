"""`file_issue` and `promote` refusing a second Issue for one Challenge (solorepo's DR-221).
"""

from types import ModuleType, SimpleNamespace

from checks.collect import check
from checks.probes.harness import (
    FakeFiling,
    environment,
    load_channel,
    run_verb,
    stood_in,
)

TITLE = "A Challenge filed once"
BODY = "**Waits on.** Nothing.\n\nWhat was noticed.\n"
DISTINCT_BODY = "**Waits on.** Nothing.\n\nA separate queue concern.\n"


@check("filing probes", pre=True)
def filing_probes() -> list[str]:
    """`file_issue` and `promote` refusing a second Issue for one Challenge (solorepo's DR-221).

    The three acts of a promotion — file, reply, resolve — are not one
    transaction, so the failure this guards is a retry after one of the later
    two failed, with the Issue already filed. Both halves are stated here
    because the two verbs hold different keys: `promote` has the thread and
    `file` has only the title, and a caller types `file` with no thread at all.

    The cases on the title. A filing into an empty listing goes through and is
    recorded. The same title filed a second time is refused with nothing
    created, and the refusal names the standing Issue's number, since a caller
    told only that it may not file is left with the collision and no act. A
    unrelated title and body are not refused by a listing holding the first. A listing
    GitHub will not answer for does not stop a filing: the guard is a courtesy
    against a retry, not a gate, and an outage that made every filing impossible
    would be the worse failure.

    The cases on the thread. A thread already carrying `Promoted to <url>.` is
    refused with the Issue named, and nothing is filed — the half-done act's
    remainder is the thread, so the refusal names `post resolve`, which is read
    rather than assumed, as the second filing's refusal is read for
    `post answer`: solorepo's DR-221 has it that each refusal carries its
    remedy, and a refusal could lose that paragraph with the collision intact.
    The thread is read once, which is what the returned bodies of
    `refuse_if_sole_author` are for. A thread
    carrying no such link promotes as before. A thread that merely cites an Issue
    URL promotes too, which is the case `check_pr.PROMOTED` would have vetoed:
    this repository asks a reviewer to dereference citations, so an argued thread
    carrying someone else's Issue URL is ordinary, and refusing it would lose the
    Challenge rather than delay it.

    The cases on the voices (solorepo's DR-224). Against a thread carrying one
    Trailer, the caller's own, `promote` files and replies and leaves the thread
    open, and both `post resolve` and `post answer` decline to close it — the
    resolve refusing outright and the answer replying without resolving, each
    with the Issue's link already on the thread, which is the case the code this
    change replaces would have closed. Against a thread carrying a second Job's
    Trailer all three behave as solorepo's DR-127 left them.

    A refusal's text is read, not just its presence: `run_verb` reports an
    exception as text rather than raising it, so a truthy answer alone cannot
    tell the refusal from the fake being asked something it has no answer for.

    Every case here files at a level, which only a session may do
    (solorepo's DR-235), so `ACTOR_SESSION` is unset around them rather than
    left as the environment has it: the gate runs inside the coder loop's
    container as well as on a laptop, and the same case would otherwise be a
    filing in one place and a refused level in the other.
    """
    channel, _, programs = load_channel()
    move, post = programs["move"], programs["post"]
    problems: list[str] = []

    with environment(GITHUB_RUN_ID=None, ACTOR_SESSION=None):
        fake = FakeFiling()
        said = run_verb(channel, fake, lambda: move.file_issue(TITLE, BODY, level="hard"))
        if said or len(fake.created) != 1:
            problems.append(f"filing: a first filing said {said!r} and created {len(fake.created)}")

        said = run_verb(channel, fake, lambda: move.file_issue(TITLE, BODY, level="hard"))
        if not said or "900" not in said or "post answer" not in said or len(fake.created) != 1:
            problems.append(f"filing: a second filing under one title said {said!r} and left "
                            f"{len(fake.created)} created")

        said = run_verb(
            channel,
            fake,
            lambda: move.file_issue("A separate queue", DISTINCT_BODY, level="hard"),
        )
        if said or len(fake.created) != 2:
            problems.append(f"filing: a filing under an unused title said {said!r} and left "
                            f"{len(fake.created)} created")

        unread = FakeFiling()
        said = run_verb(channel, unread, lambda: move.file_issue(TITLE, BODY))
        labels = next(iter(unread.created.values()), ("", "", []))[2]
        if said or labels != ["challenge"]:
            problems.append(f"filing: a filing with no level said {said!r} and landed {labels!r}; "
                            "`challenge` alone is the reviewer's queue (solorepo's DR-230)")

        blind = FakeFiling(list_fails=True)
        said = run_verb(channel, blind, lambda: move.file_issue(TITLE, BODY, level="hard"))
        if said or blind.listings != 1 or len(blind.created) != 1:
            problems.append(f"filing: a filing whose listing GitHub would not answer said {said!r} "
                            f"after {blind.listings} listing(s), and created {len(blind.created)}")

        duplicate = FakeFiling([
            (
                901,
                "Prevent duplicate Challenge filings",
                "Refuse repeated Challenge work before it begins.",
            ),
            (902, "Prevent filing errors", "Document filing error recovery before work begins."),
        ])
        said = run_verb(
            channel,
            duplicate,
            lambda: move.file_issue(
                "Prevent duplicate Challenge filing",
                "**Waits on.** Nothing.\n\nRefuse repeated Challenge work before it begins.",
                level="hard",
            ),
        )
        if not said or "901" not in said or duplicate.created:
            problems.append(
                f"filing: a semantic duplicate said {said!r} and created {duplicate.created!r}"
            )

    problems += semantic_ratio_probes(move)
    problems += semantic_queue_probes(move)
    problems += promotion_probes(channel, post)
    return problems


def semantic_ratio_probes(move: ModuleType) -> list[str]:
    """Check the solorepo's DR-266 threshold at and below the adopted boundary."""
    class ScoredIndex:
        def add_document(self, *args: object) -> None:
            return None

        def finalize(self) -> None:
            return None

        def search(self, _query: str, top_k: int = 5) -> list[SimpleNamespace]:
            return scores[:top_k]

    issues = [
        {"number": 1, "title": "First", "body": "", "url": "https://github.com/o/r/issues/1"},
        {"number": 2, "title": "Second", "body": "", "url": "https://github.com/o/r/issues/2"},
    ]
    problems: list[str] = []
    scores = [
        SimpleNamespace(identifier="1", score=1.79),
        SimpleNamespace(identifier="2", score=1.0),
    ]
    with stood_in(move.challenges.bm25, SearchIndex=ScoredIndex):
        match = move.challenges.semantic_duplicate(issues, "Proposed", "body")
    if match != issues[0]:
        problems.append(f"filing: the 1.79 semantic ratio matched {match!r}, not the leading Issue")

    scores = [
        SimpleNamespace(identifier="1", score=1.78),
        SimpleNamespace(identifier="2", score=1.0),
    ]
    with stood_in(move.challenges.bm25, SearchIndex=ScoredIndex):
        match = move.challenges.semantic_duplicate(issues, "Proposed", "body")
    if match is not None:
        problems.append(f"filing: the 1.78 semantic ratio matched {match!r}, below the 1.79 cutoff")
    return problems


def semantic_queue_probes(move: ModuleType) -> list[str]:
    """Run solorepo's DR-266 corpus shapes through the real BM25F implementation."""
    issues = [
        {
            "number": 901,
            "title": "Prevent duplicate Challenge filings",
            "body": "Refuse repeated Challenge work before it begins.",
            "url": "https://github.com/o/r/issues/901",
        },
        {
            "number": 902,
            "title": "Prevent filing errors",
            "body": "Document filing error recovery before work begins.",
            "url": "https://github.com/o/r/issues/902",
        },
        {
            "number": 903,
            "title": "Document deployment gate",
            "body": "Explain the deployment gate for release.",
            "url": "https://github.com/o/r/issues/903",
        },
        {
            "number": 904,
            "title": "Document review gate",
            "body": "Explain the review gate for release.",
            "url": "https://github.com/o/r/issues/904",
        },
    ]
    duplicate = move.challenges.semantic_duplicate(
        issues[:2],
        "Prevent duplicate Challenge filing",
        "**Waits on.** Nothing.\n\nRefuse repeated Challenge work before it begins.",
    )
    adjacent = move.challenges.semantic_duplicate(
        issues,
        "Document release gate",
        "**Waits on.** Nothing.\n\nExplain the release gate guide.",
    )
    sole_issue = move.challenges.semantic_duplicate(
        issues[:1],
        "Prevent duplicate Challenge filing",
        "**Waits on.** Nothing.\n\nRefuse repeated Challenge work before it begins.",
    )
    problems = []
    if duplicate != issues[0]:
        problems.append(f"filing: the real duplicate corpus matched {duplicate!r}, not the leading Issue")
    if adjacent is not None:
        problems.append(f"filing: the adjacent corpus matched {adjacent!r}")
    if sole_issue is not None:
        problems.append(f"filing: a one-Issue queue matched {sole_issue!r}")
    return problems


def read_bodies(bodies: list[str], reads: list[int]) -> list[str]:
    """One thread read: records the read in `reads` and answers a copy of `bodies`."""
    reads.append(1)
    return list(bodies)


ISSUE_LINK = "https://github.com/o/r/issues/900"


def sole_author_probes(channel: ModuleType, post: ModuleType) -> list[str]:
    """The three verbs against a thread carrying one Trailer, the caller's own (solorepo's DR-289).

    A notice is this shape by construction, and A16's falsifier is the thread
    only the Actor who raised it can resolve, so a resolve from that Actor is
    what the decision addresses — at every door, since the falsifier reads "by any
    sequence of these verbs".

    The cases. `promote` files once, replies with the Issue's link, and DOES
    resolve the thread immediately, as the link serves as the durable artifact.
    `post resolve` on the same thread *already carrying that link* resolves it:
    the link acts as the second party. `post answer` with a body repeating
    the link replies and resolves, which is the verb the standing refusal
    points at.

    Both replies are read for the Trailer coming last, which keeps `sole_author`
    true of the reply, though the link permits the resolution regardless.
    """
    problems = []
    replied_to: list[tuple[str, str]] = []
    resolved: list[str] = []
    filed: list[tuple[str, str | None]] = []
    own_voice_body = "my notice\n\nActor: gha-1\nAgent: probe"
    promoted_body = f"Promoted to {ISSUE_LINK}.\n\nActor: gha-1\nAgent: probe"

    with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe"),
          stood_in(post, thread_comments=lambda _: [own_voice_body],
                   reply=lambda t, b: replied_to.append((t, b)),
                   resolve=lambda t: resolved.append(t)),
          stood_in(channel, sibling=lambda _: Filer(filed))):
        said = run_verb(channel, FakeFiling(),
                        lambda: post.promote("t1", TITLE, BODY, "hard"))

    if said:
        problems.append(f"filing: promoting sole-authored thread exited with error: {said!r}")
    if len(filed) != 1:
        problems.append(f"filing: promoting sole-authored thread did not file exactly once: {filed!r}")
    if len(resolved) != 1:
        problems.append(f"filing: promoting sole-authored thread did not resolve the thread: {resolved!r}")

    resolved.clear()
    with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe"),
          stood_in(post, thread_nodes=lambda _: [
                       {"body": own_voice_body, "author": {"login": "caindy-solorepo-coder"}},
                       {"body": promoted_body, "author": {"login": "caindy-solorepo-coder"}},
                   ],
                   resolve=lambda t: resolved.append(t))):
        said = run_verb(channel, FakeFiling(),
                        lambda: post.resolve_verb("t1"))
    if said:
        problems.append(f"filing: post resolve on a promoted sole-authored thread failed: {said!r}")
    if not resolved:
        problems.append(f"filing: post resolve on a promoted sole-authored thread did not resolve it: {resolved!r}")

    replied_to.clear()
    resolved.clear()
    with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe"),
          stood_in(post, thread_comments=lambda _: [own_voice_body, promoted_body],
                   reply=lambda t, b: replied_to.append((t, b)),
                   resolve=lambda t: resolved.append(t))):
        said = run_verb(channel, FakeFiling(),
                        lambda: post.answer("t1", f"Promoted to {ISSUE_LINK}."))
    if said:
        problems.append(f"filing: post answer with a link on a sole-authored thread failed: {said!r}")
    if not resolved:
        problems.append(f"filing: post answer with a link on a sole-authored thread did not resolve it: {resolved!r}")

    return problems


def multi_voice_probes(channel: ModuleType, post: ModuleType) -> list[str]:
    """The same three verbs against a thread carrying a second Job's Trailer (solorepo's DR-289).

    The control on `sole_author_probes`: what solorepo's DR-289 holds is that a thread with
    a promotion link may be resolved even by a single voice; a thread with two voices continues
    to behave as solorepo's DR-127 left it, and a failure here says the decision widened past
    its own scope.

    The cases. `promote` files once, replies `Promoted to <url>.` without the
    words `Left open`, and resolves. `post resolve` resolves. `post answer`
    replies without those words and resolves. The second voice carries
    `Actor: gha-2` under the same login, because `sole_author` reads the Trailer
    and on this repository the login never differs (solorepo's DR-068).
    """
    problems = []
    replied_to: list[tuple[str, str]] = []
    resolved: list[str] = []
    filed: list[tuple[str, str | None]] = []
    own_voice_body = "my notice\n\nActor: gha-1\nAgent: probe"
    other_voice_body = "my reply\n\nActor: gha-2\nAgent: probe"

    with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe"),
          stood_in(post, thread_comments=lambda _: [own_voice_body, other_voice_body],
                   reply=lambda t, b: replied_to.append((t, b)),
                   resolve=lambda t: resolved.append(t)),
          stood_in(channel, sibling=lambda _: Filer(filed))):
        said = run_verb(channel, FakeFiling(),
                        lambda: post.promote("t1", TITLE, BODY, "hard"))

    if said:
        problems.append(f"filing: promoting multi-voice thread exited with error: {said!r}")
    if len(filed) != 1:
        problems.append(f"filing: promoting multi-voice thread did not file exactly once: {filed!r}")
    if len(replied_to) != 1 or "Promoted to" not in replied_to[0][1] or "Left open" in replied_to[0][1]:
        problems.append(f"filing: promoting multi-voice thread reply was incorrect: {replied_to!r}")
    if len(resolved) != 1 or resolved[0] != "t1":
        problems.append(f"filing: promoting multi-voice thread did not resolve: {resolved!r}")

    resolved.clear()
    with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe"),
          stood_in(post, thread_nodes=lambda _: [
                       {"body": own_voice_body, "author": {"login": "caindy-solorepo-coder"}},
                       {"body": other_voice_body, "author": {"login": "caindy-solorepo-coder"}}
                   ],
                   resolve=lambda t: resolved.append(t))):
        said = run_verb(channel, FakeFiling(),
                        lambda: post.resolve_verb("t1"))
    if said or len(resolved) != 1:
        problems.append(f"filing: post resolve on multi-voice thread did not succeed as expected: {said!r}, resolved: {resolved!r}")

    replied_to.clear()
    resolved.clear()
    with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe", AI_AGENT="probe"),
          stood_in(post, thread_comments=lambda _: [own_voice_body, other_voice_body],
                   reply=lambda t, b: replied_to.append((t, b)),
                   resolve=lambda t: resolved.append(t))):
        said = run_verb(channel, FakeFiling(),
                        lambda: post.answer("t1", "the point is met."))
    if (said or len(replied_to) != 1 or len(resolved) != 1
            or "Left open" in replied_to[0][1]):
        problems.append(f"filing: post answer on multi-voice thread said {said!r}, replied "
                        f"{replied_to!r} and resolved {resolved!r}")

    return problems


def reviewer_promotion_probes(channel: ModuleType, post: ModuleType) -> list[str]:
    """The approving reviewer promoting a coder-authored notice (solorepo's DR-285).

    `sole_author` is caller-relative: against a thread carrying only the coder's
    Trailer, `promote` run under the reviewer's Actor Trailer finds a second voice
    and resolves the thread in the same pass, without leaving it open for a follow-up
    Job.
    """
    problems = []
    replied_to: list[tuple[str, str]] = []
    resolved: list[str] = []
    filed: list[tuple[str, str | None]] = []
    coder_notice_body = "noticed and not done\n\nActor: gha-1\nAgent: probe"

    with (environment(GITHUB_RUN_ID="2", ACTOR_SESSION="gha-2",
                      ACTOR_AGENT="probe", AI_AGENT="probe"),
          stood_in(post, thread_comments=lambda _: [coder_notice_body],
                   reply=lambda t, b: replied_to.append((t, b)),
                   resolve=lambda t: resolved.append(t)),
          stood_in(channel, sibling=lambda _: Filer(filed))):
        said = run_verb(channel, FakeFiling(),
                        lambda: post.promote("t1", TITLE, BODY, None))

    if said:
        problems.append(f"filing: reviewer promoting coder notice exited with error: {said!r}")
    if len(filed) != 1 or filed != [(TITLE, None)]:
        problems.append("filing: reviewer promoting coder notice did not file unlevelled: "
                        f"{filed!r}")
    if (len(replied_to) != 1 or "Promoted to" not in replied_to[0][1]
            or "Left open" in replied_to[0][1]):
        problems.append("filing: reviewer promoting coder notice reply was incorrect: "
                        f"{replied_to!r}")
    if len(resolved) != 1 or resolved[0] != "t1":
        problems.append("filing: reviewer promoting coder notice did not resolve: "
                        f"{resolved!r}")

    return problems


def promotion_probes(channel: ModuleType, post: ModuleType) -> list[str]:
    """`promote` against a thread that already carries a promotion link, and one that does not
    (solorepo's DR-127); then every verb against one voice and two (solorepo's DR-224); then
    reviewer promotion under solorepo's DR-285.

    The cases on the standing link are below; `sole_author_probes`,
    `multi_voice_probes` and `reviewer_promotion_probes` carry the rest, and each
    states its own.
    """
    problems = []
    filed: list[tuple[str, str | None]] = []

    def promoting(bodies: list[str]) -> tuple[str | None, int]:
        """One `promote` of thread `t1` over a thread holding `bodies`, as `(what it exited with,
        thread reads)`; the exit is `None` where the verb returned.

        `channel.signed` is not stood in and is reached whichever way the verb
        goes, since `promote` composes its reply as an argument and Python
        evaluates that before `reply` is called. It exits where the environment
        does not say who is speaking, which no gate run outside a coder or
        reviewer job does, so the environment is supplied rather than assumed.
        """
        filed.clear()
        reads: list[int] = []
        with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"),
              stood_in(post, thread_comments=lambda _: read_bodies(bodies, reads),
                       reply=lambda *a: None, resolve=lambda *a: None),
              stood_in(channel, sibling=lambda _: Filer(filed))):
            return run_verb(channel, FakeFiling(),
                            lambda: post.promote("t1", TITLE, BODY, "hard")), len(reads)

    said, reads = promoting(["Promoted to https://github.com/o/r/issues/900."])
    if not said or "900" not in said or "post resolve" not in said or filed:
        problems.append(f"filing: promoting a thread that already carries a link said {said!r} "
                        f"and filed {filed!r}")

    said, reads = promoting(["a point nobody promoted yet"])
    if said or len(filed) != 1:
        problems.append(f"filing: promoting an unpromoted thread said {said!r} and filed {filed!r}")
    if reads != 1:
        problems.append(f"filing: one promotion read the thread {reads} time(s)")

    cited = "this is the same shape as https://github.com/caindy/solorepo/issues/440"
    said, _ = promoting([cited])
    if said or len(filed) != 1:
        problems.append(f"filing: promoting a thread that merely cites an Issue said {said!r} "
                        f"and filed {filed!r}")

    filed.clear()
    with (environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"),
          stood_in(post, thread_comments=lambda _: ["a point nobody promoted yet"],
                   reply=lambda *a: None, resolve=lambda *a: None),
          stood_in(channel, sibling=lambda _: Filer(filed))):
        said = run_verb(channel, FakeFiling(), lambda: post.promote("t1", TITLE, BODY, None))
    if said or filed != [(TITLE, None)]:
        problems.append(f"filing: promoting with no level said {said!r} and filed {filed!r}; "
                        "the Issue lands `challenge` alone (solorepo's DR-230)")

    problems += sole_author_probes(channel, post)
    problems += multi_voice_probes(channel, post)
    problems += reviewer_promotion_probes(channel, post)
    return problems


class Filer:
    """`move` as `promote` reaches it: `file_issue` recording its call rather than filing."""

    def __init__(self, filed: list[tuple[str, str | None]]) -> None:
        self.filed = filed

    def file_issue(self, title: str, body: str, level: str | None = None, roadmap: bool = False,
                   blocked_by: list[int] | None = None) -> tuple[str, str]:
        """The call recorded, answered with a number and URL as the real one answers."""
        self.filed.append((title, level))
        return "900", ISSUE_LINK
