"""The board: issue files under `issues/`, where the directory is the state.

An issue is `issues/<stage>/<slug>.md`. The slug is its id. Front matter holds
only `difficulty`, and optionally `waits_on` and `parent`; everything else is
observed from the directory or derived from git.
"""

from __future__ import annotations

import re
import subprocess
import threading
from collections import OrderedDict
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

STAGES = ("roadmap", "backlog", "underway", "todo", "in-progress", "desk-check", "done")
DIFFICULTIES = ("easy", "medium", "hard", "developer")
ISSUES = "issues"
ORDER = f"{ISSUES}/backlog/ORDER"
"""The backlog's running order: one slug per line, the developer's above `# groomed below`."""
MARKER = "# groomed below"
ELSEWHERE = ":"
"""What marks a `waits_on` entry as `<repository>:<slug>`, an Issue on another repository's board."""

_FRONT = re.compile(r"\A---\n(?P<block>.*?)\n---(?:\n|\Z)", re.DOTALL)
_HEADING = re.compile(r"^(?:#{1,6}\s*|\*\*)(?P<name>[^*\n]+?)\.?(?:\*\*)?\s*$")


class GitError(RuntimeError):
    """A git command exited non-zero."""


def git(cwd: Path, *args: str, check: bool = True) -> str:
    """Run git in `cwd` and return stripped stdout."""
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and done.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} (in {cwd}): "
            f"{done.stderr.strip() or done.stdout.strip()}"
        )
    return done.stdout.strip()


def git_run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in `cwd` and return the finished process, whatever its exit code."""
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def head_and_dirty(tree: Path) -> tuple[str, bool]:
    """A worktree's HEAD commit, and whether it has changes `git add -A` would stage.

    One `git status --porcelain=v2 --branch` answers both, where `rev-parse
    HEAD` and `status --porcelain` would start two processes.
    """
    head, dirty = "", False
    for line in git(tree, "status", "--porcelain=v2", "--branch").splitlines():
        if line.startswith("# branch.oid "):
            head = line.removeprefix("# branch.oid ")
        elif not line.startswith("#"):
            dirty = True
    return head, dirty


def git_ok(cwd: Path, *args: str) -> bool:
    """Whether a git command exits zero."""
    return (
        subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True
        ).returncode
        == 0
    )


@dataclass
class Issue:
    """One issue file as it stands in a working tree."""

    slug: str
    stage: str
    front: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def path(self) -> str:
        return f"{ISSUES}/{self.stage}/{self.slug}.md"

    @property
    def difficulty(self) -> str | None:
        value = self.front.get("difficulty")
        return value if value in DIFFICULTIES else None

    @property
    def title(self) -> str:
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return self.slug.replace("-", " ")


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown file into its front matter mapping and its body."""
    match = _FRONT.match(text)
    if not match:
        return {}, text
    try:
        front = yaml.safe_load(match["block"]) or {}
    except yaml.YAMLError:
        front = {}
    return (front if isinstance(front, dict) else {}), text[match.end() :]


def as_list(value: Any) -> list[str]:
    """A front matter value that may be a scalar or a list, as a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def section(body: str, name: str) -> str | None:
    """The text under a heading or bold lead named `name`, or None if absent.

    `## The plan` runs to the next heading of the same or a higher level, so
    its `###` subsections belong to it. `**The plan.**` runs to the next
    heading or bold lead of either form.
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        head = _HEADING.match(line.strip())
        if head and head["name"].strip().lower() == name.lower():
            level = _level(line)
            rest: list[str] = []
            for later in lines[i + 1 :]:
                other = _level(later) if _HEADING.match(later.strip()) else None
                if other is not None and other <= level:
                    break
                rest.append(later)
            return "\n".join(rest).strip()
    return None


def last_section(body: str, name: str) -> str:
    """The text under the last heading or bold lead named `name`, or "" if absent."""
    lines = body.splitlines()
    starts = [
        i
        for i, line in enumerate(lines)
        if (head := _HEADING.match(line.strip()))
        and head["name"].strip().lower() == name.lower()
    ]
    if not starts:
        return ""
    return section("\n".join(lines[starts[-1] :]), name) or ""


