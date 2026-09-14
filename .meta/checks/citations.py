"""What prose claims about the record, read against the record.

A12 asks three things of a citation, and the steps here resolve them in turn:
the number it names, and then the claim it goes on to make — an Article that
resolves, a quotation that appears where it is attributed, a relation that is
the slot it claims to be, and a line that reads what it is cited for (solorepo's DR-150).

History in citations.history.md (solorepo's DR-171).
"""
import re

import yaml

from collect import META, ROOT, TEMPLATE, check
from files import FENCED, inherited, tree

DR = re.compile(r"\bDR-(\d{3})\b")
# A citation of solorepo's record, in the form the material a portfolio inherits
# writes one: the possessive, then a run, so `solorepo's DR-073, DR-107` names two.
FOREIGN = re.compile(r"solorepo's DR-\d{3}\b(?:(?:,| and|, and) DR-\d{3}\b)*")
SCAFFOLD = "work:portfolio/solorepo"


def issue_citation():
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


@check("cited decisions")
def cited_decisions(index):
    """Validate that every Decision Record cited in durable prose resolves in the index.

    Ensures that Decision citations (`DR-nnn`) in durable files resolve to known Decision
    records in `index` (or the template seed), and enforces that files inherited by
    specialized portfolios use the qualified `solorepo's DR-nnn` form (solorepo's DR-121, solorepo's DR-124).

    Parameters:
        index (dict): LinkML model index mapping URI identifiers to entity tuples.

    Returns:
        list[str]: Validation problem messages for dangling or unqualified DR citations.
    """
    known = {d.rsplit("/", 1)[-1] for d, (cls, _, _) in index.items() if cls == "Decision"}
    if not known:
        return []
    home = SCAFFOLD in index
    seed = {m.group(1) for path in (TEMPLATE / ".meta" / "assertions" / "decisions").glob("DR-*.yaml")
            if (m := DR.search(path.name))}
    copied = copied_files()
    problems = []
    for path in durable(copied):
        seeded = TEMPLATE in path.parents
        try:
            text = FENCED.sub("", path.read_text())
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(ROOT)
        foreign = {num for m in FOREIGN.finditer(text) for num in DR.findall(m.group())}
        bare = set(DR.findall(FOREIGN.sub("", text)))
        if home:
            for num in sorted(foreign - known):
                problems.append(f"{rel}: solorepo's DR-{num} is cited and does not exist")
        for num in sorted(bare - (seed if seeded else known)):
            problems.append(f"{rel}: DR-{num} is cited and does not exist")
        if path in copied:
            for num in sorted(bare):
                problems.append(f"{rel}: DR-{num} is cited bare in a file a portfolio inherits, "
                                "where it will come to mean the portfolio's; cite it as solorepo's")
    return problems


# A12 asks three things of a citation and `cited decisions` resolves one of them:
# the number. What follows resolves the rest — the claim the citation goes on to
# make about the thing it names (solorepo's DR-130, solorepo's #147). Four shapes, chosen
# because each is a string search rather than a reading: an Article number that
# resolves, a quotation that appears where it is attributed, a relation that is
# the slot it claims to be, and a line that reads what it is cited for. A
# paraphrase is none of these and is nobody's check.
BLOCK = re.compile(r"```.*?```", re.S)
SPAN = re.compile(r"`[^`\n]*`")
ARTICLE = re.compile(r"\bA(\d{1,2})\b")
CITE = r"(?:DR-\d{3}|A\d{1,2})"
# Punctuation and markup boundaries that delimit citation scopes (sentence punctuation,
# markdown link brackets, and table cell pipes).
GAP = r"[^.;:|\[\]()\n]{0,30}?"

# Bounded non-citation span ensuring relation verbs bind to the nearest adjacent citation
# anchor in either direction without spanning intervening citations (solorepo's DR-175).
NEAREST = rf"(?:(?!{CITE})[^.;:|\[\]()\n]){{0,30}}?"
# Attribution: the words that turn a quotation into a claim about the entry
# beside it. Deliberately not `is` or `was`, which put a quotation next to a
# citation in sentences that are not attributing it to anything.
SAYS = r"says|say|said|reads|read|states|state|stated|calls it|names it|puts it|has it|quotes"
# What is not a claim: a relation denied, or one entertained and not made.
HEDGED = re.compile(r"\b(not|never|no longer|would|could|should|might|may|cannot|"
                    r"rather than|instead of|if)\b", re.I)


