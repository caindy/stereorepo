"""The branch half of the handoff: A18, and what a branch that changes the record owes with it.

What is read here is the tree and this repository's own commits, never GitHub:
uncommitted or unpushed work, a stale render, and an adopted decision naming
no Artifact that carries it (solorepo's DR-175).
"""
import json
import pathlib
import re
import subprocess
from collections.abc import Sequence

from lib.check_pr import META, ROOT, github, review

# The record's own rendered index. Every branch that settles a decision rewrites
# it and no entry names it, so the step below passes over it — the exclusion A20
# already makes, for the reason it gives: naming the record itself would satisfy
# the letter and defeat the point.
INDEX = ".meta/decisions.md"

# An entry of the record, by the file it is written in.
ENTRY_FILE = re.compile(r"^\.meta/assertions/decisions/DR-(\d+)\.yaml$")

# An Artifact's path, as the two files that declare one write it: four spaces,
# because an Artifact is an item of a single list in each file and `path` is its
# slot. Read with a regex rather than parsed, because `check_pr.py` is run with
# bare `python3` everywhere it runs — CI, `just pr`, the reviewer's tool list —
# and so holds to the standard library and has no YAML reader to reach for.
ARTIFACT = re.compile(r"^    path: (\S+)$", re.M)

# A row of `decisions.md`'s by-artifact table: the file, then the entries naming
# it. The record's other tables key on an entry rather than on a backticked
# path, so none of them match.
ROW = re.compile(r"^\| \[`([^`]+)`\][^|]*\|([^|]*)\|", re.M)
DR = re.compile(r"DR-(\d+)")

# The render, invoked as `just render` invokes it. Naming what it is run with is
# this file's only choice: it needs PyYAML and this one does not have it.
RENDER = ["uvx", "--python", "3.13", "--with", "pyyaml", "python",
          str(META.resolve() / "render.py"), "--check"]

RECORD = (".meta/assertions/decisions/", ".meta/decisions.md")

ADVANCE_NOTICE_MARKER = "<!-- solorepo:advance-finding -->"
"""HTML comment marker identifying an in-place advance finding notice (solorepo's DR-255)."""

MERGE_REFUSAL_MARKER = "<!-- solorepo:merge-refusal -->"
"""HTML comment marker identifying an in-place merge refusal notice (solorepo's DR-255)."""


def standing_notices(pr_number: int | str) -> list[tuple[str, str]]:
    """Return every active advance or refusal notice (solorepo's DR-255).

    Args:
        pr_number: The pull request number to inspect.

    Returns:
        list[tuple[str, str]]: `(kind, finding_text)` pairs for each active
            notice, where kind is 'advance' or 'refusal'.
    """
    try:
        data = github.gh("pr", "view", str(pr_number), "--json", "comments")
        comments = data.get("comments", [])
        if not isinstance(comments, list):
            return []
        notices = []
        for c in comments:
            body = c.get("body", "") if isinstance(c, dict) else ""
            if ADVANCE_NOTICE_MARKER in body or MERGE_REFUSAL_MARKER in body:
                kind = "refusal" if MERGE_REFUSAL_MARKER in body else "advance"
                lines = [line.strip().removeprefix("> ").strip()
                         for line in body.splitlines() if line.strip().startswith("> ")]
                if lines and lines[0]:
                    notices.append((kind, lines[0]))
                    continue
                finding = next(
                    (
                        s for line in body.splitlines()
                        if (s := line.strip())
                        and not s.startswith("<!--")
                        and not s.startswith("Actor:")
                        and not s.startswith("Agent:")
                    ),
                    "notice stands",
                )
                notices.append((kind, finding))
        return notices
    except (OSError, json.JSONDecodeError, AttributeError):
        return []


def advance_notice(pr_number: int | str) -> str | None:
    """Return the advance-finding text if one stands (solorepo's DR-255).

    Args:
        pr_number: The pull request number to inspect.

    Returns:
        str | None: The finding text from the active advance notice, or None.
    """
    return next((finding for kind, finding in standing_notices(pr_number) if kind == "advance"), None)


