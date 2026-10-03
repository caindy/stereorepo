"""Validation of schema slot references cited in living repository prose against LinkML ontologies.

Verifies that prose claims about schema slots resolve against declared schemas
as part of the citation verification subject (stereorepo's DR-150, dividing the gate into
per-subject check modules including prose claims about the record). Sits under the
`.meta/checks/citations/` package following the package structure convention (stereorepo's DR-345,
converting imported meta modules into packages whose __init__ registers defined members).

Former slot checking derives historically deleted slots per class from git diffs,
filtering out any slot declared anywhere in current schemas, and flags obsolete slot
names in backticks within documents asserting those classes. Living durable files
are scanned while historical records under `assertions/decisions/`, as well as
test probe suites under `checks/probes/`, are deliberately excluded: decisions
record historical context at authoring time
(legitimately naming former slots removed during refactoring), while test probes author
synthetic violating fixtures rather than durable claims about the repository record.
History in citations.history.md (stereorepo's DR-171).
"""
import pathlib
import re
import subprocess
from collections.abc import Callable, Sequence
from typing import Any, NamedTuple

import yaml
from linkml_runtime import SchemaView

from checks.citations import loaders, prose
from checks.collect import ROOT, CouldNotRun, Found, Index, Passed, StepOutcome, check, view_for

QUALIFIED_SLOT = re.compile(r"`?(?P<class>[A-Z][a-zA-Z0-9]+)\.(?P<slot>[a-z][a-z0-9_]+)`?")
SLOT_PHRASES = (
    re.compile(r"`(?P<slot>[a-z][a-z0-9_]+)`\s+slot\b"),
    re.compile(r"\bslot\s+`(?P<slot>[a-z][a-z0-9_]+)`"),
    re.compile(r"`(?P<slot>[a-z][a-z0-9_]+)`\s+on\s+`?(?P<class>[A-Z][a-zA-Z0-9]+)`?"),
    re.compile(r"`?(?P<class>[A-Z][a-zA-Z0-9]+)`?'s\s+`(?P<slot>[a-z][a-z0-9_]+)`"),
)
SLOT_HEDGED = re.compile(
    rf"{prose.HEDGED.pattern}|\b(no|none|neither|removed|retire|retired|deprecated|former|replaced)\b",
    re.I,
)
CLAUSE_SPLIT = re.compile(r";\s*|\.\s+|\.$|,\s+|\s*(?:---|--|\u2014|\u2013)\s*")
SCHEMA_PATHS = (
    ".meta/work/",
    ".meta/ddd/",
    ".meta/work_ontology.yaml",
    ".meta/ddd_ontology.yaml",
)


def git_is_shallow() -> tuple[bool | None, str | None]:
    """Determine whether the git checkout has truncated shallow history.

    Returns:
        tuple[bool | None, str | None]: (is_shallow, None) on success, or (None, failure_reason)
        if git query could not be executed or failed.
    """
    try:
        res = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"],
            check=False, capture_output=True, text=True, timeout=30,
        )
        if res.returncode != 0:
            return None, f"git rev-parse exited with code {res.returncode}"
        return res.stdout.strip() == "true", None
    except subprocess.TimeoutExpired:
        return None, "git rev-parse timed out after 30 seconds"
    except (OSError, subprocess.SubprocessError) as err:
        return None, f"git rev-parse failed: {err}"


