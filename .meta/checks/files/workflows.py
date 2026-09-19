"""What the workflows and the scaffold owe each other: no scaffold-only path in inherited files, the two gate workflows held equal, the reviewer's trunk-restore set held to the control plane, the control plane held to the tree, and a workflow that names its harness naming it where the channel reads it.
"""
import os
import pathlib
import re
import sys
from collections.abc import Sequence
from typing import Any

import yaml

from checks.collect import (
    META,
    ROOT,
    TEMPLATE,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)
from checks.files import sources

SCAFFOLD_ONLY = ("template/", "SPECIALIZE.md", "bootstraps/")


@check("scaffold-only paths")
def scaffold_only_paths() -> StepOutcome:
    """Validate that documentation and workflows copied during Specialization contain no scaffold-only paths.

    Ensures that inherited files do not reference paths unique to solorepo (`template/`,
    `SPECIALIZE.md`, `bootstraps/`) unless explicitly qualified with a `solorepo` owner reference (solorepo's DR-036, solorepo's DR-115).

    Returns:
        Passed | Found | CouldNotRun: Validation result listing occurrences of scaffold-only paths.
    """
    problems: list[str] = []
    scanned: set[pathlib.Path] = set()

    def scan(paths: Sequence[pathlib.Path], names: Sequence[str]) -> None:
        for path in paths:
            if path.suffix not in (".md", ".yaml", ".yml") or not path.is_file():
                continue
            scanned.add(path)
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if "solorepo" in line.lower():
                    continue
                for name in names:
                    if name in line:
                        problems.append(f"{path.relative_to(ROOT)}:{number} names "
                                        f"'{name}', which a portfolio does not have")

    for token in sources.inherited():
        base = ROOT / token if (ROOT / token).exists() else META / token
        paths = [base] if base.is_file() else sorted(base.rglob("*")) if base.is_dir() else []
        scan(paths, SCAFFOLD_ONLY)
    scan(sorted(TEMPLATE.rglob("*")), tuple(n for n in SCAFFOLD_ONLY if n != "template/"))

    if not scanned:
        return CouldNotRun("no inherited paths or template/ to scan")
    if problems:
        return Found(problems)
    return Passed(f"{len(scanned)} file{'s' if len(scanned) != 1 else ''}")


# The half the two gate workflows share, by job (solorepo's DR-119): each of these is in
# both files and equal across them. The seed's own job is `gate` (solorepo's DR-115), and
# the scaffold's seed jobs are its alone.
SHARED_JOBS = ("pull-request", "sweep")


SEED_OWN_JOBS = ("gate",)


# Except where the job runs (solorepo's DR-140). This repository's gate runs on a
# self-hosted scale set that exists on one machine; a fresh clone has no cluster
# and every runner GitHub will give it. That is a fact about the machine each
# repository has, not about what the job does, and holding it equal would force
# one of the two to name a runner it does not have.
NOT_SHARED = ("runs-on",)


