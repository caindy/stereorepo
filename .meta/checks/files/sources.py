"""Which files the gate reads: the tree as git sees it, the templates, the Python under `.meta/`, and the Specialization copy set.

`tree()` is the only list of files the gate trusts, and `citations.py` reads prose out of it (solorepo's DR-150).
"""
import pathlib
import re
import subprocess

import yaml

from checks.collect import (
    META,
    ROOT,
    TEMPLATE,
)


def template_files() -> list[tuple[pathlib.Path, pathlib.Path]]:
    """Every file under `template/`, paired with the path it seeds at the repository root.

    Returns:
        list[tuple[pathlib.Path, pathlib.Path]]: `(template file, seeded file)`
        pairs in path order, or an empty list where there is no `template/`.
    """
    if not TEMPLATE.is_dir():
        return []
    return [(f, ROOT / f.relative_to(TEMPLATE)) for f in sorted(TEMPLATE.rglob("*")) if f.is_file()]


def tree() -> list[pathlib.Path]:
    """Every file git would commit or is not ignoring, or every file at all
    where there is no git to ask."""
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others",
                             "--exclude-standard", "-z"],
                            check=False, capture_output=True, text=True)
    if listed.returncode:
        return sorted(ROOT.rglob("*"))
    return sorted(ROOT / name for name in listed.stdout.split("\0") if name)


def inherited() -> list[str]:
    """What Specialization copies into a portfolio, read from the step that
    lists it, so the copy set is stated once and this check follows it. A
    portfolio carries no Specialization Discipline — its Disciplines are under
    `imported/`, and this one is not among them — so the file is absent there,
    and absent is an empty copy set rather than a step that dies on the read."""
    source = META / "assertions" / "disciplines.yaml"
    if not source.is_file():
        return []
    data = yaml.safe_load(source.read_text()) or {}
    for discipline in data.get("disciplines") or []:
        if discipline.get("id") != "work:discipline/specialization":
            continue
        for step in discipline.get("steps") or []:
            if step.startswith("Copy what is inherited"):
                return re.findall(r"`([^`]+)`", step)
    return []


def is_py(path: pathlib.Path) -> bool:
    """Whether a path under `.meta/` is Python source the gate's Python steps own.

    A `.py` file, or a file with no suffix at all whose first line is a Python
    shebang — `.meta/gate` and the channel's verbs are typed at a shell, so they
    carry the interpreter in line one instead of in a suffix. Hidden directories
    and `__pycache__` are not source.

    Every step that asks what Python lives under `.meta/` asks here, so that the
    answer is one answer.

    Args:
        path: An existing path under `META`.

    Returns:
        bool: True where the file is Python source under `.meta/`.
    """
    if any(part.startswith(".") and part != "." for part in path.relative_to(META).parts):
        return False
    if "__pycache__" in path.parts:
        return False
    if path.suffix == ".py":
        return True
    if not path.suffix and path.is_file():
        try:
            with path.open("rb") as handle:
                first = handle.readline().decode("latin1", "ignore")
                return first.startswith("#!") and "python" in first
        except OSError:
            pass
    return False


def meta_sources() -> list[pathlib.Path]:
    """Every Python source file under `.meta/`, in path order.

    Returns:
        list[pathlib.Path]: The absolute paths `is_py` accepts.
    """
    return sorted(p for p in META.rglob("*") if is_py(p))
