"""The refusal `pull_requests.merge` defers, and the ones it will not (solorepo's #982).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import argparse
import subprocess
import sys
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    answered,
    load_channel,
    outcome,
    stood_in,
    unanswered,
)

RUNNING = "4 of 4 required status checks are in progress."
"""GitHub's words where the merge waits on a check that has yet to conclude."""

FAILED = "1 of 4 required status checks has failed."
"""GitHub's words for a permanent refusal that still names a required status check.

It carries the first fragment of `pull_requests.MERGE_DEFERRED` without the
second, which is what makes the conjunction the predicate reads rather than
either word alone.
"""

POLICY = "Pull request is not mergeable: the base branch policy prohibits the merge."
"""GitHub's words for a refusal naming no check at all."""

DELETES = ("repo", "view", "--json", "deleteBranchOnMerge")
"""The read a merge makes once it has landed, and the act a refused merge owes nothing of."""

LANDED = f"merged #{'7'} as abc1234"
"""What a landed merge prints, the number interpolated rather than written.

Written plainly it is a bare `#7`, which the inherited-citations check reads as
a citation of an Issue a portfolio inheriting this file would resolve to its
own.
"""

DEFERRED_VERB = (f"say: #{'7'} waits on a required check still running, and the same head "
                 f"lands once it concludes — {RUNNING}")
"""What `move merge` exits with over a deferral, written out so that an escape cannot pass for it.

An escaped `MergeDeferredError` renders as its own words too, `outcome` reading
any exception as `type: message`; only the whole sentence the verb writes tells
the refusal it owes from the traceback it does not.
"""


def _hung(channel: Any) -> str:
    """What a tolerated timeout carries on standard error, as `lib_gh.gh` builds it.

    The bound is read from `channel.GH_TIMEOUT` rather than written, because a
    constant naming seconds the channel does not wait leaves a reader of this
    module with the wrong bound.
    """
    return (f"`gh pr merge {'7'} --squash --subject A change (#{'7'})` "
            f"answered nothing within {channel.GH_TIMEOUT}s")


def _gh(calls: list[tuple[str, ...]], refusal: str | None, returncode: int = 1) -> Any:
    """A `channel.gh` answering the reads `merge` makes, and refusing its merge call.

    `refusal` is what the merge call writes on standard error before exiting
    `returncode`, as the CLI buffers it under `tolerate_fail`; None merges
    instead, so the success path is probed against the same stand-in. Every
    call is recorded in `calls` as the arguments it was given, so a probe reads
    whether a refused merge went on to act on a pull request that never landed.

    A refused merge raises only where the caller passed `tolerate_fail`, as
    `channel.gh` raises only there, and degrades to that layer's exit
    otherwise. The keyword is the mechanism this module is named for, so a
    stand-in that raised whichever way it was called would assert the
    classification over a channel no caller can obtain.
    """
    def gh(*args: str, **kwargs: Any) -> Any:
        calls.append(args)
        if args[:2] in (("pr", "merge"), ("stack", "merge")):
            if refusal is None:
                return ""
            if not kwargs.get("tolerate_fail"):
                sys.exit(f"gh: {refusal}")
            raise subprocess.CalledProcessError(
                returncode, ["gh", *args], output="", stderr=f"{refusal}\n")
        if args[:2] == ("pr", "view") and "title,state,headRefName" in args:
            return {"title": "A change", "state": "OPEN", "headRefName": "claude/issue-982"}
        if args[:2] == ("pr", "view"):
            return {"state": "MERGED", "mergeCommit": {"oid": "abc1234def"}}
        if args[:1] == ("api",):
            return {}
        if args == DELETES:
            return {"deleteBranchOnMerge": True}
        raise unanswered(args, "the gh stand-in")

    return gh


def _merged(channel: Any, pull_requests: Any, refusal: str | None, returncode: int = 1,
            stack: bool = False) -> tuple[Any, list[tuple[str, ...]]]:
    """`merge` over a `gh` that refuses with `refusal`, stacked where `stack` says so."""
    calls: list[tuple[str, ...]] = []
    with stood_in(channel, gh=_gh(calls, refusal, returncode), repo=lambda: "owner/repo"):
        came_to = outcome(lambda: pull_requests.merge("7", stack=stack))
    return came_to, calls


def _verb_deferred(channel: Any, move: Any) -> tuple[str | None, bool]:
    """What `move merge` came to over a refusal the merge layer defers, and whether it exited.

    The verb dispatch is driven rather than the library call, because the
    deferral is not a `SystemExit` and an operator's verb that lets it out
    reports a traceback where it owes a reason. `answered` reads the exit off
    the exception's class before `outcome` renders it to text, so that an
    escaped deferral cannot satisfy a case written to forbid one.
    """
    args = argparse.Namespace(verb="merge", pr="7", stack=False, auto=False)
    with stood_in(channel, gh=_gh([], RUNNING), repo=lambda: "owner/repo"):
        _, code, exited = answered(lambda: move.cli._dispatch_pr_verb(args))
    return code, exited