def _parse_deleted_slots(diff_text: str) -> dict[str, set[str]]:
    r"""Parse class-scoped deleted slot identifiers from git diff text.

    Relies on `git log -p -W` (`--function-context`) to expand diff hunks to enclosing
    context. Under git's default YAML funcname rules, functions match lines starting at
    column 0 (`classes:`), pulling preceding class declarations into the hunk context.

    Tracks a positional state machine adhering to LinkML ontology indentation conventions:
    - Class declarations open at 2 spaces indentation (`^[ +-]  ClassName:\s*$`).
    - Class `slots:` blocks open at 4 spaces indentation (`^[ +-]    slots:\s*$`).
    - Deleted slot list entries appear at 6 spaces indentation (`^-      -\s+slot_name`).
    - Scope resets on diff hunk boundaries (`^@@`), file transitions (`^diff --git`),
      commit boundaries (`^commit `), next class declarations (`^[ +-]  [A-Z]`), or
      sibling class keys at 4 spaces (`^[ +-]    [a-z_]+:\s*$`).

    Parameters:
        diff_text (str): Output text from `git log -p -W`.

    Returns:
        dict[str, set[str]]: Mapping of declaring class names to removed slot identifiers.
    """
    deleted_by_class: dict[str, set[str]] = {}
    curr_class: str | None = None
    in_class_slots = False

    for line in diff_text.splitlines():
        if line.startswith("diff --git") or line.startswith("commit ") or line.startswith("@@"):
            curr_class = None
            in_class_slots = False
            continue
        m_cls = re.match(r"^[ +-]  ([A-Z][a-zA-Z0-9]+):\s*$", line)
        if m_cls:
            curr_class = m_cls.group(1)
            in_class_slots = False
            continue
        if curr_class:
            if re.match(r"^[ +-]    slots:\s*$", line):
                in_class_slots = True
            elif re.match(r"^[ +-]    [a-z_]+:\s*$", line):
                in_class_slots = False
            elif re.match(r"^[ +-]  [A-Z]", line):
                curr_class = None
                in_class_slots = False
            elif in_class_slots:
                m_del = re.match(r"^-      -\s+([a-z][a-z0-9_]+)", line)
                if m_del:
                    deleted_by_class.setdefault(curr_class, set()).add(m_del.group(1))

    return deleted_by_class


def deleted_schema_slots() -> tuple[dict[str, set[str]] | None, str | None]:
    """Extract class-scoped deleted schema slot names from git commit diffs up to HEAD.

    Returns:
        tuple[dict[str, set[str]] | None, str | None]: Mapping of class name to deleted slot
        identifiers and None on success, or None and a specific failure reason string.
    """
    is_shallow, shallow_err = git_is_shallow()
    if shallow_err is not None:
        return None, shallow_err
    if is_shallow:
        return (
            None,
            "shallow clone: git history is truncated and former schema slots cannot be derived",
        )

    try:
        cmd = ["git", "-C", str(ROOT), "log", "-p", "-W", "HEAD", "--", *SCHEMA_PATHS]
        res = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30)
        if res.returncode != 0:
            return None, f"git log exited with code {res.returncode}"
    except subprocess.TimeoutExpired:
        return None, "git log timed out after 30 seconds"
    except (OSError, subprocess.SubprocessError) as err:
        return None, f"git log failed: {err}"

    return _parse_deleted_slots(res.stdout), None


def file_asserted_classes(path: pathlib.Path, views: Sequence[Any]) -> set[str]:
    """Derive the document-level set of classes instantiated within a YAML assertion file.

    Parameters:
        path (pathlib.Path): Target assertion file path.
        views (Sequence[Any]): Loaded LinkML schema views.

    Returns:
        set[str]: Class names instantiated within top-level container slots.
    """
    if path.suffix not in (".yaml", ".yml"):
        return set()
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return set()
    if not isinstance(data, dict):
        return set()
    sv, root = view_for(data, views)
    if sv is None or root is None:
        return set()
    classes: set[str] = set()
    for key in data:
        try:
            slot = sv.induced_slot(key, root)
            if slot and slot.range in sv.all_classes():
                classes.add(slot.range)
        except (KeyError, ValueError, AttributeError):
            pass
    return classes


def _compile_schema_indices(
    views: Sequence[Any],
) -> tuple[dict[str, set[str]], set[str]]:
    """Compile class-to-slot mapping and complete slot vocabulary from loaded schema views."""
    class_slots: dict[str, set[str]] = {}
    all_slots: set[str] = set()
    for sv in views:
        for cname in sv.all_classes():
            try:
                cslots = set(sv.class_slots(cname))
                class_slots.setdefault(cname, set()).update(cslots)
                all_slots.update(cslots)
            except (KeyError, ValueError, AttributeError):
                pass
        for sname in sv.all_slots():
            all_slots.add(sname)
    return class_slots, all_slots


