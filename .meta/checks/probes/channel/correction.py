"""`post correct`, and the refusal that stops a comment landing malformed (solorepo's DR-286).

The defect is a sentence that cannot be reached: `audit_comment_trailers` reds
the form gate for the life of a pull request on a comment carrying a Trailer
typed into its text, and until this verb no act of any Role could change one.
So the two halves are probed against each other — what the channel now refuses
to post, and what it can correct where something was posted anyway — and the
audit is run over both, since a refusal that admits a body the audit reds would
leave the gap open under a new verb.

One module for one probe, so a history log's Evidence names the file holding it
(solorepo's DR-209).
"""
import functools
import subprocess
import sys
from typing import Any

from checks.collect import META, check
from checks.probes.harness import (
    environment,
    exit_of,
    load_channel,
    load_module,
    stood_in,
    unanswered,
)

REPO = "o/r"
"""The repository every call here is made against, under no name a citation check
reads (solorepo's DR-124)."""

CODER = "who-the-credential-is"
"""The login `gh api user` answers, and the author of every comment this channel may correct.

Deliberately not `<owner>-<repo>-<role>`, which is the shape
`channel.role_login()` composes. The account bound is read off the credential
rather than off the Role name the credential was picked by
(solorepo's DR-286), and the two readings diverge in production only when the
credential and the `--role` name disagree — which is the case the bound exists
to catch. A login of the Role-derived shape would make them the same string
here, and a `correct` that asked `role_login("coder")` instead would pass every
case in this module.
"""

REVIEWER = "who-the-other-credential-is"
"""A second account, whose comments this channel may not correct."""

CONVERSATION_ID = "5736004158"
THREAD_ID = "2345678901"
"""The two comments GitHub holds: one on the conversation, one on the diff."""

CONVERSATION_URL = f"https://github.com/{REPO}/pull/996#issuecomment-{CONVERSATION_ID}"
THREAD_URL = f"https://github.com/{REPO}/pull/996#discussion_r{THREAD_ID}"

MINE = "Actor: gha-1\nAgent: probe"
"""The Trailer `channel.trailers()` composes under this module's environment."""

WORDS = "the words that replace it"
"""What a correction replaces a body with, in every case that is not a withdrawal."""

DOUBLED = ("**Noticed and not done.** @solo\n\nthe item\n\nActor: recorded by the channel\n\n"
           "**Noticed and not done.** @solo\n\nthe item")
"""The shape solorepo's #996 carried: a body doubled with a Trailer typed into its running text."""

MARKED = "**Noticed and not done.** @solo\n\nthe item"
"""A body carrying `notice`'s own marker and no Trailer, which only `notice` refuses."""


class FakeComments:
    """GitHub answering the REST calls `correct` makes, and recording the writes.

    Attributes:
        held: Each comment GitHub holds, by collection and identifier.
        patched: One entry per body replaced, as `(collection, id, body)`.
        deleted: One entry per comment deleted, as `(collection, id)`.
    """

    def __init__(self, held: dict[tuple[str, str], str]) -> None:
        self.held = held
        self.patched: list[tuple[str, str, str]] = []
        self.deleted: list[tuple[str, str]] = []

    def gh(self, *args: Any, **keywords: Any) -> Any:
        """The call answered as GitHub answers it, its write recorded.

        Raises:
            AssertionError: For a call this fake does not model, named in the
                message so the report says what it was asked.
            subprocess.CalledProcessError: For a read of a comment GitHub does
                not hold, which is what `named_comment` tolerates while it asks
                the other collection.
        """
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": REPO}
        if args[:2] == ("api", "user"):
            return CODER
        if args[0] == "api":
            at = str(args[1]).split("/")
            collection, number = "/".join(at[-3:-1]), at[-1]
            method = args[args.index("-X") + 1] if "-X" in args else "GET"
            if method == "GET":
                author = self.held.get((collection, number))
                if author is None:
                    raise subprocess.CalledProcessError(1, "gh")
                return {"id": int(number), "user": {"login": author},
                        "html_url": f"https://github.com/{REPO}/pull/996#c{number}"}
            if method == "PATCH":
                body = next(a for a in args if str(a).startswith("body="))
                self.patched.append((collection, number, str(body)[len("body="):]))
                return ""
            if method == "DELETE":
                self.deleted.append((collection, number))
                return ""
        raise unanswered(args, "GitHub")