def _level(line: str) -> int:
    """A heading's level (1-6); a bold lead ranks below every heading (7)."""
    stripped = line.strip()
    hashes = len(stripped) - len(stripped.lstrip("#"))
    return hashes if hashes else 7


def sections(body: str, name: str) -> int:
    """How many headings or bold leads are named `name`."""
    count = 0
    for line in body.splitlines():
        head = _HEADING.match(line.strip())
        if head and head["name"].strip().lower() == name.lower():
            count += 1
    return count


def last_of(body: str, names: tuple[str, ...]) -> str | None:
    """Which of `names` the last heading or bold lead among them is named, or None."""
    wanted = {name.lower(): name for name in names}
    last = None
    for line in body.splitlines():
        head = _HEADING.match(line.strip())
        if head and head["name"].strip().lower() in wanted:
            last = wanted[head["name"].strip().lower()]
    return last


PAIR_NOTES = "Pair notes"
"""The section of an Issue file where the loop keeps each turn's closing message."""


def with_note(text: str, label: str, note: str) -> str:
    """`text`, an Issue file, with `note` quoted under `label` at its end.

    Every line is quoted (`> `), and no heading or bold lead the loop reads
    matches a quoted line, so a note that names `Needs elaboration` or
    `The plan` steers nothing. The note goes under the file's last heading or
    bold lead when that is `Pair notes`, and under a new `## Pair notes`
    heading otherwise, so it never reads as part of a section above it.
    """
    quote = "\n".join(
        f"> {line}".rstrip()
        for line in [f"**{label}**", "", *note.strip().splitlines()]
    )
    names = [
        head["name"].strip().lower()
        for line in text.splitlines()
        if (head := _HEADING.match(line.strip()))
    ]
    under = names[-1:] == [PAIR_NOTES.lower()]
    opening = "" if under else f"## {PAIR_NOTES}\n\n"
    return text.rstrip("\n") + f"\n\n{opening}{quote}\n"


def bullets(text: str) -> list[str]:
    """The top-level bullet items of a Markdown block, stripped of their markers
    and of backticks."""
    return [
        line[2:].strip().strip("`")
        for line in text.splitlines()
        if line.startswith(("- ", "* "))
    ]


def needs_elaboration(body: str) -> bool:
    """Whether a seat or the loop has sent this issue back for elaboration."""
    return section(body, "Needs elaboration") is not None


def read(tree: Path, slug: str) -> Issue | None:
    """The issue with this slug in a working tree, wherever it now sits."""
    for stage in STAGES:
        path = tree / ISSUES / stage / f"{slug}.md"
        if path.is_file():
            front, body = parse(path.read_text())
            return Issue(slug, stage, front, body)
    return None


def locations(tree: Path, slug: str) -> list[str]:
    """Every stage directory holding a file with this slug."""
    return [s for s in STAGES if (tree / ISSUES / s / f"{slug}.md").is_file()]


@dataclass(frozen=True)
class Reading:
    """The board as one commit holds it: what each stage lists, and each file's text.

    `texts` holds every file directly inside a stage directory, `ORDER` among
    them, keyed by its path from the repository root. A commit never changes,
    so a reading of one never goes stale.
    """

    sha: str
    listing: dict[str, list[str]]
    texts: dict[str, str]


_SHA = re.compile(r"[0-9a-f]{40}")
_PARENT = re.compile(r"^parent:", re.MULTILINE)
_KEPT_READINGS = 64
_KEPT_TEXTS = 4096
_readings: OrderedDict[str, Reading] = OrderedDict()
"""Readings by commit SHA, the least recently used first. A SHA fixes the whole
tree, so the key needs no repository, and a checkout and its worktrees share
what one of them read."""
_texts: OrderedDict[str, str] = OrderedDict()
"""File texts by blob id, so a new commit reads only the files it changed."""
_lock = threading.Lock()


def resolve(repo: Path, ref: str) -> str:
    """The commit SHA `ref` names, or `ref` itself where it names none.

    A full SHA costs no git process. A reader that calls others resolves once
    and passes the SHA on, so a moving ref such as `HEAD` is read once per call
    and every reader in that call sees one commit.
    """
    if _SHA.fullmatch(ref):
        return ref
    done = git_run(repo, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}")
    return done.stdout.strip() if done.returncode == 0 else ref


