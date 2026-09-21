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

A suppression owes three things and two steps elsewhere hold two of them: the
rule it names, which `broad suppressions` here requires, and the reason it
carries, which `meta lints` requires (solorepo's DR-177). `suppression causes`
holds the third, reading that reason for a cause this repository can fix
(solorepo's DR-225).

`inline commentary` and `suppression causes` are ratcheted rather than flat:
the tree held 210 body comment blocks across 15 files when the first was
written, and one internally caused suppression when the second landed, and the
Ratchet Discipline is what a checker that cannot be clean at once does. The
baselines are
`.meta/checks/comments.baseline.yaml` and
`.meta/checks/suppressions.baseline.yaml`, and each may fall and may not rise.
The comparison itself is `collect.against_baseline`, shared with the
`meta types` step of `files.py` (solorepo's DR-210).

`repeated suppressions` ratchets too, against
`.meta/checks/suppressions.baseline.yaml`, and its comparison is
`against_repeats` rather than the shared one: a group is keyed by its rule and
reason rather than by a path, so a baseline entry the tree has dropped is one
to delete rather than one naming a file that no longer exists
(solorepo's DR-223).

Scope: every Python and Rust file git lists.
"""
import ast
import collections
import io
import pathlib
import re
import tokenize

from checks.collect import (
    META,
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    against_baseline,
    check,
    recorded_baseline,
)
from checks.files import meta_sources, tree

BASELINE = META / "checks" / "comments.baseline.yaml"
SUPPRESSIONS_BASELINE = META / "checks" / "suppressions.baseline.yaml"
SUPPRESSIONS = SUPPRESSIONS_BASELINE

# How many sites sharing one rule and one reason make a root cause rather than a
# coincidence. Two is the literal reading of the Suppression Audit Protocol and
# refuses the honest pair — two query builders in one module meeting one
# constraint — so the limit is three, where a reason has been copied rather than
# arrived at twice (solorepo's DR-223).
REPEAT_LIMIT = 3
# The Protocol's escape hatch, narrowed to what is outside this repository: a
# specification or an upstream tracker a reader can open. `DR-nnn`, `Article n`
# and `#n` name something inside the repository, and a cause inside it is one to
# fix rather than to repeat (solorepo's DR-223).
EXTERNAL = re.compile(r"(https?://|RFC\s*\d+)", re.IGNORECASE)

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
REASON = re.compile(r"#\s*reason:\s*(?P<why>\S.*)$")
ALLOW = re.compile(r"#!?\[\s*allow\s*\(")

# A dereference of something outside this repository, blanked from a reason
# before its cause is read: a foreign tracker's host spells a module name of
# this one, so `https://github.com/python/mypy/issues/1` is the boundary
# citation the clause asks for and not a reference to
# `.meta/lib/check_pr/github.py` (solorepo's DR-225).
UPSTREAM = re.compile(r"https?://\S+")
# The four shapes a cause inside this repository takes, each resolved against
# this tree rather than read: a path the repository holds, a dotted reference
# whose head is a module under `.meta/`, an Issue number, and a Decision Record
# number (solorepo's DR-225).
REPO_PATH = re.compile(r"[\w.][\w./-]*\.(?:py|md|ya?ml|rs|toml|json|sh|txt)\b")
DOTTED = re.compile(r"\b(\w+)\.\w+")
ISSUE = re.compile(r"#\d+\b")
DECISION = re.compile(r"\bDR-\d{3}\b")

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
Suppression = collections.namedtuple("Suppression", "line rule reason")


def sources() -> list[pathlib.Path]:
    """Every Python file git lists, including extension-less scripts under .meta/."""
    tracked_py = [p for p in tree() if p.suffix == ".py" and p.is_file()]
    return sorted(set(tracked_py + meta_sources()))


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


def modules() -> set[str]:
    """Every module name a Python file under `.meta/` defines, a package named by its directory."""
    return {path.parent.name if path.stem == "__init__" else path.stem for path in sources()}


def reasons(source: str) -> list[tuple[int, str]]:
    """Every suppression's reason in a Python source, as `(line, reason)` pairs.

    A suppression carrying no reason yields nothing: `meta lints` is the step
    that refuses that one (solorepo's DR-177), and one defect reported by two
    steps reads as two.

    A line yields one reason at most, however many directives it carries.
    `tokenize` emits one comment token per physical line, so a line spelling
    both a `noqa` and a `type: ignore` matches both patterns against the same
    text and both rests end at the same `# reason:` — counting that twice would
    read one suppression as two and inflate the ratchet by the difference.

    Raises `SyntaxError` or `tokenize.TokenError` when the source will not
    parse; the caller names the file.
    """
    found = []
    for comment in python_comments(source):
        for pattern in (NOQA, TYPE_IGNORE):
            match = pattern.search(f"#{comment.text}")
            if match is None:
                continue
            why = REASON.search(match.group("rest"))
            if why:
                found.append((comment.line, why.group("why").strip()))
                break
    return found


def internal_cause(reason: str, names: set[str]) -> str | None:
    """What of this repository a suppression's reason names, or `None` where it names nothing here.

    The half of the surviving-suppression clause that is decidable: that a cause
    is foreign cannot be proved from a sentence, because a library name is a
    word, but that a cause is local can be, because the thing named is in this
    tree and the reader can open it (solorepo's DR-225).

    Args:
        reason: The text after `# reason:`, as `reasons` returns it.
        names: The module names `modules` found under `.meta/`.

    Returns:
        str | None: What the reason names here, in the words the failure line
        reads with, or `None` where nothing it names resolves to this
        repository.
    """
    text = UPSTREAM.sub(" ", reason)
    for match in REPO_PATH.finditer(text):
        if (ROOT / match.group()).is_file():
            return f"names `{match.group()}` of this repository"
    for match in DOTTED.finditer(text):
        if match.group(1) in names:
            return f"names `{match.group(1)}` of this repository"
    issue = ISSUE.search(text)
    if issue:
        return f"defers to {issue.group()}, an Issue of this repository"
    decision = DECISION.search(text)
    if decision:
        return f"names {decision.group()}, a Decision of this repository"
    return None


def cause_site(relative: str, line: int, cause: str, reason: str) -> str:
    """Formats an internal suppression cause as a site line for against_baseline."""
    return f"{relative}:{line}: {cause} — `{reason[:60]}`"


def suppression_reasons(source: str) -> list[Suppression]:
    """Every Python suppression of a source as `(line, rule, reason)`, the reason normalised.

    `rule` is the directive with the codes it names and no spacing — `noqa:F401`,
    `type: ignore[untyped-decorator]` — so that one rule spelled two ways is one
    rule. `reason` is what follows `# reason:`, casefolded with backticks
    dropped, runs of whitespace collapsed and surrounding punctuation trimmed,
    so that a copy differing only in spacing, capitals or a full stop groups with
    its original. `meta lints` is what requires the reason to be written at all
    (solorepo's DR-177), and a suppression carrying none reads here as the empty
    reason.

    Normalisation reaches the copy and not the paraphrase: two reasons differing
    by a word are two reasons to this function, and a repetition disguised that
    way is the reviewer's to see.

    Args:
        source: The Python source text.

    Returns:
        list[Suppression]: One entry per `noqa` or `type: ignore` comment, in
        line order.

    Raises:
        SyntaxError: The source does not parse; the caller names the file.
        tokenize.TokenError: The source does not tokenize; the caller names the file.
    """
    found = []
    for comment in python_comments(source):
        for pattern, what in ((NOQA, "noqa"), (TYPE_IGNORE, "type: ignore")):
            match = pattern.search(f"#{comment.text}")
            if match is None:
                continue
            given = REASON.search(match.group("rest"))
            reason = given.group("why") if given else ""
            codes = re.sub(r"\s+", "", match.group("codes") or "")
            normalised = re.sub(r"\s+", " ", reason.replace("`", "").casefold())
            found.append(Suppression(comment.line, what + codes, normalised.strip(" .,;:")))
    return found


def repeated(reading: dict[str, str]) -> tuple[dict[str, list[str]], list[str]]:
    """The suppression groups over a set of sources, and the sources that would not parse.

    A group is one rule written with one reason, keyed `<rule> — <reason>`, and
    its value is every site that wrote it as `<path>:<line>`. A suppression whose
    reason cites something outside this repository is left out of the grouping
    entirely: that is the Suppression Audit Protocol's one surviving kind, and a
    boundary a foreign platform forces on the code may recur as often as the
    code meets it (solorepo's DR-207, solorepo's DR-223).

    Args:
        reading: Repository-relative path to the Python source text at it.

    Returns:
        tuple[dict[str, list[str]], list[str]]: The groups, and one line per
        source that would not parse.
    """
    groups: dict[str, list[str]] = collections.defaultdict(list)
    problems = []
    for relative, source in sorted(reading.items()):
        try:
            found = suppression_reasons(source)
        except (SyntaxError, tokenize.TokenError) as error:
            problems.append(f"{relative}: does not parse — {error}")
            continue
        for one in found:
            if EXTERNAL.search(one.reason):
                continue
            groups[f"{one.rule} — {one.reason}"].append(f"{relative}:{one.line}")
    return dict(groups), problems


def against_repeats(groups: dict[str, list[str]], recorded: dict[str, int]) -> list[str]:
    """What the repeat ratchet has to say about the groups it found, against the groups it recorded.

    A group counts once it reaches `REPEAT_LIMIT` sites, and once the baseline
    records it, so that a recorded group which has shrunk is still spoken about.
    The comparison is two-sided as every ratchet here is, and worded for a key
    that is a rule and a reason rather than a path: a group over its number is a
    root cause written once more, so the line says to fix the cause rather than
    to write the new number; a group under it, or down below `REPEAT_LIMIT`, is
    progress the baseline has to bank.

    `collect.against_baseline` is not reused: it reads a key that is not a file
    on disk as a stale entry, which is right for a per-file ratchet and wrong
    for every failing group here (solorepo's DR-223).

    Args:
        groups: Group key to every site in it, as `<path>:<line>`.
        recorded: Group key to the number of sites the baseline allows.

    Returns:
        list[str]: One line per group whose count is not its recorded number,
        and then one line per site in that group for groups at or above
        `REPEAT_LIMIT`. A group shrunk below the limit reports only the
        instruction to remove its entry.
    """
    counts = {key: len(sites) for key, sites in groups.items()
              if len(sites) >= REPEAT_LIMIT or key in recorded}
    where = SUPPRESSIONS.relative_to(ROOT).as_posix()
    problems = []
    for key in sorted(set(counts) | set(recorded)):
        count, allowed = counts.get(key, 0), recorded.get(key, 0)
        if count == allowed:
            continue
        if count < REPEAT_LIMIT:
            problems.append(f"{key}: down to {count} sites — remove the entry from {where}")
            continue
        if count > allowed:
            problems.append(f"{key}: {count} sites, over its baseline of {allowed} — one root "
                            f"cause written {count} times; fix the cause, do not raise {where}")
        else:
            problems.append(f"{key}: {count} sites, under its baseline of {allowed} — "
                            f"write {count} in {where}")
        problems.extend(f"     {line}" for line in groups.get(key, []))
    return problems


@check("commented-out code")
def commented_out_code() -> StepOutcome:
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
def broad_suppressions() -> StepOutcome:
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

@check("suppression causes")
def suppression_causes() -> StepOutcome:
    """A suppression's reason names a cause outside this repository, ratcheted (A2, solorepo's DR-225).

    The third thing a suppression owes, after the rule `broad suppressions`
    requires and the reason `meta lints` requires. A suppression earns its keep
    only as an immutable external boundary constraint, so a reason whose cause
    is inside this repository fails by construction: an internal cause is one
    this repository can fix, which is what solorepo's DR-207 says to do with it.
    An Issue number is refused along with the rest, because deferring to an
    Issue is the escape the clause exists to close.

    What the step proves is the local half alone. It says nothing about a reason
    that names no cause this tree holds, which stays with the suppression audit
    solorepo's DR-207 requires before a handoff.

    The tree is not clean, so the step ratchets against
    `suppressions.baseline.yaml`, which may fall and may not rise. One entry is
    left, and annotating `.meta/render.py` is what empties it.
    """
    if not SUPPRESSIONS_BASELINE.is_file():
        return CouldNotRun(f"{SUPPRESSIONS_BASELINE.relative_to(ROOT).as_posix()} is missing")
    recorded = {k: v for k, v in recorded_baseline(SUPPRESSIONS_BASELINE).items() if " — " not in k}
    names, counts, sites, read = modules(), {}, {}, 0
    for source in sources():
        relative = source.relative_to(ROOT).as_posix()
        try:
            found = reasons(source.read_text(encoding="utf-8"))
        except (SyntaxError, tokenize.TokenError) as error:
            return Found((f"{relative}: does not parse — {error}",))
        read += len(found)
        named = [(line, why, cause) for line, why in found
                 if (cause := internal_cause(why, names))]
        if named:
            counts[relative] = len(named)
            sites[relative] = [cause_site(relative, line, cause, why)
                               for line, why, cause in named]
    problems = against_baseline(counts, sites, recorded, "internal suppression causes",
                                SUPPRESSIONS_BASELINE)
    if problems:
        return Found(tuple(problems))
    return Passed(f"{read} suppression reasons read, {sum(counts.values())} naming a cause "
                  f"inside this repository, each file at its baseline")

@check("repeated suppressions")
def repeated_suppressions() -> StepOutcome:
    """No rule and reason are suppressed together at three sites or more, ratcheted (solorepo's DR-207, solorepo's DR-223).

    An identical reason at many sites is one root cause written many times, and
    the Suppression Audit Protocol says to fix the cause: "the suppression is
    not the fix; it is the record that nobody looked." `meta lints` and
    `broad suppressions` pass such a run every time, because each site carries a
    reason and each names a rule — which is how the prescribed fix for a
    file-scope suppression, narrowing it to the line, defeats the rule behind
    it.

    The tree is not clean, so the step ratchets against
    `suppressions.baseline.yaml`, and a group at its recorded number passes. A
    group over it fails because the cause was written once more; a group under
    it fails because a baseline nobody lowers has stopped being one; a group
    down below `REPEAT_LIMIT` fails until its entry is deleted.

    Scope is the Python under `.meta/`. Rust is left out because `#[allow(...)]`
    is refused outright by `broad suppressions`, so it has no repetition to
    count.
    """
    if not SUPPRESSIONS.is_file():
        return CouldNotRun(f"{SUPPRESSIONS.relative_to(ROOT).as_posix()} is missing")
    python = sources()
    groups, unparsed = repeated({
        source.relative_to(ROOT).as_posix(): source.read_text(encoding="utf-8")
        for source in python
    })
    if unparsed:
        return Found(tuple(unparsed))
    problems = against_repeats(groups, {k: v for k, v in recorded_baseline(SUPPRESSIONS).items() if " — " in k})
    if problems:
        return Found(tuple(problems))
    counted = [sites for sites in groups.values() if len(sites) >= REPEAT_LIMIT]
    return Passed(f"{sum(len(sites) for sites in counted)} suppressions in {len(counted)} "
                  f"repeated groups across {len(python)} files, each group at its baseline")


def comment_site(relative: str, block: Block) -> str:
    """Formats an inline commentary block as a site line for against_baseline."""
    return f"{relative}:{block.line}: `{block.text[:70]}`"


@check("inline commentary")
def inline_commentary() -> StepOutcome:
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
