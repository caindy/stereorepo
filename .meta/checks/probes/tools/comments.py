"""The detectors of `comments.py` that the comment steps read through, so a wrong answer shows as a wrong verdict rather than a failure (stereorepo's DR-207).
"""
import pathlib
from typing import Any

from checks.collect import ROOT, StepOutcome, against_baseline, check
from checks.probes.tools.lockstep import lockstep, lockstep_probes, verdict


@check("comment probes", pre=True)
def comment_probes(root: pathlib.Path = ROOT) -> StepOutcome:
    """`comments.py`'s three detectors, against the comments they exist to catch and the comments they must let through.

    A heuristic over comment text is a boundary like any other, and the cost of
    a false positive here is a gate that refuses a licence header or a sentence
    of Reference prose. Every keep-exception has a case, and every detector has
    the innocent neighbour it must not catch (stereorepo's DR-207).

    The ratchet the `inline commentary` step reads through is asked the same
    way: a count at its baseline, over it, under it, and an entry naming a file
    the tree no longer has. It is `collect.against_baseline` and is shared with
    the `meta types` step (stereorepo's DR-210); both callers' site formatting
    (`comments.comment_site` and `files.mypy_errors`) and their baseline
    parameters are probed.

    `internal_cause` is a fourth detector and carries the same cost both ways:
    a false negative reopens the escape stereorepo's DR-225 closes, and a false
    positive refuses a reason whose cause is a foreign tracker.

    The `repeated suppressions` step reads through a second ratchet and a fifth
    detector, and both are asked here: what counts as one rule written with one
    reason, what the threshold lets through, what the external-citation escape
    hatch lifts, and the three ways `comments.against_repeats` fails a group
    (stereorepo's DR-223).

    The `meta lines` step reads through a third ratchet and a second output
    parser, and both are asked here: what `files.ruff_findings` counts and how
    it sites a finding, and the ratchet over it (stereorepo's DR-177).

    Every Python Project's gate package keeps its own copy of the
    keep-exceptions, suppression patterns and statement detectors, and the
    lockstep asserts that each copy still matches `comments.py`
    (stereorepo's DR-250), so a Project's `uv run gate` and the root gate give
    one verdict on one comment. The Projects are read from `structure.yaml`:
    in the scaffold, the Python seed; in a portfolio, every Project
    `just bootstrap python` laid down. A portfolio with none has nothing to
    keep in lockstep, and the step's scope says so (stereorepo's DR-305).

    Args:
        root: The repository whose `structure.yaml` names the Projects to keep in lockstep.

    Returns:
        StepOutcome: `Found` with one line per wrong answer, or `Passed`
        naming the Projects kept in lockstep.
    """
    from checks import comments
    here = pathlib.Path(__file__).relative_to(ROOT).as_posix()
    blocks_found, sites = _blocks_and_sites(comments, here)
    problems = (_code_detectors(comments) + _keep_exceptions(comments) + _suppressions(comments)
                + _causes(comments) + blocks_found + _ratchet(comments, here, sites)
                + _type_errors(here) + _ruff_findings(here) + _rust_comments(comments)
                + _repeats(comments) + _repeat_ratchet(comments) + lockstep_probes(comments))
    synced, projects = lockstep(comments, root)
    return verdict(problems + synced, projects)


def _expecting(kind: Any) -> tuple[Any, list[str]]:
    """A recorder for detector `kind`: `expect(want, got, case)` keeps one problem where `got` is not `want`, and `problems` is what it kept."""
    problems = []

    def expect(want: Any, got: Any, case: Any) -> None:
        if want != got:
            problems.append(f"comment probes: {kind} answered {got!r} for {case!r}, expected {want!r}")
    return expect, problems