def _stage_file(path: str) -> bool:
    """Whether `path` lies directly inside a stage directory, where a reading holds it."""
    parts = path.split("/")
    return len(parts) == 3 and parts[0] == ISSUES and parts[1] in STAGES


def _decoded(data: bytes) -> str:
    """A blob's bytes as `subprocess.run(..., text=True)` would have given them."""
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def _blobs(repo: Path, oids: Collection[str]) -> dict[str, str]:
    """The texts of these blob ids, from one `git cat-file --batch`.

    The output is read by the byte size each header gives, since a text holds
    newlines of its own. A blob git cannot give raises `GitError`, so no
    reading is kept with a file missing from it.
    """
    done = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo,
        input="".join(f"{oid}\n" for oid in oids).encode(),
        capture_output=True,
    )
    out, at, found = done.stdout, 0, {}
    while at < len(out):
        end = out.index(b"\n", at)
        header = out[at:end].split()
        at = end + 1
        if len(header) != 3:
            continue
        size = int(header[2])
        found[header[0].decode()] = _decoded(out[at : at + size])
        at += size + 1
    lost = set(oids) - found.keys()
    if done.returncode != 0 or lost:
        raise GitError(
            f"git cat-file --batch (in {repo}): "
            f"{done.stderr.decode(errors='replace').strip() or 'missing ' + ', '.join(sorted(lost))}"
        )
    return found


def reading(repo: Path, ref: str) -> Reading | None:
    """The board at `ref`, read once per commit, or None where `ref` names no commit.

    A ref that names nothing yet, such as a branch not made, is not kept, so
    the first read after it is made sees its board.
    """
    sha = resolve(repo, ref)
    with _lock:
        if sha in _readings:
            _readings.move_to_end(sha)
            return _readings[sha]
    tree = subprocess.run(
        ["git", "ls-tree", "-r", "-z", sha, "--", f"{ISSUES}/"],
        cwd=repo,
        capture_output=True,
    )
    if tree.returncode != 0:
        return None
    oid_of: dict[str, str] = {}
    for entry in tree.stdout.split(b"\0"):
        meta, _, name = entry.partition(b"\t")
        fields = meta.split()
        path = name.decode("utf-8", errors="surrogateescape")
        if len(fields) == 3 and fields[1] == b"blob" and _stage_file(path):
            oid_of[path] = fields[2].decode()
    with _lock:
        known = {oid: _texts[oid] for oid in oid_of.values() if oid in _texts}
    missing = sorted(set(oid_of.values()) - known.keys())
    fetched = _blobs(repo, missing) if missing else {}
    listing: dict[str, list[str]] = {stage: [] for stage in STAGES}
    for path in oid_of:
        name = Path(path)
        if name.suffix == ".md" and name.name != "README.md":
            listing[name.parent.name].append(name.stem)
    taken = Reading(
        sha,
        {stage: sorted(slugs) for stage, slugs in listing.items()},
        {path: {**known, **fetched}[oid] for path, oid in oid_of.items()},
    )
    with _lock:
        for oid, text in fetched.items():
            _texts[oid] = text
        while len(_texts) > _KEPT_TEXTS:
            _texts.popitem(last=False)
        _readings[sha] = taken
        while len(_readings) > _KEPT_READINGS:
            _readings.popitem(last=False)
    return taken


def listed(repo: Path, ref: str, stage: str) -> list[str]:
    """Slugs in one stage directory at a git ref, in filename order."""
    board = reading(repo, ref)
    return list(board.listing.get(stage, [])) if board else []


def listed_by_stage(repo: Path, ref: str) -> dict[str, list[str]]:
    """`listed` for every stage at once."""
    board = reading(repo, ref)
    return {stage: list(board.listing[stage]) if board else [] for stage in STAGES}


def show(repo: Path, ref: str, path: str) -> str:
    """A file's text as committed at a ref, stripped, or '' where it is missing."""
    if not _stage_file(path):
        return git(repo, "show", f"{ref}:{path}", check=False)
    board = reading(repo, ref)
    return board.texts.get(path, "").strip() if board else ""


