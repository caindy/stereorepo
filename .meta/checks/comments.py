"""Invariants over comments: what a comment in source is allowed to be.

Steps that read comment tokens rather than the assertion graph — a line of code
left behind as a comment, a suppression too broad to say what it suppresses, and
narration inside a function body that belongs in a docstring, a Decision Record,
a `<module>.history.md` log or a `just` recipe instead (solorepo's DR-171,
solorepo's DR-194, solorepo's DR-196).

The keep-exceptions are the closed list a body comment is measured against:
legal notices, tool directives, and an external boundary constraint carrying a
dereferenced citation. A Reference docstring is the fourth and needs no rule
here, because a docstring is a string and never reaches a comment token.

Python is read with `tokenize` and `ast`, so a `#` inside a string literal is
not a comment and a docstring is not one either. Rust is read with the small
scanner in `rust_spans`, because there is no Rust parser in the gate's
dependencies and the three things asked of it — `//`, `/* */` and `#[allow]` —
are decidable from the token stream alone.

`inline commentary` is ratcheted rather than flat: the tree held 210 body
comment blocks across 15 files when the step was written, and the Ratchet
Discipline is what a checker that cannot be clean at once does. The baseline is
`.meta/checks/comments.baseline.yaml` and it may fall and may not rise. The
comparison itself is `collect.against_baseline`, shared with the `meta types`
step of `files.py` (solorepo's DR-210).

Scope: every Python file under `.meta/`, which is the Project this gate is for,
and every Rust file git lists, because `.meta/` holds none and the seed crates
are where an `#[allow]` would appear.
"""
import ast
import collections
import io
import pathlib
import re
import tokenize

from collect import (
    META,
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    against_baseline,
    check,
    recorded_baseline,
)
from files import tree

BASELINE = META / "checks" / "comments.baseline.yaml"

# A tool directive: the third keep-exception, and the one a linter or formatter
# reads rather than a person. `reason:` is here because `meta lints` requires it
# beside every suppression, so it is a directive's tail and not narration.
DIRECTIVE = re.compile(
    r"^(noqa\b|type:\s*ignore\b|fmt:\s*\w+|pragma:|ruff:|mypy:|isort:|pylint:|pyright:"
    r"|nosec\b|coding[:=]|reason:|prettier-ignore|rustfmt::)"
)
# A legal notice: the first keep-exception.
NOTICE = re.compile(r"(copyright|SPDX-License-Identifier|licen[cs]e)", re.IGNORECASE)
# A dereferenced citation: the checkable half of the second keep-exception. That
# the constraint is an immutable external boundary is the reviewer's to judge;
# that it names something a reader can open is this step's.
CITATION = re.compile(r"(DR-\d{3}|Article\s+\d+|#\d+|RFC\s*\d+|https?://|\[\[[^\]]+\]\])")

# The two Python suppressions, each read once for both halves of what a
# suppression owes: `codes`, the rule it names, which `broad suppressions`
# requires, and `rest`, what follows it, where `meta lints` looks for the
# reason. Two patterns for the two halves would be the same suppression parsed
# in two modules, drifting the moment either moved.
NOQA = re.compile(r"#\s*noqa(?P<codes>:\s*[A-Z]+[0-9]*(?:\s*,\s*[A-Z]+[0-9]*)*)?(?P<rest>.*)$")
TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore(?P<codes>\[[^\]]*\])?(?P<rest>.*)$")
REASON = re.compile(r"#\s*reason:\s*\S")
ALLOW = re.compile(r"#!?\[\s*allow\s*\(")

# The statement kinds a commented-out line is recognised by. A comment whose
# text merely parses proves nothing — `TODO` is a Name and `fmt: skip` is an
# annotation — so what counts is a statement that does something.
STATEMENTS = (
    ast.Assign, ast.AugAssign, ast.Import, ast.ImportFrom, ast.FunctionDef,
    ast.AsyncFunctionDef, ast.ClassDef, ast.Return, ast.If, ast.For, ast.While,
    ast.With, ast.Try, ast.Raise, ast.Assert, ast.Delete, ast.Global, ast.Nonlocal,
)
# Rust has no parser here, so a commented-out line is recognised by the shapes a
# sentence of prose does not take: a statement terminator, a block delimiter, or
# a keyword in the position only code puts it in.
RUST_CODE = re.compile(
    r"(;\s*$|^\s*[{}]\s*$|\{\s*$|^\s*(let|fn|pub|use|impl|struct|enum|mod|match|return|unsafe)\b)"
)

