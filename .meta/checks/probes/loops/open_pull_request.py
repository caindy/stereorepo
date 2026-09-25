"""Draft creation and automatic review handoff probes for `move open`."""
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
        stood_in(move.pull_requests.check_pr, check=lambda _title, _body: []),
        stood_in(move.pull_requests.handoff, request_review=request_review),
    ):
        ended = outcome(lambda: move.pull_requests.open_pull_request("Open draft", "body"))

    if ended.code:
        return [f"open: creating a draft exited with {ended.code!r}"]
    if not created or created[0][-1] != "--draft":
        return [f"open: GitHub was called without --draft: {created!r}"]
    if requested != [("1043", "reviewer")]:
        return [f"open: expected reviewer handoff after creation, got {requested!r}"]
    return []
