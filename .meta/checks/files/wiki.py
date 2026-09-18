"""The wiki: wikilinks that resolve, a lead paragraph that defines its concept, and one page per term of the Ubiquitous Language (solorepo's DR-187, solorepo's DR-190).
"""
import pathlib
import re
from collections.abc import Sequence

import yaml

from checks.collect import (
    ROOT,
    Index,
    check,
)
from checks.files import history, sources
from checks.files.markdown import FENCED

WIKILINK = re.compile(r"\[\[(.*?)\]\]")


LEAD_COPULA = re.compile(
    r"^\*\*(?:`(?P<backticked>[^`]+)`|(?P<plain>[^*]+))\*\*\s+"
    r"(?P<copula>is|are|was|were|refers to|serves as|organizes|provides|names|represents)\b",
    re.IGNORECASE,
)


def _strip_fenced(text: str) -> str:
    """Strips fenced code blocks and inline backticks while preserving line count."""
    return str(FENCED.sub(lambda m: "\n" * m.group(0).count("\n"), text))


def _build_ontology_lookup(index: Index) -> set[str]:
    """Builds a case-insensitive lookup set of valid ontology entities from index.

    Every spelling a writer reasonably reaches for is a key: the full
    identifier and its tail, the preferred label, the name and the alternative
    labels, each also slugified. A Decision is additionally keyed by its number
    in the three forms citations take — `dr-85`, `dr-085` and `85` — and an
    Article by `a8` and `8`.
    """
    lookup: set[str] = set()
    for ident, (cls, obj, _) in index.items():
        lookup.add(ident.lower())
        tail = ident.rsplit("/", 1)[-1].lower()
        lookup.add(tail)
        if cls == "Decision" or ident.startswith("work:decision/"):
            num = tail.lstrip("0") or "0"
            lookup.add(f"dr-{num}".lower())
            if num.isdigit():
                lookup.add(f"dr-{int(num):03d}".lower())
            lookup.add(num)
        if cls == "Article" or ident.startswith("work:article/"):
            lookup.add(f"a{tail}".lower())
            lookup.add(tail)
        pref = obj.get("pref_label")
        if pref:
            lookup.add(pref.lower())
            lookup.add(pref.lower().replace(" ", "-").replace("_", "-"))
        name = obj.get("name")
        if name:
            lookup.add(name.lower())
            lookup.add(name.lower().replace(" ", "-").replace("_", "-"))
        for alt in obj.get("alt_labels") or []:
            lookup.add(alt.lower())
            lookup.add(alt.lower().replace(" ", "-").replace("_", "-"))
    return lookup


def _build_wiki_files_map(
        file_list: Sequence[pathlib.Path]) -> dict[tuple[str, str], pathlib.Path]:
    """Builds lookup mapping of wiki files from a list of paths.

    Keyed by `(context, slug)`, both lowercased: a page under `wiki/<ctx>/` is
    keyed by its directory, and a page directly under `wiki/` by the empty
    context.
    """
    wiki_map: dict[tuple[str, str], pathlib.Path] = {}
    for f in file_list:
        try:
            rel = f.relative_to(ROOT)
        except ValueError:
            rel = f
        if len(rel.parts) >= 2 and rel.parts[0] == "wiki" and rel.suffix == ".md":
            if len(rel.parts) == 3:
                ctx = rel.parts[1].lower()
                stem = rel.stem.lower()
                wiki_map.setdefault((ctx, stem), f)
            elif len(rel.parts) == 2:
                wiki_map.setdefault(("", rel.stem.lower()), f)
    return wiki_map


def _rel(path: pathlib.Path) -> pathlib.Path:
    """`path` relative to the repository root, or as given where it is not under it."""
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def _slugged(text: str) -> str:
    """`text` lowercased with spaces and underscores as hyphens, which is how the wiki map and the ontology lookup are keyed."""
    return text.lower().replace(" ", "-").replace("_", "-")


def _in_ontology(norm: str, norm_slug: str, ontology_lookup: set[str]) -> bool:
    """Whether the ontology answers `norm` or its slug, bare or under either CURIE prefix."""
    return any(candidate in ontology_lookup
               for prefix in ("", "work:", "ddd:")
               for candidate in (prefix + norm, prefix + norm_slug))


def _scoped_page(target: str, source_path: pathlib.Path, wiki_map: dict[tuple[str, str], pathlib.Path]) -> bool:
    """Whether a target naming its context, `<context>/<slug>`, is a page of that context or a file relative to the page that wrote it."""
    ctx_part, slug_part = target.split("/", 1)
    if (_slugged(ctx_part), _slugged(slug_part).removesuffix(".md")) in wiki_map:
        return True
    return (source_path.parent / f"{target}.md").is_file() or (ROOT / "wiki" / f"{target}.md").is_file()


