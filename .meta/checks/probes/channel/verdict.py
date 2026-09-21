"""`post review`, `post raise`, and `post notice` against the head the run read, and the head GitHub holds (solorepo's #566, solorepo's #572).
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
    """As much of GitHub as `post review`, `raise`, and `notice` ask about: head, reviews, and threads.

    `head` is what `pr view --json headRefOid` answers, which is GitHub's
    answer at the moment of posting and so the value the run's own head is
    compared against. `posted` collects the verdict flag of every `pr review`
    that went through, and `comments` collects thread comment parameters.
    `reads` counts the head reads, verifying unpinned runs read only as needed
    and pinned runs avoid redundant fetches.

    A call this fake has no answer for raises `AssertionError` naming it, which
    `outcome` reports as text.
    """

    def __init__(self, head: str) -> None:
        self.head, self.reads = head, 0
        self.posted: list[str] = []
        self.comments: list[dict[str, str]] = []

    def __call__(self, *args: str, parse: bool = True, **kwargs: object) -> object:
        """One `gh` call: the pull request's head, a verdict posted, or the reviews/threads read back."""
        if args[:2] == ("pr", "view") and "headRefOid" in args:
            self.reads += 1
            return self.head
        if args[:2] == ("pr", "view") and "reviews" in args:
            return {"reviews": [{"state": "APPROVED"} for _ in self.posted]}
        if args[:2] == ("pr", "review"):
            self.posted.append(args[3])
            return ""
        if args[:2] == ("repo", "view") and "nameWithOwner" in args:
            return {"nameWithOwner": "caindy/solorepo"}
        if args[:2] == ("repo", "view") and "owner" in args:
            return {"owner": {"login": "solo"}}
        if args[:2] == ("api", "repos/caindy/solorepo/pulls/7/comments"):
            parsed: dict[str, str] = {}
            for i in range(2, len(args), 2):
                val = args[i + 1]
                if "=" in val:
                    k, v = val.split("=", 1)
                    parsed[k] = v
            self.comments.append(parsed)
            return {"html_url": f"https://github.com/caindy/solorepo/pull/7#discussion_r{len(self.comments)}"}
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")


@check("verdict probes", pre=True)
def verdict_probes() -> list[str]:
    """`post review`, `post raise`, and `post notice` against the head the run read and GitHub holds.

    GitHub records reviews and review comments against remote head state, so
    currency defects are visible in the divergence between `SOLOREPO_REVIEW_HEAD`
    and remote `headRefOid`. The environment variable represents the pinned head
    the run evaluated, while `FakeVerdict` simulates remote repository state.

    Cases verified:
    - Moved head under a run: review verdicts, raise threads, and notices refuse, posting nothing.
    - Currency holding under a run: verdicts and threads post with exactly one head check.
    - Unpinned session (no head set): verdicts skip head reads; threads read head once and post.
    """
    channel, _, programs = load_channel()
    post = programs["post"]
    problems = []

    def reviewed(head: str, pinned: str | None) -> tuple[str | None, "FakeVerdict"]:
        """One `--approve` of pull request 7 with GitHub at `head` and the run pinned to `pinned`."""
        fake = FakeVerdict(head)
        with (environment(SOLOREPO_REVIEW_HEAD=pinned, GITHUB_RUN_ID="1",
                          ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"),
              stood_in(channel, piped=lambda timeout=0.5: "what was checked, and what was found")):
            return run_verb(channel, fake, lambda: post.review("7", "approve")), fake

    def raised(head: str, pinned: str | None) -> tuple[str | None, "FakeVerdict"]:
        """One thread raised on pull request 7 with GitHub at `head` and the run pinned to `pinned`."""
        fake = FakeVerdict(head)
        with environment(SOLOREPO_REVIEW_HEAD=pinned, GITHUB_RUN_ID="1",
                         ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"):
            return run_verb(channel, fake, lambda: post.raise_verb("7", "file.py", 10, "finding")), fake

    def noticed(head: str, pinned: str | None) -> tuple[str | None, "FakeVerdict"]:
        """One notice thread on pull request 7 with GitHub at `head` and the run pinned to `pinned`."""
        fake = FakeVerdict(head)
        with environment(SOLOREPO_REVIEW_HEAD=pinned, GITHUB_RUN_ID="1",
                         ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"):
            return run_verb(channel, fake, lambda: post.notice("7", "file.py", 10, "noticed")), fake

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

    said, fake = raised(PUSHED, READ)
    if not said or READ not in said or PUSHED not in said or fake.comments:
        problems.append(f"raise: a run whose head moved was told {said!r} and posted {fake.comments!r}")

    said, fake = raised(READ, READ)
    if said or len(fake.comments) != 1 or fake.comments[0].get("commit_id") != READ or fake.reads != 1:
        problems.append(f"raise: a run whose head is unchanged said {said!r}, posted {fake.comments!r}, reads {fake.reads}")

    said, fake = raised(PUSHED, None)
    if said or len(fake.comments) != 1 or fake.comments[0].get("commit_id") != PUSHED or fake.reads != 1:
        problems.append(f"raise: a session with no head pinned said {said!r}, posted {fake.comments!r}, reads {fake.reads}")

    said, fake = noticed(PUSHED, READ)
    if not said or READ not in said or PUSHED not in said or fake.comments:
        problems.append(f"notice: a run whose head moved was told {said!r} and posted {fake.comments!r}")

    return problems