def scalars(node):
    """Recursively traverse a YAML document node and yield all leaf scalar string values.

    Parameters:
        node (object): Parsed YAML object (dict, list, or scalar).

    Yields:
        str: Next scalar string found within the node.
    """
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from scalars(value)
    elif isinstance(node, list):
        for value in node:
            yield from scalars(value)


def prose(path):
    """Extract prose spans from a file, excluding code blocks and structural comments.

    For Markdown, strips fenced code blocks; for YAML, extracts flattened scalar strings.

    Parameters:
        path (pathlib.Path): Path of file to extract prose from.

    Returns:
        list[str]: List of flattened whitespace-normalized prose spans.
    """
    try:
        text = path.read_text()
    except (UnicodeDecodeError, OSError):
        return []
    if path.suffix in (".yaml", ".yml"):
        try:
            return [flat(s) for s in scalars(yaml.safe_load(text))]
        except yaml.YAMLError:
            return []
    return [flat(BLOCK.sub(" ", text))]


def flat(text):
    """Normalizes arbitrary sequences of whitespace in text into a single space."""
    return re.sub(r"\s+", " ", text)


@check("cited articles")
def cited_articles():
    """Validate that every Article number cited in prose resolves in the Charter.

    Ensures `An` references outside code spans match live or reserved articles in `charter.yaml`.

    Returns:
        list[str]: Validation problem messages for unresolved Article citations.
    """
    charter = yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    live = {int(a["id"].rsplit("/", 1)[-1]) for a in charter.get("articles") or []}
    reserved = {r["number"] for r in charter.get("retired_articles") or []}
    if not live:
        return []
    problems = []
    for path in durable(copied_files()):
        cited = {int(m.group(1)) for span in prose(path)
                 for m in ARTICLE.finditer(SPAN.sub(" ", span))}
        for num in sorted(cited - live - reserved):
            problems.append(f"{path.relative_to(ROOT)}: A{num} is cited and is no Article, "
                            "live or reserved")
    return problems


def normalise(text):
    """Normalize text for quotation matching by folding case, quotes, and typography.

    Parameters:
        text (str): Raw quotation or source text.

    Returns:
        str: Normalized lowercase text with typography and formatting stripped.
    """
    text = flat(text.replace("’", "'").replace("‘", "'")  # noqa: RUF001  # reason: normalising unicode smart quotes to ascii quotes
                .replace("“", '"').replace("”", '"'))
    return re.sub(r"[`*_]", "", text).lower()


def entry_text(cite, charter):
    """Retrieve the complete normalized text of a Decision Record or Article entry.

    Parameters:
        cite (str): Citation identifier (`DR-nnn` or `An`).
        charter (dict[int, dict]): Charter article definitions indexed by article number.

    Returns:
        str | None: Normalized concatenated text of all entry scalars, or None if not found.
    """
    if cite.startswith("DR-"):
        path = META / "assertions" / "decisions" / f"{cite}.yaml"
        if not path.is_file():
            return None
        try:
            return normalise(" ".join(scalars(yaml.safe_load(path.read_text()))))
        except yaml.YAMLError:
            return None
    article = charter.get(int(cite[1:]))
    if article is None:
        return None
    return normalise(" ".join(scalars(article)))


# What may stand between a citation and the words attributed to it: almost
# nothing. `DR-043's step read "..."` puts a noun in the gap and thereby
# attributes the words to a step that entry changed rather than to the entry,
# and a reader who opens that entry is right not to find them there — the shape
# solorepo's DR-044 uses of its predecessor. The claim is un-dereferenceable
# too, and it is not this check's: a check that tests something other than what
# it says it tests is worse than one that is narrow.
SUBJECT = r",?(?:\s+(?:which|itself|already|also|still|then|only|here|now|"
SUBJECT += r"explicitly|expressly|plainly)){0,2}\s*"
# A quotation and the entry it is attributed to, in the two orders prose puts
# them: the citation first and the quotation after it, or the quotation first
# and the attribution behind it. Twelve characters at least, because a quoted
# word is a term being used and not a claim being sourced.
QUOTED = (re.compile(rf"(?P<cite>{CITE}){SUBJECT}\b(?:{SAYS})\b[^\"\n]{{0,20}}"
                     rf"\"(?P<quote>[^\"\n]{{12,}})\""),
          re.compile(rf"\"(?P<quote>[^\"\n]{{12,}})\"[^\"\n]{{0,20}}?\b(?:{SAYS})\b"
                     rf"{SUBJECT}(?P<cite>{CITE})\b"))
ELISION = re.compile(r"…|\.\.\.|\[[^\]]*\]")


