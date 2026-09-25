"""`classify_issue` and `--take`, each over the states the take door decides (solorepo's DR-264).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import functools
import sys
from typing import Any

from checks import citations
from checks.collect import check
from checks.probes.harness import answered, environment, stood_in, unanswered

PULL = {"number": 7, "headRefName": "claude/issue-5"}
"""The open pull request on the loop's branch for Issue 5, where a case has one."""

REFUSAL = "gh: mock API error"
"""What a listing stood in for to refuse exits with, where the caller gave no fallback."""

CODER = "o-r-coder"
"""The coder Role's login over `o/r`, as `github.role_login` composes it."""


@check("take probes", pre=True)
def take_probes() -> list[str]:
    """The Issue classifier, and the take door read through it (solorepo's DR-264).

    `classify_issue`, one case per state, in the order the take door decides
    them: a closed Issue is `CLOSED` whatever its labels; a claim with a pull
    request open is `TAKEN` at any level, `hard` included, since a run is
    standing; `hard` is `HELD` without one; a Challenge with no level is
    `UNREAD`, one at `human` is `HANDED_BACK`, a roadmap Issue is `ROADMAP`
    and one with neither label is `UNLABELLED`; and at a level a loop takes,
    an Issue with open blockers is `BLOCKED`, a claim alone is `CLAIMED`,
    a pull request alone is `RESUMABLE`, and neither is `OFFERED`. A claim
    by somebody other than the coder is no claim, and `coder_login=None` reads
    every claim as nobody's.

    `take`, against a GitHub answered from a dict, every field of every
    decision held: each state's `by` is the word the take door wrote for it,
    with `why` beside the ones that stand down and `said` the line the run
    log gets; a claim with a pull request is the pull request's number on the
    label's door and a resume on the verdict's door (solorepo's DR-142); a
    claim with no pull request runs, which is what the shell it replaced did
    with a run that claimed and died; a hand-back left open resumes and says
    so; an Issue with no label at all is said to be labelled nothing; a pull
    request listing GitHub refuses reads as no pull request on both doors,
    where the hand-back's own reading of the same listing still exits; and an
    Issue GitHub will not answer for, or a name that is not a number, ends
    the label's door with a reason that says which, and is `unnamed` with
    its own `why` on the others.
    """
    check_pr = citations.load_check_pr()
    return _classify_cases(check_pr) + _take_cases(check_pr) + _exit_cases(check_pr)


def _issue(labels: list[str], assignees: list[str] | None = None,
           state: str = "OPEN") -> dict[str, Any]:
    """An Issue as `gh issue view --json state,assignees,labels` answers it."""
    return {"state": state,
            "labels": [{"name": name} for name in labels],
            "assignees": [{"login": who} for who in assignees or []]}


def _classify_cases(check_pr: Any) -> list[str]:
    """`classify_issue` over one case per state, and over a claim that is not the coder's."""
    classify, states = check_pr.state.classify_issue, check_pr.state.IssueState
    cases: list[tuple[str, dict[str, Any], str | None, bool, Any]] = [
        ("closed under a claim and a pull request",
         _issue(["challenge", "easy"], [CODER], "CLOSED"), CODER, True, states.CLOSED),
        ("claimed with a pull request at hard", _issue(["challenge", "hard"], [CODER]),
         CODER, True, states.TAKEN),
        ("hard, unclaimed", _issue(["challenge", "hard"]), CODER, False, states.HELD),
        ("hard, claimed, no pull request", _issue(["challenge", "hard"], [CODER]),
         CODER, False, states.HELD),
        ("challenge with no level", _issue(["challenge"]), CODER, False, states.UNREAD),
        ("human", _issue(["challenge", "human"]), CODER, False, states.HANDED_BACK),
        ("roadmap", _issue(["roadmap"]), CODER, False, states.ROADMAP),
        ("no label of either kind", _issue([]), CODER, False, states.UNLABELLED),
        ("easy, claimed, no pull request", _issue(["challenge", "easy"], [CODER]),
         CODER, False, states.CLAIMED),
        ("medium, unclaimed, pull request open", _issue(["challenge", "medium"]),
         CODER, True, states.RESUMABLE),
        ("easy, unclaimed, with open blocker",
         {**_issue(["challenge", "easy"]), "blockedBy": {"nodes": [{"number": 42}]}},
         CODER, False, states.BLOCKED),
        ("medium, unclaimed, with closed blocker",
         {**_issue(["challenge", "medium"]),
          "blockedBy": {"nodes": [{"number": 42, "state": "CLOSED"}]}},
         CODER, False, states.OFFERED),
        ("easy, unclaimed, no pull request", _issue(["challenge", "easy"]),
         CODER, False, states.OFFERED),
        ("claimed by somebody else with a pull request",
         _issue(["challenge", "easy"], ["o-r-reviewer"]), CODER, True, states.RESUMABLE),
        ("claimed with a pull request, read as nobody's",
         _issue(["challenge", "easy"], [CODER]), None, True, states.RESUMABLE),
    ]
    problems = []
    for name, issue, login, open_pull, expected in cases:
        found = classify(issue, login, open_pull)
        if found is not expected:
            problems.append(f"classify_issue: {name} read as {found.value}, not {expected.value}")
    return problems


