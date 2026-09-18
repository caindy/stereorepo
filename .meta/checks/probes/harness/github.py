"""GitHub stood in for: answered from a dict for the verbs that rebase, arm, hand off and dispatch, and from a list of polls for `--watch` (solorepo's DR-158).
"""
import datetime
import sys


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

    What a run leaves behind: `pulls`, as the calls left them; `reads`, how many
    `pr view` reads each number took; `dispatched`, every dispatch as
    `(number, task)` in order — the task because `coder.yml` defaults it to
    `review`, so a dispatch that lost it would run the review-answering pass on
    a pull request with no verdict to answer and rebase nothing, the one
    mutation a probe reading the number alone cannot see; and `edited`, the
    numbers `pr edit` touched. A dispatch of any workflow but `coder.yml`, and
    any call this fake has no answer for, raise `AssertionError` naming the
    call, which `outcome` reports as text.
    """

    REFUSALS = ("no_rebase", "no_arm", "no_stick", "lands", "blip", "no_dispatch")
    """The keywords `__init__` takes beside `pulls`, each the numbers one call answers as the class docstring says."""

    def __init__(self, pulls, **refused):
        unknown = set(refused) - set(self.REFUSALS)
        if unknown:
            raise TypeError(f"FakeGitHub takes {', '.join(self.REFUSALS)}, not {', '.join(sorted(unknown))}")
        self.pulls = {str(n): dict(p) for n, p in pulls.items()}
        self.reads = {}
        for number, pull in self.pulls.items():
            pull.setdefault("head", f"head{number}")
        for name in self.REFUSALS:
            setattr(self, name, {str(n) for n in refused.get(name, ())})
        self.dispatched = []
        self.linked = []
        self.edited = []

    def view(self, number):
        """One `pr view` of `number`, counted in `reads`, as GitHub would answer it at this moment.

        `mergeable` is `UNKNOWN` while the pull request's `unknown` reads
        remain, counted down here rather than in the caller, because what is
        modelled is GitHub answering the same question differently over time.
        The head, the arming and the state are the stale object while `slow`
        reads remain. And when `pushed` reaches zero on this read, the outside
        push lands at its end: the head moves, the old commit is kept for the
        `compare` of its oid, and `behind` becomes `leaves`.
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
        answer = {"number": int(number), "title": f"pull {number}",
                  "state": shown.get("state", "OPEN"),
                  "mergeCommit": {"oid": f"merged{number}"},
                  "baseRefName": pull.get("base", "main"),
                  "headRefName": pull.get("branch", f"claude/issue-{number}"),
                  "headRefOid": shown["head"],
                  "reviewRequests": [{"login": who} for who in pull.get("requested") or []],
                  "reviews": [{"author": {"login": who}, "state": state}
                              for who, state in pull.get("verdicts") or []],
                  "mergeable": mergeable,
                  "autoMergeRequest": {"enabledAt": "now"} if shown["armed"] else None,
                  "statusCheckRollup": pull.get("checks", []),
                  "updatedAt": pull.get("updatedAt", (datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)).isoformat())}
        if pull.get("pushed"):
            pull["pushed"] -= 1
            if not pull["pushed"]:
                pull["stale"] = (dict(pull), 0)
                pull["head"] = f"pushed{number}"
                pull["behind"] = pull.get("leaves", pull["behind"])
        return answer

    def __call__(self, *args, parse=True, **kwargs):
        """One `gh` call, answered from the dict.

        `repo view` is `o/r` with branches deleted on merge, so a Role's login
        as `channel.role_login` composes it is `o-r-<role>`
        (solorepo's DR-107), which is what a case's `requested` and `verdicts`
        spell for the verb to recognise the reviewer. `pr list` is every
        pull request as `view` answers it, less `statusCheckRollup`
        (solorepo's DR-153). `pr update-branch` refuses a number in `no_rebase`,
        and otherwise keeps the pull request as it was for `slow` reads and for
        the `compare` of the head it has not moved yet, then sets `behind` to
        `again`, drops the arming where `drops` says, and moves the head.
        `pr edit` applies `--remove-reviewer` and `--add-reviewer` to
        `requested`, so what a probe reads back is what GitHub would be holding
        rather than the call the verb made. `pr merge` refuses a number in
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
            return self.view(args[2])
        if head == ("stack", "link"):
            self.linked.append(tuple(args[2:]))
            return ""
        if head == ("workflow", "run") and args[2] == "coder.yml":
            return self.dispatch(args)
        if args[0] == "api":
            return self.api(args[1])
        answered = {("pr", "update-branch"): self.update_branch, ("pr", "edit"): self.edit,
                    ("pr", "merge"): self.merge, ("issue", "view"): self.issue}
        if head in answered:
            return answered[head](args)
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")

    def update_branch(self, args):
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

    def edit(self, args):
        """`pr edit`: `--remove-reviewer` and `--add-reviewer` applied to `requested`, the number recorded in `edited`."""
        number = str(args[2])
        self.edited.append(number)
        pull = self.pulls[number]
        asked = list(pull.get("requested") or [])
        for flag in ("--remove-reviewer", "--add-reviewer"):
            if flag in args:
                who = args[args.index(flag) + 1]
                if flag == "--remove-reviewer" and who in asked:
                    asked.remove(who)
                elif flag == "--add-reviewer" and who not in asked:
                    asked.append(who)
        pull["requested"] = asked
        return ""

    def merge(self, args):
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

    def dispatch(self, args):
        """`workflow run coder.yml`: refused for a number in `no_dispatch`; otherwise `(number, task)` recorded in `dispatched`."""
        number = next(a.split("=", 1)[1] for a in args if a.startswith("pull_request="))
        task = next((a.split("=", 1)[1] for a in args if a.startswith("task=")), None)
        if number in self.no_dispatch:
            sys.exit("gh: Resource not accessible by personal access token")
        self.dispatched.append((number, task))
        return ""

    def compare(self, endpoint):
        """`api .../compare/...`: how far behind the commit asked about is, with one rate-limit exit first for a number in `blip`."""
        oid = endpoint.rsplit("...", 1)[1]
        number = oid.removeprefix("head").removeprefix("moved").removeprefix("pushed")
        if number in self.blip and self.pulls[number].get("rebased"):
            self.blip.discard(number)
            sys.exit("gh: API rate limit exceeded")
        pull = self.pulls[number]
        was, _ = pull.get("stale") or (pull, 0)
        return {"behind_by": pull["behind"] if oid == pull["head"] else was["behind"]}

    def issue(self, args):
        """`issue view`: the branch's Challenge, or the CLI's exit where the case marks it unreadable."""
        issue = self.pulls[str(args[2])].get("issue") or {}
        if issue.get("unreadable"):
            sys.exit("gh: Could not resolve to an issue or pull request")
        return {"state": issue.get("state", "OPEN"),
                "labels": [{"name": "challenge"}, {"name": issue.get("level", "medium")}]}

    def api(self, endpoint):
        """Any other `api` call: the compare, the `stack` object of a layer, or the repository's own settings."""
        if "/compare/" in endpoint:
            return self.compare(endpoint)
        if "/pulls/" in endpoint:
            pull = self.pulls.get(endpoint.rsplit("/", 1)[-1]) or {}
            return {"stack": {"id": 1, "number": pull.get("stack", 1)}} if pull.get("layer") else {}
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

    def __init__(self, polls):
        self.polls = list(polls)

    def __call__(self, *args):
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
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")
