"""The merge manager's mutual exclusion: the git tag lease the queue runs under (solorepo's DR-267).

Creating `LOCK_REF` is the compare-and-set. GitHub offers a precondition on
neither a ref update nor a ref delete, so the create refused because the ref
exists is the whole of what one caller can learn about another, and breaking a
lease whose holder has stopped is a delete and a re-attempted create rather than
one operation; `broke_merge_lock` carries the residual that leaves.

The module imports `channel` and the standard library and nothing else in
`lib.move`, so a probe stands a seam in on the lease apart from the gate over an
open pull request and the ranking by leverage that share the package."""
import datetime
import json
import subprocess
from typing import Any, cast

import channel

LOCK_REF = "tags/merge-manager-lock"
"""The ref whose creation is the merge manager's mutual exclusion (solorepo's DR-267).

The tag namespace is the one `move mint` reserves a Decision number in, by
creating `refs/tags/{name}` at `.meta/lib/move/decisions.py:144`, so every
endpoint this lock uses is one the repository exercises on every minted
number."""


LOCK_STALE_MINUTES = 30.0
"""How old a lock held by no workflow run must be before the next caller breaks it.

A holder that names a run is tested against that run, which is exact; this is
the bound for a holder that names a session instead. A holder carrying no date
at all is tested against neither and is broken on sight, since nothing it could
be compared with exists."""


LOCK_NOT_FOUND = "HTTP 404"
"""What `gh`'s standard error carries for a ref or tag GitHub answers is not there.

It is the one failure of a lock read that says something about the lock rather
than about GitHub, so it is the one this module reads as an answer."""


class LockUnreadableError(Exception):
    """GitHub would not answer for the lock, which says nothing about who holds it.

    Distinct from an absent or unservable lock, which GitHub does answer for and
    which `lock_holder` reports as None: this is a failure of the read itself,
    and a caller that treats it as a free lock breaks a live one.
    """

    def __init__(self, endpoint: str, why: str) -> None:
        """Name the read that failed and what it failed with, which the callers print.

        Parameters:
            endpoint (str): The `gh api` path that was read.
            why (str): What GitHub or the parse said.
        """
        super().__init__(f"{endpoint}: {why}")


def lock_read(endpoint: str) -> Any:
    """One read of the lock, answering None where GitHub says there is nothing there.

    `channel.gh`'s `default=` cannot be used for this: it is returned for any
    non-zero exit and for any body that will not parse alike, so the caller
    cannot tell an absent lock from a GitHub that is down, and the two want
    opposite acts.

    Parameters:
        endpoint (str): The `gh api` path to read.

    Returns:
        Any: What GitHub answered, or None for a 404.

    Raises:
        LockUnreadableError: On any other failure, and on a body that will not parse.
    """
    try:
        return channel.gh("api", endpoint, tolerate_fail=True)
    except subprocess.CalledProcessError as exc:
        if LOCK_NOT_FOUND in (exc.stderr or ""):
            return None
        raise LockUnreadableError(endpoint, (exc.stderr or "").strip()) from exc
    except json.JSONDecodeError as exc:
        raise LockUnreadableError(endpoint, f"answered what is not JSON: {exc}") from exc


def lock_holder() -> dict[str, Any] | None:
    """Read the lock's tag object, or None where nothing readable holds the lock.

    Returns:
        dict | None: The tag object GitHub answers for the ref, carrying the
            `message` naming the holder and the `tagger` date it was taken at;
            None where GitHub answers that the ref is absent, or that it stands
            at an object the tags endpoint will not serve — a ref made by hand,
            or one pointing at a commit — which is no lock this module wrote.

    Raises:
        LockUnreadableError: Where GitHub would not answer either read.
    """
    ref = lock_read(f"repos/{channel.repo()}/git/ref/{LOCK_REF}")
    if not isinstance(ref, dict):
        return None
    sha = (ref.get("object") or {}).get("sha")
    tag = lock_read(f"repos/{channel.repo()}/git/tags/{sha}") if sha else None
    return cast(dict[str, Any], tag) if isinstance(tag, dict) else None


def lock_is_dead(tag: dict[str, Any], now: datetime.datetime) -> bool:
    """Whether the run or session holding the lock has stopped without giving it back.

    A held lock that nothing will ever release freezes every merge after it,
    which is the failure class solorepo's DR-264 exists to end, so the next
    caller breaks one. A holder that names a workflow run is tested against
    that run: GitHub reports a cancelled or crashed run as `completed`, and a
    lock held by a completed run is nobody's. A holder that names a session
    instead, or one whose run GitHub will not answer for, is tested against
    `LOCK_STALE_MINUTES`, since there is nothing else to ask. A holder carrying
    no date is dead whatever it names, there being neither test to make on it.

    Parameters:
        tag (dict): The tag object `lock_holder` read.
        now (datetime.datetime): The moment the test is made.

    Returns:
        bool: Whether the lock is the next caller's to break.
    """
    held_by = str(tag.get("message") or "").strip()
    if held_by.startswith(channel.RUN_MARK):
        run = channel.gh("run", "view", held_by.removeprefix(channel.RUN_MARK),
                         "--json", "status", default=None)
        if run:
            return str(run.get("status")) == "completed"
    taken = (tag.get("tagger") or {}).get("date")
    if not taken:
        return True
    since = (now - datetime.datetime.fromisoformat(str(taken))).total_seconds() / 60.0
    return since >= LOCK_STALE_MINUTES


