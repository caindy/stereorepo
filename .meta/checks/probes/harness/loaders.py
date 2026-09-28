"""The scripts under `.meta/` loaded as modules without running their `main()`, so a probe can call what they define.
"""
import importlib.util
import pathlib
import sys
import types
from importlib.machinery import SourceFileLoader

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
