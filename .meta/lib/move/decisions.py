"""The Decision lifecycle: the number minted and reserved, and a record's status as
the verbs read it (solorepo's DR-264)."""
import pathlib
import re
import subprocess
import sys

import channel

# The status an entry gives itself, matched in the entry's own text rather than
# parsed out of it: these programs run under plain `python3` and the channel
# imports nothing but the standard library, where `.meta/gate` and
# `.meta/dereference.py` take their `pyyaml` from a `uvx` shebang.
STATUS = re.compile(r"^\s+status:\s*(\S+)\s*$", re.M)


def entry_status(raw: str) -> str | None:
    """Parse declared decision status from raw Decision Record YAML.

    Parameters:
        raw (str): Raw YAML string of a single Decision Record file.

    Returns:
        str or None: The declared status (e.g. 'ADOPTED', 'SUPERSEDED'), or None if
            not exactly one status line is matched.
    """
    found = STATUS.findall(raw)
    return found[0] if len(found) == 1 else None


def minted_for(branch: str) -> list[str]:
    """Identify Decision Record numbers reserved for a branch that have not landed on trunk.

    Parameters:
        branch (str): Branch name to inspect.

    Returns:
        list[str]: Unredeemed Decision Record identifiers (e.g. ['DR-nnn']) reserved
            for the specified branch.
    """
    mine: list[str] = []
    for number in sorted(reserved() - numbers_on("main")):
        name = f"DR-{number:03d}"
        ref = channel.gh("api", f"repos/{channel.repo()}/git/ref/tags/{name}")["object"]
        if ref["type"] != "tag":
            continue
        message = channel.gh("api", f"repos/{channel.repo()}/git/tags/{ref['sha']}").get("message") or ""
        if message.startswith(f"{name} reserved for {branch}."):
            mine.append(name)
    return mine


ROOT = channel.HERE.parent.parent


DECISIONS = ROOT / ".meta" / "assertions" / "decisions"


ENTRY = re.compile(r"^DR-(\d+)$")


RESERVATION = re.compile(r"^refs/tags/DR-(\d+)$")


ATTEMPTS = 20


def numbers_here() -> set[int]:
    """The numbers the record in this working tree holds."""
    return {int(m.group(1)) for path in DECISIONS.glob("DR-*.yaml")
            if (m := ENTRY.match(path.stem))}


def numbers_on(branch: str) -> set[int]:
    """Query Decision Record numbers present on a specified remote branch.

    Parameters:
        branch (str): Remote branch name to inspect.

    Returns:
        set[int]: Set of Decision Record numbers committed to the branch.
    """
    where = DECISIONS.relative_to(ROOT)
    listing = channel.gh("api", f"repos/{channel.repo()}/contents/{where}?ref={branch}")
    return {int(m.group(1)) for entry in listing
            if (m := ENTRY.match(pathlib.Path(entry["name"]).stem))}


def reserved() -> set[int]:
    """Query all Decision Record numbers reserved via git tags on GitHub.

    Returns:
        set[int]: Set of Decision numbers corresponding to refs/tags/DR-* tags.
    """
    refs = channel.gh("api", f"repos/{channel.repo()}/git/matching-refs/tags/DR-")
    return {int(m.group(1)) for ref in refs if (m := RESERVATION.match(ref["ref"]))}


def branch_here() -> str:
    """Return the short branch name of the active checkout, or 'an unnamed branch' if detached.

    Returns:
        str: Current git branch name, or 'an unnamed branch' on detached HEAD.
    """
    found = subprocess.run(["git", "-C", str(ROOT), "symbolic-ref", "-q", "--short", "HEAD"],
                           check=False, capture_output=True, text=True)
    return found.stdout.strip() if not found.returncode else "an unnamed branch"


def mint() -> int:
    """Allocate and reserve the next sequential Decision Record identifier via an annotated tag (solorepo's DR-128).

    Queries the repository tree, trunk history, and existing DR-* git tags to identify
    the next available Decision number, then creates an annotated tag refs/tags/DR-<n>
    pointing to main's head commit. Retries on 422 conflicts up to ATTEMPTS times to
    resolve concurrent allocations safely.

    Returns:
        int: The allocated Decision number.

    Raises:
        SystemExit: If allocation fails after ATTEMPTS iterations.
    """
    branch = branch_here()
    taken = numbers_here() | numbers_on("main") | reserved()
    at = max(taken, default=0) + 1
    head = channel.gh("api", f"repos/{channel.repo()}/commits/main", "--jq", ".sha", parse=False)
    for number in range(at, at + ATTEMPTS):
        name = f"DR-{number:03d}"
        message = (f"{name} reserved for {branch}.\n\nThe number is fixed the moment it is "
                   "first cited, and this tag is what fixes it. It outlives the entry: "
                   "nothing issues this number again, and a reservation whose pull request "
                   "never merges is withdrawn as an entry, not by deleting the tag.")
        # The tag object first, which never conflicts, then the ref, which is
        # the act: two calls because the object carries the tagger and the
        # message, and a lightweight tag would carry neither. An object whose
        # ref was refused is unreachable and git collects it, so a number lost
        # to another session costs nothing that lasts.
        tag = channel.gh("api", f"repos/{channel.repo()}/git/tags",
                         "-f", f"tag={name}", "-f", f"message={message}",
                         "-f", f"object={head}", "-f", "type=commit")
        try:
            channel.gh("api", f"repos/{channel.repo()}/git/refs",
                       "-f", f"ref=refs/tags/{name}", "-f", f"sha={tag['sha']}", parse=False)
        except SystemExit as exc:
            if "already exists" not in str(exc.code).lower():
                raise
            print(f"{name} is taken; asking for the next", file=sys.stderr)
            continue
        # Read back from GitHub afterwards to verify the tag actually points to
        # our commit. A ref created and pointing elsewhere is a reservation
        # somebody else's, and this Job would otherwise go and write the entry under it.
        now = channel.gh("api", f"repos/{channel.repo()}/git/ref/tags/{name}")["object"]["sha"]
        if now != tag["sha"]:
            sys.exit(f"say: GitHub shows tag {name} at {now[:7]} after the call, not {tag['sha'][:7]}")
        print(f"minted {name}, reserved for {branch}; write it as "
              f".meta/assertions/decisions/{name}.yaml")
        return number
    sys.exit(f"say: {ATTEMPTS} numbers from DR-{at:03d} are all reserved already; "
             "something is minting faster than this can read")
