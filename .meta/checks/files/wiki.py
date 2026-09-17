"""The wiki: wikilinks that resolve, a lead paragraph that defines its concept, and one page per term of the Ubiquitous Language (solorepo's DR-187, solorepo's DR-190).
"""
import pathlib
import re

import yaml

from collect import (
    ROOT,
    check,
)
from files import history, markdown, sources

WIKILINK = re.compile(r"\[\[(.*?)\]\]")


LEAD_COPULA = re.compile(
    r"^\*\*(?:`(?P<backticked>[^`]+)`|(?P<plain>[^*]+))\*\*\s+"
    r"(?P<copula>is|are|was|were|refers to|serves as|organizes|provides|names|represents)\b",
    re.IGNORECASE,
)


def _strip_fenced(text: str) -> str:
    """Strips fenced code blocks and inline backticks while preserving line count."""
    return markdown.FENCED.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _build_ontology_lookup(index):
    """Builds a case-insensitive lookup set of valid ontology entities from index.

    Every spelling a writer reasonably reaches for is a key: the full
    identifier and its tail, the preferred label, the name and the alternative
    labels, each also slugified. A Decision is additionally keyed by its number
    in the three forms citations take — `dr-85`, `dr-085` and `85` — and an
    Article by `a8` and `8`.
    """
    lookup = set()
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


def _build_wiki_files_map(file_list):
    """Builds lookup mapping of wiki files from a list of paths.

    Keyed by `(context, slug)`, both lowercased: a page under `wiki/<ctx>/` is
    keyed by its directory, and a page directly under `wiki/` by the empty
    context.
    """
    wiki_map = {}
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


def _resolves_wikilink(target: str, source_path: pathlib.Path, wiki_map: dict, ontology_lookup: set) -> bool:
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
    norm_slug = norm.replace(" ", "-").replace("_", "-")
    if norm in ontology_lookup or norm_slug in ontology_lookup:
        return True

    for prefix in ("work:", "ddd:"):
        if (prefix + norm) in ontology_lookup or (prefix + norm_slug) in ontology_lookup:
            return True

    test_target = clean
    if test_target.lower().startswith("wiki/"):
        test_target = test_target[5:]

    if "/" in test_target:
        ctx_part, slug_part = test_target.split("/", 1)
        ctx_k = ctx_part.lower().replace(" ", "-").replace("_", "-")
        slug_k = slug_part.lower().replace(" ", "-").replace("_", "-").removesuffix(".md")
        if (ctx_k, slug_k) in wiki_map:
            return True
        rel_candidate = source_path.parent / f"{test_target}.md"
        if rel_candidate.is_file() or (ROOT / "wiki" / f"{test_target}.md").is_file():
            return True
    else:
        try:
            rel = source_path.relative_to(ROOT)
        except ValueError:
            rel = source_path
        if len(rel.parts) >= 3 and rel.parts[0] == "wiki":
            current_ctx = rel.parts[1].lower()
            if (current_ctx, norm_slug) in wiki_map:
                return True
        if ("solorepo", norm_slug) in wiki_map:
            return True
        if ("", norm_slug) in wiki_map:
            return True
        if any(s == norm_slug for (c, s) in wiki_map):
            return True

    return False


@check("wikilinks")
def wikilinks(index, md_files=None):
    """Internal concept references use closed-world wikilinks (A2, solorepo's DR-185).

    Every wikilink ([[concept]] or scoped [[context/concept]]) must resolve
    deterministically against either an existing wiki page in the repository
    (under wiki/<context>/<slug>.md) or a minted concept, discipline, decision,
    or article in the repository index. A reference to an unregistered term or
    missing page is red and fails verification.
    """
    problems = []
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