def owned_and_open() -> tuple[str, list[tuple[int, str, list[str] | None]]]:
    """Identify the pull request associated with the current branch or list open ones.

    Returns:
        tuple[str, list[tuple[int, str, list[str] | None]]]: Current branch name and
            list of tuples containing PR number, title, and unaddressed thread summaries.
    """
    branch = subprocess.run(["git", "branch", "--show-current"],
                            check=False, capture_output=True, text=True).stdout.strip()
    if branch and branch != "main":
        found = github.gh("pr", "list", "--head", branch, "--state", "open",
                   "--json", "number,title")
        if found:
            return branch, [(p["number"], p["title"], review.unaddressed(github.threads(str(p["number"]))))
                            for p in found]
        return branch, []
    return branch, [(p["number"], p["title"], None)
                    for p in github.gh("pr", "list", "--state", "open", "--json", "number,title")]


def residue() -> list[str]:
    """Identifies local branches and worktrees whose remote tracking branches are gone.

    Returns:
        list[str]: Descriptions and git cleanup commands for orphaned branches and worktrees.

    The pull request a gone branch carried names the line and nothing else, so
    a branch GitHub will not answer for is reported as unreadable and still
    carries its removal commands. What GitHub said in refusing goes on a
    continuation line under the branch, where a message of any length costs the
    listing no column: a credential that has expired fails every branch alike,
    and that reads differently from one node GitHub declined to serve.
    """
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], check=False, capture_output=True, text=True).stdout
    git("fetch", "--prune", "--quiet", "origin")
    gone = [line.split()[0] for line in
            git("for-each-ref", "--format=%(refname:short) %(upstream:track,nobracket)",
                "refs/heads/").splitlines()
            if line.endswith(" gone")]
    if not gone:
        return []
    worktrees: dict[str, str | None] = {}
    path: str | None = None
    for line in git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/"):
            worktrees[line[len("branch refs/heads/"):]] = path
    here = git("rev-parse", "--show-toplevel").strip()
    out: list[str] = []
    for branch in gone:
        refusal = ""
        try:
            found = github.gh("pr", "list", "--head", branch,
                              "--state", "all", "--json", "number,state")
        except SystemExit as unreadable:
            state = "pull request unreadable"
            refusal = github.reason(unreadable)
        else:
            state = (f"#{found[0]['number']} {found[0]['state'].lower()}"
                     if found else "no pull request")
        tree = worktrees.get(branch)
        out.append(f"  {branch} — {state}" + (f"; worktree {tree}" if tree else ""))
        if refusal:
            out.append(f"    {refusal}")
        if tree == here:
            out.append("    this worktree stands on it: remove it from the main checkout, "
                       "or let the harness at exit")
            continue
        if tree:
            out.append(f"    git worktree remove {tree}")
        out.append(f"    git branch -D {branch}")
    return out


def unpushed() -> list[str]:
    """Verifies that the working tree has no uncommitted changes and all commits are pushed.

    Returns:
        list[str]: Validation error messages for uncommitted or unpushed modifications.
    """
    def git(*args: str) -> tuple[int, str, str]:
        """Executes a git command and returns its status code, stdout, and stderr.

        Returns:
            tuple[int, str, str]: Return code, stripped stdout, and stripped stderr.
        """
        out = subprocess.run(["git", *args], check=False, capture_output=True, text=True)
        return out.returncode, out.stdout.strip(), out.stderr.strip()

    problems: list[str] = []
    code, dirty, err = git("status", "--porcelain")
    if code:
        return [f"git status failed, so nothing here was checked: {err}"]
    if dirty:
        problems.append(f"{len(dirty.splitlines())} uncommitted change(s); a successor sees none of them")
    code, upstream, _ = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if code:
        problems.append("the branch has no upstream; push it, or there is nothing to hand over")
        return problems
    code, ahead, err = git("rev-list", f"{upstream}..HEAD")
    if code:
        return [*problems, f"git rev-list failed, so pushed state is unknown: {err}"]
    if ahead:
        problems.append(f"{len(ahead.splitlines())} commit(s) not pushed; the branch is the handoff")
    return problems