def _check_clause_citations(
    clause: str,
    rel: str,
    class_slots: dict[str, set[str]],
    all_slots: set[str],
) -> list[str]:
    """Check a single clause for qualified and explicit slot citations."""
    problems: list[str] = []
    for m in QUALIFIED_SLOT.finditer(clause):
        cls, slot = m.group("class"), m.group("slot")
        if cls in class_slots and slot not in class_slots[cls]:
            problems.append(
                f"{rel}: '{cls}.{slot}' cites slot '{slot}', which is not declared on class {cls}"
            )

    for pat in SLOT_PHRASES:
        for m in pat.finditer(clause):
            slot = m.group("slot")
            if cls := m.groupdict().get("class"):
                if cls in class_slots and slot not in class_slots[cls]:
                    problems.append(
                        f"{rel}: '{m.group(0)}' cites slot '{slot}', "
                        f"which is not declared on class {cls}"
                    )
            elif slot not in all_slots:
                problems.append(
                    f"{rel}: '{m.group(0)}' cites slot '{slot}', which is not declared in schemas"
                )
    return problems


def _check_clause_former_slots(
    clause: str,
    rel: str,
    asserted_classes: set[str],
    former_slots: dict[str, set[str]],
) -> list[str]:
    """Check a single clause for bare backticked former slots scoped to asserted classes."""
    if not asserted_classes:
        return []
    problems: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"`([a-z][a-z0-9_]*)`", clause):
        b_slot = m.group(1)
        if b_slot in seen:
            continue
        removed_from = [
            c for c in asserted_classes
            if b_slot in former_slots.get(c, set())
        ]
        if not removed_from:
            continue
        seen.add(b_slot)
        classes_str = ", ".join(sorted(removed_from))
        problems.append(
            f"{rel}: '`{b_slot}`' cites '{b_slot}', "
            f"removed from {classes_str} and declared on no current schema class"
        )
    return problems


class SlotIndices(NamedTuple):
    """Indices compiled from declared schema classes, all slots, and removed slots."""

    class_slots: dict[str, set[str]]
    all_slots: set[str]
    former_slots: dict[str, set[str]]


def check_prose_spans(
    spans: Sequence[str],
    rel: str,
    indices: SlotIndices,
    asserted_classes: set[str],
) -> list[str]:
    """Validate slot citations across a sequence of prose spans."""
    problems: list[str] = []
    for span in spans:
        for clause in CLAUSE_SPLIT.split(span):
            clause = clause.strip()
            if not clause or SLOT_HEDGED.search(clause):
                continue
            problems.extend(
                _check_clause_citations(clause, rel, indices.class_slots, indices.all_slots)
            )
            problems.extend(
                _check_clause_former_slots(
                    clause, rel, asserted_classes, indices.former_slots
                )
            )
    return problems


def _scan_durable_file(
    path: pathlib.Path,
    views: Sequence[Any],
    indices: SlotIndices,
) -> list[str]:
    """Extract prose spans and validate all contained slot references for a durable file."""
    rel = path.relative_to(ROOT).as_posix()
    asserted_classes = file_asserted_classes(path, views)
    spans = prose.prose(path)
    if path.suffix in (".yaml", ".yml"):
        try:
            text = path.read_text(encoding="utf-8")
            spans = spans + prose.comments(text)
        except (OSError, UnicodeDecodeError):
            pass
    return check_prose_spans(spans, rel, indices, asserted_classes)


def _former_slots(
    raw_deleted: dict[str, set[str]],
    class_slots: dict[str, set[str]],
    all_slots: set[str],
) -> dict[str, set[str]]:
    """Derive class-scoped deleted slots that are declared on no current schema class."""
    former_slots: dict[str, set[str]] = {}
    for cls, slots_set in raw_deleted.items():
        former = (slots_set - all_slots) - class_slots.get(cls, set())
        if former:
            former_slots[cls] = former
    return former_slots


