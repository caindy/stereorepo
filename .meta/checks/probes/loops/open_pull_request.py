"""Draft creation and review handoff probes for `move open` (solorepo's DR-287,
solorepo's DR-291)."""
from typing import Any

from checks.collect import check
from checks.probes.harness import load_channel, outcome, stood_in


@check("open pull request probes", pre=True)
def open_pull_request_probes() -> list[str]:
    """`move open` creates a draft and requests review from the reviewer Role."""
    channel, _, programs = load_channel()
    move = programs["move"]
    created: list[tuple[Any, ...]] = []
    requested: list[tuple[str, str]] = []

    def gh(*args: Any, **_: Any) -> str:
        created.append(args)
        return "https://github.com/owner/repo/pull/1043"

    def request_review(number: str, role: str) -> None:
        requested.append((number, role))

    with (
        stood_in(channel, gh=gh),
        stood_in(move.pull_requests.check_pr.form, check=lambda _title, _body: []),
        stood_in(move.pull_requests.handoff, request_review=request_review),
    ):
        ended = outcome(lambda: move.pull_requests.open_pull_request("Open draft", "body"))

    if ended.code:
        return [f"open: creating a draft exited with {ended.code!r}"]
    if not created or created[0][-1] != "--draft":
        return [f"open: GitHub was called without --draft: {created!r}"]
    if requested != [("1043", "reviewer")]:
        return [f"open: expected reviewer handoff after creation, got {requested!r}"]

    requested.clear()
    created.clear()

    def gh_easy(*args: Any, **_: Any) -> Any:
        created.append(args)
        if args[:2] == ("pr", "create"):
            return "https://github.com/owner/repo/pull/1044"
        if args[:2] == ("issue", "view"):
            return {"labels": [{"name": "challenge"}, {"name": "easy"}]}
        return {}

    target = 100
    easy_body = (
        "## Title\n\n"
        "**What this changes.** None.\n\n"
        f"**What it closes.**\n- Closes #{target} — easy task\n"
    )

    with (
        stood_in(channel, gh=gh_easy),
        stood_in(move.pull_requests.check_pr.form, check=lambda _title, _body: []),
        stood_in(move.pull_requests.handoff, request_review=request_review),
    ):
        ended_easy = outcome(
            lambda: move.pull_requests.open_pull_request("Open easy draft", easy_body)
        )

    if ended_easy.code:
        return [f"open: creating easy draft exited with {ended_easy.code!r}"]
    if requested:
        return [f"open: expected no reviewer handoff for easy issue, got {requested!r}"]
    return []
