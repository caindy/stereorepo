"""Each pure step watched failing, against a tree built to fail it, and then
watched passing against the same tree put right. A guardrail never observed
to fail is not evidence of anything."""

from __future__ import annotations

from pathlib import Path

import pytest

from gate import (
    CouldNotRun,
    Found,
    Passed,
    Step,
    closing_block,
    comments,
    doc,
    evidence_against,
    lints,
    orphans,
    rendered,
    run,
    select,
)

# Assembled, so that the scanner does not read the probe's own data as a
# suppression in this file.
NOQA = "# " + "noqa: F401"
TYPE_IGNORE = "# " + "type: ignore[assignment]"
BARE_NOQA = "# " + "noqa"
BARE_TYPE_IGNORE = "# " + "type: ignore"
REASON = "  # " + "reason: "

ROOT_MANIFEST = (
    '[project]\nname = "probe-workspace"\n\n[tool.uv.workspace]\n'
    'members = ["packages/probe"]\n\n[tool.ruff.lint]\nignore = []\n'
)
PACKAGE_MANIFEST = (
    '[project]\nname = "probe"\nversion = "0.0.0"\nreadme = "README.md"\n'
)


class Tree:
    """A throwaway workspace with one package, under pytest's temporary
    directory, so probes leave nothing behind that the orphan check would
    then find."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.write("pyproject.toml", ROOT_MANIFEST)
        self.write("packages/probe/pyproject.toml", PACKAGE_MANIFEST)
        self.write("packages/probe/README.md", "The probe package.\n")
        self.write("packages/probe/src/probe/__init__.py", '"""The probe package."""\n')

    def write(self, path: str, text: str) -> Tree:
        full = self.root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text, encoding="utf-8")
        return self


@pytest.fixture
def tree(tmp_path: Path) -> Tree:
    return Tree(tmp_path)


def found(outcome: object) -> tuple[str, ...]:
    assert isinstance(outcome, Found), outcome
    return outcome.problems


def passed(outcome: object) -> str:
    assert isinstance(outcome, Passed), outcome
    return outcome.scope


def test_a_markdown_file_nothing_names_is_an_orphan(tree: Tree) -> None:
    assert (
        passed(orphans(tree.root))
        == "1 markdown files under 1 packages, each named by a source file"
    )

    tree.write("packages/probe/src/probe/stray.md", "Nothing names this.\n")
    problems = found(orphans(tree.root))
    assert len(problems) == 1
    assert "stray.md" in problems[0]

    tree.write(
        "packages/probe/src/probe/__init__.py",
        '"""The probe package. History: `stray.md`."""\n',
    )
    assert passed(orphans(tree.root)).startswith("2 markdown files")


def test_a_history_entry_names_a_test_that_exists(tree: Tree) -> None:
    listed = ["tests/test_probe.py::test_it"]
    tree.write(
        "packages/probe/src/probe/probe.history.md",
        "# History\n\n<!--\n### The form\n\nEvidence: `nothing`\n-->\n",
    )
    assert (
        passed(evidence_against(tree.root, listed))
        == "0 entries across 1 history logs, each naming a test that exists"
    )

    tree.write(
        "packages/probe/src/probe/probe.history.md",
        "### It broke\n\nEstablished: nothing.\n",
    )
    problems = found(evidence_against(tree.root, listed))
    assert problems == (
        "packages/probe/src/probe/probe.history.md: 'It broke' names no evidence",
    )

    tree.write(
        "packages/probe/src/probe/probe.history.md",
        "### It broke\n\nEvidence: `tests/test_probe.py::test_gone`\n",
    )
    problems = found(evidence_against(tree.root, listed))
    assert "test_gone" in problems[0]

    tree.write(
        "packages/probe/src/probe/probe.history.md",
        "### It broke\n\nEvidence: `tests/test_probe.py::test_it`\n",
    )
    assert passed(evidence_against(tree.root, listed)).startswith("1 entries")


def test_a_rule_switched_off_in_configuration_is_refused(tree: Tree) -> None:
    assert passed(lints(tree.root)).endswith("2 manifests, none switching a rule off")

    tree.write(
        "pyproject.toml", ROOT_MANIFEST.replace("ignore = []", 'ignore = ["E501"]')
    )
    problems = found(lints(tree.root))
    assert problems == (
        "pyproject.toml: `ignore` switches 1 rules off in configuration",
    )

    tree.write(
        "pyproject.toml",
        ROOT_MANIFEST + '\n[tool.ruff.lint.per-file-ignores]\n"tests/**" = ["S101"]\n',
    )
    problems = found(lints(tree.root))
    assert len(problems) == 1
    assert "gives no reason" in problems[0]

    tree.write(
        "pyproject.toml",
        ROOT_MANIFEST
        + '\n[tool.ruff.lint.per-file-ignores]\n"tests/**" = ["S101"]'
        + REASON
        + "assert is the point\n",
    )
    assert isinstance(lints(tree.root), Passed)

    tree.write(
        "pyproject.toml",
        ROOT_MANIFEST + "\n[tool.mypy]\nignore_missing_imports = true\n",
    )
    assert "ignore_missing_imports" in found(lints(tree.root))[0]


def test_a_suppression_at_a_site_carries_a_reason(tree: Tree) -> None:
    tree.write("packages/probe/src/probe/a.py", '"""A."""\n\nimport os  ' + NOQA + "\n")
    problems = found(lints(tree.root))
    assert problems == ("packages/probe/src/probe/a.py:3: `noqa` gives no reason",)

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\nimport os  '
        + NOQA
        + REASON
        + "re-exported\nx = 1  "
        + TYPE_IGNORE
        + "\n",
    )
    problems = found(lints(tree.root))
    assert problems == (
        "packages/probe/src/probe/a.py:4: `type: ignore` gives no reason",
    )

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\nimport os  ' + NOQA + REASON + "re-exported\n",
    )
    assert passed(lints(tree.root)).startswith("1 suppressions across 2 source files")


def test_a_public_item_without_a_docstring_is_found(tree: Tree) -> None:
    assert (
        passed(doc(tree.root))
        == "1 public items across 1 modules, each with a docstring"
    )

    tree.write(
        "packages/probe/src/probe/a.py",
        "def f():\n    pass\n\n\nclass C:\n    def m(self):\n        pass\n\n"
        "    def _p(self):\n        pass\n",
    )
    problems = found(doc(tree.root))
    assert [p.split("`")[1] for p in problems] == ["module", "f", "C", "C.m"]

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\n\ndef f():\n    """F."""\n\n\nclass C:\n    """C."""\n\n'
        '    def m(self):\n        """M."""\n',
    )
    assert passed(doc(tree.root)).startswith("5 public items across 2 modules")


def test_only_a_finding_fails(tree: Tree, capsys: pytest.CaptureFixture[str]) -> None:
    steps: list[Step] = [
        ("could", lambda _root: CouldNotRun("no tool")),
        ("ok", lambda _root: Passed("all")),
        ("bad", lambda _root: Found(("x",))),
    ]
    assert run(tree.root, steps[:2], environ={}) == 0
    assert run(tree.root, steps[:2], environ={"CI": "true"}) == 1
    assert run(tree.root, steps, environ={}) == 1
    assert run(tree.root, [], environ={}) == 2
    out = capsys.readouterr()
    assert "?  could: no tool\n" in out.out
    assert "ok ok — all\n" in out.out
    assert "x  bad (1)\n     x\n" in out.out
    assert "?  steps that could not run (1)" in out.out
    assert out.err.startswith("usage: uv run gate [gate | lints")


def test_closing_block_conditions_on_ci() -> None:
    lines, fatal = closing_block([], environ={"CI": "true"})
    assert lines == []
    assert not fatal

    lines, fatal = closing_block(["step: missing"], environ={})
    assert len(lines) == 2
    assert not fatal
    assert "zero where a person runs" in lines[0]
    assert "  step: missing" in lines[1]

    lines, fatal = closing_block(["step: missing"], environ={"CI": "true"})
    assert len(lines) == 2
    assert fatal


def test_a_word_selects_one_step_at_most() -> None:
    assert len(select("gate")) > 1
    assert [label for label, _ in select("evidence")] == ["evidence"]
    assert select("everything") == []
    assert rendered(Passed("s"), "l") == "ok l — s\n"


def test_commented_out_code_is_found(tree: Tree) -> None:
    tree.write("packages/probe/src/probe/a.py", '"""A."""\n\n# x = 1\n')
    problems = found(comments(tree.root))
    assert len(problems) == 1
    assert "commented-out code" in problems[0]
    assert "x = 1" in problems[0]

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\n# The variable holds state.\n',
    )
    assert isinstance(comments(tree.root), Passed)


def test_a_bare_suppression_is_found(tree: Tree) -> None:
    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\nimport os  ' + BARE_NOQA + REASON + "needed\n",
    )
    problems = found(comments(tree.root))
    assert problems == (
        "packages/probe/src/probe/a.py:3: bare `noqa` names no rule",
    )

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\nx = 1  ' + BARE_TYPE_IGNORE + REASON + "untyped\n",
    )
    problems = found(comments(tree.root))
    assert problems == (
        "packages/probe/src/probe/a.py:3: bare `type: ignore` names no rule",
    )

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\nimport os  ' + NOQA + REASON + "needed\n",
    )
    assert isinstance(comments(tree.root), Passed)


def test_inline_body_commentary_is_found_unless_exempted(tree: Tree) -> None:
    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\n\ndef f():\n    """F."""\n    # explain what f does\n    pass\n',
    )
    problems = found(comments(tree.root))
    assert len(problems) == 1
    assert "inline commentary" in problems[0]

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\n\ndef f():\n    """F."""\n    # pragma: no cover\n    pass\n',
    )
    assert isinstance(comments(tree.root), Passed)

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\n\ndef f():\n    """F."""\n    # bounded by DR-207\n    pass\n',
    )
    assert isinstance(comments(tree.root), Passed)

    tree.write(
        "packages/probe/src/probe/a.py",
        '"""A."""\n\n\ndef f():\n    """F."""\n'
        "    # SPDX-License-Identifier: MIT\n    pass\n",
    )
    assert isinstance(comments(tree.root), Passed)


def test_clean_comments_pass(tree: Tree) -> None:
    assert passed(comments(tree.root)).endswith(
        "clean of commented code, bare suppressions, and inline commentary"
    )
