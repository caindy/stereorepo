"""Correcting what the channel already said: the reach into a posted comment (solorepo's DR-286).

`audit_comment_trailers` reds the form gate for the life of a pull request on a
comment whose Trailer is doubled, missing or not last, and no verb of the
channel could change one. `correct` replaces the body of a comment this account
posted, or withdraws it. The refusals beside it are what make that verb rare:
the channel declines a body typing a Trailer of its own, which is what the audit
reds and what `signed` saw only at the tail of a body (solorepo's DR-260), and
declines a notice body that already carries the marker `notice` supplies.
"""
import json
import re
import subprocess
import sys
from typing import Any

import channel
import check_pr

NOTICED = "**Noticed and not done.**"


def refuse_a_typed_trailer(text: str) -> str:
    """Refuses a body carrying an `Actor:` or `Agent:` line in its own text (solorepo's DR-286).

    The channel composes the Trailer from what the run attests and appends it
    itself, so a line typed into the body lands beside the one it signs with and
    is what the form gate's trailer audit reds. Fenced code and block quotes are
    exempt, as they are in the audit.

    Parameters:
        text: The body as the caller wrote it, before signing. A tail that is
            already this run's own block is what `signed` accepts a second time,
            so it is set aside rather than read as a line typed in.

    Returns:
        str: The body with that tail taken off, where it carries no such line.
            The block comes off rather than riding through, because `answer`
            splices prose behind the caller's words before signing, and a block
            left in the middle of the body is the doubled Trailer this refusal
            exists to stop. `signed` puts one back wherever the words end up.

    Raises:
        SystemExit: If the body types a Trailer into its running text.
    """
    written = text.rstrip("\n")
    block = channel.trailers()
    if written.endswith(block):
        written = written[: -len(block)]
    actors, agents = check_pr.typed_trailers(written)
    typed = [f"Actor: {name}" for name in actors] + [f"Agent: {name}" for name in agents]
    if typed:
        sys.exit("say: refusing — this body types a Trailer into its own text "
                 f"({', '.join(typed)}). "
                 "The channel composes the Trailer from what the run attests and appends it "
                 "itself (solorepo's DR-069, solorepo's DR-233), so the comment would carry two "
                 "and red the form gate's trailer audit for the life of the pull request "
                 "(solorepo's DR-260).\n"
                 "     Nothing was posted. Drop the line, or fence it or quote it, where the "
                 "audit reads it as the words it is.")
    return written


def refuse_a_typed_marker(text: str) -> str:
    """Refuses a notice body already carrying the marker `notice` supplies (solorepo's A15).

    Parameters:
        text: The body as the caller wrote it, before the marker and the mention.

    Returns:
        str: The same body, where it carries no marker.

    Raises:
        SystemExit: If the body already carries the marker.
    """
    if check_pr.NOTICED.search(text):
        sys.exit(f"say: refusing — this body already carries {NOTICED}, which is `notice`'s to "
                 "supply along with the mention. A second marker is what a body doubled back on "
                 "itself looks like to a reader.\n"
                 "     Nothing was posted. Pipe in the words alone.")
    return text


CONVERSATION = "issues/comments"
"""The REST collection holding a comment on a pull request's or an Issue's conversation."""

ON_THE_DIFF = "pulls/comments"
"""The REST collection holding a comment on a line of the diff, thread or reply alike."""

REFERENCE = re.compile(r"(?:#issuecomment-(\d+)|#discussion_r(\d+)|^(\d+))$")
"""A comment named as GitHub links it, or by its identifier alone.

The fragment says which collection holds it, which is what the verbs print when
they post; an identifier alone says only the number, and both collections are
asked for it.
"""


def named_comment(reference: str) -> tuple[str, dict[str, Any]]:
    """Reads the comment a reference names, from whichever collection holds it.

    Parameters:
        reference: The comment's URL, or its identifier alone.

    Returns:
        tuple[str, dict[str, Any]]: The REST collection it was found in, and
            GitHub's payload for it.

    Raises:
        SystemExit: If the reference names no comment, or no collection holds one
            by that identifier.
    """
    found = REFERENCE.search(reference.strip())
    if not found:
        sys.exit(f"say: {reference!r} names no comment. A comment is named by the URL the verb "
                 "that posted it printed — one ending `#issuecomment-<id>` or "
                 "`#discussion_r<id>` — or by that identifier alone.")
    conversation, on_the_diff, bare = found.groups()
    number = conversation or on_the_diff or bare
    if conversation:
        collections: tuple[str, ...] = (CONVERSATION,)
    elif on_the_diff:
        collections = (ON_THE_DIFF,)
    else:
        collections = (CONVERSATION, ON_THE_DIFF)
    for collection in collections:
        try:
            held = channel.gh("api", f"repos/{channel.repo()}/{collection}/{number}",
                              tolerate_fail=True)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        return collection, dict(held)
    sys.exit(f"say: GitHub holds no comment {number} in {' or '.join(collections)}. "
             "Nothing was changed.")


def corrected_body(withdraw: bool, said: str) -> str | None:
    """Reads what a `correct` run replaces a comment with, or None where it withdraws it.

    Parameters:
        withdraw: Whether the run carries `--withdraw`.
        said: What arrived on stdin, empty where nothing did.

    Returns:
        str | None: The replacement body, or None for a withdrawal.

    Raises:
        SystemExit: If a withdrawal came with a body, or a correction came with none.
    """
    if withdraw:
        if said:
            sys.exit("say: refusing — `--withdraw` deletes the comment and says nothing in its "
                     "place, so the body on stdin would go nowhere. Drop the flag to correct "
                     "the comment with these words instead.")
        return None
    if not said:
        sys.exit("say: nothing on stdin — a correction is the words that replace the body. "
                 "`--withdraw` is how a comment is taken back rather than rewritten.")
    return refuse_a_typed_trailer(said)


def correct(reference: str, text: str | None) -> None:
    """Replaces the body of a comment this account posted, or withdraws it (solorepo's DR-286).

    The replacement carries the correcting run's own Trailer, so the record says
    which Job last spoke. A withdrawal deletes the comment, and deletes the
    thread with it where the comment is the one that opened it, replies by other
    accounts included.

    A withdrawal leaves no comment behind to carry a Trailer, which is inherent
    to deleting; running unattested is not. So the run is asked who is speaking
    before the delete, and `channel.trailers()` refuses one the environment does
    not name, as it does on every other act of the channel (solorepo's Article
    19, solorepo's DR-233). What it answers is printed beside the withdrawal, so
    the run's own record says which Job took the sentence back.

    Parameters:
        reference: The comment's URL, or its identifier alone.
        text: The words that replace the body, or None to withdraw the comment.

    Raises:
        SystemExit: If GitHub holds no such comment, another account posted it,
            or a withdrawal's run does not say who is speaking.
    """
    collection, held = named_comment(reference)
    author = str((held.get("user") or {}).get("login", ""))
    speaking = channel.login()
    if author != speaking:
        sys.exit(f"say: refusing — {author or 'another account'} posted that comment and this "
                 f"channel speaks as {speaking}. A Role corrects what it said itself; what "
                 "another account said is answered where it stands, and the account that said "
                 "it corrects it — `--role` picks the credential.")
    at = f"repos/{channel.repo()}/{collection}/{held['id']}"
    if text is None:
        attested = channel.trailers()
        channel.gh("api", at, "-X", "DELETE", parse=False)
        print(f"withdrew {held.get('html_url', at)}\n{attested}")
        return
    channel.gh("api", at, "-X", "PATCH", "-f", f"body={channel.signed(text)}", parse=False)
    print(held.get("html_url", at))