def _code_detectors(comments: Any) -> list[str]:
    """`python_code` and `rust_code` against commented-out code and the prose they must let through."""
    expect, problems = _expecting("python_code")
    for text in ("x = compute(1)", "return None", "import os", "del cache[key]",
                 "if ready: run()", "for item in rows:", "print(payload)",
                 "def helper(x):", "raise SystemExit(1)"):
        expect(True, comments.python_code(text), text)
    for text in ("the gate checks this", "TODO", "noqa: F401", "fmt: skip",
                 "type: ignore[attr-defined]", "reason: registration order is deliberate",
                 "Copyright 2026 the author", "Registered last, and a reader wants it under them",
                 "one step, one line, in the shape A21 names", ""):
        expect(False, comments.python_code(text), text)

    expect, rust_problems = _expecting("rust_code")
    for text in ("let x = 1;", "fn main() {", "}", "use std::io;",
                 "pub struct Seed {", "return value;"):
        expect(True, comments.rust_code(text), text)
    for text in ("The seed crate exposes one example", "SPDX-License-Identifier: MIT",
                 "#[allow] is refused by clippy::allow_attributes", "see the xtask crate"):
        expect(False, comments.rust_code(text), text)
    return problems + rust_problems


def _keep_exceptions(comments: Any) -> list[str]:
    """`keep_exception` naming each permissible kind, and None for narration."""
    expect, problems = _expecting("keep_exception")
    expect("directive", comments.keep_exception("noqa: F401"), "noqa")
    expect("notice", comments.keep_exception("Copyright 2026 the author"), "copyright")
    expect("notice", comments.keep_exception("SPDX-License-Identifier: MIT"), "spdx")
    expect("citation", comments.keep_exception("GitHub collapses this, see stereorepo's DR-171"), "DR")
    expect("citation", comments.keep_exception("the API caps a page at 100, see https://docs.github.com/x"), "url")
    expect("citation", comments.keep_exception("refused in the same words as A19, see Article 19"), "article")
    expect(None, comments.keep_exception("build the list first, then sort it"), "narration")
    return problems


def _suppressions(comments: Any) -> list[str]:
    """`suppressions` catching a bare `noqa`, a bare `type: ignore` and every `#[allow]`, and letting the coded, the expected and the quoted through."""
    problems = []
    bare = comments.suppressions("value = call()  # noqa\n")
    if not (len(bare) == 1 and bare[0][0] == 1 and "noqa" in bare[0][1]):
        problems.append(f"comment probes: bare `noqa` not caught, got {bare!r}")
    coded = comments.suppressions("value = call()  # noqa: F401  # reason: registers steps\n")
    if coded:
        problems.append(f"comment probes: `noqa: F401` should pass, got {coded!r}")
    bare_type = comments.suppressions("value = call()  # type: ignore\n")
    if not (len(bare_type) == 1 and "type: ignore" in bare_type[0][1]):
        problems.append(f"comment probes: bare `type: ignore` not caught, got {bare_type!r}")
    if comments.suppressions("value = call()  # type: ignore[attr-defined]\n"):
        problems.append("comment probes: `type: ignore[attr-defined]` should pass")
    allowed = comments.suppressions("#[allow(dead_code)]\nfn f() {}\n", rust=True)
    if not (len(allowed) == 1 and "expect" in allowed[0][1]):
        problems.append(f"comment probes: `#[allow(dead_code)]` not caught, got {allowed!r}")
    if not comments.suppressions("#![allow(clippy::all)]\n", rust=True):
        problems.append("comment probes: crate-level `#![allow(...)]` not caught")
    if comments.suppressions("#[expect(dead_code)]\nfn f() {}\n", rust=True):
        problems.append("comment probes: `#[expect(dead_code)]` should pass")
    if comments.suppressions("NOQA = re.compile(r\"#\\s*noqa\")\n"):
        problems.append("comment probes: a `noqa` inside a string literal is not a suppression")
    if comments.suppressions("/// Prefer `#[expect]`, because `#[allow(dead_code)]` outlives its cause.\n", rust=True):
        problems.append("comment probes: an `#[allow(...)]` inside a doc comment is not a suppression")
    beside = comments.suppressions("#[allow(dead_code)] // the trait is not built yet\n", rust=True)
    if not beside:
        problems.append("comment probes: an `#[allow(...)]` beside a comment is still a suppression")
    return problems


