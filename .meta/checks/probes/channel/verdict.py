"""`post review` against the head the run read, and the head GitHub holds (solorepo's #566).
"""


from checks.collect import check
from checks.probes.harness import (
    environment,
    load_channel,
    run_verb,
    stood_in,
)

READ = "7f7179344444444444444444444444444444444"
"""The head a run read, standing in for the commit `review.yml` pinned it to."""

PUSHED = "b30d836aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
"""The head a push left on the pull request while that run was still going."""


class FakeVerdict:
    """As much of GitHub as `post review` asks about: the pull request's head, the review it posts, and the reviews it reads back.

    `head` is what `pr view --json headRefOid` answers, which is GitHub's
    answer at the moment of posting and so the value the run's own head is
    compared against. `posted` collects the verdict flag of every `pr review`
    that went through, so a case can read whether anything was filed rather
    than infer it from a refusal's text. `reads` counts the head reads, which
    is the only way from here to see that an unpinned run asks GitHub nothing.

    A call this fake has no answer for raises `AssertionError` naming it, which
    `outcome` reports as text.
    """

    def __init__(self, head: str) -> None:
        self.head, self.reads = head, 0
        self.posted: list[str] = []

    def __call__(self, *args: str, parse: bool = True, **kwargs: object) -> object:
        """One `gh` call: the pull request's head, a verdict posted, or the reviews read back."""
        if args[:2] == ("pr", "view") and "headRefOid" in args:
            self.reads += 1
            return self.head
        if args[:2] == ("pr", "view") and "reviews" in args:
            return {"reviews": [{"state": "APPROVED"} for _ in self.posted]}
        if args[:2] == ("pr", "review"):
            self.posted.append(args[3])
            return ""
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")


@check("verdict probes", pre=True)
def verdict_probes() -> list[str]:
    """`post review` against the head the run read, and the head GitHub holds (solorepo's #566).

    GitHub records a review against whatever the pull request's head is when
    the review lands, so the defect is invisible in the verb and visible only
    in the two values it holds at once. So `SOLOREPO_REVIEW_HEAD` is set and
    unset around each case rather than stood in for — the variable is the fact
    — and the head GitHub reports is stood in for by `FakeVerdict`.

    The cases. A head that moved under the run posts nothing, and the refusal
    names both commits, since a session told only that it may not post cannot
    say which reading is stale. A head that agrees posts as before, with the
    verdict recorded. And a verdict from a session, which nothing pinned a head
    for, posts without asking GitHub for one at all — the environment variable
    is what says a run is being held to a head, and a laptop review would
    otherwise be refused for a value no laptop sets.

    A refusal's text is read, not just its presence: `run_verb` reports an
    exception as text rather than raising it, so a truthy answer alone cannot
    tell the refusal from the fake being asked something it has no answer for.
    """
    channel, _, programs = load_channel()
    post = programs["post"]
    problems = []

    def reviewed(head: str, pinned: str | None) -> tuple[str | None, "FakeVerdict"]:
        """One `--approve` of pull request 7 with GitHub at `head` and the run pinned to `pinned`, as `(what it exited with, the fake)`."""
        fake = FakeVerdict(head)
        with (environment(SOLOREPO_REVIEW_HEAD=pinned, ACTOR_SESSION="gha-1", AI_AGENT="probe"),
              stood_in(channel, piped=lambda timeout=0.5: "what was checked, and what was found")):
            return run_verb(channel, fake, lambda: post.review("7", "approve")), fake

    said, fake = reviewed(PUSHED, READ)
    if not said or READ not in said or PUSHED not in said or fake.posted:
        problems.append(f"verdict: a run whose head moved was told {said!r} and posted {fake.posted!r}")

    said, fake = reviewed(READ, READ)
    if said or fake.posted != ["--approve"]:
        problems.append(f"verdict: a run whose head is unchanged said {said!r} and posted {fake.posted!r}")

    said, fake = reviewed(PUSHED, None)
    if said or fake.posted != ["--approve"] or fake.reads:
        problems.append(f"verdict: a session with no head pinned said {said!r}, posted "
                        f"{fake.posted!r} and read the head {fake.reads} time(s)")
    return problems
