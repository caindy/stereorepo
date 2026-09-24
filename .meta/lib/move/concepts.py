"""The mint of a Concept: the reservation a row in the Ubiquitous Language
stands on (solorepo's DR-276), given by the solo in a session or by the
Challenge a run works, where that Challenge asks for the word by identifier
(solorepo's DR-282)."""
import re
import subprocess
import sys

import channel

IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*:concept/([a-z0-9]+(?:-[a-z0-9]+)*)$")
"""A Concept identifier as the vocabularies write one, capturing the tail the
reservation is named for."""

TAGS = "concept/"
"""The namespace the reservation tags sit in, so `git ls-remote --tags origin
'concept/*'` reads them all and no Decision reservation answers."""

REFUSED = ("say: a run may not mint `{ident}` into the Ubiquitous Language on a branch that "
           "names no Challenge. A Concept is the solo's word, and a run is not beside him "
           "(solorepo's DR-235, solorepo's DR-276); the Challenge a loop branch names is where he "
           "asks for one (solorepo's DR-282). Say what the word is for on the pull request and "
           "leave the row out.")

NOT_ASKED = ("say: a run may mint `{ident}` only where the Challenge its branch names asks for "
             "it on a line of its own, `**Mint.** `{ident}``, and #{issue}'s body has no such "
             "line (solorepo's DR-282). Say what the word is for on the pull request and leave "
             "the row out.")

ASKS = re.compile(r"^\s*\*\*Mint\.\*\*\s+`"
                  r"([a-z0-9]+(?:-[a-z0-9]+)*:concept/[a-z0-9]+(?:-[a-z0-9]+)*)`\s*$", re.M)
"""A line of a Challenge body that asks for a Concept: the lead-in `**Mint.**` and the
identifier in backticks, one to a line, and nothing else on it. A mention in prose asks for
nothing, and an identifier asks for itself alone and not for any word it prefixes."""

ASKED = "#{issue} asks for `{ident}`, and this run mints it on that Challenge's say-so"
"""What the run log says where the Challenge names the Concept (solorepo's DR-282)."""

MALFORMED = ("say: `{ident}` is not a Concept identifier; write it as "
             "`<context>:concept/<slug>`, which is the row the vocabulary will carry")

STANDING = "concept/{slug} is reserved already; the row stands on the reservation that is there"


def slug(ident: str) -> str:
    """Reduce a Concept identifier to the tail its reservation is named for.

    Parameters:
        ident (str): The identifier the vocabulary row will carry, such as
            `work:concept/seed-commit`.

    Returns:
        str: The identifier's tail, such as `seed-commit`; the empty string
            where `ident` is not a Concept identifier.
    """
    found = IDENTIFIER.match(ident.strip())
    return found.group(1) if found else ""


def is_reserved(name: str) -> bool | None:
    """Report whether GitHub already holds a reservation tag for a Concept slug.

    Parameters:
        name (str): The Concept identifier's tail.

    Returns:
        bool or None: True where `refs/tags/concept/<name>` exists on the
            remote, False where it does not, and None where the remote would
            not say, which `mint_concept` answers by attempting the write.
    """
    found = channel.gh("api", f"repos/{channel.repo()}/git/matching-refs/tags/{TAGS}{name}",
                       default=None)
    if found is None:
        return None
    return any(ref.get("ref") == f"refs/tags/{TAGS}{name}" for ref in found)


def branch() -> str:
    """The branch checked out here, as `git` names it, or the empty string where it cannot say."""
    try:
        found = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=True,
                               capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""
    return found


def asked_for(ident: str) -> str:
    """The Challenge that asks a run for `ident`, or the run ended where none does.

    A run's branch is `<harness>/issue-<n>`, and the Challenge it names is
    where the solo asks for a word. The ask is a line of the body of its own,
    `**Mint.**` and then `<context>:concept/<slug>` in backticks, one to a line, which
    is the form `ASKS` reads (solorepo's DR-282): a body that mentions the
    identifier in a sentence asks for nothing, and a line asking for a longer
    word asks for no word it prefixes. A branch naming no Challenge, and a
    Challenge with no such line for this identifier, are each refused with why.

    Parameters:
        ident (str): The Concept identifier.

    Returns:
        str: The Challenge's number.

    Raises:
        SystemExit: Where the branch names no Challenge or the Challenge does not ask.
    """
    _, cut, rest = branch().partition("/issue-")
    if not cut or not rest.isdigit():
        sys.exit(REFUSED.format(ident=ident))
    body = str(channel.gh("issue", "view", rest, "--json", "body").get("body") or "")
    if ident.strip() not in ASKS.findall(body):
        sys.exit(NOT_ASKED.format(ident=ident, issue=rest))
    return rest


def mint_concept(ident: str) -> str:
    """Reserve a Concept on GitHub as the say-so a vocabulary row stands on (solorepo's DR-276).

    Creates the annotated tag `refs/tags/concept/<tail>` over main's head, as
    `decisions.mint` reserves a Decision number (solorepo's DR-128). The tag is
    what `vocabulary mints` reads, so a row added with no reservation behind it
    fails the gate. Reserving one twice is not an error: the second call reports
    the reservation that is there and makes no second reservation, whether the
    read before the write found it or the write itself did. Where the write
    finds it, the tag object this call posted before the ref is left
    unreferenced, which costs nothing and is collected with the rest.

    Parameters:
        ident (str): The Concept identifier the vocabulary row will carry.

    Returns:
        str: The identifier's tail, which is the reservation's name.

    Raises:
        SystemExit: If called inside a workflow run whose Challenge does not
            ask for the Concept, if `ident` is not a Concept identifier, or if
            GitHub refuses the tag for any reason but the ref existing already
            or answers with a ref this call did not write.
    """
    name = slug(ident)
    if not name:
        sys.exit(MALFORMED.format(ident=ident))
    asked = asked_for(ident) if channel.in_a_run() else ""
    if asked:
        print(ASKED.format(issue=asked, ident=ident))
    if is_reserved(name):
        print(STANDING.format(slug=name))
        return name
    head = channel.gh("api", f"repos/{channel.repo()}/commits/main", "--jq", ".sha", parse=False)
    ground = (f"Challenge #{asked} asked for this Concept on a `**Mint.**` line, and a run on "
              "its branch minted it on that say-so (solorepo's DR-282)." if asked
              else "The solo minted this Concept into the Ubiquitous Language.")
    message = (f"{TAGS}{name} reserved for {ident}.\n\n{ground} The reservation outlives the "
               "row: a Concept withdrawn is recorded as withdrawn rather than untagged, so the "
               "tag never says a word is current, only on whose say-so it was minted.")
    tag = channel.gh("api", f"repos/{channel.repo()}/git/tags",
                     "-f", f"tag={TAGS}{name}", "-f", f"message={message}",
                     "-f", f"object={head}", "-f", "type=commit")
    try:
        channel.gh("api", f"repos/{channel.repo()}/git/refs",
                   "-f", f"ref=refs/tags/{TAGS}{name}", "-f", f"sha={tag['sha']}", parse=False)
    except SystemExit as exc:
        if "already exists" not in str(exc.code).lower():
            raise
        print(STANDING.format(slug=name))
        return name
    now = channel.gh("api", f"repos/{channel.repo()}/git/ref/tags/{TAGS}{name}")["object"]["sha"]
    if now != tag["sha"]:
        sys.exit(f"say: GitHub shows tag {TAGS}{name} at {now[:7]} after the call, "
                 f"not {tag['sha'][:7]}")
    print(f"minted {ident} as {TAGS}{name}; write the row as {ident} and give it a wiki "
          "page (A17)")
    return name