def at_ref(repo: Path, ref: str, stage: str, slug: str) -> Issue | None:
    """An issue as committed at a ref, or None."""
    board = reading(repo, ref)
    text = board.texts.get(f"{ISSUES}/{stage}/{slug}.md") if board else None
    if text is None:
        return None
    front, body = parse(text)
    return Issue(slug, stage, front, body)


def order(repo: Path, ref: str) -> list[str]:
    """The slugs `issues/backlog/ORDER` names at `ref`, first to last.

    The developer's placements sit above the `# groomed below` marker and
    grooming's ranking below it, so the file's own line order is the running
    order. Blank lines and `#` lines name nothing; a missing file names nothing.
    """
    board = reading(repo, ref)
    text = board.texts.get(ORDER) if board else None
    if text is None:
        return []
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def without(text: str, slug: str) -> str:
    """The text of an `ORDER` file with every line naming `slug` removed."""
    return "".join(
        line for line in text.splitlines(keepends=True) if line.strip() != slug
    )


def parts(parent_of: dict[str, str], backlog: Collection[str]) -> set[str]:
    """The backlog slugs whose parent is also in the backlog: the parts of a Flight there.

    `ORDER` names every other backlog slug, a Flight or a standalone Issue, and
    a part runs where its Flight's line is. A part whose Flight has left the
    backlog, for `done/` or a desk check, stands alone until the Flight is back.
    """
    return {slug for slug in backlog if parent_of.get(slug) in backlog}


def backlog_parents(kin: dict[str, dict[str, str]]) -> dict[str, str]:
    """Each backlog Issue in `families` that names a parent, mapped to that parent."""
    return {
        child: parent
        for parent, kids in kin.items()
        for child, stage in kids.items()
        if stage == "backlog"
    }


@dataclass
class Node:
    """One entry of the running order: a backlog slug and, for a Flight, its backlog parts in run order."""

    slug: str
    parts: list[Node] = field(default_factory=list)

    def flat(self) -> list[str]:
        """The slugs this entry runs, in order: each part's, then its own."""
        return [x for part in self.parts for x in part.flat()] + [self.slug]


def running_tree(
    repo: Path, ref: str, kin: dict[str, dict[str, str]] | None = None
) -> list[Node]:
    """The backlog at `ref` as the loop reaches it: top-level entries, each Flight holding its parts.

    The top-level slugs, those `ORDER` names first to last and then the rest in
    filename order, each stand for themselves or for a Flight. A Flight holds
    its backlog parts, each part after any sibling its `waits_on` names and
    otherwise in filename order, a part that is a Flight holding its own the
    same way. A `waits_on` cycle among siblings falls back to filename order.
    An entry naming another repository (`ELSEWHERE`) names no sibling, so it
    does not order parts.
    """
    ref = resolve(repo, ref)
    kin = families(repo, ref) if kin is None else kin
    backlog = listed(repo, ref, "backlog")
    inner = parts(backlog_parents(kin), backlog)
    top = [s for s in dict.fromkeys(order(repo, ref)) if s in backlog and s not in inner]
    top += [s for s in backlog if s not in top and s not in inner]
    seen: set[str] = set()

    def expand(slug: str) -> Node:
        seen.add(slug)
        kids = sorted(
            c for c, stage in kin.get(slug, {}).items() if stage == "backlog" and c not in seen
        )
        waits = {}
        for kid in kids:
            issue = at_ref(repo, ref, "backlog", kid)
            front = issue.front if issue else {}
            waits[kid] = {w for w in as_list(front.get("waits_on")) if ELSEWHERE not in w}
        placed: list[str] = []
        while kids:
            kid = next(
                (k for k in kids if not ((waits[k] & set(kids)) - {k})), kids[0]
            )
            kids.remove(kid)
            placed.append(kid)
        return Node(slug, [expand(kid) for kid in placed if kid not in seen])

    return [expand(slug) for slug in top]


def running_order(repo: Path, ref: str) -> list[str]:
    """Every backlog slug at `ref`, in the order the loop reaches it.

    `running_tree` flattened: a Flight runs its parts in place, and then itself.
    """
    return [x for node in running_tree(repo, ref) for x in node.flat()]