def product_views(
    index: Index,
    load: Callable[[str], Any] = SchemaView,
) -> tuple[list[Any], list[str]]:
    """Load the LinkML schemas the portfolio's Projects name in their `schemas` slot.

    `SchemaView` parses lazily, so each view is asked for its classes here: a
    file that is not a schema fails where its path and Project can be named,
    and so does one that declares no class, which YAML that is not LinkML
    loads as (stereorepo's DR-304).

    Parameters:
        index (Index): The identified objects of the assertions.
        load (Callable[[str], Any]): Builds a schema view from a file path.

    Returns:
        tuple[list[Any], list[str]]: The loaded views, and one problem line per
        named schema that is missing, does not load, or declares no class.
    """
    views: list[Any] = []
    problems: list[str] = []
    for ident, (cls, obj, _where) in sorted(index.items()):
        if cls != "Project":
            continue
        for rel in obj.get("schemas") or []:
            path = ROOT / rel
            if not path.is_file():
                problems.append(f"{ident}: schema '{rel}' does not exist")
                continue
            try:
                sv = load(str(path))
                declared = sv.all_classes()
            except Exception as err:  # noqa: BLE001  # reason: LinkML and the YAML parser raise their own hierarchies for a file that is not a schema, and any of them is a problem to name rather than a crash
                problems.append(f"{ident}: schema '{rel}' does not load: {err}")
                continue
            if not declared:
                problems.append(f"{ident}: schema '{rel}' declares no class")
                continue
            views.append(sv)
    return views, problems


@check("cited schema slots")
def cited_schema_slots(
    views: Sequence[Any],
    index: Index,
    deleted: Callable[[], tuple[dict[str, set[str]] | None, str | None]] = deleted_schema_slots,
) -> StepOutcome:
    """Validate that schema slots cited in living durable prose resolve against LinkML declarations.

    Resolves against stereorepo's schemas and the product schemas the
    portfolio's Projects name. A class both declare passes a citation of a
    slot either one declares, since which of them a sentence means cannot be
    told (stereorepo's DR-304). Excludes historical decision records
    (`assertions/decisions/`) and test probe suites (`checks/probes/`).

    Parameters:
        views (Sequence[Any]): Loaded LinkML SchemaView instances.
        index (Index): The identified objects of the assertions, read for Projects' `schemas`.
        deleted (Callable): Supplier yielding class-scoped deleted slot names or error from diffs.

    Returns:
        StepOutcome: Passed with file and slot metrics, Found naming unresolved slot
        citations or product schemas that do not load, or CouldNotRun if git
        history is truncated or unreadable.
    """
    raw_deleted, reason = deleted()
    if raw_deleted is None:
        return CouldNotRun(reason or "git history could not be read to derive former schema slots")

    product, unloaded = product_views(index)
    if unloaded:
        return Found(unloaded)

    class_slots, all_slots = _compile_schema_indices([*views, *product])
    former_slots = _former_slots(raw_deleted, class_slots, all_slots)

    indices = SlotIndices(class_slots=class_slots, all_slots=all_slots, former_slots=former_slots)
    problems: list[str] = []
    scanned = 0

    for path in loaders.durable(loaders.copied_files()):
        rel = path.relative_to(ROOT).as_posix()
        if (
            "assertions/decisions/" in rel
            or "checks/probes/" in rel
        ):
            continue
        scanned += 1
        problems.extend(_scan_durable_file(path, views, indices))

    if problems:
        return Found(problems)
    return Passed(
        f"{scanned} living durable files scanned (excluding decisions, "
        f"and probes) against {len(all_slots)} schema slots across {len(class_slots)} classes "
        f"in {len(views) + len(product)} schemas, {len(product)} of them the portfolio's own"
    )
