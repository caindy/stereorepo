"""Where the repository is, the registry, and the assertions read into an index.

Every step of the gate reaches what this module holds: the paths, the schemas,
the one pass over `.meta/assertions/` that turns the documents into identified
objects and reference sites, and `@check`, which is how a step says it is one.
Nothing here checks anything, which is why every other module of the gate may
import it and it imports none of them (solorepo's DR-150).

The registry is here rather than in `check.py` for that reason alone: a step
registers itself at its definition, so the decorator has to be importable by
every module that defines one, and `check.py` imports those modules.

Which slots hold references is read off the schema rather than listed here: a
slot is a reference when its range is a class with an identifier and it is not
inlined. Listing them by hand would drift from the schemas the moment either
moved.
"""
import collections
import inspect
import pathlib
import re
import typing
from collections.abc import Callable
from typing import NamedTuple

import yaml
from linkml_runtime import SchemaView

META = pathlib.Path(__file__).resolve().parent.parent
ROOT = META.parent
TEMPLATE = ROOT / "template"
TOKEN = re.compile(r"__[A-Z][A-Z0-9_]*__")
SCHEMAS = ("work_ontology.yaml", "ddd_ontology.yaml")

Step = collections.namedtuple("Step", "label run pre sources")
# Every step of the gate, in the order they are defined. A table of labels kept
# somewhere else is a second place to edit for every step, and it sits far from
# the function it names, so the label and the docstring that explains the step
# are never read together; the decorator puts them together.
STEPS: list[Step] = []
# What `main` has to give a step, and the only parameter names a step may
# require. A step takes the ones it names, in the order it names them.
SOURCES = ("index", "refs", "views", "asked", "pages")


class CouldNotRun:
    """The step did not run. Loud, unmarked, and exits zero."""
    def __init__(self, why):
        self.why = why


class Passed:
    """The step ran and found nothing. Carries what it checked (its scope)."""
    def __init__(self, scope):
        self.scope = scope


class Found:
    """The step found problems. One line per problem."""
    def __init__(self, problems):
        self.problems = problems


StepOutcome = Passed | Found | CouldNotRun
"""What a step comes to, and the only thing a step returns. Named apart from `probes.harness`'s
`Outcome`, which is what a call under a probe exited with."""

StepFunction = typing.TypeVar("StepFunction", bound=Callable[..., StepOutcome])
"""A step, whatever sources it names. `check` hands back the same function, so a step keeps its
own signature and whatever annotations it carries."""


def check(label: str, pre: bool = False) -> Callable[[StepFunction], StepFunction]:
    """Register a step under the label the gate prints, at its definition.

    A parameter with a default is not a source: it is a seam a probe passes a
    fake through, and nothing is passed for it here. A parameter without one
    must name a source, and a step that asks for anything else is refused at
    import — which is the moment to find it, since the alternative is a gate
    that dies on the step rather than on the typo.

    `pre` runs the step before the schemas load. LinkML's loader raises on the
    first repeated key with no file and no line, so a duplicate in `work/*.yaml`
    used to take the whole gate down before the check that names both had a
    chance to run (solorepo's #23). A precheck is a step that must not stand
    behind that door.

    Args:
        label: What the gate prints for this step.
        pre: Whether the step runs before the schemas load.

    Returns:
        Callable[[StepFunction], StepFunction]: A decorator that appends the
        step to `STEPS` and hands it back unchanged, and that raises `TypeError`
        where the step requires a parameter `SOURCES` does not name.
    """
    def register(fn: StepFunction) -> StepFunction:
        sources = tuple(name for name, p in inspect.signature(fn).parameters.items()
                        if p.default is inspect.Parameter.empty)
        unknown = [name for name in sources if name not in SOURCES]
        if unknown:
            raise TypeError(f"{fn.__name__} requires {', '.join(unknown)}, which the gate has "
                            f"nothing to pass; a step's sources are {', '.join(SOURCES)}")
        STEPS.append(Step(label, fn, pre, sources))
        return fn

    return register


