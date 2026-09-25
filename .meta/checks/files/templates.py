"""The templates and the YAML they are written in: duplicate keys, duplicate concept IDs, surviving placeholders, a template that does not parse, and the conventions the seeded template must echo.
"""
import pathlib
import re
from collections.abc import Sequence
from typing import Any

import yaml

from checks.collect import (
    META,
    ROOT,
    TEMPLATE,
    TOKEN,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
    view_for,
)
from checks.files import sources


class Strict(yaml.SafeLoader):
    """YAML SafeLoader subclass that intercepts and records duplicate mapping keys (solorepo's DR-053)."""


_DUPLICATES: list[tuple[object, int]] = []


def _note_duplicates(loader: yaml.SafeLoader, node: yaml.MappingNode,
                     deep: bool = False) -> dict[Any, Any]:
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            _DUPLICATES.append((key, key_node.start_mark.line + 1))
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _note_duplicates)


@check("duplicate keys", pre=True)
def duplicate_keys() -> list[str]:
    """Validate that no YAML or YML file across `.meta/` and `template/` defines duplicate keys.

    Enforces that all workflow and assertion YAML files parse without repeated keys,
    preventing silent dictionary value overwrites during loading (solorepo's DR-053, solorepo's DR-120).

    Returns:
        list[str]: Validation problem messages identifying file, line number, and duplicate key name.

    A document that will not parse at all is passed over rather than reported:
    `template parses` owns the malformed document, and a key cannot be written
    twice in a file with no keys.
    """
    problems: list[str] = []
    for path in sorted([*META.rglob("*.yaml"), *META.rglob("*.yml"),
                        *TEMPLATE.rglob("*.yaml"), *TEMPLATE.rglob("*.yml")]):
        _DUPLICATES.clear()
        try:
            yaml.load(path.read_text(), Loader=Strict)
        except yaml.YAMLError:
            continue
        problems += [f"{path.relative_to(ROOT)}:{line} '{key}' written twice"
                     for key, line in _DUPLICATES]
    return problems


