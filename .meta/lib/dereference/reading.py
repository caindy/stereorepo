"""The deterministic half: the citations `check.py` extracts, the sentence each sits in, the entry it names, and the scope a branch is read in, from the diff and the ground that moved (stereorepo's DR-192).
"""
import importlib.util
import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from typing import Any

import yaml

from lib.dereference import META, ROOT

# A sentence ends at a stop and a space before something that starts one. The
# lookahead carries `*` and a digit because a page's own emphasis and its
# numbered steps start sentences here: `**Enforces** … **Checked by** …` is one
# line of the Charter and two claims about two different things.
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'`(\[*\d])")


# What opens a row of a table or an item of a list, and therefore ends the one
# above it. A stop is not the only boundary a page has, and it is not the
# boundary a list uses: `- [DR-045](…) — withdrawn.` follows `An audit report.`
# with no stop-and-capital between them, so a splitter reading sentences alone
# hands each item the tail of the item before it and asks about the wrong pair.
ITEM = re.compile(r"^\s*(?:\||[-*+]\s|\d+[.)]\s)")
CONTEXT = 600


CHECKS = META / "checks"


def citations() -> Any:
    """`.meta/checks/citations/`, imported for its extraction and nothing else.

    Importing runs nothing — everything it does is under `main()` — and the
    functions used here read files. It is imported rather than copied because
    what a citation is, and which files
    hold one durably, is one fact, and a copy of it here would be a second
    answer that drifts.

    The gate's steps moved out of `check.py` into `.meta/checks/`
    (stereorepo's DR-150), so what this reaches for now has a name: the citation
    grammar and the copy set are the `citations` package's, and nothing else in
    the gate is wanted here. Its own siblings are imported by plain name, so the
    directory goes on `sys.path` first, and the package is imported by name
    since a package has no one file to load (stereorepo's DR-218).
    """
    if str(CHECKS) not in sys.path:
        sys.path.insert(0, str(CHECKS))
    return importlib.import_module("citations")


def git(*args: str, default: str | None = None) -> str:
    """Executes a git command in the repository root and returns its stdout."""
    out = subprocess.run(["git", *args], check=False, capture_output=True, text=True, cwd=ROOT)
    if out.returncode:
        if default is None:
            sys.exit(f"dereference: git {' '.join(args[:2])}: {out.stderr.strip()}")
        return default
    return out.stdout


def articles() -> dict[int, dict[str, Any]]:
    """Every Article, by number, as the entry a citation of it names."""
    charter = yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    return {int(a["id"].rsplit("/", 1)[-1]): a for a in charter.get("articles") or []}


def target(cite: str, index: dict[int, dict[str, Any]]) -> str | None:
    """What a citation names, as text a reader could be handed, or None where it
    names nothing here.

    Nothing here is not this step's finding. A number that resolves to nothing
    is `cited decisions`' and `cited articles`', which are deterministic and in
    the gate; reporting it again would be two checkers saying one thing, and the
    one whose answer is a reading saying it worse.
    """
    if cite.startswith("DR-"):
        path = META / "assertions" / "decisions" / f"{cite}.yaml"
        return path.read_text() if path.is_file() else None
    article = index.get(int(cite[1:]))
    return yaml.safe_dump(article, sort_keys=False, allow_unicode=True) if article else None


# A sentence naming more than this is an index and not a claim: the Charter's
# closing line lists ten entries it came from, and `decisions.md` is a table of
# every one. Each is a pointer, each would come back `ok`, and paying for the
# reading of a list is paying for the form rather than the claim.
MANY = 4


def spans(chk: Any, path: pathlib.Path) -> list[str]:
    """The units a claim is made in: an assertion's scalars, or a page's
    paragraphs and table rows.

    An assertion is `prose`'s reading — one span per scalar, the parser's own,
    and the reason a citation in a YAML comment is out of scope here as it is
    there. Anything else is not: `prose` flattens a whole page to one string,
    which is what the four string searches want and the opposite of what a
    reader reads.

    A question needs the sentence somebody wrote, so a page is cut on its blank
    lines and again wherever a line opens a row or an item, its continuation
    lines joining the item above. Both halves are the same failure. Without the
    first, `decisions.md` is one sentence citing every entry in the record.
    Without the second, that file's withdrawn list is asked one item out of
    step: an item opening `- [DR-nnn](…) — withdrawn.` follows the last sentence
    of the item above it with no stop-and-capital in between, so each entry is
    asked to support the reason belonging to its predecessor, and a coder who
    fixed what came back would be rewriting true prose to satisfy a splitter —
    which is the failure stereorepo's DR-134 names as its falsifier, arriving by
    construction.
    """
    if path.suffix in (".yaml", ".yml"):
        result: list[str] = chk.prose(path)
        return result
    try:
        text = chk.BLOCK.sub(" ", path.read_text())
    except (UnicodeDecodeError, OSError):
        return []
    found = []
    for block in re.split(r"\n\s*\n", text):
        item: list[str] = []
        for line in block.splitlines():
            if ITEM.match(line) and item:
                found.append(str(chk.flat(" ".join(item))))
                item = []
            item.append(line)
        if item:
            found.append(str(chk.flat(" ".join(item))))
    return [span for span in found if span.strip()]