def _first_difference(a: Any, b: Any, path: str) -> tuple[str, str] | None:
    """Where two loaded YAML values first differ, as a dotted path, or None."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in list(a) + [k for k in b if k not in a]:
            if key not in a or key not in b:
                return f"{path}.{key}", "only on one side"
            found = _first_difference(a[key], b[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(a, list) and isinstance(b, list):
        for i, (x, y) in enumerate(zip(a, b, strict=False)):
            found = _first_difference(x, y, f"{path}[{i}]")
            if found:
                return found
        if len(a) != len(b):
            return f"{path}[{min(len(a), len(b))}]", "only on one side"
        return None
    return None if a == b else (path, f"{a!r} against {b!r}")


@check("gate workflows agree")
def gate_workflows_agree() -> StepOutcome:
    """Validate that the root gate workflow and seeded template workflow agree on shared jobs.

    Verifies structural and semantic parity across triggers, permissions, and shared jobs
    (`pull-request`, `sweep`) between `.github/workflows/gate.yml` and `template/.github/workflows/gate.yml` (solorepo's DR-115, solorepo's DR-119, solorepo's DR-140).

    Returns:
        Passed | Found | CouldNotRun: Validation result detailing any discrepancy between shared workflow halves.

    The `on` key is read under the boolean `True` before its own name: YAML 1.1
    reads a bare `on` as a boolean and pyyaml is a 1.1 parser, so a workflow
    written the ordinary way arrives with `True` for a key.
    """
    ours = ROOT / ".github" / "workflows" / "gate.yml"
    seed = TEMPLATE / ".github" / "workflows" / "gate.yml"
    if not (ours.is_file() and seed.is_file()):
        return CouldNotRun("either ours or template workflow is absent")
    a = yaml.safe_load(ours.read_text()) or {}
    b = yaml.safe_load(seed.read_text()) or {}
    shared: dict[str, tuple[Any, Any]] = {
        "on": (a.get(True, a.get("on")), b.get(True, b.get("on"))),
        "permissions": (a.get("permissions"), b.get("permissions"))}
    jobs_a, jobs_b = a.get("jobs") or {}, b.get("jobs") or {}
    problems = []
    for name in SHARED_JOBS:
        for path, jobs in ((ours, jobs_a), (seed, jobs_b)):
            if name not in jobs:
                problems.append(f"jobs.{name}: not in {path.relative_to(ROOT)}, "
                                "and it is a job both gate workflows define")
        if name in jobs_a and name in jobs_b:
            halves = [{k: v for k, v in jobs[name].items() if k not in NOT_SHARED}
                      for jobs in (jobs_a, jobs_b)]
            shared[f"jobs.{name}"] = (halves[0], halves[1])
    for name in jobs_b:
        if name not in SHARED_JOBS + SEED_OWN_JOBS:
            problems.append(f"jobs.{name}: in {seed.relative_to(ROOT)} and neither shared "
                            f"nor the seed's own; the seed's jobs are {', '.join(SEED_OWN_JOBS)} "
                            f"and the shared {', '.join(SHARED_JOBS)}")
    for label, (x, y) in shared.items():
        found = _first_difference(x, y, label)
        if found:
            where, how = found
            problems.append(f"{where}: {how} — {ours.relative_to(ROOT)} and "
                            f"{seed.relative_to(ROOT)} share this half, and it is held equal")
    if problems:
        return Found(problems)
    return Passed(f"{ours.relative_to(ROOT)} and {seed.relative_to(ROOT)} agree")


REVIEW_WORKFLOW = ROOT / ".github" / "workflows" / "review.yml"
"""The reviewer workflow, which restores the control plane from trunk before a reviewer reads anything."""


RESTORE_LINE = re.compile(r"^\s+(?:\.claude|TRUNK:)[^\n]*$", re.M)
"""A line of `review.yml` listing the trunk-restore set as paths: the pathspec line under
`git restore`, which begins with `.claude`, or the `TRUNK` environment variable."""


RESTORE_COUNT = re.compile(r"^\s+(?:# |\*\*)(\w+) paths (?:are|in the worktree are) trunk's", re.M)
"""A line of `review.yml` stating how many paths are trunk's, in the step's comment and in the
constraints every agent is bound by; the number is a word, which the step reads back."""


RESTORE_PROSE = re.compile(r"\*\*\w+ paths in the worktree are trunk's[^\n]*\n(.*?`)\.(?=\s)", re.S)
"""The sentence after the constraints' count that enumerates the paths in backticks: everything
up to the full stop that closes the last backticked path."""


NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                "ten", "eleven", "twelve")
"""The number words the workflow's prose may spell a count with."""


@check("control plane restore")
def control_plane_restore() -> StepOutcome:
    """The reviewer workflow restores exactly the control plane from trunk, in every place it states the set (solorepo's DR-217).

    `depth.CONTROL_PLANE` is the one statement of what the control plane is,
    and under `.meta/lib/` it names the initialiser and the packages of
    control-plane scripts rather than the directory (solorepo's DR-219).
    `.github/workflows/review.yml` states the trunk-restore set four times: as
    the pathspec of the `run trunk's channel` step, as the `TRUNK` variable that
    builds `.review/head/`, as a count in that step's comment, and as a count
    and an enumeration in the constraints every agent the review spawns is
    bound by. This step fails when the two path lists are not the control plane
    less the workflows' own directory, in either direction; when either count
    is not their length; or when the enumeration names a different set.
    """
    if not REVIEW_WORKFLOW.is_file():
        return CouldNotRun(f"{REVIEW_WORKFLOW.relative_to(ROOT).as_posix()} is missing")
    sys.path.insert(0, str(META))
    import depth
    text = REVIEW_WORKFLOW.read_text(encoding="utf-8")
    lists: list[tuple[str, ...]] = []
    for line in RESTORE_LINE.findall(text):
        words = line.split()
        lists.append(tuple(words[1:] if words[0] == "TRUNK:" else words))
    if len(lists) != 2:
        return Found((f"review.yml: expected two trunk-restore lists and found {len(lists)}",))
    problems = []
    if lists[0] != lists[1]:
        problems.append("review.yml: the `git restore` pathspec and `TRUNK` differ: "
                        f"{' '.join(lists[0])} against {' '.join(lists[1])}")
    restored = {entry.rstrip("/") for entry in lists[0]}
    expected = {prefix.rstrip("/") for prefix in depth.CONTROL_PLANE
                if not prefix.startswith(".github/workflows")}
    for missing in sorted(expected - restored):
        problems.append(f"review.yml: `{missing}` is control plane in depth.CONTROL_PLANE and "
                        "the trunk-restore lists do not carry it; add it to both")
    for extra in sorted(restored - expected):
        problems.append(f"review.yml: the trunk-restore lists carry `{extra}`, which "
                        "depth.CONTROL_PLANE does not name; add it there or drop it here")
    counts = RESTORE_COUNT.findall(text)
    if len(counts) != 2:
        problems.append(f"review.yml: expected the count of trunk's paths stated twice and found {len(counts)}")
    for word in counts:
        if word.lower() not in NUMBER_WORDS or NUMBER_WORDS.index(word.lower()) != len(lists[0]):
            problems.append(f"review.yml: says {word!r} paths are trunk's and the pathspec lists {len(lists[0])}")
    prose = RESTORE_PROSE.search(text)
    named = {entry.rstrip("/") for entry in re.findall(r"`([^`]+)`", prose.group(1))} if prose else set()
    if named != restored:
        problems.append("review.yml: the constraints enumerate "
                        f"{' '.join(sorted(named)) or 'nothing'} and the pathspec restores "
                        f"{' '.join(sorted(restored))}")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(restored)} paths restored from trunk, stated four ways, all the control plane")