def _concept_ids_in_file(path: pathlib.Path) -> list[str]:
    """Checks one YAML file for duplicate concept IDs in any concept_set."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    try:
        loader = yaml.SafeLoader(text)
        node = loader.get_single_node()
    except yaml.YAMLError:
        return []
    if not isinstance(node, yaml.MappingNode):
        return []
    problems: list[str] = []
    for k_node, v_node in node.value:
        if k_node.value == "concept_set" and isinstance(v_node, yaml.SequenceNode):
            seen: dict[str, int] = {}
            for item_node in v_node.value:
                if isinstance(item_node, yaml.MappingNode):
                    for ik_node, iv_node in item_node.value:
                        if ik_node.value == "id":
                            cid = str(iv_node.value)
                            line = iv_node.start_mark.line + 1
                            if cid in seen:
                                try:
                                    rel = path.relative_to(ROOT)
                                except ValueError:
                                    rel = path
                                problems.append(
                                    f"{rel}:{line} concept '{cid}' declared twice in concept_set "
                                    f"(first at line {seen[cid]}) (solorepo's DR-190)"
                                )
                            else:
                                seen[cid] = line
    return problems


@check("duplicate concept ids", pre=True)
def duplicate_concept_ids(
        paths: Sequence[pathlib.Path] | None = None) -> list[str]:
    """Validate that no YAML assertion or template file declaring a concept_set contains duplicate concept IDs.

    Enforces that concept declarations within any concept_set carry unique identifiers,
    preventing silent dictionary overwrites and divergent definitions in the Ubiquitous
    Language (solorepo's DR-190, solorepo's #549).

    Args:
        paths: Specific paths to scan, or None to scan all assertion and template YAML files.

    Returns:
        list[str]: Validation problem messages identifying file, line number, and duplicate concept ID.
    """
    if paths is None:
        scan_paths: list[pathlib.Path] = sorted([
            *(META / "assertions").rglob("*.yaml"),
            *TEMPLATE.rglob("*.yaml"),
        ])
        bootstraps_dir = ROOT / "bootstraps"
        if bootstraps_dir.is_dir():
            scan_paths.extend(sorted(bootstraps_dir.glob("*/assertions/*.yaml")))
    else:
        scan_paths = list(paths)

    problems: list[str] = []
    for path in scan_paths:
        problems.extend(_concept_ids_in_file(path))
    return problems


@check("surviving placeholders")
def surviving_placeholders() -> list[str]:
    """No template token survives anywhere outside `template/` (solorepo's DR-034).

    Scanning only the files `template/` shadows was exact and also useless:
    Specialization deletes `template/` before running the gate, so by the time
    the check ran there was nothing left to compare against and it passed
    vacuously. Scanning everything else keeps it alive in a portfolio, where it
    is the only thing standing between a half-filled skeleton and a first commit.

    The cost is that prose here may not spell a token literally. That is cheap,
    and a literal token outside `template/` is a defect in any case.

    "Everything" is the tree as git sees it: tracked files and untracked ones
    it does not ignore. A build directory is not the tree — rustc writes a
    marker of exactly this shape into every dependency file under `target/`,
    and a scan that walked in there failed the gate for having built the Rust
    seed.
    """
    problems: list[str] = []
    for path in sources.tree():
        if path.is_symlink() or not path.is_file() \
                or TEMPLATE in path.parents or ".git" in path.parts:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        found = sorted(set(TOKEN.findall(text)))
        if found:
            problems.append(f"{path.relative_to(ROOT)}: {', '.join(found)} was never filled in")
    return problems


@check("template parses")
def template_parses(views: Sequence[Any]) -> list[str]:
    """The template is data and is not linted in place. It is checked by filling
    it in and testing the result, which is the only version anyone runs.

    A `.yml` here is a workflow, not an assertion: nothing in the scaffold ever
    loads it, so it is parsed and no further. A container would reject it, and
    the alternative to parsing it is that a portfolio's first CI run is where a
    typo in it is found.
    """
    problems: list[str] = []
    for src, _ in sources.template_files():
        if src.suffix not in (".yaml", ".yml"):
            continue
        filled = TOKEN.sub("placeholder", src.read_text())
        rel = src.relative_to(ROOT)
        try:
            data = yaml.safe_load(filled)
        except yaml.YAMLError as exc:
            problems.append(f"{rel}: does not parse once filled in — {exc}")
            continue
        if not data or src.suffix == ".yml":
            continue
        sv, _ = view_for(data, views)
        if sv is None:
            problems.append(f"{rel}: no container accepts {sorted(data)}")
    return problems


@check("template conventions agree")
def template_conventions_agree() -> StepOutcome:
    """Validate that root agent instructions and seeded template instructions agree on core conventions.

    Verifies that operational conventions asserted in root `AGENTS.md` and `.meta/README.md`
    are faithfully mirrored in `template/AGENTS.md` and `template/.meta/README.md` (solorepo's DR-183).

    Returns:
        Passed | Found | CouldNotRun: Validation result reporting missing convention phrases in template files.
    """
    if not TEMPLATE.is_dir():
        return Passed("no template/ in portfolio")

    ours_agents = ROOT / "AGENTS.md"
    seed_agents = TEMPLATE / "AGENTS.md"
    ours_readme = META / "README.md"
    seed_readme = TEMPLATE / ".meta" / "README.md"

    if not (ours_agents.is_file() and seed_agents.is_file() and
            ours_readme.is_file() and seed_readme.is_file()):
        return CouldNotRun("one or more required convention files are absent")

    agents_conventions = (
        (
            "symlinks to AGENTS.md",
            ("`CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` are symlinks",),
        ),
        ("minting decisions", (".meta/say/move mint",)),
        ("operator surface", ("`just --list`",)),
        ("review handoff", (".meta/say/move request-review",)),
        ("watch semaphore", ("just watch",)),
        ("sweep semaphore", ("just sweep",)),
        ("next issue", ("`just next`",)),
        ("harness memory prohibition", ("harness's memory",)),
        ("empty directory README", ("empty directory carries a README",)),
        ("gate is an exit check", ("exit condition, not an entrance condition",)),
    )

    readme_conventions = (
        ("next issue", ("`just next`",)),
        ("minting decisions", (".meta/say/move mint",)),
        ("operator surface", ("`just --list`",)),
    )

    problems: list[str] = []

    def _check_file(path: pathlib.Path,
                    conventions: Sequence[tuple[str, tuple[str, ...]]]) -> None:
        """Verifies that all specified convention phrases exist in a file."""
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        rel = path.relative_to(ROOT)
        for label, phrases in conventions:
            if not any(phrase in text for phrase in phrases):
                problems.append(f"{rel}: missing convention for '{label}' (expected {phrases[0]!r})")

    for path, convs in ((ours_agents, agents_conventions),
                        (seed_agents, agents_conventions),
                        (ours_readme, readme_conventions),
                        (seed_readme, readme_conventions)):
        _check_file(path, convs)

    if problems:
        return Found(problems)
    return Passed(f"{seed_agents.relative_to(ROOT)} and {seed_readme.relative_to(ROOT)} agree with root conventions")
