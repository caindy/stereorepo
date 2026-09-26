"""The mint of a Concept: refused to a run whose Challenge does not ask, reserved by a session
or by a run whose Challenge asks by identifier, and reserved once (solorepo's DR-276,
solorepo's DR-282).
"""


from typing import Any

from checks.collect import check
from checks.probes.harness import environment, load_channel, run_verb, stood_in

ASKING = "**What was noticed.** The loop needs a word for it.\n\n**Mint.** `work:concept/door`\n"
"""A Challenge body that asks for the Concept in the form `ASKS` reads."""

SILENT = "**What was noticed.** The loop needs a word for it, and this body names none."
"""A Challenge body that asks for no Concept."""

MENTIONING = ("**What was noticed.** Do not mint `work:concept/door`; the record rejected it "
              "(solorepo's DR-282 says to write **Mint.** and the identifier to ask).")
"""A Challenge body that mentions the identifier in prose and asks for nothing."""

LONGER = "**What was noticed.** The loop needs a word.\n\n**Mint.** `work:concept/door-frame`\n"
"""A Challenge body asking for a longer word, which the shorter one prefixes."""

ISSUE = "7"
"""The Challenge a run's loop branch names in the cases below."""

UNMODELLED = "the mint asked the fake for {args!r}"
"""What the fake raises on a call no case models, so the step reports what was asked."""

RUN = "gha-1234"
"""An `ACTOR_SESSION` carrying the mark a workflow writes and nothing else
does, which is what `channel.in_a_run()` reads (solorepo's DR-148)."""

SLUGS = (("work:concept/door", "door"), ("work:concept/seed-commit", "seed-commit"),
         ("ddd:concept/bounded-context", "bounded-context"), ("Seed Commit", ""),
         ("work:decision/276", ""), ("  ", ""))
"""Each argument put to `slug`, and the reservation it must reduce to: the
identifier's tail, and nothing at all for anything that is not one."""

TAKEN = "say: gh: Reference already exists (HTTP 422)"
"""What `channel.gh` exits with where the ref is written between the read and
the write, which is the race two sessions minting one word produce."""


class FakeGitHub:
    """`channel.gh` stood in for the two reads and three writes a mint makes.

    Records every call, so a case can say what was asked as well as what was
    answered: the refusal's own evidence is that GitHub was never reached.

    Attributes:
        calls: Every call's positional arguments, in order.
        reserved: The Concept slugs the remote already holds a tag for.
        silent: Whether the reservation read answers the caller's fallback,
            which is what a rate limit or a transient failure looks like.
        taken: Whether the ref write is refused because the ref exists.
    """

    def __init__(self, reserved: tuple[str, ...] = (), silent: bool = False,
                 taken: bool = False, body: str = "") -> None:
        self.calls: list[tuple[str, ...]] = []
        self.reserved = reserved
        self.silent = silent
        self.taken = taken
        self.body = body

    def __call__(self, *args: str, **kwargs: Any) -> Any:
        """What the fake answers one call with, raising `AssertionError` on a
        call it does not model."""
        self.calls.append(args)
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "caindy/solorepo"}
        if args[:2] == ("issue", "view"):
            return {"body": self.body}
        where = args[1] if len(args) > 1 else ""
        if "matching-refs/tags/" in where:
            if self.silent:
                return kwargs.get("default")
            name = where.rsplit("matching-refs/tags/", 1)[1]
            held = name.rsplit("/", 1)[-1] in self.reserved
            return [{"ref": f"refs/tags/{name}"}] if held else []
        if where.endswith("/commits/main"):
            return "f" * 40
        if where.endswith("/git/tags"):
            return {"sha": "a" * 40}
        if where.endswith("/git/refs"):
            if self.taken:
                raise SystemExit(TAKEN)
            return ""
        if "/git/ref/tags/" in where:
            return {"object": {"sha": "a" * 40}}
        raise AssertionError(UNMODELLED.format(args=args))

    def wrote(self, fragment: str) -> list[tuple[str, ...]]:
        """Every recorded call carrying `fragment` in one of its arguments."""
        return [call for call in self.calls if any(fragment in arg for arg in call)]