def _causes(comments: Any) -> list[str]:
    """`reasons` reading a suppression's reason off a source — one per line, however many directives the line carries — and `internal_cause` refusing a cause this tree holds while letting a foreign one through (stereorepo's DR-225)."""
    problems = []
    source = (
        "value = call()  # noqa: F401  # reason: registers check steps\n"
        "other = call()  # type: ignore[untyped-decorator]  # reason: see collect.check\n"
        "bare = call()  # noqa: F401\n"
        "both = call()  # noqa: F401  # type: ignore[union-attr]  # reason: one suppression\n"
    )
    read = comments.reasons(source)
    if read != [(1, "registers check steps"), (2, "see collect.check"), (4, "one suppression")]:
        problems.append(f"comment probes: reasons read {read!r}, expected the three that carry one")
    names = comments.modules()
    missing = [name for name in ("collect", "comments", "check", "citations") if name not in names]
    if missing:
        problems.append(f"comment probes: modules() missed {missing!r}, which are modules under .meta/")

    expect, cause_problems = _expecting("internal_cause")
    for text in ("flat `collect` import makes this Any; see collect.check",
                 "the root cause is filed as #557",
                 "`render.rendered()` carries no annotations — .meta/render.py re-exports it",
                 "the ordering stereorepo's DR-207 settles",
                 "see files.tree"):
        expect(True, comments.internal_cause(text, names) is not None, text)
    for text in ("mypy does not narrow this, see https://github.com/python/mypy/issues/12345",
                 "the import is the test of whether PyYAML is installed",
                 "GraphQL query templates have literal curly braces",
                 "normalising unicode smart quotes to ascii quotes",
                 "registers check steps", "registration order is deliberate",
                 "see github.com/python/mypy#1",
                 "see github.com/python/mypy/issues/1234",
                 "running python.exe on Windows requires binary mode",
                 "git.status reports untracked files",
                 "HTTP response status.code is checked"):
        expect(False, comments.internal_cause(text, names) is not None, text)
    return problems + cause_problems


def _blocks_and_sites(comments: Any, here: Any) -> tuple[list[str], list[str]]:
    """`blocks` finding the one body comment in a sample and `comment_site` naming it: the problems, and the site list the ratchet cases read."""
    problems = []
    source = (
        "# a module-level comment, which is not body commentary\n"
        "URL = \"https://example.test/#not-a-comment\"\n"
        "def f():\n"
        "    \"\"\"A Reference docstring, which is a string and never a comment.\"\"\"\n"
        "    # narration, on two lines\n"
        "    # that is one block\n"
        "    value = 1  # SPDX-License-Identifier: MIT\n"
        "    other = 2  # the header caps at 100, see stereorepo's DR-171\n"
        "    return value + other  # noqa: F401  # reason: a directive\n"
    )
    found = [b for b in comments.blocks(comments.python_comments(source))
             if b.inline and comments.keep_exception(b.text) is None]
    if len(found) != 1 or found[0].line != 5:
        problems.append(f"comment probes: expected one body comment at line 5, got "
                        f"{[(b.line, b.text) for b in found]!r}")
    if any(comments.python_code(c.text) for c in comments.python_comments(source)):
        problems.append("comment probes: a false positive for commented-out code in the sample")
    one = [comments.comment_site(here, found[0])]
    if one[0] != f"{here}:5: `narration, on two lines that is one block`":
        problems.append(f"comment probes: comment_site gave {one[0]!r}")
    return problems, one


