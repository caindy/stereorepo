"""The pull request lifecycle: opening, layering, merging and superseding (solorepo's DR-264)."""
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence

import channel
import check_pr
from lib.move import advance, common, decisions, handoff


def refuse_unformed(pull: int | str, body: str | None, title: str | None) -> None:
    """Refuse a revision that would leave a pull request off the form (solorepo's A15).

    Whichever half the caller passes, the other is read from GitHub, because the
    form is a property of the pair and a title revised alone can still leave a
    body that no longer answers it.

    Parameters:
        pull (int | str): The pull request being revised.
        body (str | None): The body about to be written, or None to read GitHub's.
        title (str | None): The title about to be written, or None to read GitHub's.

    Raises:
        SystemExit: If the resulting pair does not satisfy the form.
    """
    revised, now = title, body
    if revised is None or now is None:
        held = channel.gh("pr", "view", str(pull), "--json", "title,body")
        revised = held["title"] if revised is None else revised
        now = held["body"] if now is None else now
    problems = check_pr.check(revised, now)
    if not problems:
        return
    formatted = "\n".join(f"  - {p}" for p in problems)
    sys.exit(f"say: revised {'title and body' if body and title else 'title' if title else 'body'} "
             f"does not satisfy the form (solorepo's A15):\n{formatted}\n"
             "Fix the form before revising the pull request.")


def revise(number: str | int, body: str | None = None, title: str | None = None) -> None:
    """Replace a body or a title, on a pull request or an Issue.

    A body is signed at creation and nowhere afterwards, so an edit that
    bypassed the channel would leave a Trailer naming the wrong Actor under
    prose that Actor never wrote. The title is what the index is worth, and
    changing it is an act GitHub records.

    A pull request's body is held to the form (solorepo's A15). An Issue's is
    held to GitHub's blocked-by relationship: a revision may say in prose what
    the relationship already holds, and may not introduce a blocker it does not,
    which is `move waits`'s to set (solorepo's DR-213).
    """
    if body is None and title is None:
        sys.exit("say: nothing to revise — pipe a body in, or pass --title")
    what = common.kind(number)
    if what == "pull request":
        refuse_unformed(number, body, title)
    elif body is not None:
        common.refuse_unbacked_waits(number, body)
    noun = "pr" if what == "pull request" else "issue"
    cmd = [noun, "edit", str(number)]
    if title is not None:
        cmd += ["--title", title]
    if body is not None:
        cmd += ["--body", body]
    channel.gh(*cmd, parse=False)
    print(f"{what} #{number}: {' and '.join(w for w, v in (('body', body), ('title', title)) if v is not None)} set")


def stacked(pr: str | int) -> str | None:
    """The number of the stack a pull request is a layer of, read from GitHub, or None when it is not one.

    The pull request payload carries a `stack` object on a layer and nothing
    otherwise. `gh pr view` does not expose it, so the endpoint is read.

    Parameters:
        pr (str | int): Pull request number to inspect.

    Returns:
        str | None: The stack's number as GitHub reports it, or None.
    """
    stack = channel.gh("api", f"repos/{channel.repo()}/pulls/{pr}").get("stack") or {}
    number = stack.get("number")
    return None if number is None else str(number)


def link(below: str | int, above: str | int) -> None:
    """Link one pull request onto another as the layer above it, as the Role.

    Linking is an act GitHub records, like a merge (solorepo's DR-075), so it goes through
    here, and it is not a verb: a layer is opened linked, `open --on`, or made
    one, `layer --on`, and the link is half of either. Open, then link, was a
    composition a caller assembled by hand and could leave half done (solorepo's DR-116).
    `gh stack submit` opens pull requests unsigned and stays blocked. After a
    layer merges, GitHub rebases the layers above it, which is the whole reason
    for a stack over a hand-built one (solorepo's DR-100).

    `gh stack link` takes either two pull requests, which starts a stack, or a
    stack's number and the layer to add, and refuses a call naming fewer pull
    requests than the stack already holds. So when `below` is already a layer,
    the call names its stack's number in place of `below` (solorepo's #496).
    """
    stack = stacked(below)
    print(channel.gh("stack", "link", stack if stack else str(below), str(above),
                     parse=False, timeout=None))


