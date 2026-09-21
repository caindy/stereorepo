"""An Issue answered from its labels, an obviation answered from what each number is, a filing answered from an open listing, and a wiki page answered from a string.
"""
import pathlib
import re
import subprocess
from typing import Any, ClassVar

from checks.collect import ROOT
from checks.probes.harness.acts import unanswered

LIST_REFUSAL = "gh: mock API error"
"""What a listing stood in for to fail exits with, in the words `channel.gh` exits with."""


class FakeIssue:
    """As much of GitHub as `claim`, `stop` and `triage` ask about: one Issue's labels, its assignees, its comments, and the read-back of each.

    One Issue, because the verb takes one. `labels`, `assignees` and
    `comments` are as the calls leave them; `views` counts the reads of the
    labels, which is the only way from here to see the branch a run takes — a
    claim that refuses nobody and a claim that never asked look identical in
    the assignees. `fail` makes every call raise
    `subprocess.CalledProcessError`, which is what a deleted Issue or a token
    without the scope looks like to the channel. `repo view` answers `o/r` and
    `api user` answers `login`, by default `o-r-coder`, the coder Role's login for that repository
    as `channel.role_login` composes it (solorepo's DR-107), which is what a
    claim that went through leaves in `assignees` and a comment posted leaves
    as its author. `state` and `login` are attributes rather than arguments,
    because almost every case wants an open Issue and the coder's login: a case
    assigns `state = "CLOSED"` where the verb asks whether the reading door
    would accept the delivery, and `login = "o-r-reviewer"` where it asks which
    Role is speaking rather than merely signing as one — `move triage`, whose
    verdict is the reviewer's wherever it runs (solorepo's DR-235).
    """

    def __init__(self, labels: list[str], fail: bool = False, assignees: list[str] | None = None,
                 comments: list[dict[str, Any]] | None = None) -> None:
        self.labels, self.assignees, self.views = list(labels), list(assignees or []), 0
        self.comments: list[dict[str, Any]] = list(comments or [])
        self.fail = fail
        self.state = "OPEN"
        self.login = "o-r-coder"

    def __call__(self, *args: str, parse: bool = True, **kwargs: Any) -> Any:
        """One `gh` call: `issue view` of the labels or the assignees, `issue edit` of either, the login, or the comments listed or one posted."""
        if self.fail:
            raise subprocess.CalledProcessError(1, ["gh", *list(args)], output="", stderr="mock API error")
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("pr", "list"):
            return []
        if args[:2] == ("issue", "view"):
            return self.view(args)
        if args[:2] == ("issue", "edit"):
            return self.edit(args)
        if args[:2] == ("api", "user"):
            return self.login
        if args[:1] == ("api",) and len(args) > 1 and "comments" in args[1]:
            if "-f" not in args:
                return list(self.comments)
            body = args[args.index("-f") + 1].removeprefix("body=")
            self.comments.append({"body": body, "user": {"login": "o-r-coder"}})
            return {"html_url": f"https://github.com/o/r/issues/1/comments/{len(self.comments)}"}
        raise unanswered(args)

    def view(self, args: tuple[str, ...]) -> dict[str, Any]:
        """`issue view` of any fields this fake holds: the labels, counted in `views`, the assignees, or the state.

        The fields are read off the value of `--json` rather than matched
        against the call's words, so a verb that asks for two at once is
        answered in one call — `move reread` asks for the state beside the
        assignees, since the reading door it delivers to declines a closed
        Issue (solorepo's DR-235).
        """
        asked = args[args.index("--json") + 1].split(",") if "--json" in args else []
        answer: dict[str, Any] = {}
        for field in asked:
            if field == "labels":
                self.views += 1
                answer["labels"] = [{"name": name} for name in self.labels]
            elif field == "assignees":
                answer["assignees"] = [{"login": who} for who in self.assignees]
            elif field == "state":
                answer["state"] = self.state
            else:
                raise unanswered(args)
        if not answer:
            raise unanswered(args)
        return answer

    def edit(self, args: tuple[str, ...]) -> str:
        """`issue edit`: an assignee added or removed, or every `--add-label` and `--remove-label` applied, either without the other.

        A call that only removes is `move reread` taking a level off a
        Challenge (solorepo's DR-235); until it existed, every labelling verb
        added one label as it dropped another, and reading the removals under
        an addition was enough.
        """
        if "--add-assignee" in args:
            self.assignees.append(args[args.index("--add-assignee") + 1])
            return ""
        if "--remove-assignee" in args:
            login = args[args.index("--remove-assignee") + 1]
            if login in self.assignees:
                self.assignees.remove(login)
            return ""
        if "--add-label" in args or "--remove-label" in args:
            for i, arg in enumerate(args):
                if arg == "--add-label" and args[i + 1] not in self.labels:
                    self.labels.append(args[i + 1])
            for i, arg in enumerate(args):
                if arg == "--remove-label" and args[i + 1] in self.labels:
                    self.labels.remove(args[i + 1])
            return ""
        raise unanswered(args)