@check("quoted claims")
def quoted_claims():
    """Validate that quotations attributed to an Article or Decision appear in that entry.

    Matches attributed quotations in prose against the normalized text of cited entries,
    accounting for elisions and bracketed interpolations.

    Returns:
        list[str]: Validation problem messages for unattributed or mismatched quotations.

    A quotation attributed to an entry that does not exist is passed over
    rather than reported: `cited decisions` and `cited articles` own the
    citation that names nothing, and reporting it twice reports it twice.
    """
    charter = {int(a["id"].rsplit("/", 1)[-1]): a for a in (yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    ).get("articles") or []}
    problems = []
    for path in durable(copied_files()):
        for span in prose(path):
            for pattern in QUOTED:
                for m in pattern.finditer(span):
                    entry = entry_text(m["cite"], charter)
                    if entry is None:
                        continue
                    claimed = [part.strip(" ,.;:—-")
                               for part in ELISION.split(normalise(m["quote"]))]
                    missing = [part for part in claimed
                               if len(part) >= 8 and part not in entry]
                    if missing:
                        problems.append(
                            f"{path.relative_to(ROOT)}: \"{missing[0]}\" is attributed to "
                            f"{m['cite']}, which does not contain it")
    return problems


# A relation between two entries, and the slot that is the only place it is
# recorded. `superseded_by` is checked from either end: where a later entry
# killed part of an earlier one the schema puts the link on the successor's
# `supersedes` and leaves `superseded_by` empty, so a prose sentence in the
# passive is answered by either slot.
RELATIONS = {
    "supersedes": ("supersedes", "Decision", False),
    "supersede": ("supersedes", "Decision", False),
    "superseding": ("supersedes", "Decision", False),
    "superseded by": ("superseded_by", "Decision", True),
    "applies": ("applies", "Article", False),
    "apply": ("applies", "Article", False),
    "departs from": ("departs_from", "Article", False),
    "depart from": ("departs_from", "Article", False),
    "departing from": ("departs_from", "Article", False),
}
STATED = re.compile(rf"(?P<subject>{CITE})(?P<before>{NEAREST})"
                    rf"\b(?P<word>{'|'.join(sorted(RELATIONS, key=len, reverse=True))})\b"
                    rf"(?P<after>{GAP})(?P<object>{CITE})\b", re.I)


@check("stated relations")
def stated_relations(index):
    """Validate that semantic relationships between entries stated in prose match assertion slots.

    Checks indicative statements using relational verbs (`supersedes`, `applies`, `departs_from`)
    against explicit relation slots in Decision Record definitions (solorepo's DR-175).

    Parameters:
        index (dict): LinkML model index mapping URI identifiers to entity tuples.

    Returns:
        list[str]: Validation problem messages for relations stated in prose but unset in the model.
    """
    problems = []
    decisions = {ident.rsplit("/", 1)[-1]: obj
                 for ident, (cls, obj, _) in index.items() if cls == "Decision"}
    if not decisions:
        return []
    for path in durable(copied_files()):
        for span in prose(path):
            for m in STATED.finditer(span.replace("`", "")):
                slot, wants, either = RELATIONS[m["word"].lower()]
                entry = decisions.get(m["subject"].removeprefix("DR-"))
                target = ("work:decision/" + m["object"].removeprefix("DR-") if wants == "Decision"
                          else "work:article/" + m["object"].removeprefix("A"))
                if entry is None or not m["object"].startswith("DR-" if wants == "Decision" else "A"):
                    continue
                if HEDGED.search(m["before"]) or HEDGED.search(m["after"]):
                    continue
                held = [entry.get(slot)] if slot == "superseded_by" else list(entry.get(slot) or [])
                if either:
                    other = decisions.get(m["object"].removeprefix("DR-")) or {}
                    held += list(other.get("supersedes") or [])
                    target = [target, "work:decision/" + m["subject"].removeprefix("DR-")]
                if not set(held) & set(target if either else [target]):
                    problems.append(
                        f"{path.relative_to(ROOT)}: \"{flat(m.group(0))}\" is a relation stated in "
                        f"prose, and {m['subject']}'s `{slot}` does not name it; a relation here "
                        "is a slot")
    return problems


# A path and a line, cited as one code span, which is the form a reviewer writes
# a precedent in. Anchored to the span so that `see foo.py:1` is prose about a
# file rather than a claim about a line.
PATH_LINE = re.compile(r"`(?P<path>[^`\s:]*[./][^`\s:]*):(?P<line>\d+)`")