def head_branch(pr: str | int) -> str:
    """Returns the head branch name for a pull request."""
    return str(channel.gh("pr", "view", str(pr), "--json", "headRefName")["headRefName"])


def layer(pr: str | int, below: str | int) -> None:
    """Make an open pull request a layer on another: retarget its base onto the
    lower layer's branch, and link the two.

    A pull request opened against trunk and found to wait on another (solorepo's DR-100)
    is retargeted rather than closed and reopened: it is merged, never
    abandoned, and the edit is an act GitHub records. Retargeting without
    linking left a pull request whose base was a branch GitHub would not
    rebase it over when that branch merged; both halves are one verb now.
    """
    base = head_branch(below)
    channel.act(
        lambda: channel.gh("pr", "edit", str(pr), "--base", base, parse=False),
        lambda: str(channel.gh("pr", "view", str(pr), "--json", "baseRefName")["baseRefName"]),
        lambda now: now == base,
        lambda now: f"say: GitHub shows #{pr} based on {now} after the call, not {base}")
    link(below, pr)
    print(f"#{pr} is a layer on #{below} ({base})")


def open_pull_request(title: str, body: str, base: str = "main",
                      on: str | int | None = None, draft: bool = False) -> None:
    """Open a pull request, signed; with `on`, open it as a layer on that one.

    The base is the lower layer's branch, read from GitHub rather than typed,
    and the link follows the creation, so a layer is never open and unlinked.
    With `draft`, a draft, which the merge manager, `advance` and the reconciler
    pass over; `move ready` takes it out once the branch holds changes
    (solorepo's DR-273).
    """
    problems = check_pr.check(title, body)
    if problems:
        formatted = "\n".join(f"  - {p}" for p in problems)
        sys.exit(f"say: pull request body does not satisfy the form (solorepo's A15):\n{formatted}\n"
                 "Fix the form before opening the pull request.")
    if on:
        base = head_branch(on)
    try:
        url = channel.gh("pr", "create", "--title", title, "--base", base, "--body", body,
                         *(["--draft"] if draft else []), parse=False, tolerate_fail=True)
    except subprocess.CalledProcessError as exc:
        if "No commits between" in exc.stderr:
            sys.exit(f"say: head branch has no commits ahead of {base}; GitHub requires at "
                     "least one commit to open a pull request. Author an initial plan seed "
                     "commit with `.meta/say/commit --allow-empty -m \"Record initial plan for "
                     "Challenge #<n>\"` before opening the pull request (solorepo's DR-269).")
        sys.exit(f"gh: {exc.stderr.strip()}")
    print(url)
    if on:
        link(on, url.rstrip("/").rsplit("/", 1)[-1])


def arm(pr: str | int, subject: str) -> None:
    """Hand GitHub the intent to merge when the ruleset is satisfied.

    One call, and two callers: the merge verb arming for the first time, and
    `advance` arming again where moving the branch dropped it.
    """
    channel.gh("pr", "merge", str(pr), "--squash", "--auto", "--subject", subject, parse=False)


def behind_by(pull: common.Pull) -> int:
    """How many commits of its base a pull request's head is missing.

    `mergeStateStatus` is the obvious question and answers a different one.
    GitHub computes it when it is asked for, so the first read after a push to
    trunk is `UNKNOWN`; and `BLOCKED` outranks `BEHIND`, so a pull request
    waiting on a review reports the review and hides the fact that it is also
    out of date — which is every `medium` pull request (solorepo's DR-112), and the case
    where nobody is watching. A comparison answers what is actually being
    decided: whether the head is missing commits the base has. GitHub answers
    that the same way whatever else is outstanding.
    """
    return int(channel.gh("api", f"repos/{channel.repo()}/compare/"
                               f"{pull['baseRefName']}...{pull['headRefOid']}")["behind_by"])


ADVANCE = ("number,title,state,baseRefName,headRefName,headRefOid,autoMergeRequest,"
           "reviewRequests,mergeable,mergeStateStatus,latestReviews,updatedAt,isDraft,changedFiles")


def head_now(number: str | int) -> tuple[common.Pull, int]:
    """The commit GitHub has a pull request on, and what that commit is behind
    its base by — the two read beside each other, in that order.

    One question in two parts: whether there is a rebase to ask for, and which
    commit it would be asked against. `advance` asks it twice — once to find
    out there is work, and again when the waiting is over and the call is the
    next thing that happens — and the pair is written here so that the second
    asking cannot anchor the compare to a different reading than the first did.
    """
    before = channel.gh("pr", "view", str(number), "--json", ADVANCE)
    return before, behind_by(before)