def _ratchet(comments: Any, here: Any, one: Any) -> list[str]:
    """The shared ratchet at, over and under its baseline, and over an entry naming a file the tree no longer has (stereorepo's DR-210)."""
    problems = []
    def ratcheted(counts: dict[str, int], sites: dict[str, Any], recorded: dict[str, int]) -> list[str]:
        """The shared ratchet, asked about counts under the `inline commentary` step's baseline."""
        return against_baseline(counts, sites, recorded, "body comments", comments.BASELINE)

    if ratcheted({here: 1}, {here: one}, {here: 1}):
        problems.append("comment probes: a file at its baseline should pass")
    grew = ratcheted({here: 2}, {here: one}, {here: 1})
    if not any("over its baseline of 1" in line for line in grew):
        problems.append(f"comment probes: a file over its baseline should fail, got {grew!r}")
    fell = ratcheted({here: 1}, {here: one}, {here: 2})
    if not any("under its baseline of 2" in line for line in fell):
        problems.append(f"comment probes: a file under its baseline should fail, got {fell!r}")
    if not any(f"     {one[0]}" in line for line in grew):
        problems.append(f"comment probes: a failing file should list its sites, got {grew!r}")
    stale = ratcheted({}, {}, {"no/such/file.py": 3})
    if not any("does not exist" in line for line in stale):
        problems.append(f"comment probes: a baseline entry for a missing file should fail, got {stale!r}")
    if ratcheted({}, {}, {}):
        problems.append("comment probes: an empty baseline over a clean tree should pass")
    return problems


def _type_errors(here: Any) -> list[str]:
    """`files.mypy_errors` counting and siting one error, and the ratchet reading it over its baseline."""
    problems = []
    from checks import files
    mypy_sample = f"{here}:42: error: Need type annotation  [var-annotated]\n"
    type_counts, type_sites = files.mypy_errors(mypy_sample)
    if type_counts != {here: 1}:
        problems.append(f"comment probes: mypy_errors counts gave {type_counts!r}")
    expected_site = f"{here}:42: Need type annotation  [var-annotated]"
    if type_sites != {here: [expected_site]}:
        problems.append(f"comment probes: mypy_errors sites gave {type_sites!r}")
    type_grew = against_baseline({here: 1}, type_sites, {here: 0},
                                 "type errors", files.TYPES_BASELINE)
    if not any("1 type errors, over its baseline of 0" in line for line in type_grew):
        problems.append(f"comment probes: type errors over baseline should fail, got {type_grew!r}")
    if not any(f"     {expected_site}" in line for line in type_grew):
        problems.append(f"comment probes: type error site not formatted, got {type_grew!r}")
    return problems


def _ruff_findings(here: Any) -> list[str]:
    """`files.ruff_findings` counting and siting a finding, and the ratchet over it."""
    problems = []
    from checks import files
    sample = (f"{here}:7:101: E501 Line too long (118 > 100)\n"
              "Found 1 error.\n")
    counts, sites = files.ruff_findings(sample)
    if counts != {here: 1}:
        problems.append(f"comment probes: ruff_findings counts gave {counts!r}")
    expected = f"{here}:7: E501 Line too long (118 > 100)"
    if sites != {here: [expected]}:
        problems.append(f"comment probes: ruff_findings sites gave {sites!r}")
    grew = against_baseline({here: 1}, sites, {here: 0},
                            "lines over the limit", files.LINES_BASELINE)
    if not any("1 lines over the limit, over its baseline of 0" in line for line in grew):
        problems.append(f"comment probes: lines over baseline should fail, got {grew!r}")
    if not any(f"     {expected}" in line for line in grew):
        problems.append(f"comment probes: line finding site not formatted, got {grew!r}")
    return problems


def _rust_comments(comments: Any) -> list[str]:
    """`rust_comments` reading line, block and doc comments off a sample."""
    problems = []
    rust = (
        "// A plain line comment.\n"
        "const URL: &str = \"https://example.test\";\n"
        "/* a block comment\n"
        "   over two lines */\n"
        "/// let doubled = lines(\" a \");\n"
        "fn f() {}\n"
    )
    seen = comments.rust_comments(rust)
    if [c.line for c in seen] != [1, 3, 4, 5]:
        problems.append(f"comment probes: rust_comments read lines {[c.line for c in seen]!r}, expected [1, 3, 4, 5]")
    if [c.doc for c in seen] != [False, False, False, True]:
        problems.append(f"comment probes: rust_comments marked {[c.doc for c in seen]!r} as doc, "
                        "expected only the `///` line")
    return problems