def sentences(chk: Any, path: pathlib.Path) -> list[tuple[str, str, list[str]]]:
    """Every sentence of a file that cites an entry, with the span around it.

    A citation inside a code span is the shape of one and not one, and is
    dropped the way `cited articles` drops it. The word boundaries are this
    file's: `check.py` puts them where each of its patterns needs them, and a
    bare `CITE` would read the `A1` inside a token that merely contains one.
    """
    cites = re.compile(rf"\b{chk.CITE}\b")
    found: list[tuple[str, str, list[str]]] = []
    for span in spans(chk, path):
        at = 0
        for part in SENTENCE.split(span):
            at = span.find(part, at)
            named = sorted({m.group() for m in cites.finditer(chk.SPAN.sub(" ", part))})
            if named and len(named) <= MANY:
                around = span[max(0, at - CONTEXT):at + len(part) + CONTEXT]
                found.append((part.strip(), around.strip(), named))
            at += len(part)
    return found


def as_it_was(chk: Any, path: pathlib.Path, text: str) -> set[str]:
    """The citing sentences a file held at the base.

    Written to a file with the same suffix and read back through the same
    `sentences`, because `prose` reads a path and reads a `.yaml` as a document
    and anything else as text. Handing it the bytes some other way would mean a
    second reading of what a file is, which is the thing this file does not do.
    """
    with tempfile.NamedTemporaryFile("w", suffix=path.suffix, delete=False) as handle:
        handle.write(text)
        was = pathlib.Path(handle.name)
    try:
        return {sentence for sentence, _, _ in sentences(chk, was)}
    finally:
        was.unlink()


def durable_prose(chk: Any) -> set[pathlib.Path]:
    """The durable files the questions are asked of: what `chk.durable` names, less Python and less every rendered page but the justfile."""
    import render
    durable: set[pathlib.Path] = set(chk.durable(chk.copied_files()))
    meta_dir = pathlib.Path(render.__file__).resolve().parent
    skip = {(meta_dir / name).resolve() for name in render.rendered()} - {(meta_dir / ".." / "justfile").resolve()}
    return {p for p in durable if p.suffix != ".py" and p.resolve() not in skip}


def pair(path: pathlib.Path, cite: str, sentence: str, around: str, body: str, **more: Any) -> dict[str, Any]:
    """One question: the sentence at `path`, the citation, the span it sits in and what the citation names."""
    return {"path": str(path.relative_to(ROOT)), "cite": cite, "sentence": sentence,
            "context": around, "body": body, **more}


def sampled(
    chk: Any,
    index: dict[int, dict[str, Any]],
    durable: set[pathlib.Path],
    sample: int,
) -> list[dict[str, Any]]:
    """A rotating sample of `sample` pairs over every durable file, the offset turning with the commit count (stereorepo's DR-192).

    A record holding fewer pairs than `sample` answers each of them once, and
    no pair twice: the rotation wraps to fill the window, and a window wider
    than the pool would otherwise wrap onto pairs it already holds.
    """
    all_pairs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(durable):
        for sentence, around, named in sentences(chk, path):
            for cite in named:
                body = target(cite, index)
                if body is None or (cite, sentence) in seen:
                    continue
                seen.add((cite, sentence))
                all_pairs.append(pair(path, cite, sentence, around, body))
    if not all_pairs:
        return []
    commit_str = git("rev-list", "--count", "HEAD", default="0").strip()
    count = int(commit_str) if commit_str.isdigit() else 0
    offset = (count * sample) % len(all_pairs)
    return (all_pairs + all_pairs)[offset:offset + min(sample, len(all_pairs))]