def stack_layers(root: common.Pull, pulls: Sequence[common.Pull]) -> list[common.Pull]:
    """Return the open linear stack beginning with `root`.

    Parameters:
        root: The bottom pull request of the stack.
        pulls: The complete list of all open pull requests across the repository.

    Returns:
        list[Pull]: Bottom-first open pull requests forming the linear stack.

    Raises:
        SystemExit: If the open pull requests form a fork or cycle above `root`.
    """
    layers = [root]
    seen = {root["headRefName"]}
    while True:
        above = [pull for pull in pulls if pull["baseRefName"] == layers[-1]["headRefName"]]
        if not above:
            return layers
        if len(above) != 1 or above[0]["headRefName"] in seen:
            sys.exit(f"say: #{root['number']} does not head a linear open stack; "
                     "GitHub cannot advance its layers as one transition")
        layers.append(above[0])
        seen.add(above[0]["headRefName"])


def stack_root(pull: common.Pull, pulls: Sequence[common.Pull]) -> common.Pull:
    """Return `pull`'s bottom layer among open pull requests.

    An unstacked pull request is its own bottom layer.

    Parameters:
        pull: The pull request whose stack root is sought.
        pulls: The complete list of all open pull requests across the repository.

    Returns:
        Pull: The bottom layer pull request in pull's stack, or pull itself if unstacked.

    Raises:
        SystemExit: If the pull request bases form a cycle.
    """
    by_head = {candidate["headRefName"]: candidate for candidate in pulls}
    root = pull
    seen = {root["headRefName"]}
    while root["baseRefName"] in by_head:
        root = by_head[root["baseRefName"]]
        if root["headRefName"] in seen:
            sys.exit(f"say: #{pull['number']} belongs to a cyclic open pull-request stack")
        seen.add(root["headRefName"])
    return root


def layers_below(pull: common.Pull, pulls: Sequence[common.Pull]) -> list[common.Pull]:
    """The open pull requests `pull` is stacked on, nearest first; empty for a root.

    A layer is based on the head of the layer below it, so the chain is read
    off `baseRefName` through the open pull requests until it reaches a base
    no open pull request heads.

    Parameters:
        pull: The pull request whose lower layers are sought.
        pulls: Every open pull request, carrying `headRefName` and `baseRefName`.

    Returns:
        list[Pull]: The layers below, the one `pull` is based on first.

    Raises:
        SystemExit: If the pull request bases form a cycle.
    """
    by_head = {candidate["headRefName"]: candidate for candidate in pulls}
    below: list[common.Pull] = []
    seen = {pull["headRefName"]}
    layer = pull
    while layer["baseRefName"] in by_head:
        layer = by_head[layer["baseRefName"]]
        if layer["headRefName"] in seen:
            sys.exit(f"say: #{pull['number']} belongs to a cyclic open pull-request stack")
        seen.add(layer["headRefName"])
        below.append(layer)
    return below


def conflicting_below(pull: common.Pull, pulls: Sequence[common.Pull]) -> common.Pull | None:
    """The nearest layer below `pull` that conflicts with its own base, or None.

    A conflicting stack is resolved from the bottom (solorepo's DR-133): a
    layer is rebased only once every layer below it is clean, since rebasing
    it earlier would carry the lower layers' unresolved commits as its own.
    Each lower layer's mergeability is settled before it is read, as the
    bulk listing answers `UNKNOWN` for a branch not yet recomputed; one still
    `UNKNOWN` when the bound runs out is passed over, since only `CONFLICTING`
    is a conflict, and the next pass reads it settled.

    Parameters:
        pull: The pull request a rebase is proposed for.
        pulls: Every open pull request, carrying `headRefName`, `baseRefName`,
            `number` and `mergeable`.

    Returns:
        Pull | None: The nearest lower layer whose mergeability is `CONFLICTING`,
            or None where `pull` is a root or no layer below it conflicts.

    Raises:
        SystemExit: If the pull request bases form a cycle, or a lower layer's
            mergeability cannot be read.
    """
    for layer in layers_below(pull, pulls):
        if mergeability(layer) == "CONFLICTING":
            return layer
    return None


