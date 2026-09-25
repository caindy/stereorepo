"""GitHub stood in for: answered from a dict for the verbs that rebase, arm, hand off and dispatch, and from a list of polls for `--watch` (solorepo's DR-158).
"""
import datetime
import json
import subprocess
import sys
from collections.abc import Iterable, Sequence
from typing import Any

from checks.probes.harness.acts import unanswered

UNKNOWN_REFUSALS = "FakeGitHub takes {known}, not {unknown}"
"""What construction raises on a keyword outside `FakeGitHub.REFUSALS`."""

STACK_UNCHECKED_OUT = "gh stack rebase called without preceding gh stack checkout"
"""What a stack rebase raises where nothing checked the stack out first."""

STACK_UNKNOWN_BRANCH = "gh stack rebase: branch {branch!r} not found in fake pulls"
"""What a stack rebase raises where the checked-out branch names no pull request this fake holds."""


NOT_FOUND = "gh: Not Found (HTTP 404)"
"""What `gh api` says of a ref or tag GitHub does not hold, which `lock_read` reads as an answer."""

UNREADABLE = "gh: HTTP 500: Internal Server Error"
"""What `gh` says of a read GitHub would not answer at all, which `lock_read` raises on."""


class GitStore:
    """The git object store the merge manager's lock is taken in (solorepo's DR-267).

    Enough of GitHub for the compare-and-set `take_merge_lock` turns on: a tag
    object is written and kept under the sha it is answered with, a ref is
    created once and refused with GitHub's own words after that, and `DELETE`
    drops it. `refs`, `tags` and `runs` are the store, so a case seeds a lock
    already held by writing into them and reads back what a run left; a run
    nothing names is answered `in_progress`, which is a holder still alive, and
    a run named with None is one GitHub will not answer for.

    A read of something the store does not hold fails the way `channel.gh`
    fails, rather than raising out of a subscript: it raises what
    `tolerate_fail` raises, answers `default` where one was given, and exits
    otherwise. That is what lets a case seed a ref standing at no tag — the
    state `take_merge_lock` breaks on sight — rather than stopping the probe.

    `unreadable` is the other failure, which a 404 is not: it maps a mark in an
    endpoint to the number of reads answered before that endpoint stops being
    answered at all, so a case seeds a GitHub that refuses the lock read from
    the first call, or one that answers the take's read-back and refuses the
    release's. The two failures want opposite acts of the lock, and only a store
    that can raise both observes it making the distinction. `FakeGitHub`
    consults the same marks against the calls it answers itself, so the mark,
    the countdown and the failure are one mechanism and not two.

    It stands beside a `gh` rather than inside one: `FakeGitHub` holds one, and
    so does every hand-written stub in a probe that reaches the real
    `merge_manager`, which takes the lock before it evaluates anything.
    """

    def __init__(self) -> None:
        self.refs: dict[str, str] = {}
        self.tags: dict[str, dict[str, Any]] = {}
        self.runs: dict[str, str | None] = {}
        self.unreadable: dict[str, int] = {}

    @staticmethod
    def asked(args: Iterable[Any]) -> bool:
        """Whether this `gh` call is the store's, which is the test a stub delegates on."""
        call = [str(a) for a in args]
        if call[:2] == ["run", "view"]:
            return True
        return bool(call[:1] == ["api"] and len(call) > 1
                    and ("/git/" in call[1] or call[1].endswith("/commits/main")))

    def __call__(self, *args: Any, parse: bool = True, **kwargs: Any) -> Any:
        """One call the store answers: trunk's head, a run's status, or a tag or ref of the lock.

        `parse` is honoured as `channel.gh` honours it, answering text rather
        than an object, because the wrappers forward it and the lock's create
        and delete both pass it.
        """
        if args[:2] == ("run", "view"):
            status = self.runs.get(str(args[2]), "in_progress")
            return {"status": status} if status else self.failing(args, kwargs, UNREADABLE)
        endpoint, rest = str(args[1]), [str(a) for a in args[2:]]
        return self.unparsed(self.answer(endpoint, rest, args, kwargs), parse)

    @staticmethod
    def unparsed(answer: Any, parse: bool) -> Any:
        """What `gh` answers for this call, as text where the caller asked for no parse."""
        if parse or isinstance(answer, str):
            return answer
        return json.dumps(answer)

    def answer(self, endpoint: str, rest: list[str], args: Any, kwargs: dict[str, Any]) -> Any:
        """One `api` call: trunk's head, a tag read or written, or a ref created, read or dropped.

        Parameters:
            endpoint (str): The `gh api` path.
            rest (list): The call's arguments after the endpoint, which the
                fields and `-X` are read from.
            args (tuple): The whole `gh` call, for a failure to name.
            kwargs (dict): The call's keywords, which say what a failure is owed.

        Returns:
            Any: What GitHub would answer, or what the failure is owed.
        """
        if endpoint.endswith("/commits/main"):
            return "trunk"
        if self.refusing(endpoint):
            return self.failing(args, kwargs, UNREADABLE)
        fields = dict(f.split("=", 1) for f in rest if "=" in f)
        if "/git/tags/" in endpoint:
            held = self.tags.get(endpoint.rsplit("/", 1)[-1])
            return dict(held) if held else self.missing(args, kwargs)
        if endpoint.endswith("/git/tags"):
            return self.tag(fields)
        if endpoint.endswith("/git/refs"):
            if fields["ref"] in self.refs:
                sys.exit("gh: HTTP 422: Reference already exists")
            self.refs[fields["ref"]] = fields["sha"]
            return {"ref": fields["ref"], "object": {"sha": fields["sha"]}}
        named = endpoint.split("/git/", 1)[1].split("/", 1)[1]
        return self.ref(f"refs/{named}", rest, args, kwargs)

    def refusing(self, endpoint: str) -> bool:
        """Whether this read is one GitHub will not answer, counting down what it answers first."""
        for mark, answered in self.unreadable.items():
            if mark not in endpoint:
                continue
            if answered:
                self.unreadable[mark] = answered - 1
                return False
            return True
        return False

    def missing(self, args: Any, kwargs: dict[str, Any]) -> Any:
        """Fail a read of what the store does not hold, carrying GitHub's own 404."""
        return self.failing(args, kwargs, NOT_FOUND)

    @staticmethod
    def failing(args: Any, kwargs: dict[str, Any], said: str) -> Any:
        """Fail one read as `channel.gh` fails one, which is what the caller's keywords decide.

        Parameters:
            args (tuple): The `gh` call, which the raised failure names.
            kwargs (dict): The call's keywords, `tolerate_fail` and `default`
                being the two that say what a failure is owed.
            said (str): What `gh` puts on standard error, which `lock_read`
                classifies the failure by.

        Returns:
            Any: The caller's `default`, where it gave one.

        Raises:
            subprocess.CalledProcessError: Under `tolerate_fail`, carrying
                `said` on standard error.
            SystemExit: Where the caller gave neither.
        """
        if kwargs.get("tolerate_fail"):
            raise subprocess.CalledProcessError(
                1, ["gh", *[str(a) for a in args]], output="", stderr=said)
        if "default" in kwargs:
            return kwargs["default"]
        sys.exit(said)

    def tag(self, fields: dict[str, str]) -> dict[str, Any]:
        """Write a tag object, kept under the sha it is answered with, tagged at this moment."""
        sha = f"tag{len(self.tags) + 1}"
        self.tags[sha] = {"sha": sha, "message": fields.get("message", ""),
                          "tagger": {"date": datetime.datetime.now(datetime.UTC).isoformat()}}
        return dict(self.tags[sha])

    def ref(self, ref: str, rest: list[str], args: Any, kwargs: dict[str, Any]) -> Any:
        """Read or drop one ref; one nobody holds fails as GitHub's 404 does.

        Parameters:
            ref (str): The fully qualified ref, as `refs` keys it.
            rest (list): The call's arguments after the endpoint, which `-X` is read from.
            args (tuple): The whole `gh` call, for a failure to name.
            kwargs (dict): The call's keywords, which say what a 404 is owed.

        Returns:
            Any: The ref object, the empty string for a delete, or `missing`'s answer.
        """
        verb = rest[rest.index("-X") + 1] if "-X" in rest else "GET"
        if verb == "DELETE":
            self.refs.pop(ref, None)
            return ""
        if ref not in self.refs:
            return self.missing(args, kwargs)
        return {"ref": ref, "object": {"sha": self.refs[ref], "type": "tag"}}