def _repeated(comments: Any, reasons: list[str]) -> dict[str, list[str]]:
    """The groups `comments.repeated` finds over one `sample/<n>.py` per reason, each suppressing `untyped-decorator` on line 1."""
    groups: dict[str, list[str]] = comments.repeated({
        f"sample/{number}.py":
            f"value = call()  # type: ignore[untyped-decorator]  # reason: {reason}\n"
        for number, reason in enumerate(reasons)
    })[0]
    return groups


def _repeats(comments: Any) -> list[str]:
    """`suppression_reasons` and `repeated`: what one rule and one reason is, what the threshold lets through, and what the escape hatch lifts."""
    problems = []
    read = comments.suppression_reasons(
        "value = call()  # type: ignore[untyped-decorator]  # reason:  The  `collect`  Import. \n")
    want = [(1, "type: ignore[untyped-decorator]", "the collect import")]
    if [tuple(one) for one in read] != want:
        problems.append(f"comment probes: suppression_reasons gave {[tuple(o) for o in read]!r}, "
                        f"expected {want!r}")
    noqa = comments.suppression_reasons("value = call()  # noqa: F401  # reason: x\n")[0]
    if noqa.rule != "noqa:F401":
        problems.append(f"comment probes: `noqa: F401` read as the rule {noqa.rule!r}, "
                        "expected 'noqa:F401'")

    same = _repeated(comments, ["one root cause"] * 3)
    if sorted(same.values()) != [["sample/0.py:1", "sample/1.py:1", "sample/2.py:1"]]:
        problems.append(f"comment probes: three identical reasons should be one group of three, got {same!r}")
    distinct = _repeated(comments, ["first cause", "second cause", "third cause"])
    if sorted(len(sites) for sites in distinct.values()) != [1, 1, 1]:
        problems.append(f"comment probes: three distinct reasons should be three groups of one, got {distinct!r}")
    pair = _repeated(comments, ["one root cause"] * 2)
    if comments.against_repeats(pair, {}):
        problems.append(f"comment probes: two identical reasons are under the limit and should pass, got {pair!r}")
    if comments.against_repeats(_repeated(comments, ["first", "second", "third"]), {}):
        problems.append("comment probes: three distinct reasons should pass")

    for cited in ("the language forces literal braces, see https://spec.graphql.org/",
                  "the header folds, see RFC 5322"):
        outside = _repeated(comments, [cited] * 3)
        if outside:
            problems.append(f"comment probes: {cited!r} cites outside this repository and is not "
                            f"counted, got {outside!r}")
    inside = _repeated(comments, ["the flat import, see #557"] * 3)
    if not comments.against_repeats(inside, {}):
        problems.append("comment probes: an Issue is inside this repository and does not lift the count")
    return problems


def _repeat_ratchet(comments: Any) -> list[str]:
    """`against_repeats` at its baseline, over it, under it, and for a group the tree has dropped below the limit."""
    problems = []
    three = _repeated(comments, ["one root cause"] * 3)
    key = next(iter(three))
    if comments.against_repeats(three, {key: 3}):
        problems.append("comment probes: a group at its baseline should pass")
    grew = comments.against_repeats(three, {key: 2})
    if not any("3 sites, over its baseline of 2" in line for line in grew):
        problems.append(f"comment probes: a group over its baseline should fail, got {grew!r}")
    if not any("fix the cause" in line for line in grew):
        problems.append(f"comment probes: a growing group should be told to fix the cause, got {grew!r}")
    if not any(line.strip() == "sample/0.py:1" for line in grew):
        problems.append(f"comment probes: a failing group should list its sites, got {grew!r}")
    fell = comments.against_repeats(three, {key: 4})
    if not any("3 sites, under its baseline of 4" in line for line in fell):
        problems.append(f"comment probes: a group under its baseline should fail, got {fell!r}")
    gone = comments.against_repeats(_repeated(comments, ["one root cause"] * 2), {key: 3})
    if not any("down to 2 sites — remove the entry" in line for line in gone):
        problems.append(f"comment probes: a group down below the limit should fail, got {gone!r}")
    if comments.against_repeats({}, {}):
        problems.append("comment probes: an empty baseline over a clean tree should pass")
    return problems