def _settle_layer(layer_number: str, expected_oid: str) -> common.Pull:
    """Poll GitHub until layer PR headRefOid differs from expected_oid."""
    return channel.settled(
        lambda: channel.gh("pr", "view", layer_number, "--json", ADVANCE),
        lambda now: now["headRefOid"] != expected_oid,
    )


def advance_stack(layers: Sequence[common.Pull], before: dict[str, common.Pull],
                  must_move: Mapping[str, bool]) -> tuple[list[str], list[str], dict[str, str]]:
    """Advance bottom-first stack `layers` through GitHub and report per-layer failures.

    Parameters:
        layers: Open pull requests in bottom-first stack order.
        before: Current GitHub payload by pull request number.
        must_move: Whether each layer was behind its base or sits above a layer that was.

    Returns:
        tuple[list[str], list[str], dict[str, str]]: A triple
        `(failed, refused, replay_refused)`, where `failed` collects per-layer
        problems that belong to individual pull requests, `refused` collects
        failures of writes made on their behalf, and `replay_refused` names, by
        layer, the head a refused replay was refused against — the layer's
        counterpart of the two heads `advance._advance_single_pull` tags, and
        what `advance.stalled_behind` reads.

    Raises:
        SystemExit: If an external GitHub query or command fails outside the rebase sequence.

    The three `gh stack` calls wait indefinitely rather than under
    `channel.GH_TIMEOUT`: they rebase every layer locally and then force-push
    each of them, so a bound cutting the sequence short would leave the
    branches rewritten and an unknown number of them pushed, reported to every
    layer as a failure to advance.

    A sequence that raised is no layer's refused replay and is left untagged:
    it reports the same failure for every layer whatever each one's own state,
    and a stack whose rebase GitHub refuses over conflicts is the conflicting
    branch another reader already owes a pass.
    """
    root = str(layers[0]["number"])
    try:
        channel.gh("stack", "checkout", layers[0]["headRefName"], parse=False, timeout=None)
        channel.gh("stack", "rebase", "--upstack", parse=False, timeout=None)
        channel.gh("stack", "push", parse=False, timeout=None)
    except SystemExit as exc:
        return [f"#{layer['number']} could not advance with #{root}'s stack: {exc.code}"
                for layer in layers], [], {}

    failed: list[str] = []
    refused: list[str] = []
    replay_refused: dict[str, str] = {}
    reviewer = channel.role_login("reviewer")
    for layer in layers:
        number = str(layer["number"])
        if must_move.get(number, False):
            after = _settle_layer(number, before[number]["headRefOid"])
            if after["headRefOid"] == before[number]["headRefOid"]:
                failed.append(f"#{number} is on the head it had before #{root}'s stack advanced")
                replay_refused[number] = after["headRefOid"]
                continue
        else:
            after = channel.gh("pr", "view", number, "--json", ADVANCE)
        if behind_by(after):
            failed.append(f"#{number} is still behind {after['baseRefName']} after #{root}'s stack advanced")
            replay_refused[number] = after["headRefOid"]
            continue
        asked_before = {r.get("login") for r in before[number].get("reviewRequests") or []}
        asked_after = {r.get("login") for r in after.get("reviewRequests") or []}
        if reviewer in asked_before and reviewer not in asked_after:
            try:
                handoff.request_review(number, "reviewer")
            except handoff.RequestRefused as exc:
                refused.append(f"#{number} lost its review request during #{root}'s stack advance and could not be re-requested — {exc.code}")
            except SystemExit as exc:
                failed.append(f"#{number} lost its review request during #{root}'s stack advance: {exc.code}")
        print(f"advanced #{number} in #{root}'s stack: {layer['title']}")
    return failed, refused, replay_refused


is_approved_pull = check_pr.is_approved_pull


is_changes_requested_pull = check_pr.is_changes_requested_pull


# A loop's branch, and nothing else. `(claude|gemini)/issue-<n>` is the shape `coder.yml`
# cuts, so it is the shape a dispatched coder can be sent back to; the solo's
# own pull request is the solo's to rebase, whatever it looks like from here.
LOOPS_BRANCH = re.compile(r"^(?:claude|gemini)/issue-(\d+)$")