def git_read(*args: str) -> tuple[int, str]:
    """Executes a git command in ROOT, returning its return code and stdout.

    Args:
        *args: Command arguments passed to git.

    Returns:
        tuple[int, str]: Git return code and raw standard output string.
    """
    out = subprocess.run(["git", *args], check=False, capture_output=True, text=True, cwd=ROOT)
    return out.returncode, out.stdout


def git_text(*args: str, default: str = "") -> str:
    """Executes a git command in ROOT, returning stdout on success or default on failure.

    Args:
        *args: Command arguments passed to git.
        default: Fallback string to return if the command exits non-zero.

    Returns:
        str: Output text on success, or the default fallback string.
    """
    code, out = git_read(*args)
    return default if code else out


def touched(base: str) -> list[str] | None:
    """Returns all paths modified on this branch against the merge base, including untracked files.

    Args:
        base: Target branch or commit ref to compute the merge base against.

    Returns:
        list[str] | None: Unique relative paths modified or added, or None if git diff failed.
    """
    merge = git_text("merge-base", "HEAD", base).strip() or base
    code, diffed = git_read("diff", "--name-only", merge)
    if code:
        return None
    named = diffed.split()
    named += git_text("ls-files", "--others", "--exclude-standard").split()
    return list(dict.fromkeys(named))


def artifacts() -> set[str]:
    """Extracts declared artifact paths from structure assertions.

    Returns:
        set[str]: Set of artifact path strings declared in structure assertions.
    """
    found: set[str] = set()
    for rel in ("assertions/structure.yaml", "assertions/imported/structure.yaml"):
        path = META / rel
        if path.is_file():
            found |= set(ARTIFACT.findall(path.read_text()))
    return found


def accounted() -> dict[str, set[int]]:
    """Maps artifact file paths to the set of decision numbers that enact them.

    Returns:
        dict[str, set[int]]: Mapping of artifact file paths to decision ID numbers.
    """
    path = ROOT / INDEX
    if not path.is_file():
        return {}
    return {file: {int(n) for n in DR.findall(entries)}
            for file, entries in ROW.findall(path.read_text())}


def unrendered() -> tuple[list[str] | None, list[str] | None, str]:
    """Checks whether generated documentation pages match their source assertions.

    Returns:
        tuple[list[str] | None, list[str] | None, str]: A 3-tuple containing:
            - stale: Names of pages differing from rendered output, or None on failure.
            - unrendered: Names of pages missing generated output, or None on failure.
            - error: Descriptive error message if the render command could not run.
    """
    try:
        out = subprocess.run(RENDER, check=False, capture_output=True, text=True, cwd=ROOT)
    except OSError as missing:
        return None, None, f"{RENDER[0]} could not be run — {missing}"
    said = out.stdout.strip()
    if out.returncode == 0 and said == "up to date":
        return [], [], ""
    named: dict[str, list[str]] = {}
    for line in said.splitlines():
        prefix, colon, rest = line.partition(":")
        if colon:
            named[prefix.strip()] = [n.strip() for n in rest.split(",") if n.strip()]
    if out.returncode == 1 and named and set(named) <= {"stale", "unrendered"}:
        return named.get("stale", []), named.get("unrendered", []), ""
    return None, None, ("render.py --check answered neither: "
                        + (said or out.stderr.strip() or f"exit {out.returncode}"))


def artifact_map() -> dict[str, str]:
    """Maps artifact IDs (e.g. 'work:artifact/meta-charter') to their declared paths.

    Returns a dictionary (`dict[str, str]`) mapping these artifact ID strings to
    their declared file paths relative to the workspace root.
    """
    mapping: dict[str, str] = {}
    for rel in ("assertions/structure.yaml", "assertions/imported/structure.yaml"):
        path = META / rel
        if not path.is_file():
            continue
        curr_id: str | None = None
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("- id:"):
                curr_id = stripped.split(":", 1)[1].strip()
            elif curr_id and stripped.startswith("path:"):
                p = stripped.split(":", 1)[1].strip().strip('"\'')
                mapping[curr_id] = p
                curr_id = None
    return mapping


