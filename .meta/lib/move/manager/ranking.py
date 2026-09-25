"""Whether an open pull request is a merge candidate, and which candidate has the leverage.

The merge manager's reading half: one pass's judgement of every open pull
request, and the order the eligible ones are landed in (solorepo's DR-161,
solorepo's DR-258, solorepo's DR-264). Every call here reads — the eviction to
draft and the merge itself are the package root's and the lease `lock`'s, and
the root reaches its reading through `ranking` as a module (solorepo's DR-217).

This module names nothing out of that root, and cannot: the root imports it
while still initialising, so `from lib.move.manager import <name>` here would
raise `ImportError` on a name not bound yet. That is a constraint rather than a
convenience, and the package docstring is where it is argued.
"""
import re
from collections.abc import Sequence
from typing import Any, cast

import channel
import check_pr
from lib.move import advance, challenges, common, pull_requests

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


BEHIND_BASE = "branch is behind base"
"""The reason a branch behind its base fails on; `advance_stranded` compares the exact string."""


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


def _evaluate_candidate_readiness(pull: common.Pull, owner: str,
                                  name: str) -> str | None:
    """Check post-classification candidate readiness: active refusals and decisions."""
    if find_active_merge_refusal(pull) is not None:
        return "merge previously refused"
    decisions_ok, decisions_msg = check_decisions_in_force(pull, owner, name)
    if not decisions_ok:
        return decisions_msg
    return None


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
        pull (dict): The pull request, as `lib.move.manager.MERGE_MANAGER_FIELDS`
            in the package root lists it. `headRefOid` is among the fields that
            matter here: `find_active_merge_refusal` answers `None` without it,
            so a refused pull request assembled by hand would read eligible.
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
        unready = _evaluate_candidate_readiness(pull, owner, name)
        if unready:
            reasons.append(unready)
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


MERGE_REFUSAL_MARKER = "<!-- solorepo:merge-refusal -->"
"""HTML comment marker identifying an in-place merge refusal diagnosis notice (solorepo's DR-255)."""


RESTORED_THIS_PASS = ("taken out of draft in this pass, and the gate run that restore "
                      "started has not concluded")
"""Why a pull request this pass restored from draft is no candidate of this pass's own."""


def find_active_merge_refusal(pull: common.Pull) -> dict[str, Any] | None:
    """Find active merge refusal notice on a pull request.

    A standing merge refusal notice is active when it carries the pull request's
    current head commit (`head:<head_oid>`). A pull dictionary without
    `headRefOid` has no active refusal, so callers must request that field to
    prevent a refused draft from being restored.

    Parameters:
        pull: The pull request metadata dictionary.

    Returns:
        dict[str, Any] | None: The matching refusal comment if active, or None.
    """
    head_oid = pull.get("headRefOid") or ""
    if not head_oid:
        return None
    for comment in advance.find_notice_comments(pull["number"], MERGE_REFUSAL_MARKER):
        if not isinstance(comment, dict):
            continue
        body = comment.get("body") or ""
        if MERGE_REFUSAL_MARKER in body and f"head:{head_oid}" in body:
            return comment
    return None


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


def evaluate_candidates(
    pulls: Sequence[common.Pull],
    reviewer_login: str,
    owner: str,
    name: str,
    restored: set[int],
) -> tuple[list[common.Pull], dict[int, tuple[bool, list[str]]]]:
    """Evaluate open pull requests against every semaphore, refusing those just restored.

    A pull request the caller's eviction pass took out of draft is refused
    rather than evaluated, for the reason the package docstring gives under
    "Why a refusal over a running check is deferred". Such a pull request
    appears in the evaluations as `(False, [RESTORED_THIS_PASS])` and never in
    the eligible list.

    Parameters:
        pulls (list): All open pull requests in the repository.
        reviewer_login (str): Login of the reviewer Role.
        owner (str): Repository owner.
        name (str): Repository name.
        restored (set): Numbers of the pull requests this pass took out of draft.

    Returns:
        tuple[list[Pull], dict[int, tuple[bool, list[str]]]]: Pair of eligible PRs and evaluations.
    """
    evaluations: dict[int, tuple[bool, list[str]]] = {}
    eligible: list[common.Pull] = []
    for pull in pulls:
        num = pull["number"]
        if num in restored:
            evaluations[num] = (False, [RESTORED_THIS_PASS])
            continue
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
                           or any(t in targets for t in common.parse_waits_on(other.get("body"))))
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