def mergeability(pull: common.Pull) -> str | None:
    """Whether GitHub can still merge this branch into its base.

    Waited for rather than read once, under `channel.MERGEABILITY`, which says
    why. The first read is the one already in hand, so a pull request GitHub
    has an answer for costs nothing; only an `UNKNOWN` pays, and it pays in a
    sleep rather than in a wrong answer. Bounded, because a value that is
    still unknown after half a minute is one the next push to trunk will ask
    about again — and a sweep that waited forever on one branch would hold
    up the rest.

    `mergeable` and `mergeStateStatus` are both settled onto `pull` from the
    read that answered, so a caller reading one against the other reads two
    values GitHub computed at the same moment.
    """
    fresh = channel.settled(
        lambda: channel.gh("pr", "view", str(pull["number"]), "--json", ADVANCE),
        lambda now: now.get("mergeable") != "UNKNOWN",
        channel.MERGEABILITY, held=pull)
    # Settled onto the pull request the caller holds, so the sweep's two
    # readings of one branch cost one question (solorepo's DR-149). `advance`
    # asks before it rebases and `dispatch` asks again about the same object —
    # `found` is filtered out of `open_now`, not copied — and the only thing
    # that moves between the two is a rebase this run performed, which GitHub
    # would not have performed on a branch that conflicts.
    #
    # `mergeStateStatus` settles beside it because GitHub computes the pair
    # together: renewing one and leaving the other hands the caller two
    # readings taken at different moments, and `check_mergeable_clean` refuses
    # on both.
    answer: str | None = fresh.get("mergeable")
    if fresh is not pull:
        pull["mergeStateStatus"] = fresh.get("mergeStateStatus")
    pull["mergeable"] = answer
    return answer


def _merge_auto(pr: str | int, before: common.Pull, subject: str, stack: bool) -> None:
    """Enable GitHub auto-merge on pull request once required checks pass.

    Advances the branch to base head before arming. Falls back to immediate
    merge if the branch status is already clean. Verifies that auto-merge
    request is preserved on GitHub after branch movements.
    """
    if stack or stacked(pr):
        sys.exit(f"say: #{pr} is in a stack, and GitHub does not arm a stacked pull request, "
                 "bottom included. Merge it with --stack when it is green, and GitHub "
                 "retargets the layers above as it lands.")
    if not channel.gh("api", f"repos/{channel.repo()}").get("allow_auto_merge"):
        sys.exit("say: this repository does not allow auto-merge; that is a setting on "
                 "GitHub, not a line here")
    stalled = None
    try:
        advance.advance(pr, held=True)
    except SystemExit as exc:
        stalled = str(exc.code)
    try:
        arm(pr, subject)
    except SystemExit as exc:
        if "clean status" not in str(exc.code):
            raise
    else:
        after = channel.gh("pr", "view", str(pr), "--json", "state,mergeCommit,autoMergeRequest")
        if after["state"] == "MERGED":
            print(f"merged #{pr} as {after['mergeCommit']['oid'][:7]} — {before['title']}")
        elif after.get("autoMergeRequest"):
            print(f"armed: #{pr} merges as a squash when green — {before['title']}")
            if stalled:
                try:
                    current = channel.gh("pr", "view", str(pr), "--json", ADVANCE)
                    behind = behind_by(current)
                except SystemExit as exc:
                    sys.exit(f"say: #{pr} is armed, and advancing it did not finish — "
                             f"{stalled}. GitHub would not say whether it is current "
                             f"either — {exc.code}")
                if behind:
                    sys.exit(f"say: #{pr} is armed and {behind} commit(s) behind "
                             f"{current['baseRefName']} — {stalled}")
                print(f"#{pr} is armed and current with {current['baseRefName']}; "
                      f"advancing it did not finish — {stalled}")
        else:
            sys.exit(f"say: GitHub shows #{pr} neither merged nor armed after the call")


MERGE_DEFERRED = ("status check", "in progress")
"""Every fragment GitHub's refusal holds where the merge waits on a check still running.

Both fragments are required, because only their conjunction says that a check
has yet to finish. GitHub also names a required status check in a refusal that
is permanent, where the check failed rather than started, and that refusal
carries the first fragment without the second.
"""


