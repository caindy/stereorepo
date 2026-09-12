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

import yaml
from linkml_runtime import SchemaView


META = pathlib.Path(__file__).resolve().parent.parent
ROOT = META.parent
TEMPLATE = ROOT / "template"
TOKEN = re.compile(r"__[A-Z][A-Z0-9_]*__")
SCHEMAS = ("work_ontology.yaml", "ddd_ontology.yaml")

# Every step of the gate, in the order they are defined. A table of labels kept
# somewhere else is a second place to edit for every step, and it sits far from
# the function it names, so the label and the docstring that explains the step
# are never read together; the decorator puts them together.
STEPS = []
Step = collections.namedtuple("Step", "label run pre sources")
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


def check(label, pre=False):
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
    """
    def register(fn):
        sources = tuple(name for name, p in inspect.signature(fn).parameters.items()
                        if p.default is inspect.Parameter.empty)
        unknown = [name for name in sources if name not in SOURCES]
        if unknown:
            raise TypeError(f"{fn.__name__} requires {', '.join(unknown)}, which the gate has "
                            f"nothing to pass; a step's sources are {', '.join(SOURCES)}")
        STEPS.append(Step(label, fn, pre, sources))
        return fn

    return register


def tree_root(sv):
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


def walk(obj, cls, sv, index, refs, where):
    """Collect identified objects into `index` and reference sites into `refs`."""
    if not isinstance(obj, dict):
        return
    ident = sv.get_identifier_slot(cls)
    if ident and ident.name in obj:
        index[obj[ident.name]] = (cls, obj, where)
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
                    refs.append((v, target, f"{where}: {cls}.{key}"))
        else:
            for v in values:
                walk(v, target, sv, index, refs, where)


def views():
    return [SchemaView(str(META / s)) for s in SCHEMAS]


def collect(views):
    index, refs, skipped = {}, [], []
    for path in sorted((META / "assertions").rglob("*.yaml")):
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
                walk(item, slot.range, sv, index, refs, path.name)
    return index, refs, skipped