@check("mint probes", pre=True)
def mint_probes() -> list[str]:
    """`move mint --concept` refuses a run whose Challenge does not ask, reserves a Concept for a
    session or for a run whose Challenge asks by identifier, and reserves one once
    (solorepo's DR-276, solorepo's DR-282).

    A Concept is the solo's word, and a run is not beside him — the same line
    `move claim` and `move difficulty` draw on `channel.in_a_run()`
    (solorepo's DR-148, solorepo's DR-235) — unless the Challenge the run's
    branch names asks for the word by its identifier, which is where the solo
    asks a loop for one (solorepo's DR-282). The run boundary is a branch on
    the environment, so `ACTOR_SESSION` and `GITHUB_RUN_ID` are set and unset
    around each case rather than stood in for, as `probes/channel/level.py`
    does of the same mark, and the branch is stood in.

    What the refusal is observed by is that the fake was never called: a mint
    refused after the tag object exists has reserved the word anyway. The
    session's case is observed by the ref that was written, since the tag
    object alone is unreachable and reserves nothing, and a Concept already
    reserved is observed by no tag object being asked for at all — or, where
    the read could not be made and the write is refused, by the reservation
    being reported rather than the verb dying on the 422.
    """
    channel, _, programs = load_channel()
    concepts = programs["move"].concepts
    problems: list[str] = []

    for ident, expected in SLUGS:
        if concepts.slug(ident) != expected:
            problems.append(f"mint: `{ident}` reduced to {concepts.slug(ident)!r}, "
                            f"not {expected!r}")

    fake = FakeGitHub()
    with environment(GITHUB_RUN_ID=RUN.removeprefix("gha-"), ACTOR_SESSION=RUN), \
            stood_in(concepts, branch=lambda: "claude/routing-policy"):
        said = run_verb(channel, fake, lambda: concepts.mint_concept("work:concept/door"))
    if not said or "names no Challenge" not in said or fake.calls:
        problems.append(f"mint: a run on a branch naming no Challenge was told {said!r} and "
                        f"made {fake.calls!r}")

    for body, name in ((SILENT, "asks for no Concept"), (MENTIONING, "mentions the identifier "
                       "in prose"), (LONGER, "asks for a word this one prefixes")):
        fake = FakeGitHub(body=body)
        with environment(GITHUB_RUN_ID=RUN.removeprefix("gha-"), ACTOR_SESSION=RUN), \
                stood_in(concepts, branch=lambda: f"claude/issue-{ISSUE}"):
            said = run_verb(channel, fake, lambda: concepts.mint_concept("work:concept/door"))
        if not said or f"#{ISSUE}'s body has no such line" not in said \
                or fake.wrote("git/tags"):
            problems.append(f"mint: a run whose Challenge {name} was told {said!r} and "
                            f"made {fake.calls!r}, where only a `**Mint.**` line asks")

    fake = FakeGitHub()
    with environment(GITHUB_RUN_ID=RUN.removeprefix("gha-"), ACTOR_SESSION=RUN), \
            stood_in(concepts, branch=lambda: f"claude/issue-{ISSUE}"):
        said = run_verb(channel, fake, lambda: concepts.mint_concept("Door"))
    if not said or "not a Concept identifier" not in said or fake.calls:
        problems.append(f"mint: a run minting a malformed identifier was told {said!r}, where "
                        "the refusal names the malformation before any Challenge is read")

    fake = FakeGitHub(body=ASKING)
    with environment(GITHUB_RUN_ID=RUN.removeprefix("gha-"), ACTOR_SESSION=RUN), \
            stood_in(concepts, branch=lambda: f"agy/issue-{ISSUE}"):
        said = run_verb(channel, fake, lambda: concepts.mint_concept("work:concept/door"))
    if said or not fake.wrote("ref=refs/tags/concept/door") \
            or not fake.wrote(f"Challenge #{ISSUE} asked for this Concept"):
        problems.append(f"mint: a run whose Challenge asks for the Concept said {said!r} and "
                        f"wrote {fake.calls!r}, where the Challenge's say-so is the solo's and "
                        "the tag's message names the Challenge (solorepo's DR-282)")

    fake = FakeGitHub()
    with environment(GITHUB_RUN_ID=None, ACTOR_SESSION=None):
        said = run_verb(channel, fake, lambda: concepts.mint_concept("work:concept/seed-commit"))
    if said or not fake.wrote("ref=refs/tags/concept/seed-commit") \
            or not fake.wrote("The solo minted this Concept"):
        problems.append(f"mint: a session minting a Concept said {said!r} "
                        f"and wrote {fake.calls!r}, where the tag's message names the solo")

    fake = FakeGitHub(reserved=("door",))
    with environment(GITHUB_RUN_ID=None, ACTOR_SESSION=None):
        said = run_verb(channel, fake, lambda: concepts.mint_concept("work:concept/door"))
    if said or fake.wrote("git/tags"):
        problems.append(f"mint: a Concept reserved already was minted again, saying {said!r} "
                        f"and writing {fake.calls!r}")

    fake = FakeGitHub(silent=True, taken=True)
    with environment(GITHUB_RUN_ID=None, ACTOR_SESSION=None):
        said = run_verb(channel, fake, lambda: concepts.mint_concept("work:concept/door"))
    if said:
        problems.append(f"mint: a reservation the remote would not report and the write refused "
                        f"was answered with {said!r}, not the reservation that is there")

    fake = FakeGitHub()
    with environment(GITHUB_RUN_ID=None, ACTOR_SESSION=None):
        said = run_verb(channel, fake, lambda: concepts.mint_concept(""))
    if not said or "not a Concept identifier" not in said or fake.calls:
        problems.append(f"mint: an argument naming no Concept was told {said!r} and "
                        f"made {fake.calls!r}")
    return problems