class MergeDeferredError(Exception):
    """A merge GitHub refused over a required check that has yet to conclude.

    The refusal names a moment in a check run rather than a branch that cannot
    land: the same head merges once the run concludes. A caller catching this
    leaves the pull request as it stands and asks again on its next pass, where
    the `SystemExit` `merge` raises for every other refusal is a landing GitHub
    will not give this head.

    Attributes:
        refusal (str): GitHub's own words for the refusal, as the CLI buffered
            them on standard error.
    """

    def __init__(self, refusal: str) -> None:
        super().__init__(refusal)
        self.refusal = refusal


def deferred_refusal(diagnostics: str) -> bool:
    """Whether a refused merge's diagnostics name a required check still running.

    GitHub's words for that refusal are `N of M required status checks are in
    progress`.

    Parameters:
        diagnostics (str): What the CLI wrote on standard error for the refusal.

    Returns:
        bool: True where every fragment of `MERGE_DEFERRED` is in the diagnostics.
    """
    words = diagnostics.lower()
    return all(word in words for word in MERGE_DEFERRED)


def _classified(call: Callable[[], object]) -> None:
    """Run a merge call made under `tolerate_fail`, and classify the refusal it buffers.

    Both of `merge`'s merge calls come through here, so a stacked merge defers
    on the same words an unstacked one does: written inside one branch instead,
    the classification covers whichever call it stands beside, and a caller
    with only `MergeDeferredError` to catch cannot tell which it had.

    A tolerated timeout is not a refusal GitHub gave, whatever its standard
    error happens to say, so it is read off `channel.TIMEOUT_RETURNCODE` and
    not off its words: nothing bounds what a command that answered nothing left
    on the stream before it hung.

    Parameters:
        call (Callable): The `channel.gh` merge call, under `tolerate_fail`.

    Raises:
        MergeDeferredError: Where GitHub refused over a required check that has
            yet to conclude.
        SystemExit: For every other refusal, in the words `channel.gh` would
            have exited in.
    """
    try:
        call()
    except subprocess.CalledProcessError as exc:
        refusal = (exc.stderr or "").strip()
        if exc.returncode != channel.TIMEOUT_RETURNCODE and deferred_refusal(refusal):
            raise MergeDeferredError(refusal) from exc
        sys.exit(f"gh: {refusal}")