class FakeObviation:
    """As much of GitHub as `obviate` asks about: what each number is, and the close of the one being obviated.

    `items` maps a number to what GitHub answers for it — `kind`, `"issue"` or
    `"pull request"`; `state`; `title`; and `labels`, which only an Issue
    carries. A number no case names is answered as an open Issue with no
    labels, since a case says what it is about and nothing else.

    `comments` collects `(number, body)` for every comment posted, the body
    without the `body=` flag it was sent under, and `closed` every
    `(number, reason)`, which is how a probe reads the backlink and the
    not-planned reason rather than only the exit. A close takes only the three
    reasons the GitHub CLI's reference for `gh issue close` lists —
    `completed`, `not planned`, `duplicate` — and records each as GitHub
    spells it in `stateReason`; any other spelling is the fake's own
    `AssertionError`, so a changed reason is a failing probe rather than a
    read-back that passes by construction (solorepo's DR-232).
    """

    def __init__(self, items: dict[str, dict[str, Any]] | None = None) -> None:
        self.items = {str(n): dict(what) for n, what in (items or {}).items()}
        self.comments: list[tuple[str, str]] = []
        self.closed: list[tuple[str, str]] = []

    def of(self, number: str | int) -> dict[str, Any]:
        """What GitHub answers for one number, defaulted to an open Issue carrying no labels."""
        return self.items.setdefault(str(number), {"kind": "issue", "state": "OPEN",
                                                   "title": f"#{number}", "labels": []})

    def __call__(self, *args: str, parse: bool = True, **kwargs: Any) -> Any:
        """One `gh` call: the repository, what a number is, an `issue view` or a `pr view` of it, a comment posted, or an Issue closed."""
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("issue", "view") or args[:2] == ("pr", "view"):
            return self.view(args)
        if args[:2] == ("issue", "close"):
            return self.close(args)
        if args[:1] == ("api",) and len(args) > 1 and args[1].endswith("/comments"):
            body = args[args.index("-f") + 1]
            self.comments.append((args[1].rsplit("/", 2)[1], body.removeprefix("body=")))
            return {"html_url": "https://github.com/o/r/issues/1#issuecomment-1"}
        if args[:1] == ("api",) and len(args) == 2:
            what = self.of(args[1].rsplit("/", 1)[1])
            pull = {"url": f"https://api.github.com/repos/o/r/pulls/{args[1].rsplit('/', 1)[1]}"}
            return {"pull_request": pull} if what["kind"] == "pull request" else {}
        raise unanswered(args)

    def view(self, args: tuple[str, ...]) -> dict[str, Any]:
        """`issue view` or `pr view` of the fields the `--json` beside it asked for."""
        what = self.of(args[2])
        fields = args[args.index("--json") + 1].split(",")
        answer = {"state": what["state"], "title": what["title"],
                  "labels": [{"name": name} for name in what.get("labels") or []],
                  "stateReason": what.get("stateReason")}
        if any(field not in answer for field in fields):
            raise unanswered(args)
        return {field: answer[field] for field in fields}

    REASONS: ClassVar[dict[str, str]] = {"completed": "COMPLETED", "not planned": "NOT_PLANNED",
                                         "duplicate": "DUPLICATE"}
    """What `--reason` accepts, per the CLI reference, and the `stateReason` GitHub records for each."""

    def close(self, args: tuple[str, ...]) -> str:
        """`issue close`: the reason recorded, and the Issue left closed as GitHub leaves it."""
        what = self.of(args[2])
        reason = args[args.index("--reason") + 1] if "--reason" in args else "completed"
        if reason not in self.REASONS:
            raise unanswered(args)
        self.closed.append((str(args[2]), reason))
        what["state"], what["stateReason"] = "CLOSED", self.REASONS[reason]
        return ""