def lock_created(repo: str, sha: str) -> bool:
    """Create the lock's ref at `sha`, or report the create GitHub refused.

    Parameters:
        repo (str): The repository the lock is taken in.
        sha (str): The tag object the ref is to stand at.

    Returns:
        bool: Whether this call created the ref, which is the whole of the
            compare-and-set: False is GitHub saying somebody else got there.

    Raises:
        SystemExit: On any failure but that refusal.
    """
    try:
        channel.gh("api", f"repos/{repo}/git/refs", "-f", f"ref=refs/{LOCK_REF}",
                   "-f", f"sha={sha}", parse=False)
    except SystemExit as exc:
        if "already exists" not in str(exc.code).lower():
            raise
        return False
    return True


def release_merge_lock(repo: str) -> None:
    """Delete the lock's ref, relaying what GitHub said so a delete that failed is legible.

    Parameters:
        repo (str): The repository the lock is taken in.
    """
    channel.gh("api", f"repos/{repo}/git/refs/{LOCK_REF}", "-X", "DELETE",
               parse=False, default="", echo=True)


def broke_merge_lock(repo: str, sha: str) -> bool:
    """Break a lock whose holder has stopped and take it, or stand down saying why.

    The break is a delete and a re-attempted create, which is two operations and
    not one compare-and-set. GitHub offers a precondition on neither a ref update
    nor a ref delete, so an atomic break is not available at all; what the create
    buys is that the ordinary loser is told, meeting the winner's live ref and
    standing down. The ordering it does not cover is a breaker's delete landing
    after another breaker's create, which removes a live ref and lets the second
    create succeed: of the four orderings of two deletes and two creates, two are
    safe and two are that one. The window is the round trip between a breaker's
    holder read and its delete, over a lock whose holder has already stopped, and
    it is accepted rather than closed for the reason solorepo's DR-267 gives —
    the failure to design against is the freeze, not the race, and the mechanism
    that would close it is a second lock with a staleness bound of its own.

    Parameters:
        repo (str): The repository the lock is taken in.
        sha (str): The tag object this manager's ref is to stand at.

    Returns:
        bool: Whether the lock is now this manager's.
    """
    try:
        holder = lock_holder()
    except LockUnreadableError as why:
        print(f"merge-manager: GitHub would not say who holds the lock ({why}); standing down")
        return False
    if holder is None:
        print("merge-manager: the lock stands at no tag GitHub will serve, or is gone; taking it")
    else:
        held_by = str(holder.get("message") or "somebody GitHub does not name").strip()
        if not lock_is_dead(holder, datetime.datetime.now(datetime.UTC)):
            print(f"merge-manager: another manager holds the lock ({held_by}); standing down")
            return False
        print(f"merge-manager: breaking the lock {held_by} left behind")
    release_merge_lock(repo)
    if lock_created(repo, sha):
        return True
    print("merge-manager: another manager broke the same lock first; standing down")
    return False


def take_merge_lock() -> str | None:
    """Take the merge manager's lock, or name its holder and take nothing (solorepo's DR-267).

    Creating `LOCK_REF` is the compare-and-set: a create refused because the ref
    exists is another manager holding it, and this call declines rather than
    waits, so `reconcile.yml`'s pass goes on to the reading it was scheduled for
    and `merge.yml`'s next trigger brings the merge round again. A lock whose
    holder has stopped is broken by `broke_merge_lock`, which is that create
    again over a deleted ref and carries the residual named there, and the take
    is read back from GitHub as `move mint` reads its own.

    Returns:
        str | None: The object this call wrote, which `drop_merge_lock` takes
            back; None where the lock was not taken, which is a live holder, a
            holder GitHub would not name, a break another manager won, or a
            read-back that did not show this call's own write.
    """
    repo = channel.repo()
    who = channel.speaker() or "a session the environment does not name"
    head = channel.gh("api", f"repos/{repo}/commits/main", "--jq", ".sha", parse=False)
    tag = channel.gh("api", f"repos/{repo}/git/tags", "-f", "tag=merge-manager-lock",
                     "-f", f"message={who}", "-f", f"object={head}", "-f", "type=commit")
    sha = str(tag["sha"])
    if not lock_created(repo, sha) and not broke_merge_lock(repo, sha):
        return None
    try:
        now = lock_holder()
    except LockUnreadableError as why:
        print(f"merge-manager: GitHub would not read the lock back ({why}); "
              "giving back the ref this run wrote and standing down")
        release_merge_lock(repo)
        return None
    if now is not None and now.get("sha") == sha:
        return sha
    if now is None:
        print("merge-manager: the lock did not take; giving back the ref this run wrote")
        release_merge_lock(repo)
    else:
        print("merge-manager: the lock stands at somebody else's write; standing down")
    return None


def drop_merge_lock(sha: str) -> None:
    """Give the lock back, unless somebody else's break has already taken it.

    A read that fails is not an answer that the lock is somebody else's. This
    run took the lock and nothing else will release it, and a lock nothing
    releases freezes every merge after it (solorepo's DR-264), so an unreadable
    holder is released rather than left.

    Parameters:
        sha (str): What `take_merge_lock` answered with.
    """
    repo = channel.repo()
    try:
        holder = lock_holder()
    except LockUnreadableError as why:
        print(f"merge-manager: GitHub would not say who holds the lock ({why}); "
              "giving back the one this run took")
        release_merge_lock(repo)
        return
    if holder is not None and holder.get("sha") != sha:
        print("merge-manager: the lock is somebody else's now; leaving it where it is")
        return
    release_merge_lock(repo)