def merge(pr: str | int, stack: bool = False, auto: bool = False) -> None:
    """Squash-merge a pull request using its title as the commit subject.

    Executes a squash merge on the specified pull request, attributing the merge to
    the active Role (solorepo's DR-072, solorepo's DR-075). If `stack` is True, merges
    all dependent pull requests in the stack recursively. If `auto` is True, arms
    auto-merge once required checks pass. Deletes the remote branch unless the
    repository is configured to delete head branches automatically.

    Parameters:
        pr (int or str): Pull request number to merge.
        stack (bool): If True, merges all pull request layers up to this one.
        auto (bool): If True, enables GitHub auto-merge to land when checks turn green.

    Raises:
        MergeDeferredError: If GitHub refused the merge over a required check that has
            yet to conclude, which the same head lands on once the run finishes.
        SystemExit: If the pull request is not open, is an unsupported stacked auto-merge,
            or if the merge or arming operation fails on GitHub for any other reason.

    Both merge calls tolerate their own failure so that the refusal reaches
    this layer rather than leaving through `channel.gh`: the CLI buffers
    GitHub's words on standard error, and a caller that has to read them out of
    an exit message cannot tell a check still queued from a landing refused for
    good. `_classified` takes either call's refusal, so a stacked merge waiting
    on a check defers as an unstacked one does.

    The stack merge waits indefinitely rather than under `channel.GH_TIMEOUT`:
    it lands every layer up to `pr` and restacks what remains, and a bound cut
    short would pass out of here before the read-back below that exists to
    catch a merge that did not land, leaving some layers merged and nothing
    reconciling them.

    The read-back itself is `channel.shown` under `channel.SETTLES`, not a
    single read: GitHub processes a squash merge asynchronously, and a `pr
    view` issued immediately after the merge call can still report `state:
    OPEN`. The predicate waits on the merge commit beside the state, because
    the line that prints reads both and a state that arrived without its
    commit would raise where the merge had in fact landed. A merge GitHub
    never lands still reads `OPEN` once the wait runs out, and the exit says
    so, as it always has.

    The stack call passes `echo=True`, so its exit status and both of its
    streams reach standard error. The read-back says only that the pull request
    is still open, which reads as GitHub being slow; a stack merge that exits 0
    having merged nothing says why in its own words (solorepo's #797).
    """
    before = channel.gh("pr", "view", str(pr), "--json", "title,state,headRefName")
    if before["state"] != "OPEN":
        sys.exit(f"say: #{pr} is {before['state'].lower()}, not open")
    subject = f"{before['title']} (#{pr})"
    if auto:
        _merge_auto(pr, before, subject, stack)
        return
    if stack:
        _classified(lambda: channel.gh("stack", "merge", str(pr), "--squash", "--yes",
                                       parse=False, timeout=None, echo=True,
                                       tolerate_fail=True))
    elif stacked(pr):
        sys.exit(f"say: #{pr} is a layer of a stack; the legacy merge cannot take it. "
                 "Pass --stack to merge everything up to it.")
    else:
        _classified(lambda: channel.gh("pr", "merge", str(pr), "--squash", "--subject", subject,
                                       parse=False, tolerate_fail=True))
    after = channel.shown(
        lambda: channel.gh("pr", "view", str(pr), "--json", "state,mergeCommit"),
        lambda now: now["state"] == "MERGED" and now["mergeCommit"],
        lambda now: (f"say: #{pr} is {now['state'].lower()} after the merge call; not deleting "
                     "the branch" if now["state"] != "MERGED" else
                     f"say: #{pr} is merged but GitHub shows no merge commit for it yet; not "
                     "deleting the branch"),
    )
    print(f"merged #{pr} as {after['mergeCommit']['oid'][:7]} — {before['title']}")
    branch = before["headRefName"]
    if channel.gh("repo", "view", "--json", "deleteBranchOnMerge")["deleteBranchOnMerge"]:
        print(f"GitHub deletes origin/{branch} on merge; nothing to do here")
    else:
        channel.gh("api", "-X", "DELETE", f"repos/{channel.repo()}/git/refs/heads/{branch}", parse=False)
        print(f"deleted origin/{branch}")


SUPERSEDER = re.compile(r"^(?:#?(\d+)|[Dd][Rr]-0*(\d+))$")


def superseder(what: str) -> tuple[str, str]:
    """Validate that a superseding reference has merged or been adopted.

    Checks whether the argument refers to a merged pull request or an adopted
    Decision Record on the trunk (solorepo's DR-164).

    Parameters:
        what (str): Pull request reference (e.g. '123', '#123') or Decision identifier
            (e.g. 'DR-nnn').

    Returns:
        tuple[str, str]: Short name and markdown reference string for the superseder.

    Raises:
        SystemExit: If the format is invalid, if a PR is unmerged, or if a decision
            is not yet adopted on the main branch.
    """
    found = SUPERSEDER.match(what.strip())
    if not found:
        sys.exit(f"say: --by takes a pull request, as `nnn` or `#nnn`, or a Decision, as "
                 f"`DR-nnn`; {what!r} is neither")
    if found.group(2):
        name = f"DR-{int(found.group(2)):03d}"
        entry = f"{decisions.DECISIONS.relative_to(decisions.ROOT)}/{name}.yaml"
        if int(found.group(2)) not in decisions.numbers_on("main"):
            sys.exit(f"say: the record on main holds no {name}, so it is not an answer anything "
                     "has been given yet. A Decision supersedes once its entry has landed; "
                     "until then it is a second answer in flight.")
        status = decisions.entry_status(channel.gh("api", "-H", "Accept: application/vnd.github.raw",
                                        f"repos/{channel.repo()}/contents/{entry}?ref=main",
                                        parse=False))
        if status is None:
            sys.exit(f"say: main holds {entry} and no status can be read out of it, where every "
                     "entry in the record is one entry with one `status` in it. Read the entry "
                     "and name what it says: a Decision supersedes once it is adopted.")
        if status.upper() != "ADOPTED":
            sys.exit(f"say: the record on main has {name} as {status.lower()}, not adopted, so "
                     "it holds the number and not an answer. A hole is not a replacement, and "
                     "an entry still proposed is a second answer in flight. Name the Decision "
                     "that was adopted, or the pull request that landed it.")
        return name, f"[{name}](https://github.com/{channel.repo()}/blob/main/{entry})"
    number = found.group(1)
    if common.kind(number) != "pull request":
        sys.exit(f"say: #{number} is an Issue. A Challenge does not supersede a pull request; "
                 "the change that answered it does. Name that pull request, or the Decision "
                 "it landed.")
    pull = channel.gh("pr", "view", str(number), "--json", "state,title")
    if pull["state"] != "MERGED":
        sys.exit(f"say: #{number} is {pull['state'].lower()}, not merged, so the tree does not "
                 "hold its answer yet. Two open pull requests are two answers in flight, and "
                 "which of them is the wrong one is not settled by closing the other.")
    return f"#{number}", f"#{number} — {pull['title']}"


