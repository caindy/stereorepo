"""The standing merge manager: the gate over an open pull request, the mutual exclusion
the two workflows that run it hold it under, and the landing in order of leverage
(solorepo's DR-161, solorepo's DR-264, solorepo's DR-267)."""
import datetime
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from typing import Any, cast

import channel
import check_pr
from lib.move import advance, challenges, common, pull_requests

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


STALL_CHANGES_REQUESTED_THRESHOLD = 3
"""Number of changes-requested review rounds before an autonomous loop PR is evicted to draft (solorepo's DR-258)."""


MERGE_MANAGER_FIELDS = (
    "number,title,headRefName,baseRefName,headRefOid,isDraft,mergeable,"
    "mergeStateStatus,latestReviews,reviews,reviewRequests,closingIssuesReferences,"
    "additions,deletions,statusCheckRollup,body"
)


THREADS_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          isResolved
          isOutdated
          comments(first: 50) {
            nodes {
              author { login }
              body
            }
          }
        }
      }
    }
  }
}
"""


deduplicate_checks = check_pr.deduplicate_checks


def check_green(pull: common.Pull) -> tuple[bool, str]:
    """Whether every check on the head has concluded and none failed."""
    contexts = deduplicate_checks(pull.get("statusCheckRollup") or [])
    if not contexts:
        return False, "checks pending (no checks concluded)"
    green_states = set(check_pr.GREEN)
    failed: list[str] = []
    pending: list[str] = []
    for c in contexts:
        state = (c.get("conclusion") or c.get("state") or c.get("status") or "").upper()
        name = c.get("name") or c.get("context") or "check"
        if state not in green_states:
            if state in ("PENDING", "IN_PROGRESS", "QUEUED", ""):
                pending.append(name)
            else:
                failed.append(f"{name}:{state.lower()}")
    if failed:
        return False, f"checks failing ({', '.join(failed[:3])})"
    if pending:
        return False, f"checks pending ({', '.join(pending[:3])})"
    return True, "checks green"


def check_reviewer_approval(pull: common.Pull, reviewer_login: str) -> tuple[bool, str]:
    """Whether the reviewer account has approved."""
    if check_pr.is_review_requested(pull, reviewer_login):
        return False, f"waiting on review from {reviewer_login}"
    reviews = pull.get("latestReviews") or pull.get("reviews") or []
    matching = [r for r in reviews if (r.get("author") or {}).get("login") == reviewer_login]
    if not matching:
        return False, f"no review from {reviewer_login}"
    latest = matching[-1]
    state = latest.get("state")
    if state == "APPROVED":
        return True, "approved by reviewer"
    if state == "CHANGES_REQUESTED":
        return False, f"changes requested by {reviewer_login}"
    return False, f"review from {reviewer_login} is {state.lower()}"


def read_threads(pull: common.Pull, owner: str,
                 name: str) -> tuple[list[dict[str, Any]] | None, str]:
    """The review threads of a pull request: its own where it carries them, and GitHub's otherwise.

    Parameters:
        pull (dict): The pull request, which must carry `number`.
        owner (str): The repository's owner.
        name (str): The repository's name.

    Returns:
        tuple[list[dict] | None, str]: The threads and an empty reason, or None
            and why they could not be read, which is a semaphore failing closed.
    """
    held = pull.get("reviewThreads")
    if held is not None:
        return list(held), ""
    try:
        res = channel.graphql(THREADS_QUERY, owner=owner, name=name, number=int(pull["number"]))
        repo_data = res.get("data", {}).get("repository")
        if not repo_data:
            return None, "could not read conversations (no repository data)"
        pr_data = repo_data.get("pullRequest")
        if not pr_data:
            return None, "could not read conversations (no pull request data)"
        return list(pr_data.get("reviewThreads", {}).get("nodes", [])), ""
    except (SystemExit, Exception) as exc:  # noqa: BLE001  # reason: a semaphore that cannot read fails closed, so anything raised in the read refuses the merge rather than passing it
        return None, f"could not read conversations ({type(exc).__name__})"


def unresolved_conversations(threads: Sequence[dict[str, Any]]) -> str:
    """The refusal an unresolved thread is, or the empty string where every thread is resolved.

    Counts the threads GitHub still reports unresolved, whatever their last
    comment says. `check_threads` is its one caller.

    Parameters:
        threads (list): Review thread nodes, each carrying `isResolved`.

    Returns:
        str: `<n> unresolved conversation(s)`, or the empty string.
    """
    unresolved = [t for t in threads if not t.get("isResolved")]
    return f"{len(unresolved)} unresolved conversation(s)" if unresolved else ""


def check_threads(pull: common.Pull, owner: str, name: str) -> tuple[bool, str]:
    """Whether all review conversations are resolved."""
    threads, why = read_threads(pull, owner, name)
    if threads is None:
        return False, why
    refusal = unresolved_conversations(threads)
    if refusal:
        return False, refusal
    return True, "0 unresolved conversations"


# The reason a branch that has fallen behind its base is given. Named rather
# than spelled twice, because `advance_stranded` decides on the exact string.
BEHIND_BASE = "branch is behind base"


def check_mergeable_clean(pull: common.Pull) -> tuple[bool, str]:
    """Whether the branch is current with its base, as far as the classifier does not read.

    `mergeable` and `mergeStateStatus` are read through `mergeability`, which
    waits an `UNKNOWN` out and settles both onto the pull request, so that the
    classifier reads the settled value. A branch that conflicts is the
    classifier's `NEEDS_REBASE` and not refused here (solorepo's DR-264); what
    is refused here is what `classify_pr` does not read: a branch behind its
    base, one GitHub calls dirty, and a value still `UNKNOWN` once the wait is
    spent, with a reason that says it was waited for.
    """
    mergeable = pull_requests.mergeability(pull)
    status = pull.get("mergeStateStatus")
    if status == "BEHIND":
        return False, BEHIND_BASE
    if status == "DIRTY" and mergeable != "CONFLICTING":
        return False, "branch has dirty merge state"
    if mergeable == "UNKNOWN":
        return False, "mergeable is still UNKNOWN after waiting"
    return True, "mergeable clean"


DECISION_ENTRY = re.compile(r"^\.meta/assertions/decisions/(DR-\d+)\.yaml$")
"""One entry of the record, matched over the path GitHub names a changed file by."""


STATUS_WRITTEN = re.compile(r"^\+\s+status:\s*(\S+)\s*$", re.M)
"""A `status` a diff writes, matched in the patch hunk that adds the line."""


NOT_IN_FORCE = frozenset({"PROPOSED", "RECOMMENDED"})
"""The `DecisionStatus` values `.meta/work/decisions.yaml` describes as not yet in force."""


PER_PAGE = 100
"""How many of a pull request's files are asked for at once: GitHub's own maximum."""


PAGES = 10
"""How many pages of files are read before the diff is answered for as unreadable."""


def changed_files(pull: common.Pull, owner: str, name: str) -> list[dict[str, Any]] | None:
    """The files a pull request changes, as GitHub answers for them.

    Parameters:
        pull (dict): The pull request, which must carry `number`.
        owner (str): The repository's owner.
        name (str): The repository's name.

    Returns:
        list[dict] or None: One entry per file changed, or None where the file
            list ran past the pages read.

    Raises:
        SystemExit: If a page's call to GitHub fails.
    """
    files: list[dict[str, Any]] = []
    for page in range(1, PAGES + 1):
        got = channel.gh("api", f"repos/{owner}/{name}/pulls/{int(pull['number'])}/files"
                                f"?per_page={PER_PAGE}&page={page}")
        files += got
        if len(got) < PER_PAGE:
            return files
    return None


def check_decisions_in_force(pull: common.Pull, owner: str, name: str) -> tuple[bool, str]:
    """Whether every Decision this diff carries is in force (solorepo's DR-222).

    A diff carries a Decision when it writes an entry's `status` line: adding
    the entry, or moving the status of one already on the trunk. `PROPOSED` or
    `RECOMMENDED` defers the pull request and names the entry in the reason —
    neither is yet in force, by `DecisionStatus`'s description in
    `.meta/work/decisions.yaml`; any other status, and a diff that leaves the
    line alone, clears it. A diff that cannot be read defers too — a decision
    entry GitHub sends no patch for, a file list running past the pages read,
    or a call that failed.

    Parameters:
        pull (dict): The pull request, which must carry `number`.
        owner (str): The repository's owner.
        name (str): The repository's name.

    Returns:
        tuple[bool, str]: Whether it may merge, and the reason either way.
    """
    try:
        files = changed_files(pull, owner, name)
    except (SystemExit, Exception) as exc:  # noqa: BLE001  # reason: a semaphore that cannot read fails closed, so anything raised in the read refuses the merge rather than passing it
        return False, f"could not read the diff ({type(exc).__name__})"
    if files is None:
        return False, f"could not read the diff (over {PER_PAGE * PAGES} files)"
    pending, unreadable = [], []
    for changed in files:
        found = DECISION_ENTRY.match(changed.get("filename") or "")
        if not found:
            continue
        patch = changed.get("patch")
        if not patch and (changed.get("additions") or changed.get("deletions")):
            unreadable.append(found.group(1))
        elif any(status.upper() in NOT_IN_FORCE for status in STATUS_WRITTEN.findall(patch or "")):
            pending.append(found.group(1))
    if unreadable:
        return False, f"could not read the diff of {', '.join(sorted(unreadable))}"
    if pending:
        return False, f"carries {', '.join(sorted(pending))}, not in force"
    return True, "carries only decisions in force"


def lifecycle_refusal(pull: common.Pull, found: check_pr.PullRequestState, reviewer_login: str,
                      threads: Sequence[dict[str, Any]] | None) -> str:
    """The refusal a lifecycle state reads as, in the words the log and `advance_stranded` hold.

    The classifier decides; `check_green` and `check_reviewer_approval` only
    word what it found, naming the checks that failed or are pending and the
    reviewer whose verdict is waited on (solorepo's DR-264). A state neither
    words is the empty string, for the caller to name only where nothing else
    in its list explains it.

    Parameters:
        pull (dict): The pull request the state was read off.
        found (PullRequestState): What `classify_pr` read, other than READY_TO_MERGE.
        reviewer_login (str): The reviewer Role's login.
        threads (list | None): The review threads the state was read with.

    Returns:
        str: One refusal reason, or the empty string where the state has no
            words of its own.
    """
    states = check_pr.PullRequestState
    if found is states.NEEDS_REBASE:
        return "branch conflicts with base"
    if found in (states.GATE_FAILED, states.AWAITING_GATE):
        green, worded = check_green(pull)
        if not green:
            return worded
    elif found in (states.AWAITING_REVIEW, states.CHANGES_REQUESTED):
        approved, worded = check_reviewer_approval(pull, reviewer_login)
        if not approved:
            return worded
        if found is states.CHANGES_REQUESTED:
            owed = check_pr.state.unaddressed_threads(threads or [], parked=False)
            return f"{len(owed)} unresolved conversation(s) owed an answer"
    elif found is states.AWAITING_PROMOTION:
        parked = check_pr.state.unaddressed_threads(threads or [], parked=True)
        return f"{len(parked)} notice(s) held for promotion at approval (solorepo's DR-159)"
    return ""


def evaluate_pr(pull: common.Pull, reviewer_login: str, owner: str,
                name: str) -> tuple[bool, list[str]]:
    """Evaluate a pull request against all semaphores (solorepo's DR-161, solorepo's DR-248).

    The lifecycle is the classifier's to read (solorepo's DR-264): `classify_pr`
    says whether the pull request is `READY_TO_MERGE`, and the checks here
    cover only what it does not read — a base other than trunk, a branch behind
    its base or dirty, a mergeability GitHub never settled, and a Decision not
    in force. An unresolved thread is the classifier's too: owed an answer, or
    held for promotion where its last comment is a notice, which is why
    `THREADS_QUERY` selects the comments. The threads are read from GitHub
    only where nothing else has refused and the object did not carry them,
    since a refused pull request costs no second call. A state the classifier
    found that has no words of its own is named only where no other reason
    explains it, so a mergeability GitHub never settled is refused once.

    Parameters:
        pull (dict): The pull request, as `MERGE_MANAGER_FIELDS` lists it.
        reviewer_login (str): The reviewer Role's login.
        owner (str): The repository's owner.
        name (str): The repository's name.

    Returns:
        tuple[bool, list[str]]: Whether it is eligible, and the reasons either way.
    """
    if pull.get("isDraft"):
        return False, ["draft"]
    reasons: list[str] = []
    base = pull.get("baseRefName")
    if base and base != "main":
        reasons.append(f"base is {base}, not main")
    current, why = check_mergeable_clean(pull)
    if not current:
        reasons.append(why)
    threads: list[dict[str, Any]] | None = pull.get("reviewThreads")
    checks = deduplicate_checks(pull.get("statusCheckRollup") or [])
    found = check_pr.classify_pr(pull, checks, threads, reviewer_login)
    ready = check_pr.PullRequestState.READY_TO_MERGE
    if found is ready and threads is None and not reasons:
        threads, unread = read_threads(pull, owner, name)
        if threads is None:
            reasons.append(unread)
        else:
            found = check_pr.classify_pr(pull, checks, threads, reviewer_login)
    if found is not ready:
        worded = lifecycle_refusal(pull, found, reviewer_login, threads)
        if worded:
            reasons.append(worded)
        elif not reasons:
            reasons.append(f"state is {found.value}, not READY_TO_MERGE")
    if not reasons:
        decisions_ok, decisions_msg = check_decisions_in_force(pull, owner, name)
        if not decisions_ok:
            reasons.append(decisions_msg)
    if reasons:
        return False, reasons
    return True, ["eligible"]


def report_refusals(pulls: list[common.Pull],
                    evaluations: dict[int, tuple[bool, list[str]]]) -> None:
    """Print the refusal reasons for each non-eligible pull request.

    Parameters:
        pulls (list): The open pull requests to inspect.
        evaluations (dict): Pull request number to the `(eligible, reasons)`
            pair `evaluate_pr` answered with.
    """
    for pull in pulls:
        num = pull["number"]
        ok, reasons = evaluations[num]
        if not ok:
            print(f"  #{num} ({pull.get('title', '')[:50]}): {'; '.join(reasons)}")


def pr_changed_files(pull: common.Pull, owner: str, name: str,
                     cache: dict[int, set[str] | None]) -> set[str] | None:
    """The set of modified filenames for a pull request, cached by number (solorepo's DR-258).

    Cached by pull request number across a single merge manager pass; the cache
    assumes branch head commits remain stable during that evaluation cycle.

    Parameters:
        pull (dict): The pull request dictionary.
        owner (str): Repository owner.
        name (str): Repository name.
        cache (dict): Cache dictionary mapping pull request number to set of filenames or None.

    Returns:
        set[str] or None: Set of changed file paths, or None if files could not be read.
    """
    num = pull["number"]
    if num in cache:
        return cache[num]
    try:
        files = changed_files(pull, owner, name)
    except (SystemExit, *common.UNREACHED):
        cache[num] = None
        return None
    if files is None:
        cache[num] = None
        return None
    paths: set[str] = {str(f["filename"]) for f in files if f.get("filename")}
    cache[num] = paths
    return paths


def has_active_reservation(pull: common.Pull, reviewer_login: str) -> bool:
    """Whether pull holds an active review or check reservation window (solorepo's DR-258).

    Parameters:
        pull (dict): The pull request metadata dictionary.
        reviewer_login (str): Expected login of the reviewer Role.

    Returns:
        bool: True if review is requested or status checks are actively in progress.
    """
    if pull.get("isDraft"):
        return False
    requests = pull.get("reviewRequests") or []
    if any(r.get("login") == reviewer_login or r.get("name") == reviewer_login for r in requests):
        return True
    contexts = deduplicate_checks(pull.get("statusCheckRollup") or [])
    if not contexts:
        return False
    green_states = set(check_pr.GREEN)
    has_in_flight = False
    for c in contexts:
        state = (c.get("conclusion") or c.get("state") or c.get("status") or "").upper()
        if state in ("PENDING", "IN_PROGRESS", "QUEUED"):
            has_in_flight = True
        elif state not in green_states:
            return False
    return has_in_flight


def is_stalled_autonomous_pr(pull: common.Pull, reviewer_login: str) -> bool:
    """Whether an autonomous loop pull request has stalled beyond recovery thresholds (solorepo's DR-258).

    Parameters:
        pull (dict): The pull request metadata dictionary.
        reviewer_login (str): Expected login of the reviewer Role.

    Returns:
        bool: True if loop PR has exceeded changes-requested or rebase failure thresholds.
    """
    head = pull.get("headRefName") or ""
    if not pull_requests.LOOPS_BRANCH.match(head):
        return False
    if pull.get("mergeable") == "CONFLICTING" \
            and advance._find_advance_notice_comment(pull["number"]) is not None:
        return True
    approved, _ = check_reviewer_approval(pull, reviewer_login)
    if approved:
        return False
    reviews = pull.get("reviews") or pull.get("latestReviews") or []
    cr_reviews = [
        r for r in reviews
        if (r.get("author") or {}).get("login") == reviewer_login and r.get("state") == "CHANGES_REQUESTED"
    ]
    if len(cr_reviews) < STALL_CHANGES_REQUESTED_THRESHOLD:
        return False
    last_cr = cr_reviews[-1]
    last_cr_oid = (last_cr.get("commit") or {}).get("oid")
    head_oid = pull.get("headRefOid")
    return not (head_oid and last_cr_oid and head_oid != last_cr_oid)


def evict_stalled_autonomous_pr(pull: common.Pull, reviewer_login: str = "reviewer",
                                dry_run: bool = False) -> bool:
    """Demote stalled autonomous loop PR to draft to prevent head-of-line blocking (solorepo's DR-258).

    Parameters:
        pull (dict): The pull request metadata dictionary.
        reviewer_login (str): Expected login of the reviewer Role.
        dry_run (bool): If True, log action without mutating GitHub state.

    Returns:
        bool: True if the pull request was demoted (or would be in dry run).
    """
    if not is_stalled_autonomous_pr(pull, reviewer_login):
        return False
    if dry_run:
        print(f"merge-manager: dry run — would evict stalled autonomous PR #{pull['number']} to draft")
        return True
    pull["isDraft"] = True
    try:
        channel.gh("pr", "ready", str(pull["number"]), "--undo", parse=False)
        print(f"merge-manager: evicted stalled autonomous PR #{pull['number']} to draft")
        return True
    except (SystemExit, *common.UNREACHED) as exc:
        print(f"warning: could not demote PR #{pull['number']} to draft: {exc}", file=sys.stderr)
        return False


def _restore_draft_if_ready(pull: common.Pull, reviewer_login: str, dry_run: bool) -> None:
    """Restore approved and green loop pull request from draft to ready (solorepo's DR-258)."""
    if not (pull.get("isDraft")
            and pull_requests.LOOPS_BRANCH.match(pull.get("headRefName") or "")):
        return
    approved, _ = check_reviewer_approval(pull, reviewer_login)
    if not approved:
        return
    ok_green, _ = check_green(pull)
    if ok_green and pull.get("mergeable") != "CONFLICTING":
        if not dry_run:
            try:
                channel.gh("pr", "ready", str(pull["number"]), parse=False)
                pull["isDraft"] = False
                print(f"merge-manager: restored answered and green PR #{pull['number']} from draft")
            except (SystemExit, *common.UNREACHED) as exc:
                print(f"warning: could not mark PR #{pull['number']} ready: {exc}", file=sys.stderr)
        else:
            print(f"merge-manager: dry run — would restore PR #{pull['number']} from draft")


def repo_context() -> tuple[str, str, str]:
    """Resolve repository owner, name, and default reviewer login."""
    try:
        repo = channel.repo()
        owner, name = repo.split("/")
        return owner, name, f"{owner}-{name}-reviewer"
    except (*common.UNREACHED, ValueError):
        return "owner", "repo", "reviewer"


def open_issues() -> list[dict[str, Any]]:
    """Query open repository issues for blocker calculation, failing open on errors."""
    try:
        return cast(list[dict[str, Any]], channel.gh(
            "issue", "list", "--state", "open", "--limit", "100",
            "--json", "number,title,body,blockedBy",
        ))
    except common.UNREACHED:
        return []


def evaluate_open_pulls(
    pulls: Sequence[common.Pull],
    reviewer_login: str,
    owner: str,
    name: str,
    dry_run: bool = False,
) -> tuple[list[common.Pull], dict[int, tuple[bool, list[str]]]]:
    """Evaluate open PRs against semaphores after evicting stalled loop branches.

    Parameters:
        pulls (list): All open pull requests in the repository.
        reviewer_login (str): Login of the reviewer Role.
        owner (str): Repository owner.
        name (str): Repository name.
        dry_run (bool): If True, do not mutate pull request state on GitHub.

    Returns:
        tuple[list[Pull], dict[int, tuple[bool, list[str]]]]: Pair of eligible PRs and evaluations.
    """
    for pull in pulls:
        if not pull.get("isDraft"):
            evict_stalled_autonomous_pr(pull, reviewer_login, dry_run=dry_run)
        else:
            _restore_draft_if_ready(pull, reviewer_login, dry_run=dry_run)

    evaluations: dict[int, tuple[bool, list[str]]] = {}
    eligible: list[common.Pull] = []
    for pull in pulls:
        num = pull["number"]
        ok, reasons = evaluate_pr(pull, reviewer_login, owner, name)
        evaluations[num] = (ok, reasons)
        if ok:
            eligible.append(pull)
    return eligible, evaluations


def partition_contention(
    eligible: list[common.Pull],
    pulls: Sequence[common.Pull],
    reviewer_login: str,
    owner: str,
    name: str,
) -> tuple[list[common.Pull], list[tuple[common.Pull, list[str]]]]:
    """Separate eligible candidates into uncontended and contention-deferred sets (solorepo's DR-258).

    Parameters:
        eligible (list): Candidate pull requests clearing all semaphores.
        pulls (list): All open pull requests in the repository.
        reviewer_login (str): Expected login of the reviewer Role.
        owner (str): Repository owner.
        name (str): Repository name.

    Returns:
        tuple[list[Pull], list[tuple[Pull, list[str]]]]: Uncontended PRs and contention deferred pairs.
    """
    file_cache: dict[int, set[str] | None] = {}
    reserving_older_prs = [
        p for p in pulls
        if not p.get("isDraft") and has_active_reservation(p, reviewer_login)
    ]

    contention_deferred: list[tuple[common.Pull, list[str]]] = []
    contention_nums: set[int] = set()
    for cand in eligible:
        cand_num = cand["number"]
        older_reserving = [p for p in reserving_older_prs if p["number"] < cand_num]
        if not older_reserving:
            continue
        cand_files = pr_changed_files(cand, owner, name, file_cache)
        if cand_files is None:
            contention_deferred.append((cand, ["cannot read candidate file list (over page limit or API unavailable)"]))
            contention_nums.add(cand_num)
            continue
        conflicts = []
        for older in older_reserving:
            older_files = pr_changed_files(older, owner, name, file_cache)
            if older_files is None:
                conflicts.append(f"held on older #{older['number']} in review reservation: unreadable file list (maximal contention assumed)")
            else:
                overlap = cand_files & older_files
                if overlap:
                    conflicts.append(f"shares {len(overlap)} file(s) with older #{older['number']} in review reservation")
        if conflicts:
            contention_deferred.append((cand, conflicts))
            contention_nums.add(cand_num)
        else:
            print(f"merge-manager: disjoint bypass — #{cand_num} has no file contention with older in-flight PRs")

    uncontended = [cand for cand in eligible if cand["number"] not in contention_nums]
    return uncontended, contention_deferred


def rank_by_leverage(
    uncontended: list[common.Pull],
    pulls: Sequence[common.Pull],
    issues: list[dict[str, Any]],
) -> tuple[common.Pull, list[common.Pull], dict[int, dict[str, Any]]]:
    """Rank uncontended candidates by leverage metrics (solorepo's DR-161, solorepo's DR-258).

    Parameters:
        uncontended (list): Uncontended candidate pull requests.
        pulls (list): All open pull requests in the repository.
        issues (list): Open issues for blocker calculations.

    Returns:
        tuple: Top candidate, remaining candidates, and computed metrics mapping.
    """
    metrics: dict[int, dict[str, Any]] = {}
    for pull in uncontended:
        num = pull["number"]
        is_base = any(other.get("baseRefName") == pull.get("headRefName")
                      for other in pulls if other.get("number") != num)
        targets = {num} | {ref["number"] for ref in (pull.get("closingIssuesReferences") or [])}
        unblocks_issues = sum(1 for iss in issues
                              if any(t in targets for t in challenges.issue_blockers(iss)))
        unblocks_prs = sum(1 for other in pulls if other.get("baseRefName") == pull.get("headRefName")
                           or any(t in targets for t in challenges.parse_waits_on(other.get("body"))))
        total_unblocks = unblocks_issues + unblocks_prs
        churn = (pull.get("additions") or 0) + (pull.get("deletions") or 0)
        metrics[num] = {
            "is_base": is_base,
            "unblocks": total_unblocks,
            "churn": churn,
        }

    def leverage_key(pull: common.Pull) -> tuple[int, int, int, int]:
        m = metrics[pull["number"]]
        return (1 if m["is_base"] else 0, m["unblocks"], m["churn"], -pull["number"])

    sorted_candidates = sorted(uncontended, key=leverage_key, reverse=True)
    return sorted_candidates[0], sorted_candidates[1:], metrics


def report_contention_deferred(contention_deferred: list[tuple[common.Pull, list[str]]]) -> None:
    """Print deferred candidates held on review reservation.

    Parameters:
        contention_deferred (list): Pairs of candidate pull request and refusal reasons.
    """
    for cand_pull, reasons in contention_deferred:
        print(f"deferred: #{cand_pull['number']} — {cand_pull.get('title', '')[:50]} (contention hold: {'; '.join(reasons)})")


def report_evaluation_choices(
    winner: common.Pull,
    deferred: list[common.Pull],
    metrics: dict[int, dict[str, Any]],
    contention_deferred: list[tuple[common.Pull, list[str]]],
) -> None:
    """Print evaluation outcomes for winner, deferred candidates, and contention holds.

    Parameters:
        winner (dict): Selected top-ranked candidate.
        deferred (list): Lower-leverage candidates.
        metrics (dict): Computed leverage metrics per pull request.
        contention_deferred (list): Candidate pairs held on contention.
    """
    wm = metrics[winner["number"]]
    print(f"merge-manager: evaluated {1 + len(deferred)} uncontended candidate(s)")
    print(f"chosen: #{winner['number']} — {winner['title']} "
          f"(unblocks: {wm['unblocks']}, base: {wm['is_base']}, churn: +{winner.get('additions', 0)}/-{winner.get('deletions', 0)})")
    for d in deferred:
        dm = metrics[d["number"]]
        print(f"deferred: #{d['number']} — {d['title']} "
              f"(lower leverage: unblocks: {dm['unblocks']}, base: {dm['is_base']}, churn: +{d.get('additions', 0)}/-{d.get('deletions', 0)})")
    report_contention_deferred(contention_deferred)


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


def merge_manager(dry_run: bool = False, stranded: bool = True) -> None:
    """Take the merge manager's lock and manage the queue under it, or stand down.

    This is the way in: `merge.yml` and `reconcile.yml` both run the manager and
    are in concurrency groups of their own, so GitHub holds neither apart from
    the other and `LOCK_REF` is what does (solorepo's DR-267). A dry run takes
    nothing, since it mutates nothing and would otherwise hold the queue for the
    length of a report.

    Parameters:
        dry_run (bool): If True, name the winner and merge nothing.
        stranded (bool): Whether a stranded pull request is rebased, as
            `_manage` reads it.

    Raises:
        SystemExit: With `_manage`'s code, the lock given back first.
    """
    if dry_run:
        _manage(dry_run=True, stranded=stranded)
        return
    lock = take_merge_lock()
    if lock is None:
        return
    try:
        _manage(dry_run=False, stranded=stranded)
    finally:
        drop_merge_lock(lock)


def _manage(dry_run: bool = False, stranded: bool = True) -> None:
    """Evaluate open pull requests against semaphores, rank eligible candidates
    by leverage, assert choices, deferrals, and semaphore refusals out loud, and
    squash-merge the top candidate (solorepo's DR-161, solorepo's DR-258).

    The queue evaluation `merge_manager` runs under the merge manager's lock,
    and which takes no lock itself: call that rather than this, or two managers
    merge the same queue at once (solorepo's DR-267).

    Idle with nothing eligible, it hands the open pull requests to
    `advance_stranded`, so an approved one that has merely fallen behind trunk
    is rebased here rather than waiting for a push to `main` that may never come.

    A `SystemExit` from the winning candidate's `merge` is caught so that the
    failure isolates to its own candidate: `advance_stranded` runs when
    `stranded`, as on the idle branches above, and the queue's other work moves
    rather than waiting behind a candidate that cannot land. The code is then
    re-raised. A failed merge is an anomaly rather than a state only the solo
    can clear, so unlike `advance_stranded`'s own refusals it paints the
    scheduled run red, which is what surfaces a stall.

    Parameters:
        dry_run (bool): If True, name the winner and merge nothing.
        stranded (bool): If False, leave a stranded pull request alone. The
            caller passes False on the one event `advance.yml` also runs on, a
            push to `main`: the two workflows are in different concurrency
            groups, so nothing holds them apart, and `update-branch` returns
            before GitHub has performed the rebase, so both would issue one for
            the same branch.
    """
    owner, name, reviewer_login = repo_context()
    pulls = channel.gh("pr", "list", "--state", "open", "--limit", "100", "--json", MERGE_MANAGER_FIELDS)
    if not pulls:
        print("merge-manager: idle — no open pull requests")
        return

    eligible, evaluations = evaluate_open_pulls(pulls, reviewer_login, owner, name, dry_run=dry_run)
    if not eligible:
        print(f"merge-manager: idle — 0 of {len(pulls)} open pull request(s) eligible")
        report_refusals(pulls, evaluations)
        if stranded:
            advance.advance_stranded(pulls, evaluations, owner, name, dry_run)
        return

    uncontended, contention_deferred = partition_contention(
        eligible, pulls, reviewer_login, owner, name
    )
    if not uncontended:
        print(f"merge-manager: idle — 0 of {len(eligible)} eligible candidate(s) uncontended (held on review reservation)")
        report_contention_deferred(contention_deferred)
        report_refusals(pulls, evaluations)
        if stranded:
            advance.advance_stranded(pulls, evaluations, owner, name, dry_run)
        return

    winner, deferred, metrics = rank_by_leverage(uncontended, pulls, open_issues())
    report_evaluation_choices(winner, deferred, metrics, contention_deferred)
    report_refusals(pulls, evaluations)

    if dry_run:
        print(f"merge-manager: dry run — not merging #{winner['number']}")
        return

    print(f"merge-manager: merging #{winner['number']}...")
    try:
        pull_requests.merge(str(winner["number"]),
                            stack=bool(pull_requests.stacked(winner["number"])), auto=False)
    except SystemExit as exc:
        print(f"merge-manager: could not merge #{winner['number']} — {exc.code}")
        if stranded:
            advance.advance_stranded(pulls, evaluations, owner, name, dry_run)
        sys.exit(exc.code)