@check("correction probes", pre=True)
def correction_probes() -> list[str]:
    """`post correct` over what it may reach, and the refusal that widened to the whole body.

    A comment is named by the URL the verb that posted it printed, whose
    fragment says which collection holds it, or by its identifier alone, which
    says only the number and so asks both. The account is the bound: GitHub
    would let a repository token delete what another account said, so the
    refusal is the verb's rather than GitHub's, and it is read off `gh api user`
    rather than off the Role name the credential was picked by.

    The refusal is the other half, and it is the one that stops the defect
    recurring. `signed` already declined a Trailer at the tail of a body
    (solorepo's DR-260); a Trailer typed into running text is what the audit
    reds and what nothing declined, which is how the comment on solorepo's #996
    came to stand. Fenced code and block quotes stay exempt, since the audit
    exempts them, and a body already ending in this run's own block is still
    signed a second time, since `signed` is idempotent and a caller that
    re-signs is not typing a Trailer.
    """
    channel, _, programs = load_channel()
    post = programs["post"]
    check_pr = load_module(META / "check_pr.py", "check_pr")
    with environment(GITHUB_RUN_ID="1", ACTOR_SESSION="gha-1", ACTOR_AGENT="probe"):
        return (reach_probes(channel, post) + refusal_probes(post)
                + wiring_probes(channel, post)
                + audit_probes(channel, post, check_pr))


def corrections(channel: Any, post: Any, held: dict[tuple[str, str], str],
                reference: str, text: str | None) -> tuple[str | None, FakeComments]:
    """One `correct` run against a fake GitHub: what it came to, and the fake to read afterwards."""
    fake = FakeComments(held)
    with stood_in(channel, gh=fake.gh):
        return exit_of(lambda: post.correct(reference, text)), fake


def reach_probes(channel: Any, post: Any) -> list[str]:
    """What `correct` reaches, and what it refuses to reach.

    The conversation and the diff are separate collections under one numbering
    space nothing joins, so a reference that names neither is asked of both and
    the first that holds it answers. A comment neither holds is a refusal and
    not a silent success, since a correction that changed nothing would leave
    the gate red with nothing said about it.

    A withdrawal is the one act of the channel that leaves no Trailer behind, so
    it is asked for one before it deletes: a run whose environment names no
    speaker is refused here as it is on every other act (solorepo's Article 19,
    solorepo's DR-233). The correction path is attested by `channel.signed`
    already; nothing on the destructive path was.
    """
    problems = []
    both = {("issues/comments", CONVERSATION_ID): CODER,
            ("pulls/comments", THREAD_ID): CODER}

    code, fake = corrections(channel, post, both, CONVERSATION_URL, WORDS)
    if code is not None or [c for c, _, _ in fake.patched] != ["issues/comments"]:
        problems.append(f"correction: a conversation comment named by its URL came to {code!r} "
                        f"and patched {fake.patched}")
    elif not fake.patched[0][2].rstrip().endswith(MINE):
        problems.append("correction: the replacement body does not carry the correcting run's "
                        f"own Trailer: {fake.patched[0][2]!r}")

    code, fake = corrections(channel, post, both, THREAD_URL, WORDS)
    if code is not None or [c for c, _, _ in fake.patched] != ["pulls/comments"]:
        problems.append(f"correction: a diff comment named by its URL came to {code!r} and "
                        f"patched {fake.patched}")

    code, fake = corrections(channel, post, {("pulls/comments", THREAD_ID): CODER},
                             THREAD_ID, WORDS)
    if code is not None or [c for c, _, _ in fake.patched] != ["pulls/comments"]:
        problems.append(f"correction: an identifier alone came to {code!r} and patched "
                        f"{fake.patched}; both collections are asked for one")

    code, fake = corrections(channel, post, both, CONVERSATION_URL, None)
    if code is not None or fake.deleted != [("issues/comments", CONVERSATION_ID)] or fake.patched:
        problems.append(f"correction: a withdrawal came to {code!r}, deleting {fake.deleted} and "
                        f"patching {fake.patched}")

    with environment(GITHUB_RUN_ID=None, ACTOR_SESSION=None,
                     CLAUDE_CODE_SESSION_ID=None, ANTIGRAVITY_CONVERSATION_ID=None,
                     COPILOT_AGENT_SESSION_ID=None):
        code, fake = corrections(channel, post, both, CONVERSATION_URL, None)
    if code is None or "who is speaking" not in code or fake.deleted:
        problems.append(f"correction: a withdrawal by a run the environment does not name came "
                        f"to {code!r}, deleting {fake.deleted}; the destructive verb is the one "
                        "act of the channel the attestation gate must not miss")

    refused = {
        "a comment another account posted":
            (({("issues/comments", CONVERSATION_ID): REVIEWER}, CONVERSATION_URL), REVIEWER),
        "a comment GitHub does not hold": ((both, "999"), "999"),
        "a reference that names no comment":
            ((both, f"https://github.com/{REPO}/pull/996"), "names no comment"),
    }
    for what, ((held, reference), owed) in refused.items():
        code, fake = corrections(channel, post, held, reference, WORDS)
        if code is None or owed not in code:
            problems.append(f"correction: {what} came to {code!r}, and a refusal naming "
                            f"{owed!r} is what it owes")
        elif fake.patched or fake.deleted:
            problems.append(f"correction: {what} was refused and still wrote "
                            f"{fake.patched + fake.deleted}")
    return problems


