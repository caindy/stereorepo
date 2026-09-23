"""The mint of a Concept: the reservation a row in the Ubiquitous Language
stands on (solorepo's DR-276)."""
import re
import sys

import channel

IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*:concept/([a-z0-9]+(?:-[a-z0-9]+)*)$")
"""A Concept identifier as the vocabularies write one, capturing the tail the
reservation is named for."""

TAGS = "concept/"
"""The namespace the reservation tags sit in, so `git ls-remote --tags origin
'concept/*'` reads them all and no Decision reservation answers."""

REFUSED = ("say: a run may not mint `{ident}` into the Ubiquitous Language. A Concept is the "
           "solo's word, and a run is not beside him (solorepo's DR-235, solorepo's DR-276). "
           "Say what the word is for on the pull request and leave the row out.")

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
        SystemExit: If called inside a workflow run, if `ident` is not a
            Concept identifier, or if GitHub refuses the tag for any reason but
            the ref existing already or answers with a ref this call did not
            write.
    """
    if channel.in_a_run():
        sys.exit(REFUSED.format(ident=ident))
    name = slug(ident)
    if not name:
        sys.exit(MALFORMED.format(ident=ident))
    if is_reserved(name):
        print(STANDING.format(slug=name))
        return name
    head = channel.gh("api", f"repos/{channel.repo()}/commits/main", "--jq", ".sha", parse=False)
    message = (f"{TAGS}{name} reserved for {ident}.\n\nThe solo minted this Concept into the "
               "Ubiquitous Language. The reservation outlives the row: a Concept withdrawn is "
               "recorded as withdrawn rather than untagged, so the tag never says a word is "
               "current, only that it was minted with the solo's say-so.")
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
