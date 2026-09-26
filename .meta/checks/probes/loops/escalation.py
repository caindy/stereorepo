"""Regression probes for guarded autonomous-draft escalation."""
import datetime
from typing import Any

from checks.collect import check
from checks.probes.harness import load_channel
from checks.probes.loops.bench import CODER, MINUTES, REVIEWER, _ago, _pull

ISSUE = 50
"""The Challenge and pull request number in this probe's isolated fixture."""


def _recovery_probes(
    move: Any, draft: dict[str, Any], reading: Any, issue: dict[str, Any]
) -> list[str]:
    """Verify autonomous draft recovery and subsequent escalation on failing checks."""
    failing_check = [{"name": "files", "conclusion": "FAILURE"}]
    failing_draft = {**draft, "statusCheckRollup": failing_check}
    marker = move.manager.eviction.DRAFT_RECOVERY_MARKER
    stall_marker = move.manager.eviction.STALL_ESCALATION_MARKER
    head_oid = draft["headRefOid"]
    recovered_draft = {
        **failing_draft,
        "comments": [{"body": f"{marker} head:{head_oid} check:files"}],
    }
    recovered_observed = {
        **failing_draft,
        "comments": [
            {"body": f"{marker} head:{head_oid} check:files"},
            {"body": f"{stall_marker} head:{head_oid}"},
        ],
    }
    pending_check = [{"name": "files", "status": "IN_PROGRESS", "conclusion": None}]
    cancelled_check = [{"name": "files", "conclusion": "CANCELLED"}]
    non_required = [{"name": "sweep", "conclusion": "FAILURE"}]
    hard_issue = {**issue, "labels": [{"name": "challenge"}, {"name": "hard"}]}

    problems = []
    cases: list[tuple[str, dict[str, Any], Any, str | None]] = [
        ("failing required check dispatches repair", failing_draft, reading, "repair"),
        ("failing required check already recovered observes stall",
         recovered_draft, reading, "escalate"),
        ("failing required check already observed hands to solo",
         recovered_observed, reading, "escalate"),
        ("failing required check on plan-only draft",
         {**failing_draft, "changedFiles": 0}, reading, None),
        ("failing required check on hard challenge",
         failing_draft, reading._replace(by_number={ISSUE: hard_issue}), None),
    ]
    for name, pull, when, expected in cases:
        acts = move.manager.eviction.draft_escalations([pull], when)
        kind = acts[0].kind if acts else None
        if kind != expected:
            problems.append(f"draft recovery: {name} owed {kind!r}, not {expected!r}")

    repairs = move.manager.eviction.draft_escalations([failing_draft], reading)
    if not repairs or repairs[0].title != "files" or marker not in repairs[0].body:
        problems.append("draft recovery: failing required check did not dispatch tagged repair")

    obs = move.manager.eviction.draft_escalations([recovered_draft], reading)
    if not obs or obs[0].title != "observe" or "recovery attempt" not in obs[0].body:
        problems.append("draft recovery: observation lacked recovery context")

    handback = move.manager.eviction.draft_escalations([recovered_observed], reading)
    if not handback or handback[0].title or "recovery attempt" not in handback[0].body:
        problems.append("draft recovery: handback lacked recovery context")

    for label, rollup in (
        ("pending", pending_check),
        ("cancelled", cancelled_check),
        ("non-required", non_required),
    ):
        if move.manager.eviction.failing_required_check({**draft, "statusCheckRollup": rollup}):
            problems.append(f"draft recovery: {label} check was identified as failing required")

    cancelled_acts = move.manager.eviction.draft_escalations(
        [{**draft, "statusCheckRollup": cancelled_check}], reading
    )
    if any(a.kind == "repair" for a in cancelled_acts):
        problems.append("draft recovery: cancelled check dispatched repair")

    sweep_acts = move.manager.eviction.draft_escalations(
        [{**draft, "statusCheckRollup": non_required}], reading
    )
    if any(a.kind == "repair" for a in sweep_acts):
        problems.append("draft recovery: non-required check dispatched repair")

    return problems


@check("draft escalation probes", pre=True)
def escalation_probes() -> list[str]:
    """Escalate only an inactive autonomous draft that no Actions run answers."""
    _, _, programs = load_channel()
    move = programs["move"]
    empty = move.actions.Runs([], [])
    issue = {"number": ISSUE, "labels": [{"name": "challenge"}, {"name": "medium"}],
             "assignees": []}
    handed_back = {**issue, "labels": [{"name": "challenge"}, {"name": "human"}]}
    reading = move.reconcile.Reading(
        now=datetime.datetime.now(datetime.UTC), bound=MINUTES, longest=75.0,
        coder=CODER, reviewer_login=REVIEWER, owner="o", name="r",
        by_number={ISSUE: issue}, named={ISSUE},
        coder_runs=empty, review_runs=empty, triage_runs=empty, action_runs=empty,
    )
    draft = _pull(ISSUE, isDraft=True, changedFiles=1)
    active = move.actions.Runs(
        [{"displayTitle": "other", "status": "queued", "headBranch": draft["headRefName"]}], []
    )
    rebase_done = move.actions.Runs(
        [], [{"displayTitle": f"coder-issue-#{ISSUE}", "status": "completed"}]
    )
    observed = {
        **draft,
        "comments": [{
            "body": f"{move.manager.eviction.STALL_ESCALATION_MARKER} head:{draft['headRefOid']}"
        }],
    }
    cases: list[tuple[str, dict[str, Any], Any, str | None]] = [
        ("first later observation", draft, reading, "escalate"),
        ("second later observation", observed, reading, "escalate"),
        ("plan-only draft", {**draft, "changedFiles": 0}, reading, None),
        ("fresh draft", {**draft, "updatedAt": _ago(MINUTES - 1)}, reading, None),
        ("draft with a queued Actions run", draft, reading._replace(action_runs=active), None),
        ("draft whose Challenge is already handed back", draft,
         reading._replace(by_number={ISSUE: handed_back}), None),
        ("conflict without a completed rebase", {**draft, "mergeable": "CONFLICTING"},
         reading, None),
        ("conflict after a completed rebase remains unresolved",
         {**observed, "mergeable": "CONFLICTING"}, reading._replace(coder_runs=rebase_done),
         "escalate"),
    ]
    problems = []
    for name, pull, when, expected in cases:
        acts = move.manager.eviction.draft_escalations([pull], when)
        kind = acts[0].kind if acts else None
        if kind != expected:
            problems.append(f"draft escalation: {name} owed {kind!r}, not {expected!r}")
    first = move.manager.eviction.draft_escalations([draft], reading)
    second = move.manager.eviction.draft_escalations([observed], reading)
    if not first or first[0].title != "observe" or not second or second[0].title:
        problems.append("draft escalation: the first later observation did not hold the "
                        "Challenge until a second persisted observation")
    session = {**draft, "headRefName": "coder/session-tripwire"}
    if move.manager.eviction.draft_escalations([session], reading):
        problems.append("draft escalation: a session branch was treated as autonomous")
    conflict = move.manager.eviction.draft_escalations(
        [{**observed, "mergeable": "CONFLICTING"}], reading._replace(coder_runs=rebase_done)
    )
    if conflict and "rebase attempt completed" not in conflict[0].body:
        problems.append(f"draft escalation: conflict diagnostic was {conflict[0].body!r}")
    problems.extend(_recovery_probes(move, draft, reading, issue))
    return problems
