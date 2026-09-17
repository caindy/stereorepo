"""What the workflows and the scaffold owe each other: no scaffold-only path in inherited files, the two gate workflows held equal, the reviewer's trunk-restore set held to the control plane, and the control plane held to the tree.
"""
import pathlib
import re
import sys

import yaml

from collect import (
    META,
    ROOT,
    TEMPLATE,
    CouldNotRun,
    Found,
    Passed,
    check,
)
from files import sources

SCAFFOLD_ONLY = ("template/", "SPECIALIZE.md", "bootstraps/")


@check("scaffold-only paths")
def scaffold_only_paths():
    """Validate that documentation and workflows copied during Specialization contain no scaffold-only paths.

    Ensures that inherited files do not reference paths unique to solorepo (`template/`,
    `SPECIALIZE.md`, `bootstraps/`) unless explicitly qualified with a `solorepo` owner reference (solorepo's DR-036, solorepo's DR-115).

    Returns:
        Passed | Found | CouldNotRun: Validation result listing occurrences of scaffold-only paths.
    """
    problems = []
    scanned = set()

    def scan(paths, names):
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


def _first_difference(a, b, path):
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
def gate_workflows_agree():
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
    shared = {"on": (a.get(True, a.get("on")), b.get(True, b.get("on"))),
              "permissions": (a.get("permissions"), b.get("permissions"))}
    jobs_a, jobs_b = a.get("jobs") or {}, b.get("jobs") or {}
    problems = []
    for name in SHARED_JOBS:
        for path, jobs in ((ours, jobs_a), (seed, jobs_b)):
            if name not in jobs:
                problems.append(f"jobs.{name}: not in {path.relative_to(ROOT)}, "
                                "and it is a job both gate workflows define")
        if name in jobs_a and name in jobs_b:
            shared[f"jobs.{name}"] = tuple(
                {k: v for k, v in jobs[name].items() if k not in NOT_SHARED}
                for jobs in (jobs_a, jobs_b))
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
def control_plane_restore() -> Passed | Found | CouldNotRun:
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
    lists = []
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
def control_plane_packages() -> Passed | Found | CouldNotRun:
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