Comment = collections.namedtuple("Comment", "line text inline doc own")
Block = collections.namedtuple("Block", "line text inline")


def sources() -> list[pathlib.Path]:
    """Every Python file under `.meta/`, excluding dotted directories and caches."""
    return sorted(
        p for p in META.rglob("*.py")
        if not any(part.startswith(".") and part != "." for part in p.relative_to(META).parts)
        and "__pycache__" not in p.parts
    )


def rust_sources() -> list[pathlib.Path]:
    """Every Rust file git lists."""
    return [p for p in tree() if p.suffix == ".rs" and p.is_file()]


def python_comments(source: str) -> list[Comment]:
    """The `#` comments of a Python source, each marked for whether it sits in a function body.

    Raises `SyntaxError` when the source does not parse, and `tokenize.TokenError`
    when it does not tokenize. A comment is `inline` when its line falls within
    the body of a function or method — that is, from the first statement of the
    body to the definition's last line. `doc` is always `False`: Python writes
    its Reference contracts as docstrings, which are strings and never reach a
    comment token, which is also why a `#` inside a string literal is not one.
    """
    spans = [
        (node.body[0].lineno, node.end_lineno)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body and node.end_lineno is not None
    ]
    found = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        line = token.start[0]
        found.append(Comment(line, token.string.lstrip("#").strip(),
                             any(start <= line <= end for start, end in spans), False,
                             not token.line[:token.start[1]].strip()))
    return found


def rust_spans(source: str) -> list[tuple[int, int, int, bool]]:
    """Every comment of a Rust source as `(start, end, line, doc)` over its characters.

    The one scanner both Rust readers share. String and character literals are
    skipped, so a `//` inside `"https://x"` opens no comment. `doc` marks a doc
    comment — `///`, `//!`, `/**` or `/*!` — which is Rust's Reference contract
    and carries its examples as code by design. `start` and `end` are character
    offsets and `line` is 1-based.
    """
    spans, index, line = [], 0, 1
    while index < len(source):
        char = source[index]
        if char == "\n":
            line += 1
            index += 1
        elif char in ('"', "'"):
            quote, index = char, index + 1
            while index < len(source) and source[index] != quote:
                if source[index] == "\\":
                    index += 1
                elif source[index] == "\n":
                    line += 1
                index += 1
            index += 1
        elif source.startswith("//", index):
            end = source.find("\n", index)
            end = len(source) if end < 0 else end
            spans.append((index, end, line, source.startswith(("///", "//!"), index)))
            index = end
        elif source.startswith("/*", index):
            end = source.find("*/", index)
            end = len(source) if end < 0 else end + 2
            spans.append((index, end, line, source.startswith(("/**", "/*!"), index)))
            line += source.count("\n", index, end)
            index = end
        else:
            index += 1
    return spans


def rust_comments(source: str) -> list[Comment]:
    """The comments of a Rust source, one entry per line of comment text.

    `inline` is always `False`: the step that uses it asks nothing of Rust
    function bodies. `own` says the comment starts its line, and a block
    comment's continuation lines are its own by definition.
    """
    found = []
    for start, end, line, doc in rust_spans(source):
        own = not source[source.rfind("\n", 0, start) + 1:start].strip()
        for offset, text in enumerate(source[start:end].splitlines()):
            found.append(Comment(line + offset, text.strip("/!*").strip(), False, doc,
                                 own or offset > 0))
    return found


def uncommented_rust(source: str) -> str:
    """The source with every comment blanked to spaces, line numbers and columns intact.

    What an attribute scan reads, so that `#[allow(...)]` beside a comment is
    still found and `#[allow(...)]` inside one is not.
    """
    out = list(source)
    for start, end, _, _ in rust_spans(source):
        for index in range(start, end):
            if out[index] != "\n":
                out[index] = " "
    return "".join(out)


