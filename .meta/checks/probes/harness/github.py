"""GitHub stood in for: answered from a dict for the verbs that rebase, arm, hand off and dispatch, and from a list of polls for `--watch` (solorepo's DR-158).
"""
import datetime
import sys
from collections.abc import Iterable
from typing import Any

from checks.probes.harness.acts import unanswered

UNKNOWN_REFUSALS = "FakeGitHub takes {known}, not {unknown}"
"""What construction raises on a keyword outside `FakeGitHub.REFUSALS`."""

STACK_UNCHECKED_OUT = "gh stack rebase called without preceding gh stack checkout"
"""What a stack rebase raises where nothing checked the stack out first."""

STACK_UNKNOWN_BRANCH = "gh stack rebase: branch {branch!r} not found in fake pulls"
"""What a stack rebase raises where the checked-out branch names no pull request this fake holds."""


class FakeGitHub:
    """As much of GitHub as `advance`, `merge --auto`, `request-review` and the by-hand `dispatch` ask about, answered from a dict.

    Stands in for `channel.gh`, which is where every one of the five findings
    on solorepo's #98 lived: `gh()` reports by ending the process, and what a
    caller does with that is the whole question. Answering from a dict makes
    each state a case rather than an argument about a code path nothing ran.

    `pulls` maps a number to that pull request's fields. Each field a case does
    not set takes the default given.

    - `behind`: commits the head is missing from its base. Required.
    - `armed`: whether auto-merge is enabled. Required.
    - `drops`: a rebase drops the arming. Default `False`.
    - `again`: what the branch is behind by after a rebase, for a base that moved
      again under it. Default `0`.
    - `slow`: how many reads after a rebase or a re-arming answer with the pull
      request as it was before it — the head, the arming and the merged state go
      stale together, because they are one object arriving at a read as it was a
      moment ago (solorepo's DR-158). Default `0`.
    - `pushed`: how many reads answer before a commit from outside this run lands
      on the head branch. The push lands at the end of that read, so it models a
      commit arriving between two questions; the commit it orphans keeps what it
      was behind by, and no reads are owed for it, since GitHub shows a push at
      once and only the `compare` of the old oid can still be asked. Default
      `0`, which is no push.
    - `leaves`: what the branch is behind by once that push has landed; `0` where
      the push was itself a rebase. Default: `behind`, unchanged.
    - `requested`: the logins a review is requested of. Written by `pr edit` as
      well as read, since `request-review` asks the same three questions of it
      that `advance` does: what GitHub says about merging the branch, who it
      already lists, and who it lists after the call. Default `[]`.
    - `mergeable`: what GitHub says about merging the branch. Default
      `MERGEABLE`.
    - `unknown`: how many reads answer `UNKNOWN` for `mergeable` before the value
      above, since GitHub computes it in the background and a read can arrive
      first. Default `0`.
    - `branch`: the head's name, where it is not a loop's. Default
      `claude/issue-<number>`.
    - `base`: the base's name, where it is not trunk — which is what a layer of
      a stack looks like from here. Default `main`.
    - `layer`: whether the pull request is a layer of a stack, which the
      `pulls/{number}` endpoint answers with a `stack` object. Default `False`.
    - `stack`: the number of that stack, as the endpoint reports it. Default `1`.

    `linked` collects the argument vector of every `stack link` call, so a
    probe can read what the verb named.
    - `issue`: the Challenge the branch names, as `{state, level, unreadable}`,
      read before a dispatch (solorepo's DR-142). Open and `medium` unless set,
      since the branch's number is the Issue's here; `unreadable` makes
      `issue view` fail as it does for an Issue deleted or transferred under its
      branch.
    - `verdicts`: every review on the pull request as `(login, state)`, oldest
      first, which is the order GitHub lists them in and so the order the newest
      is read off. Default `[]`.
    - `checks`: the `statusCheckRollup` `pr view` answers. Absent from
      `pr list`, as it is from GitHub's (solorepo's DR-153). Default `[]`.
    - `updatedAt`: an ISO timestamp. Default two hours ago, so a pull request is
      idle unless a case says otherwise.
    - `layer`: whether the pull request is in a stack. The pulls endpoint answers
      with a `stack` object on every layer of a stack, the bottom included, and
      on nothing else, which is what `merge --auto` reads it for (solorepo's #117).
      Default `False`.
    - `drops_review`: whether a stack rebase drops reviewer requests from `requested`.
      Default `False`.
    - `state`: `OPEN`, or `MERGED` once a landing sets it.

    The head commit is held as a value, `head<number>`, and moved to
    `moved<number>` by a rebase and `pushed<number>` by a push, because GitHub
    moves it when a rebase lands and that is what `advance` reads the rebase
    off. The keyword sets are collections of numbers:

    - `no_rebase`: `update-branch` exits with GitHub's refusal over conflicts.
    - `no_arm`: `pr merge --auto` exits with "Pull request is in clean status".
    - `no_stick`: `pr merge --auto` exits 0 and the arming does not take — the
      one arming outcome an exit code cannot see, and so the only one a
      read-back is for (solorepo's #93).
    - `lands`: the last check goes green in the window between arming and the
      read-back, so GitHub merges; the read-back finds `MERGED` and unarmed
      (solorepo's #253).
    - `blip`: one HTTP error, once, on the `compare` that reads a rebase back.
      A transient is what an API blip is, and the cheapest way into "`advance`
      failed and the branch is fine": the refusal is real, the rebase already
      happened, and nothing about the head is wrong.
    - `no_dispatch`: `workflow run` exits as GitHub answers a coder token
      without the Actions write it needs.
    - `no_stack`: the stack whose bottom layer has this number refuses its
      cascading rebase before moving any layer.
    - `no_edit`: `pr edit` exits as GitHub answers a token without the
      repository write a review request needs.
    - `no_edit_sticks`: `pr edit` exits 0 and the reviewer assignment does not
      take — the one reviewer-request outcome an exit code cannot see, and so
      the only one a read-back is for.
    - `no_view`: `pr view` of that number exits with a transport failure, which
      is how the re-read `mergeability` makes for an `UNKNOWN` answer fails.
      `pr list` still answers for it, since the list is one call for every pull
      request and a sweep reads its pull requests off that.

    What a run leaves behind: `pulls`, as the calls left them; `reads`, how many
    `pr view` reads each number took; `dispatched`, every dispatch as
    `(number, task)` in order — the task because `coder.yml` defaults it to
    `review`, so a dispatch that lost it would run the review-answering pass on
    a pull request with no verdict to answer and rebase nothing, the one
    mutation a probe reading the number alone cannot see; `edited`, the numbers
    `pr edit` touched; `checked_out`, the branch arguments passed to `stack
    checkout`; `stack_rebases`, the root pull request numbers of stacks that
    rebased; `stack_rebase_args`, the flags passed to `stack rebase`; and
    `pushed_stacks`, the count of `stack push` invocations. A dispatch of any
    workflow but `coder.yml`, and any call this fake has no answer for, raise
    `AssertionError` naming the call, which `outcome` reports as text.
    """

    pulls: dict[str, dict[str, Any]]
    reads: dict[str, int]
    dispatched: list[tuple[str, str | None]]
    linked: list[tuple[Any, ...]]
    edited: list[str]
    stack_rebases: list[str]
    stack_rebase_args: list[tuple[Any, ...]]
    checked_out: list[tuple[Any, ...]]
    pushed_stacks: int
    no_rebase: set[str]
    no_arm: set[str]
    no_stick: set[str]
    lands: set[str]
    blip: set[str]
    no_dispatch: set[str]
    no_stack: set[str]
    no_edit: set[str]
    no_edit_sticks: set[str]
    no_view: set[str]
    REFUSALS = ("no_rebase", "no_arm", "no_stick", "lands", "blip", "no_dispatch", "no_stack", "no_edit", "no_edit_sticks", "no_view")
    """The keywords `__init__` takes beside `pulls`, each the numbers one call answers as the class docstring says."""

    def __init__(self, pulls: dict[int, dict[str, Any]], **refused: list[int]) -> None:
        unknown = set(refused) - set(self.REFUSALS)
        if unknown:
            raise TypeError(UNKNOWN_REFUSALS.format(known=", ".join(self.REFUSALS),
                                                    unknown=", ".join(sorted(unknown))))
        self.pulls = {str(n): dict(p) for n, p in pulls.items()}
        self.reads = {}
        for number, pull in self.pulls.items():
            pull.setdefault("head", f"head{number}")
        for name in self.REFUSALS:
            setattr(self, name, {str(n) for n in refused.get(name, ())})
        self.dispatched = []
        self.linked = []
        self.edited = []
        self.stack_rebases = []
        self.stack_rebase_args = []
        self.checked_out = []
        self.pushed_stacks = 0
        self.comments: dict[str, list[dict[str, Any]]] = {}
        self.posted_comments: list[tuple[str, str]] = []
        self.cleared_comments: list[str] = []

    def view(self, number: int | str) -> dict[str, Any]:
        """One `pr view` of `number`, counted in `reads`, as GitHub would answer it at this moment.

        `mergeable` is `UNKNOWN` while the pull request's `unknown` reads
        remain, counted down here rather than in the caller, because what is
        modelled is GitHub answering the same question differently over time.
        The head, the arming and the state are the stale object while `slow`
        reads remain, and the merge commit follows the state shown, since a
        pull request GitHub still reports as open has none. And when `pushed`
        reaches zero on this read, the outside push lands at its end: the head
        moves, the old commit is kept for the `compare` of its oid, and
        `behind` becomes `leaves`.
        """
        self.reads[str(number)] = self.reads.get(str(number), 0) + 1
        pull = self.pulls[str(number)]
        if pull.get("unknown"):
            pull["unknown"] -= 1
            mergeable = "UNKNOWN"
        else:
            mergeable = pull.get("mergeable", "MERGEABLE")
        was, reads = pull.get("stale") or (pull, 0)
        if reads:
            pull["stale"] = (was, reads - 1)
        shown = was if reads else pull
        merged = shown.get("state") == "MERGED"
        answer = {"number": int(number), "title": f"pull {number}",
                  "state": shown.get("state", "OPEN"),
                  "mergeCommit": {"oid": f"merged{number}"} if merged else None,
                  "baseRefName": pull.get("base", "main"),
                  "headRefName": pull.get("branch", f"claude/issue-{number}"),
                  "headRefOid": shown["head"],
                  "reviewRequests": [{"login": who} for who in pull.get("requested") or []],
                  "reviews": [{"author": {"login": who}, "state": state}
                              for who, state in pull.get("verdicts") or []],
                  "mergeable": mergeable,
                  "autoMergeRequest": {"enabledAt": "now"} if shown["armed"] else None,
                  "statusCheckRollup": pull.get("checks", []),
                  "comments": list(self.comments.get(str(number), [])),
                  "updatedAt": pull.get("updatedAt", (datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)).isoformat())}
        if pull.get("pushed"):
            pull["pushed"] -= 1
            if not pull["pushed"]:
                pull["stale"] = (dict(pull), 0)
                pull["head"] = f"pushed{number}"
                pull["behind"] = pull.get("leaves", pull["behind"])
        return answer

    def __call__(self, *args: Any, parse: bool = True, **kwargs: Any) -> Any:
        """One `gh` call, answered from the dict.

        `repo view` is `o/r` with branches deleted on merge, so a Role's login
        as `channel.role_login` composes it is `o-r-<role>`
        (solorepo's DR-107), which is what a case's `requested` and `verdicts`
        spell for the verb to recognise the reviewer. `pr list` is every
        pull request as `view` answers it, less `statusCheckRollup`
        (solorepo's DR-153). `pr view` refuses a number in `no_view`, where
        `pr list` does not, so a case can refuse the re-read `mergeability`
        makes without refusing the list the sweep reads its pull requests off.
        `pr update-branch` refuses a number in `no_rebase`,
        and otherwise keeps the pull request as it was for `slow` reads and for
        the `compare` of the head it has not moved yet, then sets `behind` to
        `again`, drops the arming where `drops` says, and moves the head.
        `pr edit` refuses a number in `no_edit`, and otherwise applies
        `--remove-reviewer` and `--add-reviewer` to `requested`, so what a
        probe reads back is what GitHub would be holding rather than the call
        the verb made. `pr merge` refuses a number in
        `no_arm`, and otherwise lags the arming it shows behind the arming it
        holds by `slow` reads, sets the arming unless the number is in
        `no_stick`, and merges it if in `lands`. `workflow run coder.yml`
        refuses a number in `no_dispatch` and otherwise records
        `(pull_request, task)`. `api .../compare/...` answers about the commit it
        was asked about: the head GitHub has not moved yet is behind by what it
        was behind by before the rebase, which is the true answer to the wrong
        question and what solorepo's #245 read as a rebase that had not
        happened; a number in `blip` gets one rate-limit exit first, once its
        rebase has happened. `issue view` answers the branch's Challenge. Any
        other `api` call answers the `stack` object for a layer, or the
        repository's own settings.
        """
        head = args[:2]
        if head == ("repo", "view"):
            return {"nameWithOwner": "o/r", "deleteBranchOnMerge": True}
        if head == ("pr", "list"):
            return [{k: v for k, v in self.view(n).items() if k != "statusCheckRollup"} for n in self.pulls]
        if head == ("pr", "view"):
            if str(args[2]) in self.no_view:
                sys.exit("gh: Post https://api.github.com/graphql: net/http: TLS handshake timeout")
            return self.view(args[2])
        if head == ("stack", "link"):
            self.linked.append(tuple(args[2:]))
            return ""
        if head == ("stack", "checkout"):
            self.checked_out.append(args[2:])
            return ""
        if head == ("stack", "rebase"):
            return self.stack_rebase(args)
        if head == ("stack", "push"):
            self.pushed_stacks += 1
            return ""
        if head == ("workflow", "run") and args[2] == "coder.yml":
            return self.dispatch(args)
        if args[0] == "api":
            return self.api(*args[1:])
        answered = {("pr", "update-branch"): self.update_branch, ("pr", "edit"): self.edit,
                    ("pr", "merge"): self.merge, ("issue", "view"): self.issue}
        if head in answered:
            return answered[head](args)
        raise unanswered(args)

    def update_branch(self, args: Any) -> str:
        """`pr update-branch`: refused for a number in `no_rebase`; otherwise the rebase, shown after `slow` reads."""
        number = str(args[2])
        if number in self.no_rebase:
            sys.exit("gh: the branch has conflicts that must be resolved")
        pull = self.pulls[number]
        pull["stale"] = (dict(pull), pull.get("slow", 0))
        pull["behind"] = pull.get("again", 0)
        pull["armed"] = pull["armed"] and not pull.get("drops")
        pull["head"] = f"moved{number}"
        pull["rebased"] = True
        return ""

    def stack_rebase(self, args: tuple[Any, ...]) -> str:
        """Rebase every layer in the checked-out stack, or refuse before moving one."""
        if not self.checked_out:
            raise AssertionError(STACK_UNCHECKED_OUT)
        branch = self.checked_out[-1][0]
        root = next((number for number, pull in self.pulls.items()
                     if pull.get("branch", f"claude/issue-{number}") == branch), None)
        if root is None:
            raise AssertionError(STACK_UNKNOWN_BRANCH.format(branch=branch))
        if root in self.no_stack:
            sys.exit("gh: the stack has conflicts that must be resolved")
        self.stack_rebases.append(root)
        self.stack_rebase_args.append(args[2:])
        chain = [root]
        while True:
            head_branch = self.pulls[chain[-1]].get("branch", f"claude/issue-{chain[-1]}")
            above = [number for number, pull in self.pulls.items()
                     if pull.get("layer") and pull.get("base") == head_branch]
            if not above:
                break
            chain.append(above[0])
        moved_below = False
        for number in chain:
            pull = self.pulls[number]
            if pull.get("behind", 0) > 0 or moved_below:
                moved_below = True
                pull["stale"] = (dict(pull), pull.get("slow", 0))
                pull["behind"] = pull.get("again", 0)
                pull["head"] = f"moved{number}"
                pull["rebased"] = True
                pull["armed"] = pull["armed"] and not pull.get("drops")
                if pull.get("drops_review"):
                    pull["requested"] = []
        return ""

    def edit(self, args: Any) -> str:
        """`pr edit`: refused for a number in `no_edit`; otherwise `--remove-reviewer` and `--add-reviewer` applied to `requested` (unless in `no_edit_sticks`), the number recorded in `edited`."""
        number = str(args[2])
        if number in self.no_edit:
            sys.exit("gh: Could not add requested reviewers")
        self.edited.append(number)
        pull = self.pulls[number]
        asked = list(pull.get("requested") or [])
        for flag in ("--remove-reviewer", "--add-reviewer"):
            if flag in args:
                who = args[args.index(flag) + 1]
                if flag == "--remove-reviewer" and who in asked:
                    asked.remove(who)
                elif (flag == "--add-reviewer" and who not in asked
                      and number not in self.no_edit_sticks):
                    asked.append(who)
        pull["requested"] = asked
        return ""

    def merge(self, args: Any) -> str:
        """`pr merge --auto`: refused for a number in `no_arm`; otherwise armed unless in `no_stick`, and merged if in `lands`."""
        number = str(args[2])
        if number in self.no_arm:
            sys.exit("gh: Pull request is in clean status")
        pull = self.pulls[number]
        pull["stale"] = (dict(pull), pull.get("slow", 0))
        pull["armed"] = number not in self.no_stick
        if number in self.lands:
            pull.update(state="MERGED", armed=False)
        return ""

    def dispatch(self, args: Any) -> str:
        """`workflow run coder.yml`: refused for a number in `no_dispatch`; otherwise `(number, task)` recorded in `dispatched`."""
        number = next(a.split("=", 1)[1] for a in args if a.startswith("pull_request="))
        task = next((a.split("=", 1)[1] for a in args if a.startswith("task=")), None)
        if number in self.no_dispatch:
            sys.exit("gh: Resource not accessible by personal access token")
        self.dispatched.append((number, task))
        return ""

    def compare(self, endpoint: str) -> dict[str, Any]:
        """`api .../compare/...`: how far behind the commit asked about is, with one rate-limit exit first for a number in `blip`."""
        oid = endpoint.rsplit("...", 1)[1]
        number = oid.removeprefix("head").removeprefix("moved").removeprefix("pushed")
        if number in self.blip and self.pulls[number].get("rebased"):
            self.blip.discard(number)
            sys.exit("gh: API rate limit exceeded")
        pull = self.pulls[number]
        was, _ = pull.get("stale") or (pull, 0)
        return {"behind_by": pull["behind"] if oid == pull["head"] else was["behind"]}

    def issue(self, args: Any) -> dict[str, Any]:
        """`issue view`: the branch's Challenge, or the CLI's exit where the case marks it unreadable."""
        issue = self.pulls[str(args[2])].get("issue") or {}
        if issue.get("unreadable"):
            sys.exit("gh: Could not resolve to an issue or pull request")
        return {"state": issue.get("state", "OPEN"),
                "labels": [{"name": "challenge"}, {"name": issue.get("level", "medium")}]}

    def api(self, endpoint: str, *rest: str) -> Any:
        """Any other `api` call: the compare, the `stack` object of a layer, issue comments, or the repository's own settings."""
        if "/compare/" in endpoint:
            return self.compare(endpoint)
        if "/pulls/" in endpoint:
            pull = self.pulls.get(endpoint.rsplit("/", 1)[-1]) or {}
            return {"stack": {"id": 1, "number": pull.get("stack", 1)}} if pull.get("layer") else {}
        if "/issues/" in endpoint and endpoint.endswith("/comments"):
            pr_str = endpoint.split("/issues/")[1].split("/comments")[0]
            if "-f" in rest:
                body = rest[rest.index("-f") + 1].removeprefix("body=")
                comments = self.comments.setdefault(pr_str, [])
                new_id = len(comments) + 1
                entry = {"id": new_id, "body": body, "user": {"login": "o-r-coder"}}
                comments.append(entry)
                self.posted_comments.append((pr_str, body))
                return {"id": new_id, "html_url": f"https://github.com/o/r/pull/{pr_str}#issuecomment-{new_id}"}
            return list(self.comments.get(pr_str, []))
        if "/issues/comments/" in endpoint:
            c_id = int(endpoint.rsplit("/", 1)[-1])
            if "-X" in rest and rest[rest.index("-X") + 1] == "DELETE":
                for pr_str, c_list in list(self.comments.items()):
                    self.comments[pr_str] = [c for c in c_list if c.get("id") != c_id]
                self.cleared_comments.append(str(c_id))
                return ""
            if "-X" in rest and rest[rest.index("-X") + 1] == "PATCH":
                body = rest[rest.index("-f") + 1].removeprefix("body=")
                for c_list in self.comments.values():
                    for c in c_list:
                        if c.get("id") == c_id:
                            c["body"] = body
                return {"id": c_id, "html_url": f"https://github.com/o/r/issues/comments/{c_id}"}
            return ""
        return {"allow_auto_merge": True}

