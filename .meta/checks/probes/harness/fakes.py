"""An Issue answered from its labels, a filing answered from an open listing, and a wiki page answered from a string.
"""
import re
import subprocess

from checks.collect import ROOT


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
        if args[:2] == ("issue", "view"):
            return self.view(args)
        if args[:2] == ("issue", "edit"):
            return self.edit(args)
        if args[:2] == ("api", "user"):
            return "o-r-coder"
        if args[:1] == ("api",) and len(args) > 1 and "comments" in args[1]:
            return {"html_url": "https://github.com/o/r/issues/1/comments/1"}
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")

    def view(self, args):
        """`issue view` of the labels, counted in `views`, or of the assignees."""
        if "labels" in args:
            self.views += 1
            return {"labels": [{"name": name} for name in self.labels]}
        if "assignees" in args:
            return {"assignees": [{"login": who} for who in self.assignees]}
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")

    def edit(self, args):
        """`issue edit`: an assignee added or removed, or a label added and any `--remove-label` beside it applied."""
        if "--add-assignee" in args:
            self.assignees.append(args[args.index("--add-assignee") + 1])
            return ""
        if "--remove-assignee" in args:
            login = args[args.index("--remove-assignee") + 1]
            if login in self.assignees:
                self.assignees.remove(login)
            return ""
        if "--add-label" in args:
            label_to_add = args[args.index("--add-label") + 1]
            if label_to_add not in self.labels:
                self.labels.append(label_to_add)
            for i, arg in enumerate(args):
                if arg == "--remove-label" and args[i + 1] in self.labels:
                    self.labels.remove(args[i + 1])
            return ""
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

    def __init__(self, open_issues=None, list_fails=False):
        self.open_issues = {str(n): t for n, t in (open_issues or [])}
        self.created = {}
        self.listings = 0
        self.list_fails = list_fails
        self.next_number = 900

    def __call__(self, *args, parse=True, **kwargs):
        """One `gh` call: the open listing, an `issue create`, or the `issue view` that verifies one."""
        if args[:2] == ("repo", "view"):
            return {"nameWithOwner": "o/r"}
        if args[:2] == ("issue", "list"):
            self.listings += 1
            if self.list_fails:
                if not kwargs.get("tolerate_fail"):
                    raise SystemExit("gh: mock API error")
                raise subprocess.CalledProcessError(1, ["gh", *list(args)], output="",
                                                    stderr="mock API error")
            return [{"number": int(n), "title": t,
                     "url": f"https://github.com/o/r/issues/{n}"}
                    for n, t in self.open_issues.items()]
        if args[:2] == ("issue", "create"):
            return self.create(args)
        if args[:2] == ("issue", "view"):
            return self.view(args)
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")

    def create(self, args):
        """`issue create`: the Issue recorded and added to the open listing, its URL answered."""
        title = args[args.index("--title") + 1]
        body = args[args.index("--body") + 1]
        labels = [args[i + 1] for i, arg in enumerate(args) if arg == "--label"]
        number = str(self.next_number)
        self.next_number += 1
        self.created[number] = (title, body, labels)
        self.open_issues[number] = title
        return f"https://github.com/o/r/issues/{number}"

    def view(self, args):
        """`issue view` of a created Issue's labels, or of the blocked-by its body asked for."""
        number = str(args[2])
        _title, body, labels = self.created.get(number, ("", "", []))
        if "labels" in args:
            return {"labels": [{"name": name} for name in labels]}
        if "blockedBy" in args:
            first = body.lstrip().split("\n", 1)[0]
            refs = sorted({int(n) for n in re.findall(r"#(\d+)", first)})
            return {"blockedBy": {"nodes": [{"number": n} for n in refs]}}
        raise AssertionError(f"the fake was asked something it has no answer for: {args}")
