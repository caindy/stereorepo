"""What the probes stand in for, and the acts every probe repeats (solorepo's DR-209).

The channel loaded as modules; GitHub answered from a dict, for the verbs that
rebase, arm, hand off and dispatch; a watch answered from a list of polls; an
Issue answered from its labels; a wiki page answered from a string. And the
small acts around a call: a script loaded without running its `main()`, an
attribute or an environment variable stood in for the length of a block, and
what a call exited with, read as text rather than allowed to end the step.

Nothing here is a step. A subject module imports what it needs from here and
registers its own, and this module imports no sibling under `probes/`, so the
package's import graph is a tree with this at its root, as `collect.py` is for
the gate (solorepo's DR-150).
"""
import collections
import contextlib
import datetime
import importlib.util
import io
import os
import pathlib
import subprocess
import sys
from importlib.machinery import SourceFileLoader

import yaml

from collect import META, ROOT

Outcome = collections.namedtuple("Outcome", "code out err")
"""What a call came to: `code`, the text it exited with or `None` when it returned; `out` and `err`, what it printed."""

_ABSENT = object()


def load_module(path, name=None, register=True):
    """The Python source at `path` as a fresh module object, its `main()` unrun.

    `name` is the module's `__name__`, the file's stem by default. `register`
    puts the module in `sys.modules` under that name before it runs, which a
    module defining a dataclass needs and a plain script does not mind. `.meta/`
    and `.meta/checks/` are put on `sys.path` first, so a script that imports the
    gate's own modules resolves them the way `check.py` does.

    Loading runs the file's top level, so this is for programs whose every act
    is under `if __name__ == "__main__"`, which every script under `.meta/` is.
    Works for a program with no `.py` as well as a module with one.
    """
    for entry in (str(META / "checks"), str(META)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    path = pathlib.Path(path)
    if not path.is_absolute():
        path = ROOT / path
    name = name or path.name.removesuffix(".py")
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    if register:
        sys.modules[name] = module
    loader.exec_module(module)
    return module


def load_hook(name):
    """`.meta/hooks/<name>.py` as a module, by the stem alone."""
    return load_module(META / "hooks" / f"{name}.py", name)


def load_channel():
    """`.meta/say/` as modules: the signing primitive, the verb table, and every program the table names.

    Returns `(channel, table, programs)`: the `channel.py` module, the parsed
    `verbs.yaml`, and a dict from each program's name to its module, loaded by
    the primitive's own `sibling()` so that programs importing each other share
    one copy (solorepo's DR-117). Each call loads the channel afresh, so what one
    probe sets on a program does not reach the next.

    The programs have no `.py` and are programs rather than libraries, so the
    primitive's loader is used. Importing runs nothing: everything each does is
    under `main()`, and `main()` is under `__name__`.
    """
    channel = load_module(META / "say" / "channel.py", "channel")
    table = yaml.safe_load((META / "say" / "verbs.yaml").read_text()) or {}
    programs = {p["name"]: channel.sibling(p["name"]) for p in table.get("programs") or []}
    return channel, table, programs


@contextlib.contextmanager
def stood_in(target, **attributes):
    """The named attributes of `target` replaced for the block, and put back after it, whatever the block did.

    An attribute the target did not have is removed again on the way out
    rather than left holding the stand-in.
    """
    held = {name: getattr(target, name, _ABSENT) for name in attributes}
    for name, value in attributes.items():
        setattr(target, name, value)
    try:
        yield
    finally:
        for name, value in held.items():
            if value is _ABSENT:
                delattr(target, name)
            else:
                setattr(target, name, value)


@contextlib.contextmanager
def environment(**variables):
    """The named environment variables set for the block, `None` unsetting one, and put back after it."""
    held = {name: os.environ.get(name) for name in variables}

    def apply(values):
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    apply(variables)
    try:
        yield
    finally:
        apply(held)


def outcome(call):
    """What `call` came to, as an `Outcome`, with its printing captured rather than shown.

    Every way out is an answer. `sys.exit(text)` is `text`; a return is `None`;
    any other exception is its type and message, as `TypeError: ...`. Raised
    instead, a fake's designed refusal — an `AssertionError` naming the call it
    has no answer for — or a number a case did not model would end the step at
    its first surprise and leave `check.py`'s precheck guard to report one line
    for the whole of it with every later case unrun (A7). Returned as text, the
    refusal still says in the report what the fake was asked.
    """
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            call()
        code = None
    except SystemExit as exc:
        code = str(exc.code)
    except Exception as exc:
        code = f"{type(exc).__name__}: {exc}"
    return Outcome(code, out.getvalue(), err.getvalue())


def exit_of(call):
    """What `call` exited with, as text, or `None` when it returned; see `outcome`."""
    return outcome(call).code


def run_verb(channel, fake, call):
    """`call` with the channel's `gh` stood in by `fake`, and what it exited with."""
    with stood_in(channel, gh=fake):
        return exit_of(call)


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

    def __init__(self, pulls, no_rebase=(), no_arm=(), no_stick=(), lands=(), blip=(),
                 no_dispatch=()):
        self.pulls = {str(n): dict(p) for n, p in pulls.items()}
        self.reads = {}
        for number, pull in self.pulls.items():
            pull.setdefault("head", f"head{number}")
        self.no_rebase, self.no_arm = {str(n) for n in no_rebase}, {str(n) for n in no_arm}
        self.blip = {str(n) for n in blip}
        self.no_stick = {str(n) for n in no_stick}
        self.lands = {str(n) for n in lands}
        self.no_dispatch = {str(n) for n in no_dispatch}
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
        if head == ("pr", "update-branch"):
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
        if head == ("pr", "edit"):
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
        if head == ("pr", "merge"):
            number = str(args[2])
            if number in self.no_arm:
                sys.exit("gh: Pull request is in clean status")
            pull = self.pulls[number]
            pull["stale"] = (dict(pull), pull.get("slow", 0))
            pull["armed"] = number not in self.no_stick
            if number in self.lands:
                pull.update(state="MERGED", armed=False)
            return ""
        if head == ("workflow", "run") and args[2] == "coder.yml":
            number = next(a.split("=", 1)[1] for a in args if a.startswith("pull_request="))
            task = next((a.split("=", 1)[1] for a in args if a.startswith("task=")), None)
            if number in self.no_dispatch:
                sys.exit("gh: Resource not accessible by personal access token")
            self.dispatched.append((number, task))
            return ""
        if args[0] == "api" and "/compare/" in args[1]:
            oid = args[1].rsplit("...", 1)[1]
            number = oid.removeprefix("head").removeprefix("moved").removeprefix("pushed")
            if number in self.blip and self.pulls[number].get("rebased"):
                self.blip.discard(number)
                sys.exit("gh: API rate limit exceeded")
            pull = self.pulls[number]
            was, _ = pull.get("stale") or (pull, 0)
            return {"behind_by": pull["behind"] if oid == pull["head"] else was["behind"]}
        if head == ("issue", "view"):
            issue = self.pulls[str(args[2])].get("issue") or {}
            if issue.get("unreadable"):
                sys.exit("gh: Could not resolve to an issue or pull request")
            return {"state": issue.get("state", "OPEN"),
                    "labels": [{"name": "challenge"}, {"name": issue.get("level", "medium")}]}
        if head == ("stack", "link"):
            self.linked.append(tuple(args[2:]))
            return ""
        if args[0] == "api" and "/pulls/" in args[1]:
            pull = self.pulls.get(args[1].rsplit("/", 1)[-1]) or {}
            return {"stack": {"id": 1, "number": pull.get("stack", 1)}} if pull.get("layer") else {}
        if args[0] == "api":
            return {"allow_auto_merge": True}
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")


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


class FakeIssue:
    """As much of GitHub as `claim` and `stop` ask about: one Issue's labels, its assignees, and the read-back of both.

    One Issue, because the verb takes one. `labels` and `assignees` are as the
    calls leave them; `views` counts the reads of the labels, which is the only
    way from here to see the branch a run takes — a claim that refuses nobody
    and a claim that never asked look identical in the assignees. `fail` makes
    every call raise `subprocess.CalledProcessError`, which is what a deleted
    Issue or a token without the scope looks like to the channel. `repo view`
    answers `o/r` and `api user` answers `o-r-coder`, the coder Role's login
    for that repository as `channel.role_login` composes it
    (solorepo's DR-107), which is what a claim that went through leaves in
    `assignees`.
    """

    def __init__(self, labels, fail=False, assignees=None):
        self.labels, self.assignees, self.views = list(labels), list(assignees or []), 0
        self.fail = fail

    def __call__(self, *args, parse=True, **kwargs):
        """One `gh` call: `issue view` of the labels or the assignees, `issue edit` of either, the login, or a comment posted."""
        if self.fail:
            raise subprocess.CalledProcessError(1, ["gh", *list(args)], output="", stderr="mock API error")
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("issue", "view") and "labels" in args:
            self.views += 1
            return {"labels": [{"name": name} for name in self.labels]}
        if args[:2] == ("issue", "view") and "assignees" in args:
            return {"assignees": [{"login": who} for who in self.assignees]}
        if args[:2] == ("issue", "edit") and "--add-assignee" in args:
            self.assignees.append(args[args.index("--add-assignee") + 1])
            return ""
        if args[:2] == ("issue", "edit") and "--remove-assignee" in args:
            login = args[args.index("--remove-assignee") + 1]
            if login in self.assignees:
                self.assignees.remove(login)
            return ""
        if args[:2] == ("issue", "edit") and "--add-label" in args:
            label_to_add = args[args.index("--add-label") + 1]
            if label_to_add not in self.labels:
                self.labels.append(label_to_add)
            for i, arg in enumerate(args):
                if arg == "--remove-label":
                    val = args[i + 1]
                    if val in self.labels:
                        self.labels.remove(val)
            return ""
        if args[:2] == ("api", "user"):
            return "o-r-coder"
        if args[:1] == ("api",) and len(args) > 1 and "comments" in args[1]:
            return {"html_url": "https://github.com/o/r/issues/1/comments/1"}
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")


class FakeWikiPath:
    """A wiki page as the wiki checks read one: a repository-relative path whose text is given rather than read from disk.

    Answers the `pathlib.Path` surface `files.wikilinks`,
    `files.wiki_lead_paragraphs` and `files.ubiquitous_language_wiki_parity`
    use — name, stem, suffix, parts, parent, `relative_to`, `read_text` — and
    nothing else, so a case is one string and one path rather than a file.
    """

    def __init__(self, rel_str, text):
        self._path = ROOT / rel_str
        self._text = text

    @property
    def suffix(self):
        """The path's suffix, `.md` for a page."""
        return self._path.suffix

    @property
    def name(self):
        """The file name."""
        return self._path.name

    @property
    def stem(self):
        """The file name without its suffix, which is the page's slug."""
        return self._path.stem

    @property
    def parts(self):
        """The path's components."""
        return self._path.parts

    @property
    def parent(self):
        """The directory the page is in, which names its context."""
        return self._path.parent

    def is_symlink(self):
        """Never a symlink."""
        return False

    def is_file(self):
        """Always a file."""
        return True

    def read_text(self, encoding="utf-8"):
        """The page's text, as given."""
        return self._text

    def relative_to(self, other):
        """The path relative to `other`, as `pathlib.Path.relative_to` answers it."""
        return self._path.relative_to(other)

    def __str__(self):
        return str(self._path)
