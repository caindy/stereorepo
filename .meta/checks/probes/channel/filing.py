"""`file_issue` and `promote` refusing a second Issue for one Challenge (solorepo's DR-221).
"""


from typing import Any

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
    different title is not refused by a listing holding the first, which is what
    says the comparison is the whole title and not a resemblance. A listing
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

    with environment(ACTOR_SESSION=None):
        fake = FakeFiling()
        said = run_verb(channel, fake, lambda: move.file_issue(TITLE, BODY, level="hard"))
        if said or len(fake.created) != 1:
            problems.append(f"filing: a first filing said {said!r} and created {len(fake.created)}")

        said = run_verb(channel, fake, lambda: move.file_issue(TITLE, BODY, level="hard"))
        if not said or "900" not in said or "post answer" not in said or len(fake.created) != 1:
            problems.append(f"filing: a second filing under one title said {said!r} and left "
                            f"{len(fake.created)} created")

        said = run_verb(channel, fake, lambda: move.file_issue(TITLE + " again", BODY, level="hard"))
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

    problems += promotion_probes(channel, post)
    return problems


def promotion_probes(channel: Any, post: Any) -> list[str]:
    """`promote` against a thread that already carries a promotion link, and one that does not."""
    problems: list[str] = []
    filed: list[tuple[str, str | None]] = []

    def promoting(bodies: list[str]) -> tuple[str | None, int]:
        """One `promote` of thread `t1` over a thread holding `bodies`, as `(what it exited with, thread reads)`.

        `channel.signed` is not stood in and is reached whichever way the verb
        goes, since `promote` composes its reply as an argument and Python
        evaluates that before `reply` is called. It exits where the environment
        does not say who is speaking, which no gate run outside a coder or
        reviewer job does, so the environment is supplied rather than assumed.
        """
        filed.clear()
        reads: list[int] = []

        def read(_: str) -> list[str]:
            reads.append(1)
            return list(bodies)

        with (environment(ACTOR_SESSION="gha-1", AI_AGENT="probe"),
              stood_in(post, thread_comments=read,
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
    with (environment(ACTOR_SESSION="gha-1", AI_AGENT="probe"),
          stood_in(post, thread_comments=lambda _: ["a point nobody promoted yet"],
                   reply=lambda *a: None, resolve=lambda *a: None),
          stood_in(channel, sibling=lambda _: Filer(filed))):
        said = run_verb(channel, FakeFiling(), lambda: post.promote("t1", TITLE, BODY, None))
    if said or filed != [(TITLE, None)]:
        problems.append(f"filing: promoting with no level said {said!r} and filed {filed!r}; "
                        "the Issue lands `challenge` alone (solorepo's DR-230)")
    return problems


class Filer:
    """`move` as `promote` reaches it: `file_issue` recording its call rather than filing."""

    def __init__(self, filed: list[tuple[str, str | None]]) -> None:
        self.filed = filed

    def file_issue(self, title: str, body: str, level: str | None = None,
                   roadmap: bool = False) -> tuple[str, str]:
        """The call recorded, answered with a number and URL as the real one answers."""
        self.filed.append((title, level))
        return "900", "https://github.com/o/r/issues/900"