WORKFLOWS = ROOT / ".github" / "workflows"
"""Where this repository's workflows live, the loops among them."""


WRITES_AGENT = re.compile(r"\bAI_AGENT=")
"""A workflow naming the harness in the variable the harness itself overwrites."""


WRITES_RUN_AGENT = re.compile(r"\bACTOR_AGENT=")
"""A workflow naming the harness in the variable it writes before the harness starts,
which is the one the channel signs with in a run (solorepo's DR-233)."""


@check("signed runs name their harness")
def signed_runs_name_their_harness() -> StepOutcome:
    """A workflow writes `ACTOR_AGENT` wherever it writes `AI_AGENT` (solorepo's DR-233).

    `channel.agent()` does not read `AI_AGENT` in a run, because the harness
    overwrites that name with its own build string and a value the agent's shell
    typed there cannot be told from the ordinary one. `ACTOR_AGENT` is what the
    workflow writes before the harness starts, and a run that carries none signs
    with the step GitHub attests instead — which says which step spoke and not
    which harness. So the two names are written together, in the fallback steps
    as much as in the step that chooses, and this fails where a file writes one
    without the other.

    Returns:
        Passed | Found | CouldNotRun: The counts per workflow, or each file
        whose two names are written a different number of times.
    """
    if not WORKFLOWS.is_dir():
        return CouldNotRun(f"{WORKFLOWS.relative_to(ROOT).as_posix()} is missing")
    problems, counted = [], 0
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        chosen, signed_with = len(WRITES_AGENT.findall(text)), len(WRITES_RUN_AGENT.findall(text))
        counted += chosen
        if chosen != signed_with:
            problems.append(f"{path.relative_to(ROOT)}: writes `AI_AGENT` {chosen} time(s) and "
                            f"`ACTOR_AGENT` {signed_with}; the channel signs a run with the "
                            "second, so every write of the first has one beside it")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} harness names written, each under both variables")


LIB = META / "lib"
"""Where a script under `.meta/` keeps its body, one package per script (solorepo's DR-217)."""


def scripts_of(package: str) -> tuple[pathlib.Path, ...]:
    """The scripts a package under `.meta/lib/` could be the body of.

    The relationship is fixed by name (solorepo's DR-217), so a script is looked
    up rather than declared: a package `<name>` is the body of `.meta/<name>.py`,
    of the channel program `.meta/say/<name>`, or of the hook
    `.meta/hooks/<name>.py`. More than one of those three can exist at once: a
    portfolio that writes the depth hook `.meta/hooks/depth.py`, which
    `.meta/hooks/depth.py.example` is the model for, has it beside `.meta/depth.py`
    and only one of the two is control plane. So every script the tree holds
    under the name is returned, and the caller says what a division between them
    means.

    Args:
        package: A package directory's name under `.meta/lib/`.

    Returns:
        tuple[pathlib.Path, ...]: Each script's path, in the order the three
        places are searched, and empty where the tree holds none of them.
    """
    candidates: tuple[pathlib.Path, ...] = (
        META / f"{package}.py", META / "say" / package, META / "hooks" / f"{package}.py")
    return tuple(candidate for candidate in candidates if candidate.is_file())