class _Answers:
    """`issue view` and `pr list --head` answered from a case.

    An Issue of None is a refusal of the view, answered with the caller's
    fallback. `refuse_pulls` refuses every listing: with the caller's fallback
    where one was given, and by exiting as `github.gh` does where `unset`, the
    sentinel `github.gh` takes for no fallback, was passed through.
    """

    def __init__(self, issue: dict[str, Any] | None, pull: dict[str, Any] | None,
                 unset: object, refuse_pulls: bool = False) -> None:
        self.issue, self.pull, self.unset, self.refuse_pulls = issue, pull, unset, refuse_pulls

    def __call__(self, *args: str, default: Any = None, **_: Any) -> Any:
        if args[:2] == ("issue", "view"):
            if self.issue is None:
                return default
            return dict(self.issue)
        if args[:2] == ("pr", "list"):
            if self.refuse_pulls:
                if default is self.unset:
                    sys.exit(REFUSAL)
                return default
            head = args[args.index("--head") + 1]
            return [dict(self.pull)] if self.pull and self.pull["headRefName"] == head else []
        raise unanswered(args, "the take fake")


def _decision(by: str = "", why: str = "", **fields: str) -> dict[str, str]:
    """Every field of one decision, so a case holds what `take` writes and what it leaves empty."""
    return {"by": by, "why": why, "resume": "", "level": "", "state": "", "said": "", **fields}


STALE = ("now; a Challenge at neither easy nor medium is not this loop's, on any door but "
         "the solo's own dispatch")
"""The tail of what the door says of a Challenge at no level a loop takes."""


