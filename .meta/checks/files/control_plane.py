"""
The control plane read back against the tree: the reviewer workflow restores
exactly what `depth.CONTROL_PLANE` names, and a package under `.meta/lib/` is
control plane exactly when the script it is the body of is (solorepo's DR-217,
solorepo's DR-219).

The constant is the one statement of what the control plane is, because the
reviewer workflow restores what a list says and cannot run a derivation. These
steps run the derivation the constant cannot.
"""

import pathlib
import re
import sys
import types

from checks.collect import (
    META,
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)
from checks.files.workflows import REVIEW_WORKFLOW

RESTORE_LINE = re.compile(r"^\s+\.claude[^\n]*$", re.M)
"""The line of `review.yml` listing the trunk-restore set as paths: the pathspec line under
`git restore`, which begins with `.claude`."""


RESTORE_COUNT = re.compile(r"^\s+# (\w+) paths are trunk's", re.M)
"""The line of `review.yml` stating how many paths are trunk's, in the restore step's comment;
the number is a word."""


NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                "ten", "eleven", "twelve", "thirteen", "fourteen")
"""The number words the workflow's prose may spell a count with."""


@check("control plane restore")
def control_plane_restore() -> StepOutcome:
    """The reviewer workflow restores exactly the control plane from trunk (solorepo's DR-217).

    `depth.CONTROL_PLANE` is the one statement of what the control plane is,
    and under `.meta/lib/` it names the initialiser, the shared `gh` runner and
    the packages of control-plane scripts rather than the directory
    (solorepo's DR-219).
    `.github/workflows/review.yml` states the trunk-restore set once, as the
    pathspec of the `run trunk's channel` step, with its count in that step's
    comment. The review door, `.meta/say/on`, reads the constant itself for
    the head's copies under `.review/head/` and for the constraints every
    agent the review spawns is bound by, and the door's probe holds those two
    (solorepo's DR-264). This step fails when the pathspec is not the control
    plane less the workflows' own directory, in either direction, or when the
    count is not its length.
    """
    if not REVIEW_WORKFLOW.is_file():
        return CouldNotRun(f"{REVIEW_WORKFLOW.relative_to(ROOT).as_posix()} is missing")
    sys.path.insert(0, str(META))
    import depth
    text = REVIEW_WORKFLOW.read_text(encoding="utf-8")
    lists = [tuple(line.split()) for line in RESTORE_LINE.findall(text)]
    if len(lists) != 1:
        return Found((f"review.yml: expected one trunk-restore list and found {len(lists)}",))
    problems = []
    restored = {entry.rstrip("/") for entry in lists[0]}
    expected = {prefix.rstrip("/") for prefix in depth.CONTROL_PLANE
                if not prefix.startswith(".github/workflows")}
    for missing in sorted(expected - restored):
        problems.append(f"review.yml: `{missing}` is control plane in depth.CONTROL_PLANE and "
                        "the trunk-restore pathspec does not carry it; add it")
    for extra in sorted(restored - expected):
        problems.append(f"review.yml: the trunk-restore pathspec carries `{extra}`, which "
                        "depth.CONTROL_PLANE does not name; add it there or drop it here")
    counts = RESTORE_COUNT.findall(text)
    if len(counts) != 1:
        problems.append("review.yml: expected the count of trunk's paths stated once and found "
                        f"{len(counts)}")
    for word in counts:
        if word.lower() not in NUMBER_WORDS or NUMBER_WORDS.index(word.lower()) != len(lists[0]):
            problems.append(f"review.yml: says {word!r} paths are trunk's and the pathspec lists "
                            f"{len(lists[0])}")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(restored)} paths restored from trunk, all the control plane")


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


def _shared_modules(depth_module: types.ModuleType) -> tuple[str, ...]:
    """The bare modules `depth.CONTROL_PLANE` admits directly under `.meta/lib/` (solorepo's #748).

    Args:
        depth_module: The loaded `depth` module, read for `CONTROL_PLANE`.

    Returns:
        tuple[str, ...]: Each admitted module's path, repository-relative.
    """
    lib = LIB.relative_to(ROOT).as_posix()
    return tuple(entry for entry in depth_module.CONTROL_PLANE
                 if entry.startswith(f"{lib}/") and entry.endswith(".py")
                 and not entry.endswith("/__init__.py"))


def _unadmitted_modules(depth_module: types.ModuleType) -> list[str]:
    """The bare modules under `.meta/lib/` the envelope does not admit (solorepo's #748).

    Solorepo's DR-217 fixes one package per script under `.meta/lib/<script>/`,
    so a module sitting loose beside those packages is either shared control
    plane, which `depth.CONTROL_PLANE` says and this reads back, or a package
    that was never made. The admitted set is derived from the constant rather
    than listed again here, so the constant stays the one statement of what the
    control plane is; a module the constant names and the tree does not hold is
    reported by `control_plane_packages` itself, with every other missing path.

    Args:
        depth_module: The loaded `depth` module, read for `CONTROL_PLANE`.

    Returns:
        list[str]: One finding per bare module the constant does not name.
    """
    lib = LIB.relative_to(ROOT).as_posix()
    admitted = _shared_modules(depth_module)
    named = ", ".join(f"`{entry}`" for entry in admitted)
    admits = f"depth.CONTROL_PLANE admits {named}" if named else "it admits no bare module"
    return [f"`{lib}/{item.name}` is a bare module under {lib}/ the envelope does not admit; "
            f"solorepo's DR-217 fixes one package per script under {lib}/<script>/, and "
            f"{admits}"
            for item in sorted(LIB.iterdir())
            if item.is_file() and item.suffix == ".py" and item.name != "__init__.py"
            and f"{lib}/{item.name}" not in admitted]


@check("control plane packages")
def control_plane_packages() -> StepOutcome:
    """A package under `.meta/lib/` is control plane when the script it is the body of is.

    Recognizes `.meta/lib/gh.py` as the shared control-plane runner (solorepo's DR-217,
    solorepo's DR-219, solorepo's #748).

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
    restore would name a path that is gone. A bare module under `.meta/lib/` is
    refused unless `depth.CONTROL_PLANE` names it, which is what admits the
    shared `gh` runner and nothing else.
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
    problems.extend(_unadmitted_modules(depth))
    for listed in depth.CONTROL_PLANE:
        if listed.startswith(f"{lib}/") and not (ROOT / listed.rstrip("/")).exists():
            problems.append(f"depth.CONTROL_PLANE names `{listed}`, which the tree does not hold; "
                            "the reviewer would restore a path that is gone")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(packages)} packages under .meta/lib/, each control plane exactly "
                  "when its script is")