@check("control plane packages")
def control_plane_packages() -> StepOutcome:
    """A package under `.meta/lib/` is control plane exactly when the script it is the body of is (solorepo's DR-219).

    Those packages are listed in `depth.CONTROL_PLANE` rather than derived
    (solorepo's DR-219), because the reviewer workflow restores what a list says
    and cannot run a derivation. Splitting a control-plane script is therefore a
    two-place act, the package and the constant, and this step is what holds the
    second place to the first: it runs the derivation the constant cannot, and
    fails where the two disagree.

    Every child directory of `.meta/lib/` but the interpreter's caches is a
    package, and each resolves through `scripts_of` to the scripts that take its
    name. `depth.SCAFFOLD_BOUNDARY` is then asked about each of those paths:
    where it matches, the boundary must also cover `.meta/lib/<name>/`; where it
    does not, the boundary must leave the package outside, since the restore is
    no-overlay and a package taken from trunk deletes the body the pull request
    adds. Two scripts of one name that fall on opposite sides of the boundary
    leave the package's side undecided, and that is reported rather than guessed.
    A package the constant names and the tree does not hold fails too: the
    restore would name a path that is gone.
    """
    if not LIB.is_dir():
        return CouldNotRun(f"{LIB.relative_to(ROOT).as_posix()} is missing")
    sys.path.insert(0, str(META))
    import depth
    lib = LIB.relative_to(ROOT).as_posix()
    problems: list[str] = []
    packages = sorted(entry.name for entry in LIB.iterdir()
                      if entry.is_dir() and not entry.name.startswith((".", "__")))
    for name in packages:
        prefix = f"{lib}/{name}/"
        covered = depth.SCAFFOLD_BOUNDARY.search(prefix) is not None
        scripts = {path: depth.SCAFFOLD_BOUNDARY.search(path) is not None
                   for path in (script.relative_to(ROOT).as_posix()
                                for script in scripts_of(name))}
        if not scripts:
            problems.append(f"`{prefix}` is the body of no script: solorepo's DR-217 fixes one by "
                            f"name at .meta/{name}.py, .meta/say/{name} or .meta/hooks/{name}.py, "
                            "and until a script takes the name nothing says whether the package "
                            "is control plane")
            continue
        named = " and ".join(f"`{path}`" for path in scripts)
        if len(set(scripts.values())) > 1:
            problems.append(f"`{prefix}` is the body of {named}, which the control plane divides; "
                            "say which of them it is the body of before the boundary is derived "
                            "from it")
        elif all(scripts.values()) and not covered:
            problems.append(f"`{prefix}` is the body of {named}, which is control plane, and the "
                            f"boundary does not cover it; name `{prefix}` in depth.CONTROL_PLANE")
        elif covered and not any(scripts.values()):
            problems.append(f"`{prefix}` is control plane and {named}, which it is the body of, "
                            "is not; drop it from depth.CONTROL_PLANE, or name the script there "
                            "if the envelope is meant to hold it")
    for listed in depth.CONTROL_PLANE:
        if listed.startswith(f"{lib}/") and not (ROOT / listed.rstrip("/")).exists():
            problems.append(f"depth.CONTROL_PLANE names `{listed}`, which the tree does not hold; "
                            "the reviewer would restore a path that is gone")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(packages)} packages under .meta/lib/, each control plane exactly "
                  "when its script is")


ALLOWED_TOOLS_LINE = re.compile(r'--allowedTools\s+"([^"]*)"')
"""The Claude path's `--allowedTools` value, inside the `claude_args` block scalar."""


CORE_TOOLS_LINE = re.compile(r'"core"\s*:\s*\[([^\]]*)\]')
"""The Gemini path's `tools.core` array, inside the `settings` block scalar."""


DANGEROUS_TOOLS = (
    ("Write", "write_file"),
    ("Edit", "replace"),
    ("WebFetch", "web_fetch"),
    ("WebSearch", "google_web_search"),
)
"""Each entry pairs Claude Code's name for one capability with Gemini CLI's; neither reviewer
path's allowlist may name either half, on its own or alongside the other (solorepo's #454)."""


