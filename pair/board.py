"""The board: issue files under `issues/`, where the directory is the state.

An issue is `issues/<stage>/<slug>.md`. The slug is its id. Front matter holds
only `difficulty`, and optionally `waits_on` and `parent`; everything else is
observed from the directory or derived from git.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

STAGES = ("roadmap", "backlog", "todo", "in-progress", "desk-check", "done")
DIFFICULTIES = ("easy", "medium", "hard", "developer")
ISSUES = "issues"
ORDER = f"{ISSUES}/backlog/ORDER"
"""The backlog's running order: one slug per line, the developer's above `# groomed below`."""
MARKER = "# groomed below"

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


def listed(repo: Path, ref: str, stage: str) -> list[str]:
    """Slugs in one stage directory at a git ref, in filename order."""
    names = git(repo, "ls-tree", "--name-only", ref, f"{ISSUES}/{stage}/", check=False)
    slugs = [
        Path(n).stem
        for n in names.splitlines()
        if n.endswith(".md") and Path(n).name != "README.md"
    ]
    return sorted(slugs)


def at_ref(repo: Path, ref: str, stage: str, slug: str) -> Issue | None:
    """An issue as committed at a ref, or None."""
    text = subprocess.run(
        ["git", "show", f"{ref}:{ISSUES}/{stage}/{slug}.md"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if text.returncode != 0:
        return None
    front, body = parse(text.stdout)
    return Issue(slug, stage, front, body)


def order(repo: Path, ref: str) -> list[str]:
    """The slugs `issues/backlog/ORDER` names at `ref`, first to last.

    The developer's placements sit above the `# groomed below` marker and
    grooming's ranking below it, so the file's own line order is the running
    order. Blank lines and `#` lines name nothing; a missing file names nothing.
    """
    text = subprocess.run(
        ["git", "show", f"{ref}:{ORDER}"], cwd=repo, capture_output=True, text=True
    )
    if text.returncode != 0:
        return []
    return [
        line.strip()
        for line in text.stdout.splitlines()
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


def running_order(repo: Path, ref: str) -> list[str]:
    """Every backlog slug at `ref`, in the order the loop reaches it.

    The top-level slugs, those `ORDER` names first to last and then the rest in
    filename order, each stand for themselves or for a Flight. A Flight expands
    in place into its backlog parts, each part after any sibling its
    `waits_on` names and otherwise in filename order, a part that is a Flight
    expanded the same way, and then the Flight itself. A `waits_on` cycle among
    siblings falls back to filename order.
    """
    kin = families(repo, ref)
    backlog = listed(repo, ref, "backlog")
    inner = parts(backlog_parents(kin), backlog)
    top = [s for s in dict.fromkeys(order(repo, ref)) if s in backlog and s not in inner]
    top += [s for s in backlog if s not in top and s not in inner]
    seen: set[str] = set()

    def expand(slug: str) -> list[str]:
        seen.add(slug)
        kids = sorted(
            c for c, stage in kin.get(slug, {}).items() if stage == "backlog" and c not in seen
        )
        waits = {}
        for kid in kids:
            issue = at_ref(repo, ref, "backlog", kid)
            front = issue.front if issue else {}
            waits[kid] = {w.split(":")[-1] for w in as_list(front.get("waits_on"))}
        placed: list[str] = []
        while kids:
            kid = next(
                (k for k in kids if not ((waits[k] & set(kids)) - {k})), kids[0]
            )
            kids.remove(kid)
            placed.append(kid)
        return [x for kid in placed if kid not in seen for x in expand(kid)] + [slug]

    return [x for slug in top for x in expand(slug)]


def next_ripe(
    repo: Path,
    ref: str,
    skip: frozenset[str] = frozenset(),
    within: frozenset[str] | None = None,
) -> str | None:
    """The backlog item at `ref` the loop takes next: a ripe Flight, else the first ripe item.

    The items are taken in `running_order`, so a Flight's parts run where its
    line in `ORDER` is. An item is ripe when its `waits_on` are all done,
    every Issue naming it in `parent:` is done, and it has no `Needs
    elaboration` section, which marks a send-back the developer has yet to
    answer. A ripe Flight, one with children, is taken before any other ripe
    item, so a Flight is checked as soon as its last child lands; among ripe
    Flights, and among the rest, the running order decides. Slugs in `skip`,
    and with `within` those outside it, are passed over.
    """
    done = set(listed(repo, ref, "done"))
    kin = families(repo, ref)

    def ripe(slug: str) -> bool:
        issue = at_ref(repo, ref, "backlog", slug)
        return bool(
            issue
            and not needs_elaboration(issue.body)
            and all(stage == "done" for stage in kin.get(slug, {}).values())
            and all(
                w.split(":")[-1] in done for w in as_list(issue.front.get("waits_on"))
            )
        )

    first = None
    for slug in running_order(repo, ref):
        if slug in skip or (within is not None and slug not in within):
            continue
        if first is not None and slug not in kin:
            continue
        if ripe(slug):
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
    """
    faults = []
    backlog = sorted(
        p.stem for p in (tree / ISSUES / "backlog").glob("*.md") if p.name != "README.md"
    )
    before = listed(repo, ref, "backlog")
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
    was = subprocess.run(
        ["git", "show", f"{ref}:{ORDER}"], cwd=repo, capture_output=True, text=True
    )
    kept, ranked = split_order(was.stdout) if was.returncode == 0 else ([], None)
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
    extra = sorted({s for s in below if not s.startswith("#") and (s not in wanted or below.count(s) > 1)})
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
    file is no one's child. `git grep` finds the candidate files, so the cost
    does not grow with the files that name no parent.
    """
    hits = git(repo, "grep", "-l", "-E", "^parent:", ref, "--", f"{ISSUES}/", check=False)
    found: dict[str, dict[str, str]] = {}
    for hit in hits.splitlines():
        path = Path(hit.removeprefix(f"{ref}:"))
        stage = path.parent.name
        if stage not in STAGES or stage == "roadmap" or path.suffix != ".md":
            continue
        issue = at_ref(repo, ref, stage, path.stem)
        parent = issue and issue.front.get("parent")
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