class LockedGitHub:
    """A `gh` stub, with the lock answered from a `GitStore` beside it (solorepo's DR-267).

    Every probe reaching the real `merge_manager` meets the lock, which is taken
    before anything is evaluated; a stub answering the empty dict to calls it
    does not know would answer a tag object with no sha. Wrapping is what a stub
    written before the lock needs, and `lock` is the store, so a case seeds a
    holder and reads back what the run left.
    """

    def __init__(self, gh: Any) -> None:
        self.gh, self.lock = gh, GitStore()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """One `gh` call: the store's where it answers, and the wrapped stub's otherwise."""
        if self.lock.asked(args):
            return self.lock(*args, **kwargs)
        return self.gh(*args, **kwargs)


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
    - `draft`: whether the pull request is a draft, which GitHub answers as
      `isDraft` and which `advance` reads to hold a Seed Commit out of a rebase
      that would replay it away (solorepo's DR-273). Default `False`.
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
    - `mergeStateStatus`: GitHub's word for what stops the merge — `BEHIND` for
      a branch out of date against a base that requires currency. Default
      unset, which is what every caller that does not ask about it already saw.
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
    - `verdicts`: every review on the pull request as `(login, state)` or
      `(login, state, body)`, oldest first, which is the order GitHub lists them
      in and so the order the newest is read off. The body is empty where a case
      does not give one, which is what a `COMMENTED` reply on a thread looks
      like and what tells it from a comment verdict (solorepo's DR-265).
      They fill both listings `pr view` answers with: `reviews` is all of them
      and `latestReviews` the newest per author, as GitHub composes the pair,
      so a reader that consults one and not the other is read here on the shape
      it meets in production. Default `[]`.
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
    - `runs`: the `review.yml` runs `gh run list` answers for the head branch,
      each `(headSha, status)`, which is what `request-review` reads to tell a
      request a run already answers from a stale one (solorepo's #950). Default
      `[]`, which is no run, and what any workflow but `review.yml` is answered.
    - `reviewed`: the reviews the reviews endpoint answers, each
      `(login, commit_id)` or `(login, commit_id, state, body)`, since the
      commit a review names is the one field `pr view --json reviews` does not
      carry, and since the bodiless `COMMENTED` wrapper and the `DISMISSED`
      verdict are shapes a reader of that endpoint must drop. Default a
      standing `CHANGES_REQUESTED` with a body, and `[]` for no review at all.

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
    rebased; `stack_rebase_args`, the flags passed to `stack rebase`;
    `pushed_stacks`, the count of `stack push` invocations; and `git`, the
    `GitStore` the merge manager's lock is taken in, which a case seeds and
    reads back. A dispatch of any workflow but `coder.yml`, and any call this
    fake has no answer for, raise `AssertionError` naming the call, which
    `outcome` reports as text.

    The store's `unreadable` marks reach every call this fake answers itself
    and not the store's own endpoints alone. A mark is any text in the call as
    it was typed — `/reviews`, `run list` — and a call it matches is refused
    with the caller's `default`, which is the ordinary failure a 403, a rate
    limit or a 5xx arrives as (`.meta/lib/gh.py:81-82`) rather than the hang
    that raises `GhTimeout` before a `default` is read.
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
        self.git = GitStore()

    def view(self, number: int | str, asked: Sequence[str] = ()) -> dict[str, Any]:
        """One `pr view` of `number`, counted in `reads`, as GitHub would answer it at this moment.

        `asked` is the value of the call's `--json`, and only those fields are
        answered, as GitHub answers only those: a caller that reads a field it
        did not ask for reads `None` here as it would there, so a field
        dropped from one of the verbs' constants is a probe that fails rather
        than a payload that quietly still carries it. An empty `asked` is
        every field, which is what a caller with no `--json` gets.

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
        reviews = [{"author": {"login": given[0]}, "state": given[1],
                    "body": given[2] if len(given) > 2 else ""}
                   for given in pull.get("verdicts") or []]
        newest: dict[str, dict[str, Any]] = {}
        for review in reviews:
            newest[review["author"]["login"]] = review
        answer = {"number": int(number), "title": f"pull {number}",
                  "state": shown.get("state", "OPEN"),
                  "mergeCommit": {"oid": f"merged{number}"} if merged else None,
                  "baseRefName": pull.get("base", "main"),
                  "headRefName": pull.get("branch", f"claude/issue-{number}"),
                  "headRefOid": shown["head"],
                  "reviewRequests": [{"login": who} for who in pull.get("requested") or []],
                  "reviews": reviews,
                  "latestReviews": list(newest.values()),
                  "mergeable": mergeable,
                  "mergeStateStatus": pull.get("mergeStateStatus"),
                  "autoMergeRequest": {"enabledAt": "now"} if shown["armed"] else None,
                  "isDraft": pull.get("draft", False),
                  "statusCheckRollup": pull.get("checks", []),
                  "comments": list(self.comments.get(str(number), [])),
                  "updatedAt": pull.get("updatedAt", (datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)).isoformat())}
        if pull.get("pushed"):
            pull["pushed"] -= 1
            if not pull["pushed"]:
                pull["stale"] = (dict(pull), 0)
                pull["head"] = f"pushed{number}"
                pull["behind"] = pull.get("leaves", pull["behind"])
        return {k: v for k, v in answer.items() if k in asked} if asked else answer

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
        `(pull_request, task)`. `run list --branch` answers that branch's pull
        request's `runs`, and `api .../pulls/<n>/reviews` its `reviewed`, which
        is where the commit a verdict names is read from.
        `api .../compare/...` answers about the commit it
        was asked about: the head GitHub has not moved yet is behind by what it
        was behind by before the rebase, which is the true answer to the wrong
        question and what solorepo's #245 read as a rebase that had not
        happened; a number in `blip` gets one rate-limit exit first, once its
        rebase has happened. `issue view` answers the branch's Challenge. Any
        other `api` call answers the `stack` object for a layer, or the
        repository's own settings. A call any `unreadable` mark of the store
        matches is refused before all of that, as GitHub refuses an ordinary
        read.
        """
        head = args[:2]
        if self.git.asked(args):
            return self.git(*args, parse=parse, **kwargs)
        if self.git.refusing(" ".join(str(a) for a in args)):
            return self.git.failing(args, kwargs, UNREADABLE)
        if head == ("repo", "view"):
            return {"nameWithOwner": "o/r", "deleteBranchOnMerge": True}
        asked = tuple(args[args.index("--json") + 1].split(",")) if "--json" in args else ()
        if head == ("pr", "list"):
            return [{k: v for k, v in self.view(n, asked).items() if k != "statusCheckRollup"}
                    for n in self.pulls]
        if head == ("pr", "view"):
            if str(args[2]) in self.no_view:
                sys.exit("gh: Post https://api.github.com/graphql: net/http: TLS handshake timeout")
            return self.view(args[2], asked)
        if head == ("run", "list"):
            return self.runs(args)
        if head[:1] == ("stack",):
            return self.stack(args)
        if head == ("workflow", "run") and args[2] == "coder.yml":
            return self.dispatch(args)
        if args[0] == "api":
            return self.api(*(a for a in args[1:] if a != "--paginate"),
                            paginated="--paginate" in args)
        answered = {("pr", "update-branch"): self.update_branch, ("pr", "edit"): self.edit,
                    ("pr", "merge"): self.merge, ("pr", "ready"): self.ready,
                    ("issue", "view"): self.issue}
        if head in answered:
            return answered[head](args)
        raise unanswered(args)

    def runs(self, args: Any) -> list[dict[str, Any]]:
        """`run list`: the `runs` of the pull request on that branch, newest first.

        `--workflow` is read as GitHub reads it, so that only `review.yml` is
        answered the runs: a caller that named another workflow is answered
        none, which is what GitHub answers for one that has never run on the
        branch. A branch no pull request here holds is answered none likewise.
        """
        branch = args[args.index("--branch") + 1]
        workflow = args[args.index("--workflow") + 1] if "--workflow" in args else ""
        pull = next((p for number, p in self.pulls.items()
                     if p.get("branch", f"claude/issue-{number}") == branch), {})
        return [{"headSha": run[0], "status": run[1]}
                for run in (pull.get("runs") or [] if workflow == "review.yml" else [])]

    def stack(self, args: Any) -> Any:
        """One `gh stack` call: link and checkout recorded, rebase performed, push counted."""
        answered = {"link": lambda: self.linked.append(tuple(args[2:])),
                    "checkout": lambda: self.checked_out.append(args[2:]),
                    "push": lambda: setattr(self, "pushed_stacks", self.pushed_stacks + 1)}
        if args[1] == "rebase":
            return self.stack_rebase(args)
        if args[1] not in answered:
            raise unanswered(args)
        answered[str(args[1])]()
        return ""

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

    def ready(self, args: Any) -> str:
        """`pr ready`: marks pull request ready or undoes ready status."""
        number = str(args[2])
        pull = self.pulls.get(number)
        if pull is not None:
            pull["draft"] = "--undo" in args
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

    def _comments_api(self, endpoint: str, rest: tuple[str, ...], paginated: bool) -> Any:
        """Handle issue and review comment endpoints for GitHub API fakes.

        Parameters:
            endpoint: GitHub API route being accessed.
            rest: Additional command arguments such as flags and payloads.
            paginated: Whether pagination was requested on the API call.

        Returns:
            Any: JSON response payload matching GitHub API schema.
        """
        if endpoint.endswith("/comments"):
            pr_str = endpoint.split("/issues/")[1].split("/comments")[0]
            if "-f" in rest:
                body = rest[rest.index("-f") + 1].removeprefix("body=")
                comments = self.comments.setdefault(pr_str, [])
                new_id = len(comments) + 1
                entry = {"id": new_id, "body": body, "user": {"login": "o-r-coder"}}
                comments.append(entry)
                self.posted_comments.append((pr_str, body))
                return {
                    "id": new_id,
                    "html_url": f"https://github.com/o/r/pull/{pr_str}#issuecomment-{new_id}",
                }
            comments = list(self.comments.get(pr_str, []))
            if not paginated and len(comments) > 1:
                return comments[:1]
            return comments
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

    def api(self, endpoint: str, *rest: str, paginated: bool = False) -> Any:
        """Any other `api` call: the compare, a pull request's verdicts, the `stack` object of a layer, issue comments, or the repository's own settings."""
        if "/compare/" in endpoint:
            return self.compare(endpoint)
        if endpoint.split("?")[0].endswith("/reviews"):
            pull = self.pulls.get(endpoint.split("?")[0].rsplit("/", 2)[-2]) or {}
            return [{"user": {"login": review[0]}, "commit_id": review[1],
                     "state": review[2] if len(review) > 2 else "CHANGES_REQUESTED",
                     "body": review[3] if len(review) > 3 else "asked for changes"}
                    for review in pull.get("reviewed") or []]
        if "/pulls/" in endpoint:
            pull = self.pulls.get(endpoint.rsplit("/", 1)[-1]) or {}
            return {"stack": {"id": 1, "number": pull.get("stack", 1)}} if pull.get("layer") else {}
        if "/issues/" in endpoint:
            return self._comments_api(endpoint, rest, paginated)
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