def parse_decision_yaml(path: pathlib.Path) -> tuple[str | None, list[str]]:
    """Parses a decision yaml file, returning its status and the list of enacted_in artifact ids.

    The `path` parameter expects a `pathlib.Path` instance pointing to the YAML
    decision file. Returns a tuple of `(status, enacted_in)` consisting of
    `status` (a string or None) and `enacted_in` (a list of artifact ID strings).
    """
    status: str | None = None
    enacted_in: list[str] = []

    lines = path.read_text().splitlines()
    in_enacted_in = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("status:"):
            status = stripped.split(":", 1)[1].strip().strip('"\'')
        elif stripped.startswith("enacted_in:"):
            in_enacted_in = True
            continue
        elif in_enacted_in:
            if stripped.startswith("-"):
                art = stripped.removeprefix("-").strip().strip('"\'')
                enacted_in.append(art)
            elif line.startswith("  ") and not stripped:
                continue
            elif stripped and not stripped.startswith("-") and ":" in stripped:
                in_enacted_in = False

    return status, enacted_in


def unenacted(base: str) -> tuple[list[str] | None, str]:
    """Verifies that every adopted decision settled on this branch enacts non-record artifacts.

    Args:
        base: Git ref string to compare against (e.g. 'origin/main').

    Returns:
        tuple[list[str] | None, str]: Problem descriptions (or None if base cannot resolve)
            and a summary note string.
    """
    changed = touched(base)
    if changed is None:
        return None, f"{base} did not resolve, so what this branch changed is unread"
    settled = sorted({int(m.group(1)) for p in changed if (m := ENTRY_FILE.match(p))})
    if not settled:
        return [], "this branch settles no decision"

    amap = artifact_map()
    problems: list[str] = []

    for n in settled:
        path = ROOT / f".meta/assertions/decisions/DR-{n:03d}.yaml"
        if not path.is_file():
            continue

        status, enacted_in = parse_decision_yaml(path)
        if status == "ADOPTED":
            valid_paths: list[str] = []
            for art_id in enacted_in:
                p = amap.get(art_id)
                if p and not any(p.startswith(r) for r in RECORD):
                    valid_paths.append(p)
            if not valid_paths:
                problems.append(
                    f"DR-{n:03d}: is adopted and names no Artifact carrying its rule "
                    f"under enacted_in — name at least one non-record Artifact carrying its rule"
                )

    shown = ", ".join(f"DR-{n:03d}" for n in settled)
    return problems, f"{len(settled)} decision(s) settled on this branch ({shown})"


def handoff(base: str) -> int:
    """Executes handoff validation checking unpushed commits, stale renders, and enacted artifacts.

    Args:
        base: Git ref (e.g. 'origin/main') to evaluate branch changes against.

    Returns:
        int: 0 if all handoff checks pass; 1 if any check fails.

    The render names a page relative to `.meta/`, which is how the Artifact
    asserting its prose is found too, so a name the render answered with is
    turned back into the repository-relative path the record's table and this
    file's own reads are keyed on.
    """
    def mark(label: str, problems: Sequence[str], note: str = "") -> bool:
        for p in problems:
            print(f"x  {p}")
        print(("x  " if problems else "ok ") + label
              + (f" — {note}" if note and not problems else ""))
        return bool(problems)

    failed = mark("handoff", unpushed())
    stale, orphans, unread = unrendered()
    if stale is None or orphans is None:
        print(f"?  rendered — {unread}")
    else:
        failed |= mark("rendered",
                       [f"{name} is stale; re-render with `just render` and commit it"
                        for name in stale]
                       + [f"{name} is on disk and no target renders it; `just render` writes "
                          f"nothing for it — restore the target, or drop the page"
                          for name in orphans],
                       "every generated page is the render of what it asserts")
    unnamed = [] if stale is None or orphans is None else stale + orphans
    unsure = stale is None or INDEX in {
        (pathlib.Path(".meta") / name).as_posix() for name in unnamed}
    if unsure:
        print(f"?  enacted — {INDEX} is "
              + ("unread, " if stale is None else "a page the render could not call current, ")
              + "and what names each file is read from it")
    else:
        problems, note = unenacted(base)
        if problems is None:
            print(f"?  enacted — {note}")
        else:
            failed |= mark("enacted", problems, note)
    return 1 if failed else 0