def _unscoped_page(norm_slug: str, source_path: pathlib.Path, wiki_map: dict[tuple[str, str], pathlib.Path]) -> bool:
    """Whether a bare slug is a page in the writing page's own context, the scaffold's, the wiki's root, or any context at all."""
    rel = _rel(source_path)
    if len(rel.parts) >= 3 and rel.parts[0] == "wiki" and (rel.parts[1].lower(), norm_slug) in wiki_map:
        return True
    if ("solorepo", norm_slug) in wiki_map or ("", norm_slug) in wiki_map:
        return True
    return any(s == norm_slug for (c, s) in wiki_map)


def _resolves_wikilink(target: str, source_path: pathlib.Path, wiki_map: dict[tuple[str, str], pathlib.Path],
                       ontology_lookup: set[str]) -> bool:
    """Determines whether a wikilink target resolves to a wiki page or ontology entity.

    The ontology answers first, by the target and by its slug, and then by the
    same two under each CURIE prefix. What it does not answer is looked for
    among the wiki pages. A target naming its context — `solorepo/knowledge-
    management`, with or without a leading `wiki/` — is resolved against that
    context and then as a path relative to the page that wrote it. A target
    naming none is tried in the page's own context, then in the scaffold's,
    then at the root of the wiki, and last in any context at all, so a link
    written before the page found its folder still resolves.
    """
    clean = target.strip()
    if not clean:
        return False
    norm = clean.lower()
    norm_slug = _slugged(norm)
    if _in_ontology(norm, norm_slug, ontology_lookup):
        return True
    test_target = clean[5:] if clean.lower().startswith("wiki/") else clean
    if "/" in test_target:
        return _scoped_page(test_target, source_path, wiki_map)
    return _unscoped_page(norm_slug, source_path, wiki_map)



@check("wikilinks")
def wikilinks(index: Index, md_files: Sequence[pathlib.Path] | None = None) -> list[str]:
    """Internal concept references use closed-world wikilinks (A2, solorepo's DR-185).

    Every wikilink ([[concept]] or scoped [[context/concept]]) must resolve
    deterministically against either an existing wiki page in the repository
    (under wiki/<context>/<slug>.md) or a minted concept, discipline, decision,
    or article in the repository index. A reference to an unregistered term or
    missing page is red and fails verification.
    """
    problems: list[str] = []
    tree_files = md_files if md_files is not None else sources.tree()
    wiki_map = _build_wiki_files_map(tree_files)
    ontology_lookup = _build_ontology_lookup(index)

    for path in tree_files:
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            rel = path
        if (
            rel.suffix != ".md"
            or path.is_symlink()
            or "template" in rel.parts
            or ".git" in rel.parts
        ):
            continue
        try:
            raw_text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        stripped = _strip_fenced(raw_text)
        for line_no, line in enumerate(stripped.splitlines(), 1):
            for match in WIKILINK.finditer(line):
                raw = match.group(1).strip()
                if not raw:
                    continue
                target = raw.split("|", 1)[0].split("#", 1)[0].strip()
                if not target:
                    continue
                if not _resolves_wikilink(target, path, wiki_map, ontology_lookup):
                    problems.append(
                        f"{rel}:{line_no}: [[{raw}]] resolves to nothing; "
                        f"closed-world wikilinks must name an existing wiki page or minted concept"
                    )
    return problems


def _is_wiki_page(path: pathlib.Path, rel: pathlib.Path) -> bool:
    """Whether `path` is a page the lead rule holds: markdown under `wiki/`, not a symlink, not a template, not an index README."""
    return not (rel.suffix != ".md" or path.is_symlink() or "template" in rel.parts
                or ".git" in rel.parts or len(rel.parts) < 2 or rel.parts[0] != "wiki"
                or rel.name == "README.md")


def _past_frontmatter(lines: list[str]) -> list[str]:
    """`lines` from the first line after any leading blank lines and any YAML frontmatter block (solorepo's DR-187)."""
    while lines and not lines[0]:
        lines.pop(0)
    if lines and lines[0] == "---":
        lines.pop(0)
        while lines and lines[0] != "---":
            lines.pop(0)
        if lines and lines[0] == "---":
            lines.pop(0)
        while lines and not lines[0]:
            lines.pop(0)
    return lines