def holds(
    repo: Path, ref: str, slug: str, done: Collection[str], kin: dict[str, dict[str, str]]
) -> list[str]:
    """What holds a backlog item at `ref` back; an empty list means it is ripe.

    An item is held by a `Needs elaboration` section, which marks a send-back
    the developer has yet to answer (`elaboration`); by each `waits_on`
    not in `done`; and by each Issue naming it in `parent:` that is not in
    `done/` (`part <slug>`). A `waits_on` entry naming another repository
    (`ELSEWHERE`) always holds, because the loop cannot see that board; the
    developer removes it once that Issue has landed (DR-301). `done` and `kin`
    (from `families`) are passed in so that a caller asking about many items
    reads the board once.
    """
    issue = at_ref(repo, ref, "backlog", slug)
    if issue is None:
        return ["not in backlog/"]
    held = ["elaboration"] if needs_elaboration(issue.body) else []
    held += [
        w for w in as_list(issue.front.get("waits_on")) if ELSEWHERE in w or w not in done
    ]
    held += [f"part {kid}" for kid, stage in sorted(kin.get(slug, {}).items()) if stage != "done"]
    return held


def next_ripe(
    repo: Path,
    ref: str,
    skip: frozenset[str] = frozenset(),
    within: frozenset[str] | None = None,
) -> str | None:
    """The backlog item at `ref` the loop takes next: a ripe Flight, else the first ripe item.

    The items are taken in `running_order`, so a Flight's parts run where its
    line in `ORDER` is. An item is ripe when nothing `holds` it back. A ripe
    Flight, one with children, is taken before any other ripe
    item, so a Flight is checked as soon as its last child lands; among ripe
    Flights, and among the rest, the running order decides. Slugs in `skip`,
    and with `within` those outside it, are passed over.
    """
    ref = resolve(repo, ref)
    done = set(listed(repo, ref, "done"))
    kin = families(repo, ref)
    first = None
    for slug in (x for node in running_tree(repo, ref, kin) for x in node.flat()):
        if slug in skip or (within is not None and slug not in within):
            continue
        if first is not None and slug not in kin:
            continue
        if not holds(repo, ref, slug, done, kin):
            if slug in kin:
                return slug
            first = slug
    return first


def to_groom(repo: Path, ref: str) -> list[str]:
    """The backlog slugs at `ref` that a grooming pass takes up.

    An Issue is groomed when its front matter sets a valid `difficulty` and it
    has no `Needs elaboration` section. One with such a section waits on the
    developer instead, so a pass takes up only those with neither.
    """
    ref = resolve(repo, ref)
    slugs = []
    for slug in listed(repo, ref, "backlog"):
        issue = at_ref(repo, ref, "backlog", slug)
        if issue and issue.difficulty is None and not needs_elaboration(issue.body):
            slugs.append(slug)
    return slugs


def unnamed(repo: Path, ref: str) -> list[str]:
    """The top-level backlog slugs at `ref` that `ORDER` does not name, which a pass places.

    A part of a Flight in the backlog runs at its Flight's line and needs none.
    """
    ref = resolve(repo, ref)
    named = set(order(repo, ref))
    backlog = listed(repo, ref, "backlog")
    inner = parts(backlog_parents(families(repo, ref)), backlog)
    return [s for s in backlog if s not in named and s not in inner]