def blocks(comments: list[Comment]) -> list[Block]:
    """Consecutive comment lines grouped into one block, which is one act of commentary.

    A block is reported and counted once, so a five-line paragraph of narration
    is one finding rather than five, and a citation anywhere in it exempts the
    whole. The block's line is its first, and its text is every line joined by
    a space.

    Only own-line comments group. A trailing comment is one block by itself,
    however close it sits: joined to the paragraph above it, a `noqa` or an
    `SPDX-License-Identifier` on the next statement would exempt that paragraph
    along with itself.
    """
    grouped: list[list[Comment]] = []
    for comment in comments:
        joins = (grouped and comment.own and grouped[-1][-1].own
                 and comment.line == grouped[-1][-1].line + 1)
        if joins:
            grouped[-1].append(comment)
        else:
            grouped.append([comment])
    return [Block(run[0].line, " ".join(c.text for c in run), run[0].inline)
            for run in grouped]


def keep_exception(text: str) -> str | None:
    """Which keep-exception a comment falls under, or `None` when it falls under none.

    Returns `"directive"` for a tool directive, `"notice"` for a legal or
    licensing notice, and `"citation"` for a comment naming a Decision Record,
    an Article, an Issue, an RFC, a URL or a `[[concept]]`.
    """
    if DIRECTIVE.match(text):
        return "directive"
    if NOTICE.search(text):
        return "notice"
    if CITATION.search(text):
        return "citation"
    return None


def python_code(text: str) -> bool:
    """Whether a comment's text is a Python statement rather than a sentence about one.

    A block header is completed with `pass` before parsing, so `for row in rows:`
    and `def helper(x):` are recognised: a commented-out block is commented out
    one line at a time, and its first line never parses alone.
    """
    body = text.strip()
    if not body or keep_exception(body) == "directive":
        return False
    if body.endswith(":"):
        body += "\n    pass"
    try:
        parsed = ast.parse(body)
    except (SyntaxError, ValueError):
        return False
    if len(parsed.body) != 1:
        return bool(parsed.body)
    node = parsed.body[0]
    if isinstance(node, STATEMENTS):
        return True
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)


def rust_code(text: str) -> bool:
    """Whether a comment's text is a Rust statement rather than a sentence about one."""
    body = text.strip()
    if not body or body.startswith("#["):
        return False
    return bool(RUST_CODE.search(body))


def suppressions(source: str, rust: bool = False) -> list[tuple[int, str]]:
    """The suppressions in a source that name no rule, as `(line, what)` pairs.

    A Python `noqa` or `type: ignore` comment without codes silences every rule
    at that line, and a Rust `#[allow(...)]` silences its lint for good. `#[expect]`
    is not a suppression by this measure: it fails when the lint stops firing,
    so it cannot outlive the thing it covers.

    Python is read from comment tokens and Rust from the source with its
    comments blanked, so a suppression quoted in a string, a docstring or a doc
    comment is the text of one rather than one. This module and `files.py` both
    quote every pattern here, and a line scan reports itself.

    Raises `SyntaxError` or `tokenize.TokenError` when a Python source will not
    parse; the caller names the file.
    """
    if rust:
        return [(number, "`#[allow(...)]` suppresses a lint for good; use `#[expect(...)]`")
                for number, line in enumerate(uncommented_rust(source).splitlines(), 1)
                if ALLOW.search(line)]
    found = []
    for comment in python_comments(source):
        for pattern, what in ((NOQA, "noqa"), (TYPE_IGNORE, "type: ignore")):
            match = pattern.search(f"#{comment.text}")
            if match and not match.group("codes"):
                found.append((comment.line, f"bare `{what}` names no rule"))
    return found


