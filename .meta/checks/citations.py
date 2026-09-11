"""What prose claims about the record, read against the record.

A12 asks three things of a citation, and the steps here resolve them in turn:
the number it names, and then the claim it goes on to make — an Article that
resolves, a quotation that appears where it is attributed, a relation that is
the slot it claims to be, and a line that reads what it is cited for.

The regular expressions below are a small grammar, and the commentary on each
is the design: what may stand in a gap, why a match is lazy, and which innocent
sentence a wider pattern would catch. They are gathered here so that a reader
amending one meets the rest, and so that a reader who came for something else
does not (solorepo's DR-150).
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
    """The same two, one sequence over: an Issue number, and the possessive run
    that names it as solorepo's, so `solorepo's #138, #140 and #142` names three.

    Read from `check_pr.py` rather than written here, because A12 hands that
    gate "the number whose target is an Issue" and leaves the rest to this one,
    so the Issue citation is split across the two gates and the predicate is not
    split with it: this file holds the owner over the copy set and that one
    resolves the number,
    and a string one of them reads as a citation and the other does not is the
    two disagreeing about what they are each holding half of (solorepo's DR-132).
    Written twice they had already drifted — this copy bounded no number and
    read `&#39;`, an HTML numeric entity, as a citation of thirty-nine, and
    neither difference was visible from either file.

    That direction, because `check_pr.py` imports the standard library alone
    and this one needs LinkML: it can be read from here and not the reverse.
    Importing runs nothing — everything it does is under `main()` — and reaches
    no network, which is the property that lets this check stay offline.
    """
    module = load_check_pr()
    return module.ISSUE, module.FOREIGN


def load_timing():
    """`timing.py` as a module: the runtime screen, read rather than run.

    Same bargain as `load_check_pr` below and for the same reason — importing
    runs nothing and reaches no network, everything it does is under `main()`
    — which is what lets the probe below exercise its arithmetic without a
    token or a run to read.
    """
    from importlib.machinery import SourceFileLoader
    import importlib.util

    loader = SourceFileLoader("timing", str(META / "timing.py"))
    spec = importlib.util.spec_from_loader("timing", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def load_reading_pass():
    """`reading_pass.py` as a module: the coder's falsifier, read rather than run.

    The same bargain a third time (solorepo's DR-165). This one is a step of
    `coder.yml` and runs nowhere else, so the only way its predicate is exercised
    before a run depends on it is a probe holding execution files up to it —
    which needs the module and not the command, since the command's whole answer
    is an exit status.
    """
    from importlib.machinery import SourceFileLoader
    import importlib.util

    loader = SourceFileLoader("reading_pass", str(META / "reading_pass.py"))
    spec = importlib.util.spec_from_loader("reading_pass", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def load_check_pr():
    """`check_pr.py` as a module: the pull request gate, read rather than run.

    The loader the channel's programs get, for the one file beside them that is
    a program too. Importing runs nothing and reaches no network — everything
    it does is under `main()` — which is what lets a check read its patterns and
    a probe stand GitHub in behind them.
    """
    from importlib.machinery import SourceFileLoader
    import importlib.util

    loader = SourceFileLoader("check_pr", str(META / "check_pr.py"))
    spec = importlib.util.spec_from_loader("check_pr", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def copied_files():
    """What Specialization copies into a portfolio, as paths.

    One set, so that the checks holding what a copied file owes cannot disagree
    about which files those are: a copied file is copied whatever the check
    reading it, and a second scope written out beside this one would be a second
    answer to the same question.

    `justfile` is not on the copy list: `render.py` writes it into a portfolio
    from its own literals, which is the same arrival by another door.
    """
    copied = {ROOT / "justfile"}
    for token in inherited():
        base = ROOT / token if (ROOT / token).exists() else META / token
        copied.update([base] if base.is_file() else base.rglob("*") if base.is_dir() else [])
    return copied


def durable(copied):
    """The files a citation is durable in: every page, every file a portfolio
    inherits, the seed, and the assertions.

    One set for the six checks in this file, because a citation is a citation
    wherever it was typed, and checks that each chose their own scope would
    disagree about which files A12 covers. The reasons for the set are `cited
    decisions`'s, which drew it: a `rationale` block is a paragraph a reader
    reaches directly, and a docstring in a file a portfolio copies is the prose
    a reader of that file reaches first (solorepo's DR-124).

    One set of files, not one text. `cited decisions` and `enacting citations`
    read each of them as text; the four below read a document's scalars where it
    has them, for the reason `prose` gives, so a citation written in a YAML
    comment has its number resolved and its claim not. Two checks of A12 are
    outside this set altogether. `inherited citations` reads `copied_files`
    unwrapped, because what a portfolio inherits is the whole of its question and
    the pages and the seed are not copied. And `cited issues`, the eighth, scans
    the assertions from `check_pr.py`, being in a checker that holds no YAML
    parser and so cannot read the copy list this set is drawn from.
    """
    for path in tree():
        if path.is_symlink() or not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix == ".md" or path in copied or TEMPLATE in path.parents or (
                path.suffix in (".yaml", ".yml") and (META / "assertions") in path.parents):
            yield path


@check("cited decisions")
def cited_decisions(index):
    """A DR cited in prose resolves to an entry of the record it names (solorepo's DR-121).

    An Article citation is a typed reference and has been checked since the
    references check existed; a DR citation is plain text in a paragraph, and
    nothing looked at it. `roadmap.md` cited solorepo's DR-058 for a decision
    nobody wrote down, and the number stays issued and unused so that the
    citation resolves to what it is — a hole nothing here reported.

    The assertions are scanned along with the prose. A citation inside a
    `rationale` block is a paragraph that a reader reaches directly, now that the
    entry is its own file, so it is held to the same rule rather than exempted
    for being stored as YAML. So is every file a portfolio copies, whatever its
    suffix — the schemas, the workflows, the actions, and the Python, whose
    docstrings are the prose a reader of `check.py` reaches first (solorepo's DR-124) —
    because what it copies is scanned for the reason below. A code span is a
    path or a form, not a citation.

    Whose record. The Charter, the schemas, the templates and the pages rendered
    from them are copied into every portfolio, and a portfolio's record starts
    again at `DR-001` — the seed's own entry says so. A bare `DR-104` in a copied
    file is solorepo's where it was written and reads as the portfolio's on the
    day its record reaches a hundred and four: the citation that silently comes
    to mean something else, which the Charter holds worse than one that dangles,
    and which this check would pass. So a copied file cites solorepo's record as
    solorepo's, and a bare number in one fails here, where the copy is made from.
    A citation of solorepo's record resolves against this one when this
    Portfolio is solorepo, and is passed over where it is not: the record it
    names is not there to resolve against, and "cited and does not exist" keeps
    its one meaning. Under `template/` a bare number is the seed's record, which
    is the portfolio's, and resolves against that. solorepo's #114 found a portfolio red on
    thirteen of these on its first pull request.
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
# What a citation and its claim may have between them. Short, and stopped by
# every mark a claim does not run across: the sentence's own punctuation, and
# the brackets and pipes that make a link or a table cell. `decisions.md` lists
# every entry in a table, and a row whose title contains "applies" sits between
# two links to entries — a sentence to a regular expression and to nobody else.
# Lazy, so that a relation names the citation next to it on the object side:
# read greedily, a sentence of the form `X supersedes Y, and Z applies` reaches
# past its object to the last number in the sentence and reports a relation
# nobody stated. Laziness reaches no further than that, and the subject side
# needs the same thing said the other way: `finditer` returns the leftmost
# match, so the subject would be the first citation before the verb rather than
# the one the sentence attaches it to, and the scan then resumes past the object
# so the nearer citation is never tried. `Unlike X, Y applies Z` would read X's
# `applies` for a relation Y holds, and `W and Y applies Z`, with W an Article,
# would bind a subject that is no Decision and stop there. `NEAREST` is the gap
# with no citation in it, which makes the anchor the nearest citation in both
# directions.
GAP = r"[^.;:|\[\]()\n]{0,30}?"
NEAREST = rf"(?:(?!{CITE})[^.;:|\[\]()\n]){{0,30}}?"
# Attribution: the words that turn a quotation into a claim about the entry
# beside it. Deliberately not `is` or `was`, which put a quotation next to a
# citation in sentences that are not attributing it to anything.
SAYS = r"says|say|said|reads|read|states|state|stated|calls it|names it|puts it|has it|quotes"
# What is not a claim: a relation denied, or one entertained and not made.
HEDGED = re.compile(r"\b(not|never|no longer|would|could|should|might|may|cannot|"
                    r"rather than|instead of|if)\b", re.I)


def scalars(node):
    """Every string in a loaded document, keys excluded: a key is a slot name
    and the prose is what it holds."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from scalars(value)
    elif isinstance(node, list):
        for value in node:
            yield from scalars(value)


def prose(path):
    """The prose in a file, as spans no claim runs across.

    A page is one span with its fenced blocks removed. An assertion is one span
    per string scalar, because YAML's own quotation marks delimit a scalar and
    are not a quotation inside one: read as text, every entry's `name` — a
    quoted title that opens with its own number — is a quotation attributed to
    the entry it names, and the first thing this check found was itself.

    What the parser drops, these checks drop with it: a YAML comment is not a
    scalar, so a citation written in one is read by `cited decisions`, which
    takes the whole file as text, and by none of the four below. The assertions
    do carry such citations — `.meta/assertions/structure.yaml:25` is one,
    naming solorepo's DR-090 in a comment above the Project it explains.
    Closing the gap means tokenising the file to tell a comment from a `#`
    inside a scalar, and what it buys is the claim on a line whose number is
    resolved already; the narrower reading is the one taken, and is written here
    rather than left for a reader to infer from `safe_load`.

    Whitespace is flattened. A folded scalar wraps where the line ended rather
    than where the sentence did, so a quotation that crossed the fold would
    otherwise match nothing and a relation stated across it would be invisible.
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
    return re.sub(r"\s+", " ", text)


@check("cited articles")
def cited_articles():
    """Every `A<n>` cited resolves to an Article, live or reserved (solorepo's #147).

    An Article citation is a typed reference where a slot holds it, and most of
    them are not: the Charter is cited in a paragraph, a docstring, a template
    and a workflow comment, and a number nobody issued reads in all four exactly
    like one somebody did. `cited decisions` covers the same failure for the
    record and stops at `DR-`.

    A retired number resolves. The reservation is the whole of what a retirement
    leaves behind, and a citation written before it is still about something —
    which is the point `reserved article numbers` defends from the other end.

    A code span is excluded, as it is there: `` `A12` `` in a form or a path is
    the shape of a citation and not one.
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
    """A quotation and the entry it is taken from, reduced to what they say.

    Emphasis, backticks and the two shapes of quotation mark are typography: a
    quotation that adds a `*` around a word is still the words. Case goes too,
    because a sentence quoted from the middle of another is capitalised at its
    new start and nowhere else.
    """
    text = flat(text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"'))
    return re.sub(r"[`*_]", "", text).lower()


def entry_text(cite, charter):
    """Everything the entry a citation names says, as one string, or None where
    the citation names nothing here. A Decision is its file and an Article is its
    entry, every scalar of either: the first version of this enumerated an
    Article's slots and left out `falsifier`, so A12's own falsifier, quoted
    verbatim, was reported as absent from A12."""
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
    """A quotation attributed to an entry appears in that entry (solorepo's #147).

    A citation carries the claim it names (A12), and the strongest form of that
    claim is the entry's own words. It is also the form that goes wrong
    silently: quoting from memory produces a sentence the entry would have been
    happy to contain, and only opening the entry says otherwise. Three of the
    threads on solorepo's #138, #140 and #142 turned on exactly that, and each cost a
    reviewer round.

    Only an attributed quotation is checked. `SAYS` is the attribution, and it
    is what separates a claim about an entry from a quotation that merely stands
    near a citation — the Charter's own `"A9 — a seed is data, gated by
    rendering it"` is an example of the citation form, attributed to nothing,
    and passes because nothing says it was said.

    An elision is honoured: `…`, `...` and a bracketed interpolation split the
    quotation, and each side of the split is looked for on its own. So the check
    is on the words claimed rather than on their contiguity, and a quotation
    that shortens an entry honestly still passes.
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
                        continue  # `cited decisions` and `cited articles` own that
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
    """A relation stated in prose is set as the slot it names (solorepo's #147).

    A relation here is a slot and not a paragraph — the schema says so of
    `departs_from` in as many words, because a departure marked nowhere breaks
    transitive conformity silently. A sentence claiming one is therefore either
    true and redundant or false and unfalsifiable, and solorepo's #142 carried the second:
    a `supersedes` between solorepo's DR-078 and DR-079 that neither entry
    sets, which took a reviewer round to find and a reader of the record would
    never have found at all.

    Only the indicative is a claim. A relation denied, or one weighed and not
    taken — the sentence a rejected alternative is made of — is passed over,
    which `HEDGED` does by looking at the words on either side of the verb.

    The subject must be a Decision, because all four slots are a Decision's. An
    Article does not apply anything to anybody, so `A21 applies DR-092` is a
    sentence this check has no opinion about.
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
    """A `path:line` cited beside a code span reads that span on that line (solorepo's #147).

    The form is a precedent: this was decided here, and here is the line. It is
    the citation most worth having and the one that decays fastest, because the
    line number is right until anybody edits above it and nothing re-reads it
    afterwards. solorepo's #142 cited line 23 of `.meta/actions/sweep/action.yml` for
    `!cancelled()` where that line reads `always()` — the precedent was real,
    the line was not, and reading it was the reviewer's round. Written here in
    the form the check does not read, because a docstring that quoted the
    failure would be making it.

    The neighbouring span on either side counts, since prose puts the line
    before what is on it as readily as after, and either of them being on the
    line is enough. The neighbourhood stops at the sentence: a page is read
    here as one flattened span, so a window of characters alone would reach
    back into an unrelated paragraph and judge the citation against a code
    span nobody put beside it. A citation with no span in its sentence claims
    only that the file and the line exist, and is held to that.

    The look-back is cut out of the middle of a flattened span and so is not
    backtick-balanced: where the cut lands inside a code span, the surviving
    closing backtick pairs with the next opening one and the "neighbouring
    span" is the ordinary prose between two real ones. An unbalanced leading
    fragment is dropped. The forward window needs no equivalent, because it
    starts immediately after a closing backtick, so a span the window truncates
    simply fails to match and the citation is passed over.
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
    """A file the record names cites at least one entry that names it (solorepo's DR-131).

    A renumber leaves a residue nothing sees. `cited decisions` asks whether a
    cited number resolves, so an entry rebuilt under the next free number leaves
    every citation of the old one resolving — to the neighbouring entry, which
    is a citation that has silently come to mean something else and the one the
    Charter holds worse than one that dangles. Two of those went into solorepo's #152 and
    were caught by a reviewer reading, one of them in `AGENTS.md`.

    What was already in the tree was the disagreement: `decisions.md` listed the
    new entry against the file, generated from `enacted_in`, while the prose in
    the file said the old one. So the check reads the two together, and fails a
    file the record names whose citations name no entry that names it — the
    index says this file is where some rule was put, the prose says its rules
    came from somewhere else, and one of them is wrong.

    Neither half of that is a rule on its own, and the counts are why. They are
    in solorepo's DR-131's alternatives and only there: a measurement of a moving
    tree has one home, and the copy that stood here had drifted from the entry's
    before either was a day old, a rebase having moved the ground under both.
    **Every enacting entry is cited** fails in file after file, and often did so
    from the commit that added the entry: a file carries a rule, not the account
    of every entry that moved it. **Every citation's entry names this file** fails
    hundreds of sites, because a citation is ordinarily a cross-reference to
    reasoning enacted elsewhere. Neither is what the record means, and a step
    that fails hundreds of true lines is a step somebody turns off.

    So the conjunction, which is the smallest claim both halves support: where a
    file speaks about the record at all, it agrees with the index once. A file
    that cites nothing is silent rather than wrong, and a file that cites one
    naming entry among several is passed — which is what this is blind to. Of
    the two sites in solorepo's #152 it would have caught `AGENTS.md`, whose only other
    citation named another file, and not
    `template/.github/workflows/gate.yml`, which cited solorepo's DR-119, DR-120
    already. It is a floor under the residue, not a sieve for it.

    Both repairs are honest and the failure names both: cite, where the rule is
    stated, the entry that put it there; or name this file in the entry whose
    rule it actually carries. What that trades is that the first can be done
    without reading either, and the falsifier of solorepo's DR-131 says so.

    Whose citations. `cited decisions`'s rule, for its reasons: under
    `template/` a bare number is the seed's record and says nothing about this
    one, and a citation of solorepo's record counts only where this Portfolio is
    solorepo. A number that resolves to no entry is `cited decisions`'s to
    report and is passed over here, so one mistyped digit is one failure.
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
            # An `enacted_in` naming nothing is the references check's, and a
            # slot that resolves to something other than an Artifact the
            # schema's; either way there is no path here to hold to anything.
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
    """An Issue cited in a file a portfolio inherits is cited as solorepo's (solorepo's DR-132).

    The failure `cited decisions` holds for the record's numbers, one sequence
    over. A bare `#98` in `check.py` is solorepo's where it was written and
    reads as the portfolio's own on the day that portfolio's Issues reach
    ninety-eight — the citation that comes silently to mean something else,
    which is worse than one that dangles. solorepo's #114 is that failure landed once
    already, for the DR numbers, and it took a portfolio red on its first pull
    request to find.

    Only the form is held here, and that is the whole of the split solorepo's DR-132
    settled. Whether solorepo's #98 exists is a question only GitHub can answer,
    and `check.py` reaches no network — which is what makes it the gate a
    portfolio runs on a laptop and in CI with the same result. So the owner is
    checked over the copy set, and resolving the number stays with
    `check_pr.py`. That file scans the assertions, which the copy set overlaps
    in `imported/`; what it no longer does there is hold the form as well, which
    is the second answer to one question `copied_files` is a single set to
    avoid, and was a bare number in an imported assertion reported twice by two
    gates until solorepo's DR-132 drew the seam. The predicate is read from
    that file too, by `issue_citation`, so the two halves cannot part company
    about what a citation is.

    Where it is enforced, and where it is not. The copy set is the scaffold's:
    `copied_files` reads `inherited()`, which reads the Specialization
    Discipline, and a portfolio carries no Specialization Discipline. So the
    rule is enforced where the copy is made *from*, and a portfolio's own gate
    is silent on it — `copied_files()` there is `{justfile}` and this check has
    nothing to scan, exactly as `scaffold_only_paths` says of itself. A
    portfolio that types a bare `#7` into its inherited `check.py` is not caught
    by the check it inherited, and that is the cost the chosen alternative
    names, not an oversight.

    What is passed over. A code span is a path or a form, and `FENCED` strips
    it before the scan. So is a number in quotes: `"#7"` in a fixture is the
    string a probe greps its own output for, not a citation of solorepo's #7,
    and a check that reported it would be teaching the next author to rephrase
    working code. `template/` is not on the copy list — a bare number in the
    seed is the portfolio's, which is what it will be.
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