def split_order(text: str) -> tuple[list[str], list[str] | None]:
    """The non-blank lines of an `ORDER` file above the marker, and those below it.

    Below is None when the file has no marker, and every line is then above it.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if MARKER not in lines:
        return lines, None
    at = lines.index(MARKER)
    return lines[:at], lines[at + 1 :]


def merge_order(
    ours: str, base: str, theirs: str, keep: Collection[str], rerank: bool = False
) -> str:
    """The `ORDER` a branch lands with when its edits to it conflict with `main`'s.

    `ours` is `main`'s file, `base` the file where the branch left `main`, and
    `theirs` the branch's. The lines above the marker are `main`'s, since they
    belong to the developer or to a Flight sent back from its desk check.
    Below it, `main`'s ranking stands, and each slug the branch placed there
    (one `base` did not rank) goes in after the nearest slug above it in
    `theirs` that is already placed, or first. With `rerank`, the branch's
    ranking stands instead, and `main`'s slugs it lacks follow it. A slug not
    in `keep` loses its line, as does any slug named a second time, so a line
    above the marker wins. `#` lines other than the marker are kept where
    `main` has them.
    """
    above, ours_below = split_order(ours)
    ours_below = ours_below or []
    base_below = split_order(base)[1] or []
    their_below = split_order(theirs)[1] or []
    if rerank:
        below = their_below + [s for s in ours_below if s not in their_below]
    else:
        below = list(ours_below)
        for at, slug in enumerate(their_below):
            if slug.startswith("#") or slug in base_below or slug in below:
                continue
            anchor = next((s for s in reversed(their_below[:at]) if s in below), None)
            below.insert(below.index(anchor) + 1 if anchor else 0, slug)
    seen: set[str] = set()

    def kept(lines: list[str]) -> list[str]:
        out = []
        for line in lines:
            if line.startswith("#"):
                out.append(line)
            elif line in keep and line not in seen:
                seen.add(line)
                out.append(line)
        return out

    return "\n".join([*kept(above), MARKER, *kept(below)]) + "\n"


def order_keeps(tree: Path) -> set[str]:
    """The slugs in `tree` that may have a line in `ORDER`.

    Each Flight and standalone Issue in `backlog/`, and the Issue in
    `underway/`, whose landing drops its line and whose send-back keeps it.
    """
    backlog = [
        p.stem for p in (tree / ISSUES / "backlog").glob("*.md") if p.name != "README.md"
    ]
    parent_of = {}
    for slug in backlog:
        parent = parse((tree / ISSUES / "backlog" / f"{slug}.md").read_text())[0].get(
            "parent"
        )
        if parent:
            parent_of[slug] = str(parent)
    underway = {
        p.stem for p in (tree / ISSUES / "underway").glob("*.md") if p.name != "README.md"
    }
    return (set(backlog) - parts(parent_of, backlog)) | underway


def grooming_faults(
    tree: Path, repo: Path, ref: str, targets: Collection[str], rerank: bool
) -> list[str]:
    """What a grooming pass in `tree` still lacks, against the board at `ref`.

    `ref` is the commit the pass started from, so a change on `main` during the
    pass never shows here as a fault the seats cannot see. `targets` are the
    Issues the pass took up: each, and each backlog file the pass wrote, needs a
    `difficulty` unless the pass parked it with a `Needs elaboration` section.
    Without `rerank`, the Issues already ranked below the marker keep their
    relative order. `ORDER` names only Flights and standalone Issues: a part of
    a Flight in the backlog has no line on either side of the marker, and the
    parts are read from the tree, since the pass may just have written them.
    An empty list means the pass is finished. A `hard` Issue's children are
    read at the tree's `HEAD`, so the loop commits a turn before it asks.
    The Issue in `underway/` may keep its line, since its landing drops it, and
    is never asked for one; a part of a Flight in the backlog has none there either.
    """
    ref = resolve(repo, ref)
    faults = []
    backlog = sorted(
        p.stem for p in (tree / ISSUES / "backlog").glob("*.md") if p.name != "README.md"
    )
    before = listed(repo, ref, "backlog")
    underway = {
        p.stem
        for p in (tree / ISSUES / "underway").glob("*.md")
        if p.name != "README.md" and str(parse(p.read_text())[0].get("parent")) not in backlog
    }
    issues = {
        slug: Issue(slug, "backlog", *parse((tree / ISSUES / "backlog" / f"{slug}.md").read_text()))
        for slug in backlog
    }
    inner = parts(
        {slug: str(i.front["parent"]) for slug, i in issues.items() if i.front.get("parent")},
        backlog,
    )
    for slug in backlog:
        if slug not in targets and slug in before:
            continue
        issue = issues[slug]
        if needs_elaboration(issue.body):
            continue
        if issue.difficulty is None:
            faults.append(
                f"{issue.path} needs `difficulty:` set to easy, medium, hard or developer."
            )
        elif issue.difficulty == "hard" and not children(tree, "HEAD", slug):
            faults.append(
                f"{issue.path} is hard, so split it: write each part as a new file "
                f"in issues/backlog/ with `parent: {slug}` in its front matter."
            )
    for slug in before:
        if slug not in backlog:
            faults.append(
                f"issues/backlog/{slug}.md is gone; put it back. "
                "The pass does not delete a backlog Issue or move one out of backlog/."
            )
    for path in git(tree, "diff", "--name-only", ref, "HEAD").splitlines():
        if not path.startswith(f"{ISSUES}/") or path.startswith(f"{ISSUES}/roadmap/"):
            faults.append(f"{path} changed; the pass changes only issues/, and not issues/roadmap/.")
    board = reading(repo, ref)
    was = board.texts.get(ORDER) if board else None
    kept, ranked = split_order(was) if was is not None else ([], None)
    path = tree / ORDER
    above, below = split_order(path.read_text()) if path.is_file() else ([], None)
    if below is None:
        faults.append(
            f"{ORDER} needs the line `{MARKER}`, with the ranking below it."
        )
        return faults
    stale = [s for s in above if s in inner]
    if stale:
        faults.append(
            f"above `{MARKER}` in {ORDER}, delete the line for {', '.join(stale)}: "
            "a part of a Flight in the backlog runs at its Flight's line and has none."
        )
    if [s for s in above if s not in inner] != [s for s in kept if s not in inner]:
        shown = "\n".join(s for s in kept if s not in inner) or "(nothing)"
        faults.append(
            f"the lines above `{MARKER}` in {ORDER} are the developer's; "
            f"put them back as they were:\n{shown}"
        )
    placed = set(above)
    wanted = [s for s in backlog if s not in placed and s not in inner]
    missing = [s for s in wanted if s not in below]
    if missing:
        faults.append(f"rank {', '.join(missing)} below `{MARKER}` in {ORDER}.")
    extra = sorted({
        s for s in below
        if not s.startswith("#") and (s not in wanted and s not in underway or below.count(s) > 1)
    })
    if extra:
        faults.append(
            f"below `{MARKER}` in {ORDER}, name each Flight and standalone backlog "
            "Issue not placed above it exactly once, and nothing else; a part of a "
            f"Flight in the backlog runs at its Flight's line: {', '.join(extra)}."
        )
    if not rerank and ranked:
        held = [s for s in ranked if s in backlog and s not in targets and s not in inner]
        now = [s for s in dict.fromkeys(below) if s in held]
        was_now = [s for s in held if s in now]
        if now != was_now:
            moved = [s for s, t in zip(now, was_now) if s != t]
            faults.append(
                f"below `{MARKER}` in {ORDER}, {', '.join(moved)} moved; place the "
                "Issues you groomed without moving the rest, which ran in this order:\n"
                + "\n".join(was_now)
            )
    return faults


def families(repo: Path, ref: str) -> dict[str, dict[str, str]]:
    """Every Issue at `ref` that names a parent, grouped by that parent.

    Each parent maps to its children and the stage each sits in. A roadmap
    file is no one's child. Only a file with a line starting `parent:` is
    parsed, so the cost of parsing does not grow with the files that name none.
    """
    board = reading(repo, ref)
    found: dict[str, dict[str, str]] = {}
    for name, text in board.texts.items() if board else ():
        path = Path(name)
        stage = path.parent.name
        if stage == "roadmap" or path.suffix != ".md" or not _PARENT.search(text):
            continue
        parent = parse(text)[0].get("parent")
        if parent:
            found.setdefault(str(parent), {})[path.stem] = stage
    return found


def children(repo: Path, ref: str, parent: str) -> dict[str, str]:
    """The Issues at `ref` that name `parent` as their parent, each with its stage.

    An Issue with children is a Flight. A worktree's state is read at `HEAD`,
    which holds every turn once the loop has settled it.
    """
    return families(repo, ref).get(parent, {})


def descendants(repo: Path, ref: str, parent: str) -> set[str]:
    """Every Issue at `ref` below `parent`: its children, theirs, and so on."""
    kin = families(repo, ref)
    found: set[str] = set()
    todo = [parent]
    while todo:
        for slug in kin.get(todo.pop(), {}):
            if slug not in found and slug != parent:
                found.add(slug)
                todo.append(slug)
    return found


def waiting(repo: Path, ref: str, parent: str) -> bool:
    """Whether a Flight at `ref` has a child that has not landed in `done/`."""
    return any(stage != "done" for stage in children(repo, ref, parent).values())