@check("commented-out code")
def commented_out_code():
    """No comment under `.meta/` or in a Rust source is a line of code left behind (solorepo's DR-171).

    Code kept as a comment is a claim about the program that nothing runs and
    nothing checks. Version control holds what was deleted; a comment holds only
    the reader's doubt about whether it still works.

    Python is decided by `ast`: the text must parse to a statement that does
    something, so `TODO` and `fmt: skip` are not code. Rust is decided by
    `RUST_CODE`, which looks for the shapes prose does not take, and skips doc
    comments, whose examples are code on purpose and are run by `cargo test`.
    """
    python, rust = sources(), rust_sources()
    problems, counted = [], 0
    for source in python:
        text = source.read_text(encoding="utf-8")
        try:
            comments = python_comments(text)
        except (SyntaxError, tokenize.TokenError) as error:
            problems.append(f"{source.relative_to(ROOT).as_posix()}: does not parse — {error}")
            continue
        counted += len(comments)
        for comment in comments:
            if python_code(comment.text):
                problems.append(
                    f"{source.relative_to(ROOT).as_posix()}:{comment.line}: "
                    f"commented-out code — `{comment.text[:60]}`"
                )
    for source in rust:
        comments = rust_comments(source.read_text(encoding="utf-8"))
        counted += len(comments)
        for comment in comments:
            if not comment.doc and rust_code(comment.text):
                problems.append(
                    f"{source.relative_to(ROOT).as_posix()}:{comment.line}: "
                    f"commented-out code — `{comment.text[:60]}`"
                )
    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} comments across {len(python)} Python and "
                  f"{len(rust)} Rust files, none of them code")


@check("broad suppressions")
def broad_suppressions():
    """Every suppression names the rule it suppresses (A2, solorepo's DR-177).

    The complement to `meta lints`, which holds that a suppression carries a
    reason. This holds that it carries a rule: a bare `noqa` or a bare
    `type: ignore` comment silences everything at that line, including the rule nobody
    had met yet when it was written. A Rust `#[allow(...)]` silences its lint
    until someone deletes it, where `#[expect(...)]` fails once the lint stops
    firing and so cannot outlive its cause.
    """
    python, rust = sources(), rust_sources()
    problems = []
    for source in python + rust:
        text = source.read_text(encoding="utf-8")
        relative = source.relative_to(ROOT).as_posix()
        try:
            found = suppressions(text, rust=source.suffix == ".rs")
        except (SyntaxError, tokenize.TokenError) as error:
            problems.append(f"{relative}: does not parse — {error}")
            continue
        problems.extend(f"{relative}:{number}: {what}" for number, what in found)
    if problems:
        return Found(tuple(problems))
    return Passed(f"no bare suppression across {len(python)} Python and "
                  f"{len(rust)} Rust files")

def comment_site(relative: str, block: Block) -> str:
    """Formats an inline commentary block as a site line for against_baseline."""
    return f"{relative}:{block.line}: `{block.text[:70]}`"


@check("inline commentary")
def inline_commentary():
    """Function bodies under `.meta/` hold no commentary outside the keep-exceptions, ratcheted (solorepo's DR-194, solorepo's DR-196).

    Narration inside a body is knowledge in the one container that has no reader
    but the next editor of that line. Its destinations are the item docstring,
    a Decision Record, a `<module>.history.md` log and a `just` recipe. What
    stays is a legal notice, a tool directive, and an external boundary
    constraint carrying a dereferenced citation.

    The tree is not clean, so the step ratchets: `comments.baseline.yaml` records
    what each file may still hold. A file over its baseline fails, and so does a
    file under it, because a baseline nobody lowers is a baseline that stopped
    being one. Either way every site in that file is listed, which is what the
    edit needs.
    """
    if not BASELINE.is_file():
        return CouldNotRun(f"{BASELINE.relative_to(ROOT).as_posix()} is missing")
    recorded = recorded_baseline(BASELINE)
    counts, sites = {}, {}
    for source in sources():
        relative = source.relative_to(ROOT).as_posix()
        try:
            comments = python_comments(source.read_text(encoding="utf-8"))
        except (SyntaxError, tokenize.TokenError) as error:
            return Found((f"{relative}: does not parse — {error}",))
        found = [block for block in blocks(comments)
                 if block.inline and keep_exception(block.text) is None]
        if found:
            counts[relative] = len(found)
            sites[relative] = [comment_site(relative, block) for block in found]
    problems = against_baseline(counts, sites, recorded, "body comments", BASELINE)
    if problems:
        return Found(tuple(problems))
    return Passed(f"{sum(counts.values())} body comments across {len(counts)} files, "
                  f"each file at its baseline")