def _refusal_carried(channel: Any, pull_requests: Any) -> str | None:
    """The `refusal` a deferral carries, read off the exception rather than off its text."""
    with stood_in(channel, gh=_gh([], RUNNING), repo=lambda: "owner/repo"):
        try:
            pull_requests.merge("7")
        except pull_requests.MergeDeferredError as deferral:
            return str(deferral.refusal)
    return None


@check("merge deferral probes", pre=True)
def merge_deferral_probes() -> list[str]:
    """`pull_requests.merge` over each refusal GitHub gives it (solorepo's #982).

    Both merge calls are made under `tolerate_fail`, so GitHub's words reach
    this layer as the `CalledProcessError`'s buffered standard error rather
    than as prose folded into an exit message; the stand-in raises only under
    that keyword, so a call that dropped it would fall through to the exit the
    classification never sees. Seven cases over a `channel.gh` that answers
    `merge`'s reads and refuses its merge, and an eighth over the verb the
    operator types.

    A refusal naming required checks still running raises `MergeDeferredError`
    carrying those words, and stops there rather than going on to delete a
    branch whose pull request never landed. A stacked merge refused in the same
    words defers alike, `_classified` taking both calls: the merge manager
    passes `stack=` from what the winner is, so a narrowing here would hand a
    stacked branch to the refusal path over a check that was still running. A
    refusal over a check that *failed* names a required status check too, and
    is not deferred, which is what the conjunction in `MERGE_DEFERRED` is for;
    so is a refusal naming no check at all, and both leave in the words
    `channel.gh` would have exited in. A tolerated timeout exits in the prose
    `GhTimeout` carries rather than raising a type a caller would read as a
    deferral, and it is the returncode that says so: a hang carrying GitHub's
    own deferring words on standard error is still a hang, and is the case that
    holds the classification to `channel.TIMEOUT_RETURNCODE` rather than to the
    strings a timeout happens to arrive with. A merge GitHub lands still reads
    the pull request back and prints what it landed as, which is the path the
    tolerated failure runs through untouched. Last, `move merge` exits in the
    refusal's words rather than letting the deferral out as a traceback: a type
    the merge manager catches is one the operator's verb has to answer too.
    """
    channel, _, programs = load_channel()
    pull_requests = programs["move"].pull_requests
    problems: list[str] = []
    hung = _hung(channel)

    deferred, deferred_calls = _merged(channel, pull_requests, RUNNING)
    timed_out, _ = _merged(channel, pull_requests, hung, channel.TIMEOUT_RETURNCODE)
    landed, landed_calls = _merged(channel, pull_requests, None)

    if deferred.code != f"MergeDeferredError: {RUNNING}":
        problems.append("merge: a refusal over a check still running came to "
                        f"{deferred.code!r}, where a caller with no type to catch has only "
                        "the words to read and demotes a branch that was going to land")
    elif _refusal_carried(channel, pull_requests) != RUNNING:
        problems.append("merge: the deferral carried words other than GitHub's own, where a "
                        "caller reporting why a candidate waits has those words or none")
    if DELETES in deferred_calls:
        problems.append("merge: a refused merge went on to delete the branch, which is the "
                        "act the read-back exists to hold off")
    for words, case in ((FAILED, "a check that failed"), (POLICY, "no check at all")):
        refused, _ = _merged(channel, pull_requests, words)
        if refused.code != f"gh: {words}":
            problems.append(f"merge: a refusal naming {case} came to {refused.code!r}, where "
                            "only a check still running costs a candidate its turn rather "
                            "than its landing")
    stack_deferred, _ = _merged(channel, pull_requests, RUNNING, stack=True)
    if stack_deferred.code != f"MergeDeferredError: {RUNNING}":
        problems.append(f"merge --stack: a refusal over a check still running came to "
                        f"{stack_deferred.code!r}, where the merge manager passes the stack "
                        "flag from what the winner is and a narrowing costs that winner its "
                        "landing")
    if timed_out.code != f"gh: {hung}":
        problems.append(f"merge: a tolerated timeout came to {timed_out.code!r}, where a hang "
                        "is neither a deferral nor a refusal GitHub gave")
    hung_deferring, _ = _merged(channel, pull_requests, RUNNING, channel.TIMEOUT_RETURNCODE)
    if hung_deferring.code != f"gh: {RUNNING}":
        problems.append(f"merge: a timeout carrying GitHub's deferring words came to "
                        f"{hung_deferring.code!r}, where nothing bounds what a command that "
                        "answered nothing left on the stream and the returncode is what says "
                        "a hang is not a deferral")
    if landed.code is not None or LANDED not in landed.out:
        problems.append(f"merge: a merge GitHub landed came to {landed.code!r} saying "
                        f"{landed.out!r}, where tolerating the call's failure leaves the path "
                        "a merge that succeeded takes exactly as it was")
    if DELETES not in landed_calls:
        problems.append("merge: a landed merge never asked whether GitHub deletes the branch")
    verb, exited = _verb_deferred(channel, programs["move"])
    if not exited or verb != DEFERRED_VERB:
        problems.append(f"move merge: the verb came to {verb!r} over a check still running, "
                        "where an operator is owed the reason the merge did not land rather "
                        "than a traceback")
    return problems