@check("gemini reviewer allowlist matches claude's")
def gemini_allowlist_matches_claude() -> StepOutcome:
    """The reviewer workflow bounds Gemini CLI's tool registry the way it bounds Claude Code's (solorepo's #454).

    The Claude path names what the model may call with `--allowedTools`, so a
    tool it never names is simply not there for the model to reach. Gemini
    CLI's default is the opposite: an unset `tools.core` holds the whole core
    toolset, so the same bound has to be named rather than left absent. This
    step fails when either path's list is missing, or when either path names
    either half of a `DANGEROUS_TOOLS` pair — whether the other path names its
    half too or not, since the invariant is that neither may.

    History in files.history.md (solorepo's DR-171).
    """
    if not REVIEW_WORKFLOW.is_file():
        return CouldNotRun(f"{REVIEW_WORKFLOW.relative_to(ROOT).as_posix()} is missing")
    text = REVIEW_WORKFLOW.read_text(encoding="utf-8")
    allowed_match = ALLOWED_TOOLS_LINE.search(text)
    core_match = CORE_TOOLS_LINE.search(text)
    if not allowed_match:
        return Found(("review.yml: no `--allowedTools` value on the Claude path to compare against",))
    if not core_match:
        return Found(("review.yml: no `tools.core` value on the Gemini path; unset, it holds "
                      "the whole core toolset, which is the bound solorepo's #454 found missing",))
    problems: list[str] = []
    claude_tools = {token.split("(", 1)[0] for token in allowed_match.group(1).split(",")}
    gemini_tools = {token.strip().strip('"') for token in core_match.group(1).split(",")}
    for claude_name, gemini_name in DANGEROUS_TOOLS:
        if claude_name in claude_tools:
            problems.append(f"review.yml: the Claude path names `{claude_name}`; no reviewer "
                            f"path may name this pair, so drop it from `--allowedTools`")
        if gemini_name in gemini_tools:
            problems.append(f"review.yml: the Gemini path names `{gemini_name}`; no reviewer "
                            f"path may name this pair, so drop it from `tools.core`")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(DANGEROUS_TOOLS)} tool pairs held out of both reviewer paths alike")


BEFORE_TOOL_MATCHER = re.compile(r'"matcher"\s*:\s*"\^\(([^)]*)\)\$"')
"""The Gemini path's `BeforeTool` matcher: the alternation of tool names `worktree_only.py`
is registered against, inside the `settings` block scalar."""


@check("gemini tools.core matches the BeforeTool matcher")
def gemini_core_matches_hook_matcher() -> StepOutcome:
    """`tools.core` and the `BeforeTool` matcher name the same tools, or a call reaches `worktree_only.py` never sees (solorepo's #454).

    `tools.core` decides which tools the model may call at all; the `BeforeTool`
    matcher decides which of those calls the worktree-confinement hook
    inspects. The two are meant to name the same set, and this pull request's
    own first head is the demonstration of what happens when they do not:
    `activate_skill` sat in `tools.core` and outside the matcher, admitted and
    unguarded, with every gate but a review thread green. This step fails when
    the two sets differ, in either direction.

    History in files.history.md (solorepo's DR-171).
    """
    if not REVIEW_WORKFLOW.is_file():
        return CouldNotRun(f"{REVIEW_WORKFLOW.relative_to(ROOT).as_posix()} is missing")
    text = REVIEW_WORKFLOW.read_text(encoding="utf-8")
    core_match = CORE_TOOLS_LINE.search(text)
    matcher_match = BEFORE_TOOL_MATCHER.search(text)
    if not core_match:
        return Found(("review.yml: no `tools.core` value on the Gemini path to compare against",))
    if not matcher_match:
        return Found(("review.yml: no `BeforeTool` matcher on the Gemini path to compare against",))
    core_tools = {token.strip().strip('"') for token in core_match.group(1).split(",")}
    matcher_tools = set(matcher_match.group(1).split("|"))
    problems: list[str] = []
    for extra in sorted(core_tools - matcher_tools):
        problems.append(f"review.yml: `tools.core` names `{extra}`, which the `BeforeTool` "
                        "matcher does not guard; add it there or drop it from `tools.core`")
    for extra in sorted(matcher_tools - core_tools):
        problems.append(f"review.yml: the `BeforeTool` matcher guards `{extra}`, which "
                        "`tools.core` does not name; the matcher is guarding a tool the model "
                        "cannot call, and the trunk comment's count is off by it")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(core_tools)} tools admitted, all and only the ones the BeforeTool matcher guards")