def refusal_probes(post: Any) -> list[str]:
    """The bodies the channel now declines, and the ones it still takes.

    `corrected_body` is where a withdrawal and a correction are told apart: a
    body beside `--withdraw` would go nowhere, and a correction with no body is
    not a withdrawal by omission.
    """
    problems = []
    readings = {
        "a body that says nothing about Trailers": ("the item", True),
        "a Trailer typed into running text": ("the item\n\nActor: recorded by the channel", False),
        "an Agent line typed into running text": ("the item\n\nAgent: typed", False),
        "a Trailer inside a fenced block": ("the item\n\n```\nActor: gha-9\n```\n", True),
        "a Trailer inside a quote": ("the item\n\n> Actor: gha-9\n", True),
        "a body already carrying this run's own block": (f"the item\n\n{MINE}", True),
        "the shape that stood on solorepo's #996": (DOUBLED, False),
    }
    for what, (body, taken) in readings.items():
        code = exit_of(functools.partial(post.refuse_a_typed_trailer, body))
        if (code is None) is not taken:
            problems.append(f"correction: {what} came to {code!r}, and the channel "
                            f"{'takes' if taken else 'refuses'} it")

    markers = {"a notice body of its own words": ("the item", True),
               "a notice body carrying the marker": (DOUBLED, False)}
    for what, (body, taken) in markers.items():
        code = exit_of(functools.partial(post.refuse_a_typed_marker, body))
        if (code is None) is not taken:
            problems.append(f"correction: {what} came to {code!r}, and `notice` "
                            f"{'takes' if taken else 'refuses'} it")

    arbitrations = {
        "a correction with words": ((False, "the words"), "the words"),
        "a withdrawal with none": ((True, ""), None),
    }
    for what, ((withdraw, said), expected) in arbitrations.items():
        answer = post.corrected_body(withdraw, said)
        if answer != expected:
            problems.append(f"correction: {what} read as {answer!r}, and {expected!r} is what "
                            "the run replaces the comment with")
    for what, (withdraw, said) in {"a withdrawal carrying a body": (True, "the words"),
                                   "a correction carrying none": (False, "")}.items():
        code = exit_of(functools.partial(post.corrected_body, withdraw, said))
        if code is None:
            problems.append(f"correction: {what} was taken, and it is refused")
    return problems


def watching() -> tuple[list[Any], Any]:
    """A stand-in for `channel.gh` that records each call and refuses it, beside its record."""
    asked: list[Any] = []

    def watched(*args: Any, **keywords: Any) -> Any:
        """The call recorded, then refused: a verb that reached GitHub has already failed."""
        asked.append(args)
        raise unanswered(args, "GitHub")

    return asked, watched