@check("wiki lead paragraphs")
def wiki_lead_paragraphs(index, md_files=None):
    """Every wiki page opens with a bold copular lead definition (MOS:LEAD) concurring with the vocabulary (A2, solorepo's DR-185, solorepo's DR-187).

    Maintainer-facing exposition under wiki/<context>/ (excluding index READMEs)
    must open with a top-level heading (# <Title>) and a lead sentence defining
    the subject in bold copular phrasing (**Subject** is a ...). When the subject
    corresponds to a minted concept or discipline in the index, the lead subject
    must concur with the minted preferred label.
    """
    problems = []
    tree_files = md_files if md_files is not None else sources.tree()

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
            or len(rel.parts) < 2
            or rel.parts[0] != "wiki"
            or rel.name == "README.md"
        ):
            continue
        try:
            raw_text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        lines = [line.strip() for line in history.without_comments(raw_text).splitlines()]
        while lines and not lines[0]:
            lines.pop(0)

        # Allow optional YAML frontmatter block (solorepo's DR-187)
        if lines and lines[0] == "---":
            lines.pop(0)
            while lines and lines[0] != "---":
                lines.pop(0)
            if lines and lines[0] == "---":
                lines.pop(0)
            while lines and not lines[0]:
                lines.pop(0)

        if not lines or not lines[0].startswith("# "):
            problems.append(f"{rel}: must begin with a top-level heading (# <Title>)")
            continue

        title = lines[0][2:].strip()
        title_clean = title.strip("`").strip()

        lines.pop(0)
        while lines and not lines[0]:
            lines.pop(0)

        if not lines:
            problems.append(f"{rel}: empty wiki page after title")
            continue

        lead_line = lines[0]
        match = LEAD_COPULA.match(lead_line)
        if not match:
            problems.append(
                f"{rel}: first paragraph must open with bold copular definition "
                f"(MOS:LEAD: '**Subject** is ...')"
            )
            continue

        subject = (match.group("backticked") or match.group("plain") or "").strip()
        subject_clean = subject.strip("`").strip()
        if subject_clean.lower() != title_clean.lower():
            problems.append(
                f"{rel}: lead bold subject '{subject}' does not match title '{title}'"
            )
            continue

        slug = path.stem.lower()
        concept_entry = (
            index.get(f"work:concept/{slug}")
            or index.get(f"work:discipline/{slug}")
            or index.get(f"ddd:concept/{slug}")
        )
        if concept_entry:
            pref = concept_entry[1].get("pref_label") or concept_entry[1].get("name")
            if pref and pref.strip("`").strip().lower() != subject_clean.lower():
                problems.append(
                    f"{rel}: subject '{subject}' disagrees with minted label '{pref}' in {concept_entry[2]}"
                )

    return problems


@check("ubiquitous language wiki parity")
def ubiquitous_language_wiki_parity(index, md_files=None):
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
    problems = []
    tree_files = md_files if md_files is not None else sources.tree()
    wiki_map = _build_wiki_files_map(tree_files)

    domain_vocab = ROOT / ".meta" / "assertions" / "domain_vocabulary.yaml"
    if domain_vocab.is_file():
        try:
            data = yaml.safe_load(domain_vocab.read_text(encoding="utf-8")) or {}
            for item in data.get("concept_set") or []:
                item_id = str(item.get("id") or "")
                slug = item_id.rsplit("/", 1)[-1].lower()
                found = any(s == slug for (c, s) in wiki_map if c != "solorepo")
                if not found:
                    problems.append(
                        f"domain_vocabulary.yaml: concept '{item_id}' has no corresponding wiki page (solorepo's DR-190)"
                    )
        except Exception as e:
            problems.append(f"domain_vocabulary.yaml: failed to parse for parity check: {e}")

    for (ctx, slug), path in wiki_map.items():
        if not ctx or ctx == "solorepo" or slug == "readme":
            continue
        concept_ident = f"ddd:concept/{slug}"
        work_ident = f"work:concept/{slug}"
        if concept_ident not in index and work_ident not in index:
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path
            problems.append(
                f"{rel}: wiki page '{slug}' has no corresponding concept in vocabulary schema (solorepo's DR-190)"
            )

    for (ctx, slug), path in wiki_map.items():
        if ctx != "solorepo" or slug == "readme":
            continue
        concept_ident = f"work:concept/{slug}"
        discipline_ident = f"work:discipline/{slug}"
        if concept_ident not in index and discipline_ident not in index:
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path
            problems.append(
                f"{rel}: solorepo wiki page '{slug}' has no corresponding concept or discipline in index (solorepo's DR-190)"
            )

    return problems