INLINE_PYTHON = re.compile(
    r"\b(?:python[0-9.]*|uv\s+run\s+python)\b(?:\s+-[a-zA-Z0-9_.-]+(?:\s+[^\s-]\S*)?)*\s+(-c\b|<<|-\s*<<|-\s*$)|"
    r"\|\s*(?:python[0-9.]*|uv\s+run\s+python)(?:\s+-[a-zA-Z0-9_.-]+(?:\s+[^\s-]\S*)?)*\s*$"
)
"""Matches inline Python invocations executing embedded code from CLI strings, stdin heredocs, or piped interpreters."""


def _workflow_files() -> set[pathlib.Path]:
    """Finds all GitHub Actions workflow and composite action files."""
    files: set[pathlib.Path] = set()
    candidate_dirs = (
        ROOT / ".github" / "workflows",
        TEMPLATE / ".github" / "workflows",
        META / "actions",
    )
    for d in candidate_dirs:
        if d.is_dir():
            files.update(p for p in d.rglob("*") if p.suffix in (".yml", ".yaml") and p.is_file())
    return files


def _is_shell_script(path: pathlib.Path) -> bool:
    """Checks whether a non-symlink file without extension is a shell script."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
        return (first_line.startswith("#!")
                and ("bash" in first_line or "sh" in first_line)
                and "python" not in first_line)
    except OSError:
        return False


def _shell_scripts() -> set[pathlib.Path]:
    """Finds all shell script and recipe files across the repository."""
    scripts: set[pathlib.Path] = set()
    if (ROOT / "justfile").is_file():
        scripts.add(ROOT / "justfile")
    ignored_dir_prefixes = (".", "target", "venv")
    for root, dirs, files in os.walk(ROOT):
        rel_root = pathlib.Path(root).relative_to(ROOT)
        dirs[:] = [
            d for d in dirs
            if not any(d.startswith(prefix) for prefix in ignored_dir_prefixes)
            or (rel_root == pathlib.Path() and d in (".meta", ".github"))
        ]
        for file in files:
            p = pathlib.Path(root) / file
            if p.is_symlink() or not p.is_file():
                continue
            if p.suffix in (".sh", ".bash") or (not p.suffix and _is_shell_script(p)):
                scripts.add(p)
    return scripts


def _logical_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Joins backslash-continued lines into single logical lines while preserving line numbering."""
    logical: list[tuple[int, str]] = []
    current_line = ""
    start_num = 1
    for num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") and not current_line:
            continue
        if not current_line:
            start_num = num
        if stripped.endswith("\\"):
            current_line += line.rstrip()[:-1] + " "
        else:
            current_line += line
            logical.append((start_num, current_line))
            current_line = ""
    if current_line:
        logical.append((start_num, current_line))
    return logical


def _find_inline_python_in_file(path: pathlib.Path) -> list[str]:
    """Scans one file for embedded inline Python invocations, returning problem descriptions."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"{path.relative_to(ROOT)}: could not read — {exc}"]

    problems: list[str] = []
    for number, line in _logical_lines(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if INLINE_PYTHON.search(line):
            problems.append(
                f"{path.relative_to(ROOT)}:{number} contains inline Python: '{stripped}' "
                "— externalize to a dedicated .meta/ script or CLI flag (solorepo's DR-241)"
            )
    return problems


@check("inline python")
def no_inline_python() -> StepOutcome:
    """Workflow steps, composite actions, and shell scripts contain no embedded inline Python invocations (solorepo's DR-241, solorepo's #666).

    Ensures that workflow steps, composite actions, shell scripts, and recipe
    definitions execute dedicated, type-checked Python scripts under `.meta/`
    or existing CLI flags rather than inline Python strings (`python3 -c`,
    stdin heredocs, or piped interpreters) that bypass linters, type checkers,
    and repository gate checks.

    History in files.history.md (solorepo's DR-171).
    """
    scanned = _workflow_files() | _shell_scripts()
    if not scanned:
        return CouldNotRun("no workflows, actions, or shell scripts found to scan")

    problems: list[str] = []
    for path in sorted(scanned):
        problems.extend(_find_inline_python_in_file(path))

    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(scanned)} files scanned, none containing inline Python")