def recorded_baseline(path: pathlib.Path) -> dict[str, int]:
    """A ratchet baseline read off disk: repository-relative path to the debt it may still hold.

    Args:
        path: The baseline file, a YAML mapping of path to count.

    Returns:
        dict[str, int]: The recorded counts, empty where the file is absent.
    """
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def against_baseline(counts: dict[str, int], sites: dict[str, list[str]],
                     recorded: dict[str, int], noun: str,
                     baseline: pathlib.Path) -> list[str]:
    """What a ratchet has to say about the counts it found, against the counts it recorded.

    The comparison the Ratchet Discipline turns on: a baseline that may fall
    and may not rise, so a file is failed on either side of its number — over,
    because the debt grew; under, because a baseline nobody lowers has stopped
    being one. It lives here rather than beside either step that reads it, because a
    checker importing another checker for it would be an edge back up the
    gate's import graph (solorepo's DR-150).

    Args:
        counts: Repository-relative path to the debt the tree holds.
        sites: Repository-relative path to the detail lines listed under a
            failing file, each already formatted.
        recorded: Repository-relative path to the debt the baseline allows.
        noun: What is being counted, as it reads in the failure sentence.
        baseline: The baseline file, named in the failure so the edit is stated.

    Returns:
        list[str]: One line per file whose count is not its recorded number,
        naming the number to write, and then one line per site in that file.
        A file the baseline holds and the tree no longer has is a stale entry
        and says so instead.
    """
    problems = []
    for relative in sorted(set(counts) | set(recorded)):
        count, allowed = counts.get(relative, 0), recorded.get(relative, 0)
        if count == allowed:
            continue
        if not (ROOT / relative).is_file():
            problems.append(f"{relative}: baseline holds a file that does not exist")
            continue
        direction = "over" if count > allowed else "under"
        problems.append(f"{relative}: {count} {noun}, {direction} its baseline of "
                        f"{allowed} — write {count} in {baseline.relative_to(ROOT).as_posix()}")
        problems.extend(f"     {line}" for line in sites.get(relative, []))
    return problems


def tree_root(sv):
    """Returns the class designated as tree_root in the schema view, or None."""
    for name, cls in sv.all_classes().items():
        if cls.tree_root:
            return name
    return None


def view_for(data, views):
    """The schema whose container accepts every top-level key in this document."""
    for sv in views:
        root = tree_root(sv)
        if root and set(data) <= set(sv.class_slots(root)):
            return sv, root
    return None, None


class Collected(NamedTuple):
    """What one pass over the assertions gathers: identified objects by identifier, and every reference site."""

    index: dict
    refs: list


def walk(obj, cls, sv, found, where):
    """Collect identified objects into `found.index` and reference sites into `found.refs`."""
    if not isinstance(obj, dict):
        return
    ident = sv.get_identifier_slot(cls)
    if ident and ident.name in obj:
        found.index[obj[ident.name]] = (cls, obj, where)
    for key, val in obj.items():
        try:
            slot = sv.induced_slot(key, cls)
        except Exception:
            continue
        if slot is None or slot.range not in sv.all_classes():
            continue
        target = slot.range
        values = val if isinstance(val, list) else [val]
        if sv.get_identifier_slot(target) and not (slot.inlined or slot.inlined_as_list):
            for v in values:
                if isinstance(v, str):
                    found.refs.append((v, target, f"{where}: {cls}.{key}"))
        else:
            for v in values:
                walk(v, target, sv, found, where)


def views():
    """Loads LinkML SchemaView instances for all schemas declared in SCHEMAS."""
    return [SchemaView(str(META / s)) for s in SCHEMAS]


def collect(views):
    """Scans all YAML assertions under .meta/assertions/ and bootstraps/*/assertions/, indexing entities and references."""
    found, skipped = Collected({}, []), []
    paths = sorted((META / "assertions").rglob("*.yaml"))
    bootstraps_dir = ROOT / "bootstraps"
    if bootstraps_dir.is_dir():
        paths.extend(sorted(bootstraps_dir.glob("*/assertions/*.yaml")))
    for path in paths:
        data = yaml.safe_load(path.read_text())
        if not data:
            continue
        sv, root = view_for(data, views)
        if sv is None:
            skipped.append(path.name)
            continue
        for key, val in data.items():
            slot = sv.induced_slot(key, root)
            for item in (val if isinstance(val, list) else [val]):
                walk(item, slot.range, sv, found, path.name)
    return found.index, found.refs, skipped

