"""The channel, the hooks and the scripts loaded as modules without running their `main()`, so a probe can call what they define.

History in loaders.history.md (solorepo's DR-171).
"""
import importlib.util
import pathlib
import sys
import types
from importlib.machinery import SourceFileLoader
from typing import Any

import yaml

from checks.collect import META, ROOT

NO_SPEC = "no module spec for {path}"
"""What loading raises where `importlib` declines to describe the file as a module."""


def load_module(path: str | pathlib.Path, name: str | None = None, register: bool = True) -> types.ModuleType:
    """The Python source at `path` as a fresh module object, its `main()` unrun.

    `name` is the module's `__name__`, the file's stem by default. `register`
    puts the module in `sys.modules` under that name before it runs, which a
    module defining a dataclass needs and a plain script does not mind. `.meta/`
    and `.meta/checks/` are put on `sys.path` first, so a script that imports the
    gate's own modules resolves them the way `check.py` does.

    Loading runs the file's top level, so this is for programs whose every act
    is under `if __name__ == "__main__"`, which every script under `.meta/` is.
    Works for a program with no `.py` as well as a module with one.
    """
    for entry in (str(META / "checks"), str(META)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    path = pathlib.Path(path)
    if not path.is_absolute():
        path = ROOT / path
    name = name or path.name.removesuffix(".py")
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise ImportError(NO_SPEC.format(path=path))
    module = importlib.util.module_from_spec(spec)
    if register:
        sys.modules[name] = module
    loader.exec_module(module)
    return module


def load_hook(name: str) -> types.ModuleType:
    """`.meta/hooks/<name>.py` as a module, by the stem alone."""
    return load_module(META / "hooks" / f"{name}.py", name)


def load_channel() -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """`.meta/say/` as modules: the signing primitive, the verb table, and every program the table names.

    Returns `(channel, table, programs)`: the `channel.py` module, the parsed
    `verbs.yaml`, and a dict from each program's name to its module, loaded by
    the primitive's own `sibling()` so that programs importing each other share
    one copy (solorepo's DR-117). Each call loads the channel afresh, so what one
    probe sets on a program does not reach the next; the library package each
    program in the table is the entry of, `lib.<name>` where one exists
    (solorepo's DR-217), is evicted from `sys.modules` first for the same
    reason, since a module that imported the channel once would otherwise keep
    the copy a previous probe stood its fakes in on and reach GitHub past the
    next probe's. History in loaders.history.md (solorepo's DR-171).

    The programs have no `.py` and are programs rather than libraries, so the
    primitive's loader is used. Importing runs nothing: everything each does is
    under `main()`, and `main()` is under `__name__`.
    """
    table = yaml.safe_load((META / "say" / "verbs.yaml").read_text()) or {}
    bodies = tuple(f"lib.{p['name']}" for p in table.get("programs") or [])
    for name in [n for n in sys.modules
                 if n in bodies or n.startswith(tuple(f"{body}." for body in bodies))]:
        del sys.modules[name]
    channel = load_module(META / "say" / "channel.py", "channel")
    programs = {p["name"]: channel.sibling(p["name"]) for p in table.get("programs") or []}
    return channel, table, programs
