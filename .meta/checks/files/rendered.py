"""What the rest of the gate is rendered into: the APM package compiles, and every generated page is the render of what it asserts. Registered last, so a reader watching the gate finds it under the steps whose subject it renders.
"""
import shutil
import subprocess

from checks.collect import (
    META,
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)
from checks.files import prose


@check("apm package")
def apm_package() -> StepOutcome:
    """Verifies that .meta/.apm/ passes APM CLI compilation validation when apm is available (solorepo's DR-201)."""
    apm_bin = shutil.which("apm")
    if not apm_bin:
        return CouldNotRun("apm is not installed (install via 'brew install apm' or 'curl -sSL https://aka.ms/apm-unix | sh')")
    res = subprocess.run([apm_bin, "compile", "--validate"], check=False, cwd=str(META), capture_output=True, text=True)
    if res.returncode != 0:
        lines = [line.strip() for line in (res.stdout + "\n" + res.stderr).splitlines() if line.strip()]
        return Found(tuple(lines))
    return Passed("all primitives validated successfully via apm compile --validate")


# Registered last, because this is the one step that reads what the others'
# subject is rendered into, and a reader watching the gate wants it under them.
@check("rendered prose")
def rendered_prose(pages: dict[str, str]) -> list[str]:
    """Every page render.py writes is the render of what it is written from.

    A generated page is data twice over, and the copy in the tree is the one a
    reader opens; stale, it is prose asserting something the record no longer
    says. What is compared is every target `render.py` names, including the
    templates, so the mark says what it covered.

    `unrendered` answers with page names, so the sentence saying what is wrong
    with a page is written here rather than carried out of the render, which
    has no business holding this step's wording.
    """
    render, _ = prose.rendering()
    stale = [f"{name} exists but nothing renders it" for name in render.unrendered()]
    stale += [name for name, text in pages.items()
              if not (META / name).exists()
              or (META / name).read_text() != text.rstrip("\n") + "\n"]
    import apm_compile
    stale += apm_compile.check_root_symlinks(ROOT)
    return stale