class FakeWikiPath:
    """A wiki page as the wiki checks read one: a repository-relative path whose text is given rather than read from disk.

    Answers the `pathlib.Path` surface `files.wikilinks`,
    `files.wiki_lead_paragraphs` and `files.ubiquitous_language_wiki_parity`
    use — name, stem, suffix, parts, parent, `relative_to`, `read_text` — and
    nothing else, so a case is one string and one path rather than a file.
    """

    def __init__(self, rel_str: str | pathlib.Path, text: str) -> None:
        self._path = ROOT / rel_str
        self._text = text

    @property
    def suffix(self) -> str:
        """The path's suffix, `.md` for a page."""
        return self._path.suffix

    @property
    def name(self) -> str:
        """The file name."""
        return self._path.name

    @property
    def stem(self) -> str:
        """The file name without its suffix, which is the page's slug."""
        return self._path.stem

    @property
    def parts(self) -> tuple[str, ...]:
        """The path's components."""
        return self._path.parts

    @property
    def parent(self) -> pathlib.Path:
        """The directory the page is in, which names its context."""
        return self._path.parent

    def is_symlink(self) -> bool:
        """Never a symlink."""
        return False

    def is_file(self) -> bool:
        """Always a file."""
        return True

    def read_text(self, encoding: str = "utf-8") -> str:
        """The page's text, as given."""
        return self._text

    def relative_to(self, other: pathlib.Path | str) -> pathlib.Path:
        """The path relative to `other`, as `pathlib.Path.relative_to` answers it."""
        return self._path.relative_to(other)

    def __str__(self) -> str:
        return str(self._path)


class FakeFiling:
    """As much of GitHub as `file_issue` asks about: the open Issues it lists, and the ones it creates.

    `open_issues` maps an Issue's number to its title and is the listing
    `gh issue list` answers with. `created` maps the number of each Issue a call
    created to its `(title, body, labels)`, so a probe reads what was filed and
    not only what was said, and a created Issue joins `open_issues` — which is
    what makes the second of two identical filings in one probe the case the
    guard is about. `listings` counts the reads of the open listing, the only
    way from here to tell a guard that consulted GitHub from one that never
    asked.

    The `issue view` that `file_issue` performs after creating is answered from
    `created`, so a filing that went through passes its own verification rather
    than failing on the fake.
    """

    def __init__(self, open_issues: list[tuple[int | str, str]] | None = None,
                 list_fails: bool = False) -> None:
        self.open_issues = {str(n): t for n, t in (open_issues or [])}
        self.created: dict[str, tuple[str, str, list[str]]] = {}
        self.listings = 0
        self.list_fails = list_fails
        self.next_number = 900

    def __call__(self, *args: str, parse: bool = True, **kwargs: Any) -> Any:
        """One `gh` call: the open listing, an `issue create`, or the `issue view` that verifies one."""
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("issue", "list"):
            self.listings += 1
            if self.list_fails:
                if not kwargs.get("tolerate_fail"):
                    raise SystemExit(LIST_REFUSAL)
                raise subprocess.CalledProcessError(1, ["gh", *list(args)], output="",
                                                    stderr="mock API error")
            return [{"number": int(n), "title": t,
                     "url": f"https://github.com/o/r/issues/{n}"}
                    for n, t in self.open_issues.items()]
        if args[:2] == ("issue", "create"):
            return self.create(args)
        if args[:2] == ("issue", "view"):
            return self.view(args)
        raise unanswered(args)

    def create(self, args: tuple[str, ...]) -> str:
        """`issue create`: the Issue recorded and added to the open listing, its URL answered."""
        title = args[args.index("--title") + 1]
        body = args[args.index("--body") + 1]
        labels = [args[i + 1] for i, arg in enumerate(args) if arg == "--label"]
        number = str(self.next_number)
        self.next_number += 1
        self.created[number] = (title, body, labels)
        self.open_issues[number] = title
        return f"https://github.com/o/r/issues/{number}"

    def view(self, args: tuple[str, ...]) -> dict[str, Any]:
        """`issue view` of a created Issue's labels, or of the blocked-by and body its `--json` asked for."""
        number = str(args[2])
        _title, body, labels = self.created.get(number, ("", "", []))
        if "labels" in args:
            return {"labels": [{"name": name} for name in labels]}
        fields = next((a for a in args if "blockedBy" in a), "")
        if fields:
            first = body.lstrip().split("\n", 1)[0]
            refs = sorted({int(n) for n in re.findall(r"#(\d+)", first)})
            answer: dict[str, Any] = {"blockedBy": {"nodes": [{"number": n} for n in refs]}}
            if "body" in fields.split(","):
                answer["body"] = body
            return answer
        raise unanswered(args)