@check("path and line claims")
def path_and_line_claims():
    """Validate that `path:line` citations point to existing lines containing adjacent code spans.

    Ensures that file line references cited beside code snippets in prose exist and contain
    the referenced tokens.

    Returns:
        list[str]: Validation problem messages for nonexistent paths, out-of-range lines,
        or mismatched line contents.
    """
    problems = []
    for path in durable(copied_files()):
        rel = path.relative_to(ROOT)
        for span in prose(path):
            for m in PATH_LINE.finditer(span):
                target = ROOT / m["path"]
                if not target.is_file():
                    problems.append(f"{rel}: {m.group(0)} names no file")
                    continue
                try:
                    lines = target.read_text().splitlines()
                except (UnicodeDecodeError, OSError):
                    continue
                number = int(m["line"])
                if not 1 <= number <= len(lines):
                    problems.append(f"{rel}: {m.group(0)} cites a line of a file "
                                    f"with {len(lines)}")
                    continue
                after = SPAN.findall(span[m.end():m.end() + 60].split(". ")[0])[:1]
                back = span[max(0, m.start() - 60):m.start()].rsplit(". ")[-1]
                if span[:m.start() - len(back)].count("`") % 2:
                    back = back.partition("`")[2]
                before = SPAN.findall(back)[-1:]
                near = [s for s in (s.strip("` ") for s in after + before) if s]
                if near and not any(s in lines[number - 1] for s in near):
                    problems.append(
                        f"{rel}: {m.group(0)} is cited beside "
                        + ", ".join(f"`{s}`" for s in near)
                        + f", and line {number} reads `{lines[number - 1].strip()}`")
    return problems


@check("enacting citations")
def enacting_citations(index):
    """Validate that files named in Decision `enacted_in` slots cite at least one enacting entry.

    Enforces bidirectional consistency between Decision enactment metadata and the citations
    carried in durable file prose (solorepo's DR-131).

    Parameters:
        index (dict): LinkML model index mapping URI identifiers to entity tuples.

    Returns:
        list[str]: Validation problem messages for files where citations disagree with enactment slots.

    Only an `enacted_in` slot resolving to an Artifact contributes a path. A
    slot naming nothing is `unresolved references`' finding, and one resolving
    to something other than an Artifact is the schema's; either way there is no
    path here for a citation to be held against.
    """
    known = {d.rsplit("/", 1)[-1] for d, (cls, _, _) in index.items() if cls == "Decision"}
    if not known:
        return []
    home = SCAFFOLD in index
    named = {}
    for ident, (cls, obj, _) in index.items():
        if cls != "Decision":
            continue
        for ref in obj.get("enacted_in") or []:
            target = index.get(ref)
            if target and target[0] == "Artifact":
                named.setdefault(target[1]["path"], set()).add(ident.rsplit("/", 1)[-1])

    def listed(numbers):
        shown = sorted(numbers)
        return ", ".join(f"DR-{n}" for n in shown[:6]) + (
            f" and {len(shown) - 6} more" if len(shown) > 6 else "")

    problems = []
    for path in durable(copied_files()):
        rel = str(path.relative_to(ROOT))
        if rel not in named:
            continue
        try:
            text = FENCED.sub("", path.read_text())
        except (UnicodeDecodeError, OSError):
            continue
        foreign = {num for m in FOREIGN.finditer(text) for num in DR.findall(m.group())}
        bare = set() if TEMPLATE in path.parents else set(DR.findall(FOREIGN.sub("", text)))
        cited = (bare | (foreign if home else set())) & known
        if cited and not cited & named[rel]:
            problems.append(f"{rel}: cites {listed(cited)}, and the record names it in "
                            f"{listed(named[rel])}; a file the record names cites an entry "
                            "that names it, or the entry that does names the file")
    return problems


@check("inherited citations")
def inherited_citations():
    """Validate that Issue references in files inherited by portfolios use qualified citations.

    Enforces that Issue citations in files copied during specialization use `solorepo's #n`
    rather than bare `#n` syntax to prevent collision with portfolio issue trackers (solorepo's DR-132).

    Returns:
        list[str]: Validation problem messages for bare Issue citations in inherited files.
    """
    problems = []
    issue, foreign = issue_citation()
    for path in sorted(copied_files()):
        if path.is_symlink() or not path.is_file() or ".git" in path.parts:
            continue
        try:
            text = FENCED.sub("", path.read_text())
        except (UnicodeDecodeError, OSError):
            continue
        for num in sorted(set(issue.findall(foreign.sub("", text))), key=int):
            problems.append(f"{path.relative_to(ROOT)}: #{num} is cited bare in a file a "
                            "portfolio inherits, where it will come to mean an Issue of "
                            "the portfolio's; cite it as solorepo's")
    return problems