def moved_articles(base: str, path: pathlib.Path) -> set[str]:
    """The Articles whose text differs between `base` and the charter at `path`, as `A<n>`."""
    was_text = git("show", f"{base}:{path.relative_to(ROOT)}", default="")
    was_charter = yaml.safe_load(was_text) or {} if was_text else {}
    now_charter = yaml.safe_load(path.read_text()) or {} if path.is_file() else {}
    was_art = {int(a["id"].rsplit("/", 1)[-1]): a for a in was_charter.get("articles") or []}
    now_art = {int(a["id"].rsplit("/", 1)[-1]): a for a in now_charter.get("articles") or []}
    return {f"A{num}" for num, art in now_art.items() if num not in was_art or was_art[num] != art}


def modified_entries(base: str, changed: list[pathlib.Path]) -> set[str]:
    """The Decisions and Articles this branch moved: every `DR-` assertion among `changed`, and each Article the charter's text changed (stereorepo's DR-192)."""
    entries: set[str] = set()
    for p in changed:
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            rel = p
        if (len(rel.parts) >= 4 and rel.parts[:3] == (".meta", "assertions", "decisions")
                and rel.name.startswith("DR-") and rel.suffix in (".yaml", ".yml")):
            entries.add(rel.stem)
        elif rel == pathlib.Path(".meta/assertions/imported/charter.yaml"):
            entries |= moved_articles(base, p)
    return entries


def asked(
    chk: Any,
    index: dict[int, dict[str, Any]],
    seen: set[tuple[str, str]],
    readings: Iterable[tuple[pathlib.Path, set[str], set[str] | None]],
) -> list[dict[str, Any]]:
    """The pairs over `readings`, each `(path, held, only)`: sentences in `held` are skipped, and where `only` is given so is every citation outside it, which marks the pair as ground that moved; `seen` keeps a pair from being asked twice."""
    pairs: list[dict[str, Any]] = []
    for path, held, only in readings:
        for sentence, around, named in sentences(chk, path):
            if sentence in held:
                continue
            for cite in named:
                if only is not None and cite not in only:
                    continue
                body = target(cite, index)
                if body is None or (cite, sentence) in seen:
                    continue
                seen.add((cite, sentence))
                more = {"ground_moved": True} if only is not None else {}
                pairs.append(pair(path, cite, sentence, around, body, **more))
    return pairs


def branch_paths(
    base: str,
    durable: set[pathlib.Path],
) -> tuple[list[pathlib.Path], dict[pathlib.Path, str], set[str]]:
    """The durable files this branch changed, tracked or not, each with its text at `base`, and the entries the branch moved."""
    named = git("diff", "--name-only", base).split()
    named += git("ls-files", "--others", "--exclude-standard", default="").split()
    changed = [(ROOT / name) for name in dict.fromkeys(named)]
    paths = sorted(p for p in changed if p in durable and p.is_file())
    before = {p: git("show", f"{base}:{p.relative_to(ROOT)}", default="") for p in paths}
    return paths, before, modified_entries(base, changed)


def scope(
    chk: Any,
    base: str,
    everything: bool,
    sample: int | None = None,
    durable: set[pathlib.Path] | None = None,
) -> list[dict[str, Any]]:
    """The pairs to ask about: a sentence, the span it sits in, the citation and
    what the citation names.

    Everything, what this branch wrote or affected, or a rotating sample
    (stereorepo's DR-192). The branch scope is a set difference over sentences
    rather than a read of the diff's line numbers: a folded scalar wraps where
    the line ended and not where the sentence did, so a line-based scope would
    report a claim whose only change was the width of its wrap, and would miss
    one edited across a fold. When this branch modifies an entry (a Decision or
    Article assertion), all durable sentences citing that modified entry are
    also included, catching the ground that moved under them.

    A pair is asked once. The same sentence citing the same entry in two files
    is one question with one answer, and paying twice for it is paying for the
    copy rather than the claim.

    The branch scope reads what git has been told about and what it has not,
    both: a new file is the normal shape of a decision entry, and a run before
    the hand-off that read only the committed diff would skip the file the
    branch exists to add.
    """
    index = articles()
    if durable is None:
        durable = durable_prose(chk)
    if sample:
        return sampled(chk, index, durable, sample)
    paths: list[pathlib.Path]
    before: dict[pathlib.Path, str]
    moved: set[str]
    if everything:
        paths, before, moved = sorted(durable), {}, set()
    else:
        paths, before, moved = branch_paths(base, durable)

    seen: set[tuple[str, str]] = set()
    pairs = asked(chk, index, seen, ((path, set() if everything else as_it_was(chk, path, before[path]), None)
                                     for path in paths))
    pairs += asked(chk, index, seen, ((path, set(), moved) for path in sorted(durable) if moved))
    return pairs