def supersede(pr: str | int, by: str, reason: str) -> None:
    """Close a pull request that has been superseded by another merged change or adopted decision.

    Closes an open pull request whose associated challenges have already been resolved
    by an alternative landed change (solorepo's DR-164). Posts an explanatory signed
    comment citing the superseding artifact and any unredeemed decision numbers
    minted on the branch, then closes the pull request.

    Parameters:
        pr (int or str): Pull request number to supersede.
        by (str): Superseding reference (merged PR number or adopted DR identifier).
        reason (str): Explanatory text justifying the closure.

    Raises:
        SystemExit: If the PR is not open, if any referenced challenge remains open,
            or if the close operation fails to register on GitHub.
    """
    before = channel.gh("pr", "view", str(pr), "--json",
                        "state,title,headRefName,closingIssuesReferences")
    if before["state"] not in ("OPEN", "CLOSED"):
        sys.exit(f"say: #{pr} is {before['state'].lower()}, not open or closed")
    name, cited = superseder(by)
    closes = [c["number"] for c in before["closingIssuesReferences"]]
    if not closes:
        sys.exit(f"say: #{pr} closes no Challenge, so there is nothing here another answer "
                 "could have overtaken. A Challenge that is closed already is the whole of "
                 "what tells superseded from abandoned, and what `--by` names says nothing "
                 f"about #{pr} — any merged pull request in the repository would satisfy it — "
                 "so this would be the general `close` "
                 "PR First's *Merged, never abandoned* step refuses to have. "
                 f"If there is a Challenge, name it in the body with `move revise {pr}`; if "
                 "there is not, merge is still the only exit.")
    still_open = [n for n in closes
                  if channel.gh("api", f"repos/{channel.repo()}/issues/{n}",
                                "--jq", ".state", parse=False).upper() == "OPEN"]
    if still_open:
        listed = ", ".join(f"#{n}" for n in still_open)
        sys.exit(f"say: #{pr} closes {listed}, still open, so nothing has answered that "
                 "Challenge yet. Merged, never abandoned: a Challenge with no other answer "
                 "has this pull request as the only one it has, and closing it here would "
                 "abandon the need rather than record that it was met elsewhere.")

    answered = ", ".join(f"#{n}" for n in closes)
    said = [reason.rstrip("\n"), "",
            f"**Superseded by {cited}.** Closed rather than merged, which is "
            f"PR First's *Merged, never abandoned* step and its one exception: {answered} "
            f"{'is' if len(closes) == 1 else 'are'} answered already, so this diff would "
            "install a second answer over the one the tree holds."]
    if unredeemed := decisions.minted_for(before["headRefName"]):
        said += ["", f"**Minted here and never landed:** {', '.join(unredeemed)}. The tag "
                 "stays, so nothing issues the number twice; each is closed by writing it "
                 "back into the record as WITHDRAWN, not by releasing it (solorepo's DR-128)."]
    channel.sibling("post").conversation_comment(pr, channel.signed("\n".join(said)))
    channel.act(
        lambda: channel.gh("pr", "close", str(pr), parse=False),
        lambda: str(channel.gh("pr", "view", str(pr), "--json", "state")["state"]),
        lambda after: after == "CLOSED",
        lambda after: f"say: GitHub shows #{pr} {after.lower()} after the call, not closed")
    print(f"superseded #{pr} by {name} — {before['title']}")
    for hole in unredeemed:
        print(f"{hole} was minted here and never landed; write it back as WITHDRAWN")