def _take_cases(check_pr: Any) -> list[str]:
    """`take` over each decision the door writes, every field held, on both doors."""
    sweep, unset = check_pr.sweep, check_pr.github.UNSET
    door, other = sweep.ISSUE_DOOR, "pull_request_review"
    number = PULL["number"]
    duplicate = (f"#5 is claimed by {CODER} and has open pull request #{number}; this delivery "
                 "is a duplicate")
    resumed = f"#5 has open pull request #{number} and no claim: a hand-back, taken up again"
    cases: list[tuple[str, _Answers, str, dict[str, str]]] = [
        ("closed", _Answers(_issue(["challenge", "easy"], state="CLOSED"), None, unset), door,
         _decision("closed", "closed", state="CLOSED",
                   said="#5 is closed now; this delivery is stale")),
        ("claimed with a pull request on the label's door",
         _Answers(_issue(["challenge", "easy"], [CODER]), PULL, unset), door,
         _decision("7", state="TAKEN", said=duplicate)),
        ("claimed with a pull request on the verdict's door",
         _Answers(_issue(["challenge", "easy"], [CODER]), PULL, unset), other,
         _decision(resume="7", level="easy", state="RESUMABLE", said=resumed)),
        ("hard", _Answers(_issue(["challenge", "hard"]), None, unset), door,
         _decision("held", "labelled hard", state="HELD",
                   said="#5 is hard now: the solo's, with a session beside him; this loop "
                        "stands down")),
        ("blocked with open blocker",
         _Answers({**_issue(["challenge", "easy"]), "blockedBy": {"nodes": [{"number": 42}]}},
                  None, unset), door,
         _decision("blocked", "has open blockers", state="BLOCKED",
                   said="#5 has open blockers; this loop stands down")),
        ("human", _Answers(_issue(["challenge", "human"]), None, unset), other,
         _decision("stale", "labelled challenge, human now, which no loop takes",
                   state="HANDED_BACK", said=f"#5 is labelled 'challenge, human' {STALE}")),
        ("unread", _Answers(_issue(["challenge"]), None, unset), door,
         _decision("stale", "labelled challenge now, which no loop takes", state="UNREAD",
                   said=f"#5 is labelled 'challenge' {STALE}")),
        ("roadmap", _Answers(_issue(["roadmap"]), None, unset), door,
         _decision("stale", "labelled roadmap now, which no loop takes", state="ROADMAP",
                   said=f"#5 is labelled 'roadmap' {STALE}")),
        ("unlabelled", _Answers(_issue([]), None, unset), door,
         _decision("stale", "labelled nothing now, which no loop takes", state="UNLABELLED",
                   said=f"#5 is labelled nothing {STALE}")),
        ("claimed with no pull request", _Answers(_issue(["challenge", "easy"], [CODER]),
                                                  None, unset), door,
         _decision(level="easy", state="CLAIMED")),
        ("offered", _Answers(_issue(["challenge", "medium"]), None, unset), door,
         _decision(level="medium", state="OFFERED")),
        ("resumable", _Answers(_issue(["challenge", "easy"]), PULL, unset), door,
         _decision(resume="7", level="easy", state="RESUMABLE", said=resumed)),
        ("pull listing refused on the label's door",
         _Answers(_issue(["challenge", "easy"]), PULL, unset, refuse_pulls=True), door,
         _decision(level="easy", state="OFFERED")),
        ("pull listing refused on the verdict's door",
         _Answers(_issue(["challenge", "easy"]), PULL, unset, refuse_pulls=True), other,
         _decision(level="easy", state="OFFERED")),
        ("unreadable on the verdict's door", _Answers(None, None, unset), other,
         _decision("unnamed", sweep.UNREADABLE,
                   said="#5 cannot be read; the branch names no Challenge the loop holds, and "
                        "this delivery is not its")),
    ]
    problems = []
    with environment(GITHUB_REPOSITORY="o/r"):
        for name, answers, at, expected in cases:
            with stood_in(check_pr.github, gh=answers):
                value, code, _ = answered(functools.partial(sweep.take, "5", at))
            if code is not None:
                problems.append(f"take: {name} exited with {code!r} rather than deciding")
            elif value != expected:
                wrong = {k: value.get(k) for k in expected if value.get(k) != expected[k]}
                problems.append(f"take: {name} decided {wrong!r} where {expected!r} was held")
        with stood_in(check_pr.github, gh=_Answers(None, None, unset)):
            value, code, _ = answered(functools.partial(sweep.take, "5-followup", other))
        named = _decision("unnamed", sweep.UNNAMED,
                          said="'5-followup' is not an Issue number; the branch is not the "
                               "loop's shape, and this delivery is not its")
        if code is not None or value != named:
            problems.append(f"take: a name that is not a number on the verdict's door decided "
                            f"{value!r} with exit {code!r}, not {named!r}")
    return problems


def _exit_cases(check_pr: Any) -> list[str]:
    """What ends the label's door, each saying which; and the hand-back's exit on a refusal."""
    sweep, unset = check_pr.sweep, check_pr.github.UNSET
    door = sweep.ISSUE_DOOR
    ends: list[tuple[str, _Answers, str, str]] = [
        ("unreadable", _Answers(None, None, unset), "5", "could not be read"),
        ("not a number", _Answers(_issue(["challenge", "easy"]), None, unset), "5-followup",
         "not an Issue number"),
        ("not an ASCII number", _Answers(_issue(["challenge", "easy"]), None, unset), "١٦٩",
         "not an Issue number"),
    ]
    problems = []
    with environment(GITHUB_REPOSITORY="o/r"):
        for name, answers, named, phrase in ends:
            with stood_in(check_pr.github, gh=answers):
                _, code, exited = answered(functools.partial(sweep.take, named, door))
            if not exited or phrase not in (code or ""):
                problems.append(f"take: {name} on the label's door ended with {code!r}, which "
                                f"does not say {phrase!r}, or did not end the step")
        with stood_in(check_pr.github, gh=_Answers(None, None, unset, refuse_pulls=True)):
            _, code, exited = answered(functools.partial(sweep.hand_back, "5"))
        if not exited or code != REFUSAL:
            problems.append(f"hand_back: a refused listing ended with {code!r}, not the "
                            "refusal itself, so a hand-back that could not read reads as one "
                            "that found nothing")
    return problems
