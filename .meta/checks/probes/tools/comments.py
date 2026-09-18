"""The detectors of `comments.py` that the comment steps read through, so a wrong answer shows as a wrong verdict rather than a failure (solorepo's DR-207).
"""
import pathlib

from collect import ROOT, against_baseline, check


@check("comment probes", pre=True)
def comment_probes():
    """`comments.py`'s three detectors, against the comments they exist to catch and the comments they must let through.

    A heuristic over comment text is a boundary like any other, and the cost of
    a false positive here is a gate that refuses a licence header or a sentence
    of Reference prose. Every keep-exception has a case, and every detector has
    the innocent neighbour it must not catch (solorepo's DR-110,
    solorepo's DR-207).

    The ratchet the `inline commentary` step reads through is asked the same
    way: a count at its baseline, over it, under it, and an entry naming a file
    the tree no longer has. It is `collect.against_baseline` and is shared with
    the `meta types` step (solorepo's DR-210); both callers' site formatting
    (`comments.comment_site` and `files.mypy_errors`) and their baseline
    parameters are probed.
    """
    import comments
    problems = []

    def expect(kind, want, got, case):
        """One problem naming the detector `kind` and `case` when `got` is not `want`."""
        if want != got:
            problems.append(f"comment probes: {kind} answered {got!r} for {case!r}, expected {want!r}")

    for text in ("x = compute(1)", "return None", "import os", "del cache[key]",
                 "if ready: run()", "for item in rows:", "print(payload)",
                 "def helper(x):", "raise SystemExit(1)"):
        expect("python_code", True, comments.python_code(text), text)
    for text in ("the gate checks this", "TODO", "noqa: F401", "fmt: skip",
                 "type: ignore[attr-defined]", "reason: registration order is deliberate",
                 "Copyright 2026 the solo", "Registered last, and a reader wants it under them",
                 "one step, one line, in the shape A21 names", ""):
        expect("python_code", False, comments.python_code(text), text)

    for text in ("let x = 1;", "fn main() {", "}", "use std::io;",
                 "pub struct Seed {", "return value;"):
        expect("rust_code", True, comments.rust_code(text), text)
    for text in ("The seed crate exposes one example", "SPDX-License-Identifier: MIT",
                 "#[allow] is refused by clippy::allow_attributes", "see the xtask crate"):
        expect("rust_code", False, comments.rust_code(text), text)

    expect("keep_exception", "directive", comments.keep_exception("noqa: F401"), "noqa")
    expect("keep_exception", "notice", comments.keep_exception("Copyright 2026 the solo"), "copyright")
    expect("keep_exception", "notice", comments.keep_exception("SPDX-License-Identifier: MIT"), "spdx")
    expect("keep_exception", "citation", comments.keep_exception("GitHub collapses this, see solorepo's DR-171"), "DR")
    expect("keep_exception", "citation", comments.keep_exception("the API caps a page at 100, see https://docs.github.com/x"), "url")
    expect("keep_exception", "citation", comments.keep_exception("refused in the same words as A19, see Article 19"), "article")
    expect("keep_exception", None, comments.keep_exception("build the list first, then sort it"), "narration")

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

    source = (
        "# a module-level comment, which is not body commentary\n"
        "URL = \"https://example.test/#not-a-comment\"\n"
        "def f():\n"
        "    \"\"\"A Reference docstring, which is a string and never a comment.\"\"\"\n"
        "    # narration, on two lines\n"
        "    # that is one block\n"
        "    value = 1  # SPDX-License-Identifier: MIT\n"
        "    other = 2  # the header caps at 100, see solorepo's DR-171\n"
        "    return value + other  # noqa: F401  # reason: a directive\n"
    )
    found = [b for b in comments.blocks(comments.python_comments(source))
             if b.inline and comments.keep_exception(b.text) is None]
    if len(found) != 1 or found[0].line != 5:
        problems.append(f"comment probes: expected one body comment at line 5, got "
                        f"{[(b.line, b.text) for b in found]!r}")
    if any(comments.python_code(c.text) for c in comments.python_comments(source)):
        problems.append("comment probes: a false positive for commented-out code in the sample")

    here = pathlib.Path(__file__).relative_to(ROOT).as_posix()
    one = [comments.comment_site(here, found[0])]
    if one[0] != f"{here}:5: `narration, on two lines that is one block`":
        problems.append(f"comment probes: comment_site gave {one[0]!r}")

    def ratcheted(counts, sites, recorded):
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

    import files
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