class WatchGitHub:
    """GitHub as `check_pr.py --watch` polls it: one answer per poll, off a list.

    A poll is `(state, mergeable)` and nothing else, because what is probed is
    the one change that produces no comment, no review, no thread and no
    check — so every other thing a snapshot holds is empty here, and a list
    that runs out answers `MERGED`, which is how the watch is made to end.

    `pr view` asked for the number alone, which is how `pull` reaches the
    threads query, answers `7`; asked for everything, it answers the next poll.
    One shape answers both GraphQL reads the snapshot makes: the threads query
    wants `reviewThreads` and `reviews`, and the rollup query — which took the
    checks off `pr view` (solorepo's #230) — wants `commits`, whose absence
    `checks_of` reads as a head with no checks on it, the empty this fake wants
    anyway.
    """

    def __init__(self, polls: Iterable[tuple[str, str]]) -> None:
        self.polls = list(polls)

    def __call__(self, *args: Any) -> Any:
        """One `gh` call: the repository, a pull request read, or a GraphQL query, as the class docstring says."""
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("pr", "view"):
            if args[-1] == "number":
                return {"number": 7}
            state, mergeable = self.polls.pop(0) if self.polls else ("MERGED", "MERGEABLE")
            return {"number": 7, "state": state, "comments": [], "reviews": [],
                    "mergeable": mergeable}
        if args[0] == "api":
            return {"data": {"repository": {"pullRequest": {
                "reviewThreads": {"nodes": []}, "reviews": {"nodes": []}}}}}
        raise unanswered(args)