def piping(body: str) -> Any:
    """A stand-in for `channel.stdin_body` and `channel.piped`, answering `body` to either."""
    return lambda: body


def wiring_probes(channel: Any, post: Any) -> list[str]:
    """Every verb of `post` run over a body that types a Trailer, the refusal being a wiring claim.

    Solorepo's DR-286's fourth consequence — every body `post` takes on stdin is
    read before it is signed — is a claim about where the refusal is called from, and
    `refusal_probes` above drives the function rather than any of its call
    sites. Left there, each site is free to be dropped: `main`'s own back to
    `channel.signed(channel.stdin_body())` restores the shape that stood on
    solorepo's #996, and `corrected_body`'s lets `correct` itself PATCH a
    comment into it, both with every probe in the tree green.

    So each verb is driven from its own argument vector, and each is owed a
    refusal that reached GitHub with nothing at all. `channel.gh` is stood in by
    a call recorder, and `SOLOREPO_REVIEW_HEAD` is left unset so that
    `refuse_if_head_moved` answers without asking GitHub and "nothing at all" is
    the whole assertion on every case. `notice` is driven twice, once for each
    of the two refusals in front of it.
    """
    problems = []
    typed = "the item\n\nActor: recorded by the channel\n\nand prose after it"
    driven = {
        "comment": (["post", "comment", "1005"], typed, "types a Trailer"),
        "reply": (["post", "reply", "PRRT_1"], typed, "types a Trailer"),
        "promote": (["post", "promote", "PRRT_1", "--title", "a title"], typed,
                    "types a Trailer"),
        "raise": (["post", "raise", "1005", "a/path", "7"], typed, "types a Trailer"),
        "notice": (["post", "notice", "1005", "a/path", "7"], typed, "types a Trailer"),
        "notice over the marker": (["post", "notice", "1005", "a/path", "7"], MARKED,
                                   "already carries"),
        "answer": (["post", "answer", "PRRT_1"], typed, "types a Trailer"),
        "review": (["post", "review", "1005", "--request-changes"], typed, "types a Trailer"),
        "correct": (["post", "correct", CONVERSATION_ID], typed, "types a Trailer"),
    }
    for verb, (argv, body, owed) in driven.items():
        asked, watched = watching()
        code = None
        try:
            with environment(SOLOREPO_REVIEW_HEAD=None), stood_in(sys, argv=argv), \
                    stood_in(channel, gh=watched, stdin_body=piping(body), piped=piping(body)):
                code = exit_of(post.main)
        except AssertionError:
            pass
        if asked:
            problems.append(f"correction: `post {verb}` asked GitHub {asked} over a body the "
                            "channel refuses, so the refusal is not in front of the call")
        elif code is None or owed not in code:
            problems.append(f"correction: `post {verb}` came to {code!r}, and a refusal naming "
                            f"{owed!r} is what the body it was piped owes")
    return problems


def audit_probes(channel: Any, post: Any, check_pr: Any) -> list[str]:
    """The refusal read against the audit it exists to keep green.

    A body the channel takes must, once signed, pass `audit_comment_trailers`;
    the body it refuses must be one the audit reds. Anything else is a channel
    and a gate disagreeing about the same comment, which is the disagreement
    solorepo's DR-260 closed at the tail of a body and this closes in the middle
    of one.
    """
    problems = []
    for what, body in {"a plain body": "the item",
                       "a fenced Trailer": "the item\n\n```\nActor: gha-9\n```\n"}.items():
        signed = channel.signed(post.refuse_a_typed_trailer(body))
        found = check_pr.review.audit_comment_trailers(
            [{"author": {"login": CODER}, "body": signed}], {CODER})
        if found:
            problems.append(f"correction: the channel takes {what} and the audit reds it: {found}")
    red = check_pr.review.audit_comment_trailers(
        [{"author": {"login": CODER}, "body": f"{DOUBLED}\n\n{MINE}"}], {CODER})
    if not red:
        problems.append("correction: the audit reads the shape that stood on "
                        "solorepo's #996 as sound, so the refusal guards nothing")
    return problems
