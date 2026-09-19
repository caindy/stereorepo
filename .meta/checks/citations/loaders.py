"""What the citation steps read from: the patterns a Decision and an Issue citation take, the scripts loaded for their patterns, and the files a portfolio inherits.
"""
import re

from checks.collect import META, ROOT, TEMPLATE
from checks.files import inherited, tree

DR = re.compile(r"\bDR-(\d{3})\b")


# A citation of solorepo's record, in the form the material a portfolio inherits
# writes one: the possessive, then a run, so `solorepo's DR-073, DR-107` names two,
# and `Solorepo's DR-073` names one at the head of a sentence.
FOREIGN = re.compile(r"[Ss]olorepo's DR-\d{3}\b(?:(?:,| and|, and) DR-\d{3}\b)*")
SCAFFOLD = "work:portfolio/solorepo"


def issue_citation() -> tuple[re.Pattern[str], re.Pattern[str]]:
    """Load compiled regular expressions for Issue citations from `check_pr.py`.

    Returns:
        tuple[re.Pattern, re.Pattern]: A tuple of `(ISSUE, FOREIGN)` patterns
        matching bare Issue numbers and possessive `solorepo's #n` runs (solorepo's DR-132).
    """
    module = load_check_pr()
    return module.ISSUE, module.FOREIGN


def load_timing():
    """Load `timing.py` as an isolated module object without executing top-level scripts.

    Returns:
        types.ModuleType: The imported timing module object.
    """
    import importlib.util
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("timing", str(META / "timing.py"))
    spec = importlib.util.spec_from_loader("timing", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def load_check_pr():
    """Load `check_pr.py` as an isolated module object without executing network calls.

    Returns:
        types.ModuleType: The imported check_pr module object.
    """
    import importlib.util
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("check_pr", str(META / "check_pr.py"))
    spec = importlib.util.spec_from_loader("check_pr", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def copied_files():
    """Determine the absolute paths of all files copied into a specialized portfolio.

    Returns:
        set[pathlib.Path]: File paths copied into a new portfolio via specialization.
    """
    copied = {ROOT / "justfile"}
    for token in inherited():
        base = ROOT / token if (ROOT / token).exists() else META / token
        copied.update([base] if base.is_file() else base.rglob("*") if base.is_dir() else [])
    return copied


def durable(copied):
    """Yield all durable repository files subject to citation validation.

    Covers documentation pages, inherited portfolio files, template files,
    and assertion files under `.meta/assertions/`.

    Parameters:
        copied (set[pathlib.Path]): Set of file paths copied into specialized portfolios.

    Yields:
        pathlib.Path: Next durable file path to inspect for citations.
    """
    for path in tree():
        if path.is_symlink() or not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix == ".md" or path in copied or TEMPLATE in path.parents or (
                path.suffix in (".yaml", ".yml") and (META / "assertions") in path.parents):
            yield path