def _lead_problem(rel: pathlib.Path, lines: list[str], index: Index, slug: str) -> str | None:
    """Why a page's lead fails MOS:LEAD, or None: no title, nothing after it, no bold copular lead, a subject that is not the title, or one that disagrees with the minted label."""
    if not lines or not lines[0].startswith("# "):
        return f"{rel}: must begin with a top-level heading (# <Title>)"
    title = lines[0][2:].strip()
    title_clean = title.strip("`").strip()
    rest = [line for line in lines[1:] if line]
    if not rest:
        return f"{rel}: empty wiki page after title"
    match = LEAD_COPULA.match(rest[0])
    if not match:
        return (f"{rel}: first paragraph must open with bold copular definition "
                f"(MOS:LEAD: '**Subject** is ...')")
    subject = (match.group("backticked") or match.group("plain") or "").strip()
    subject_clean = subject.strip("`").strip()
    if subject_clean.lower() != title_clean.lower():
        return f"{rel}: lead bold subject '{subject}' does not match title '{title}'"
    concept_entry = (index.get(f"work:concept/{slug}") or index.get(f"work:discipline/{slug}")
                     or index.get(f"ddd:concept/{slug}"))
    if concept_entry:
        pref = concept_entry[1].get("pref_label") or concept_entry[1].get("name")
        if pref and pref.strip("`").strip().lower() != subject_clean.lower():
            return f"{rel}: subject '{subject}' disagrees with minted label '{pref}' in {concept_entry[2]}"
    return None


@check("wiki lead paragraphs")
def wiki_lead_paragraphs(index: Index,
                         md_files: Sequence[pathlib.Path] | None = None) -> list[str]:
    """Every wiki page opens with a bold copular lead definition (MOS:LEAD) concurring with the vocabulary (A2, solorepo's DR-185, solorepo's DR-187).

    Maintainer-facing exposition under wiki/<context>/ (excluding index READMEs)
    must open with a top-level heading (# <Title>) and a lead sentence defining
    the subject in bold copular phrasing (**Subject** is a ...). When the subject
    corresponds to a minted concept or discipline in the index, the lead subject
    must concur with the minted preferred label.
    """
    problems: list[str] = []
    tree_files = md_files if md_files is not None else sources.tree()
    for path in tree_files:
        rel = _rel(path)
        if not _is_wiki_page(path, rel):
            continue
        try:
            raw_text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = _past_frontmatter([line.strip() for line in history.without_comments(raw_text).splitlines()])
        problem = _lead_problem(rel, lines, index, path.stem.lower())
        if problem:
            problems.append(problem)
    return problems


def _domain_vocabulary_problems(wiki_map: dict[tuple[str, str], pathlib.Path]) -> list[str]:
    """Every concept of `domain_vocabulary.yaml` with no page outside the scaffold's context, or one problem where the file will not parse or is not the shape a concept set has."""
    domain_vocab = ROOT / ".meta" / "assertions" / "domain_vocabulary.yaml"
    if not domain_vocab.is_file():
        return []
    problems: list[str] = []
    try:
        data = yaml.safe_load(domain_vocab.read_text(encoding="utf-8")) or {}
        for item in data.get("concept_set") or []:
            item_id = str(item.get("id") or "")
            slug = item_id.rsplit("/", 1)[-1].lower()
            if not any(s == slug for (c, s) in wiki_map if c != "solorepo"):
                problems.append(f"domain_vocabulary.yaml: concept '{item_id}' has no corresponding wiki page (solorepo's DR-190)")
    except Exception as e:
        problems.append(f"domain_vocabulary.yaml: failed to parse for parity check: {e}")
    return problems


@check("ubiquitous language wiki parity")
def ubiquitous_language_wiki_parity(
        index: Index, md_files: Sequence[pathlib.Path] | None = None) -> list[str]:
    """Every concept in a Bounded Context's Ubiquitous Language has a corresponding wiki page, and vice versa (A17, solorepo's DR-184, solorepo's DR-190).

    Enforces 1:1 parity between LinkML vocabulary assertions and Knowledge Management
    wiki pages within each Bounded Context. A domain concept without a wiki page, or
    a domain wiki page without a corresponding concept entry, fails gate verification.

    Parity is read in both directions and in three passes: every domain
    vocabulary concept has its page, every page outside the scaffold's own
    context has its minted concept, and every page in the scaffold's context
    has a concept or a Discipline. The scaffold is separated because its wiki
    explains Disciplines as well as concepts, and a Discipline is not minted
    into the vocabulary.
    """
    tree_files = md_files if md_files is not None else sources.tree()
    wiki_map = _build_wiki_files_map(tree_files)
    problems = _domain_vocabulary_problems(wiki_map)
    for (ctx, slug), path in wiki_map.items():
        if not ctx or slug == "readme":
            continue
        if ctx == "solorepo":
            minted = (f"work:concept/{slug}", f"work:discipline/{slug}")
            missing = f"solorepo wiki page '{slug}' has no corresponding concept or discipline in index"
        else:
            minted = (f"ddd:concept/{slug}", f"work:concept/{slug}")
            missing = f"wiki page '{slug}' has no corresponding concept in vocabulary schema"
        if not any(ident in index for ident in minted):
            problems.append(f"{_rel(path)}: {missing} (solorepo's DR-190)")
    return problems
