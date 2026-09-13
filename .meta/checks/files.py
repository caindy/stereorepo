"""Invariants over the tree: what is on disk, and what two files owe each other.

Steps that read the working tree rather than the index — a placeholder that
survived, a link that resolves to nothing, a path that is the scaffold's alone,
a generated page that is behind its assertions or whose framing prose a
portfolio would not inherit, and the half the two gate workflows hold equal.
`tree()` is here because it is the tree as git sees it, which is the only list
of files the gate trusts, and `citations.py` reads prose out of it
(solorepo's DR-150).
"""
import ast
import functools
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib

import yaml

from collect import (
    META,
    ROOT,
    TEMPLATE,
    TOKEN,
    CouldNotRun,
    Found,
    Passed,
    check,
    view_for,
)


class Strict(yaml.SafeLoader):
    """A loader that notices a key written twice.

    PyYAML takes the last of a repeated key without a word, so an editing slip
    becomes a value that is right by luck rather than by construction (solorepo's DR-053). It was
    right by luck once here — a script that added `broader` to concepts that
    already had one left 29 duplicates, every pair identical, and the render was
    correct for no reason anyone had checked.
    """


_DUPLICATES = []


def _note_duplicates(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            _DUPLICATES.append((key, key_node.start_mark.line + 1))
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _note_duplicates)


@check("duplicate keys", pre=True)
def duplicate_keys():
    """Every YAML the gate reads, including the schemas and the seed — and the
    seeded workflow, whose one typo `safe_load` will not report is this one: a
    second `steps:` under a job parses, the last wins, and the block that
    checks out the tree is dropped without a word. `.yml` under `.meta/` too,
    since solorepo's DR-120 put the composite actions there: a second `steps:` in the
    sweep's action takes the publish out of the sweep, and the two workflow
    stubs stay identical, so nothing else would say (solorepo's #129)."""
    problems = []
    for path in sorted([*META.rglob("*.yaml"), *META.rglob("*.yml"),
                        *TEMPLATE.rglob("*.yaml"), *TEMPLATE.rglob("*.yml")]):
        _DUPLICATES.clear()
        try:
            yaml.load(path.read_text(), Loader=Strict)
        except yaml.YAMLError:
            continue  # `template parses` owns malformed documents.
        problems += [f"{path.relative_to(ROOT)}:{line} '{key}' written twice"
                     for key, line in _DUPLICATES]
    return problems


def _template_files():
    if not TEMPLATE.is_dir():
        return []
    return [(f, ROOT / f.relative_to(TEMPLATE)) for f in sorted(TEMPLATE.rglob("*")) if f.is_file()]


def tree():
    """Every file git would commit or is not ignoring, or every file at all
    where there is no git to ask."""
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others",
                             "--exclude-standard", "-z"], capture_output=True, text=True)
    if listed.returncode:
        return sorted(ROOT.rglob("*"))
    return sorted(ROOT / name for name in listed.stdout.split("\0") if name)


@check("surviving placeholders")
def surviving_placeholders():
    """No template token survives anywhere outside `template/` (solorepo's DR-034).

    Scanning only the files `template/` shadows was exact and also useless:
    Specialization deletes `template/` before running the gate, so by the time
    the check ran there was nothing left to compare against and it passed
    vacuously. Scanning everything else keeps it alive in a portfolio, where it
    is the only thing standing between a half-filled skeleton and a first commit.

    The cost is that prose here may not spell a token literally. That is cheap,
    and a literal token outside `template/` is a defect in any case.

    "Everything" is the tree as git sees it: tracked files and untracked ones
    it does not ignore. A build directory is not the tree — rustc writes a
    marker of exactly this shape into every dependency file under `target/`,
    and a scan that walked in there failed the gate for having built the Rust
    seed.
    """
    problems = []
    for path in tree():
        if path.is_symlink() or not path.is_file() \
                or TEMPLATE in path.parents or ".git" in path.parts:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        found = sorted(set(TOKEN.findall(text)))
        if found:
            problems.append(f"{path.relative_to(ROOT)}: {', '.join(found)} was never filled in")
    return problems


@check("template parses")
def template_parses(views):
    """The template is data and is not linted in place. It is checked by filling
    it in and testing the result, which is the only version anyone runs.

    A `.yml` here is a workflow, not an assertion: nothing in the scaffold ever
    loads it, so it is parsed and no further. A container would reject it, and
    the alternative to parsing it is that a portfolio's first CI run is where a
    typo in it is found.
    """
    problems = []
    for src, _ in _template_files():
        if src.suffix not in (".yaml", ".yml"):
            continue
        filled = TOKEN.sub("placeholder", src.read_text())
        rel = src.relative_to(ROOT)
        try:
            data = yaml.safe_load(filled)
        except yaml.YAMLError as exc:
            problems.append(f"{rel}: does not parse once filled in — {exc}")
            continue
        if not data or src.suffix == ".yml":
            continue
        sv, _ = view_for(data, views)
        if sv is None:
            problems.append(f"{rel}: no container accepts {sorted(data)}")
    return problems


LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCED = re.compile(r"```.*?```|`[^`\n]*`", re.S)


@check("markdown links")
def markdown_links():
    """A relative link in a page resolves to something in the tree (solorepo's #45).

    A DR cited in prose has been checked since one dangled for a day; a markdown
    link is the same failure with more syntax, and the audit solorepo's DR-036 recorded
    found those by hand. `schemas.md` pointed at `decisions/DR-003.md` for as
    long as the record had lived somewhere else, and nothing objected.

    Resolution is against the tree as git sees it, not the filesystem: macOS
    would find `Readme.md` where the runner in CI would not. `template/` is
    exempt, because its pages link to the pages Specialization renders, which
    do not exist until it has run. Fenced and inline code is stripped first,
    since a form showing a link is not making one.
    """
    problems = []
    files = {os.path.normpath(str(f)) for f in tree()}
    for path in tree():
        if path.suffix != ".md" or path.is_symlink() \
                or TEMPLATE in path.parents or ".git" in path.parts:
            continue
        try:
            text = FENCED.sub("", path.read_text())
        except (UnicodeDecodeError, OSError):
            continue
        for target in LINK.findall(text):
            if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = os.path.normpath(str(path.parent / target))
            if resolved not in files and not pathlib.Path(resolved).is_dir():
                problems.append(f"{path.relative_to(ROOT)}: [{target}] resolves to nothing")
    return problems


WIKILINK = re.compile(r"\[\[(.*?)\]\]")
LEAD_COPULA = re.compile(
    r"^\*\*(?:`(?P<backticked>[^`]+)`|(?P<plain>[^*]+))\*\*\s+"
    r"(?P<copula>is|are|was|were|refers to|serves as|organizes|provides|names|represents)\b",
    re.IGNORECASE,
)


def _strip_fenced(text: str) -> str:
    """Strips fenced code blocks and inline backticks while preserving line count."""
    return FENCED.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _build_ontology_lookup(index):
    """Builds a case-insensitive lookup set of valid ontology entities from index."""
    lookup = set()
    for ident, (cls, obj, _) in index.items():
        lookup.add(ident.lower())
        tail = ident.rsplit("/", 1)[-1].lower()
        lookup.add(tail)
        # Handle decision notation e.g. dr-185, dr-085, 185
        if cls == "Decision" or ident.startswith("work:decision/"):
            num = tail.lstrip("0") or "0"
            lookup.add(f"dr-{num}".lower())
            if num.isdigit():
                lookup.add(f"dr-{int(num):03d}".lower())
            lookup.add(num)
        # Handle article notation e.g. A8, 8
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
    """Builds lookup mapping of wiki files from a list of paths."""
    wiki_map = {}
    for f in file_list:
        try:
            rel = f.relative_to(ROOT)
        except ValueError:
            rel = f
        if len(rel.parts) >= 2 and rel.parts[0] == "wiki" and rel.suffix == ".md":
            if len(rel.parts) == 3:
                # e.g. wiki/solorepo/knowledge-management.md
                ctx = rel.parts[1].lower()
                stem = rel.stem.lower()
                wiki_map.setdefault((ctx, stem), f)
            elif len(rel.parts) == 2:
                # e.g. wiki/README.md
                wiki_map.setdefault(("", rel.stem.lower()), f)
    return wiki_map


def _resolves_wikilink(target: str, source_path: pathlib.Path, wiki_map: dict, ontology_lookup: set) -> bool:
    """Determines whether a wikilink target resolves to a wiki page or ontology entity."""
    clean = target.strip()
    if not clean:
        return False

    # 1. Check ontology lookup first (handles concepts, disciplines, decisions, articles)
    norm = clean.lower()
    norm_slug = norm.replace(" ", "-").replace("_", "-")
    if norm in ontology_lookup or norm_slug in ontology_lookup:
        return True

    # Check CURIE forms e.g. concept/pr-first -> work:concept/pr-first
    for prefix in ("work:", "ddd:"):
        if (prefix + norm) in ontology_lookup or (prefix + norm_slug) in ontology_lookup:
            return True

    # 2. Check wiki files
    # Scoped target e.g. solorepo/knowledge-management or wiki/solorepo/knowledge-management
    test_target = clean
    if test_target.lower().startswith("wiki/"):
        test_target = test_target[5:]

    if "/" in test_target:
        ctx_part, slug_part = test_target.split("/", 1)
        ctx_k = ctx_part.lower().replace(" ", "-").replace("_", "-")
        slug_k = slug_part.lower().replace(" ", "-").replace("_", "-").removesuffix(".md")
        if (ctx_k, slug_k) in wiki_map:
            return True
        # Direct relative path check
        rel_candidate = source_path.parent / f"{test_target}.md"
        if rel_candidate.is_file() or (ROOT / "wiki" / f"{test_target}.md").is_file():
            return True
    else:
        # Unscoped target e.g. [[knowledge-management]]
        # (a) Check in current context if source is under wiki/<ctx>/
        try:
            rel = source_path.relative_to(ROOT)
        except ValueError:
            rel = source_path
        if len(rel.parts) >= 3 and rel.parts[0] == "wiki":
            current_ctx = rel.parts[1].lower()
            if (current_ctx, norm_slug) in wiki_map:
                return True
        # (b) Check in scaffold context ("solorepo")
        if ("solorepo", norm_slug) in wiki_map:
            return True
        # (c) Check root wiki files (e.g. README)
        if ("", norm_slug) in wiki_map:
            return True
        # (d) Check any context in wiki_map
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
    tree_files = md_files if md_files is not None else tree()
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
    tree_files = md_files if md_files is not None else tree()

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

        lines = [line.strip() for line in without_comments(raw_text).splitlines()]
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
    """
    problems = []
    tree_files = md_files if md_files is not None else tree()
    wiki_map = _build_wiki_files_map(tree_files)

    # 1. Check domain vocabulary concepts have corresponding wiki pages
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

    # 2. Check that non-solorepo wiki pages correspond to minted concepts in index
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

    # 3. Check solorepo core wiki pages have matching concepts or disciplines in index
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


SCAFFOLD_ONLY = ("template/", "SPECIALIZE.md", "bootstraps/")


def inherited():
    """What Specialization copies into a portfolio, read from the step that
    lists it, so the copy set is stated once and this check follows it. A
    portfolio carries no Specialization Discipline — its Disciplines are under
    `imported/`, and this one is not among them — so the file is absent there,
    and absent is an empty copy set rather than a step that dies on the read."""
    source = META / "assertions" / "disciplines.yaml"
    if not source.is_file():
        return []
    data = yaml.safe_load(source.read_text()) or {}
    for discipline in data.get("disciplines") or []:
        if discipline.get("id") != "work:discipline/specialization":
            continue
        for step in discipline.get("steps") or []:
            if step.startswith("Copy what is inherited"):
                return re.findall(r"`([^`]+)`", step)
    return []


@check("scaffold-only paths")
def scaffold_only_paths():
    """A doc that Specialization copies does not name a path a portfolio lacks (solorepo's #45).

    `template/`, `SPECIALIZE.md` and `bootstraps/` stay with the scaffold, and a
    copied page that mentions one reads as true and is not. The audit solorepo's DR-036
    recorded found the Specialization Discipline moved and its Concept left
    behind — moving a thing, it says, leaves its name behind. A copy leaves one
    the same way: prose that crosses into a portfolio still naming what stayed
    with the scaffold.

    A mention is allowed on a line that names `solorepo` as the owner, which is
    how a portfolio's page refers to the scaffold's. The check reads the copied
    set from the Specialization step, so in a portfolio — where the Discipline
    is not carried — it has nothing to scan and says nothing, which is right:
    the copy is the scaffold's to get right before it happens.

    `.yml` is read as well as `.yaml`, because the copied set is not only prose:
    a workflow is a copied file that names paths, and the gate workflow named
    two `bootstraps/` renders for as long as it travelled (solorepo's #75) without this
    check seeing a suffix it read.

    `template/` is the copied set too — the replacements, which step three
    copies whole — so it is walked here as well, for the two names it can
    carry: it cannot name itself, and the seeded gate workflow is where the
    next `bootstraps/` render would be typed (solorepo's DR-115).
    """
    problems = []
    scanned = set()

    def scan(paths, names):
        for path in paths:
            if path.suffix not in (".md", ".yaml", ".yml") or not path.is_file():
                continue
            scanned.add(path)
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if "solorepo" in line.lower():
                    continue
                for name in names:
                    if name in line:
                        problems.append(f"{path.relative_to(ROOT)}:{number} names "
                                        f"'{name}', which a portfolio does not have")

    for token in inherited():
        base = ROOT / token if (ROOT / token).exists() else META / token
        paths = [base] if base.is_file() else sorted(base.rglob("*")) if base.is_dir() else []
        scan(paths, SCAFFOLD_ONLY)
    scan(sorted(TEMPLATE.rglob("*")), tuple(n for n in SCAFFOLD_ONLY if n != "template/"))

    if not scanned:
        return CouldNotRun("no inherited paths or template/ to scan")
    if problems:
        return Found(problems)
    return Passed(f"{len(scanned)} file{'s' if len(scanned) != 1 else ''}")


# The half the two gate workflows share, by job (solorepo's DR-119): each of these is in
# both files and equal across them. The seed's own job is `gate` (solorepo's DR-115), and
# the scaffold's seed jobs are its alone.
SHARED_JOBS = ("pull-request", "sweep")
SEED_OWN_JOBS = ("gate",)
# Except where the job runs (solorepo's DR-140). This repository's gate runs on a
# self-hosted scale set that exists on one machine; a fresh clone has no cluster
# and every runner GitHub will give it. That is a fact about the machine each
# repository has, not about what the job does, and holding it equal would force
# one of the two to name a runner it does not have.
NOT_SHARED = ("runs-on",)


def _first_difference(a, b, path):
    """Where two loaded YAML values first differ, as a dotted path, or None."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in list(a) + [k for k in b if k not in a]:
            if key not in a or key not in b:
                return f"{path}.{key}", "only on one side"
            found = _first_difference(a[key], b[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(a, list) and isinstance(b, list):
        for i, (x, y) in enumerate(zip(a, b, strict=False)):
            found = _first_difference(x, y, f"{path}[{i}]")
            if found:
                return found
        if len(a) != len(b):
            return f"{path}[{min(len(a), len(b))}]", "only on one side"
        return None
    return None if a == b else (path, f"{a!r} against {b!r}")


@check("gate workflows agree")
def gate_workflows_agree():
    """The scaffold's gate workflow and the seeded one differ in nothing the
    runner reads of their shared half (solorepo's DR-119).

    solorepo's DR-115 gave a portfolio a gate workflow of its own and named the cost: two
    workflows that will drift in their shared half. The half is the triggers,
    the permissions, and every job both files define under one name — `pull
    request` and `sweep` — and what held it equal was a comment in the
    scaffold's copy saying to change both, a reminder and not a control. solorepo's DR-114
    then made the scheduled sweep fail on a Challenge with no difficulty, which
    reached the scaffold's copy as a step and the `issues: read` that step needs,
    and the seeded copy stayed a version behind (solorepo's #113).

    Compared as loaded YAML, so each file keeps its own comments and differs in
    nothing GitHub reads. The shared jobs are named here and not derived: an
    intersection of the two files' job sets is forgiving on absence, and
    cannot tell a job the seed never had from one the seed lost, so a shared
    job deleted from the seed would have been invisible — the falsifier solorepo's DR-119
    writes for itself, and the reviewer's point on solorepo's #125. So each shared job
    must be in both files, and the seed defines exactly the shared jobs and
    its own `gate` job, which solorepo's DR-115 fixed at that name so that a portfolio's
    ruleset is set once. The scaffold's seed jobs are its alone and are not
    compared. A portfolio has no `template/`, so there it compares nothing and
    passes on an empty scope, as `scaffold-only paths` does for the same reason.

    Since solorepo's DR-120 the two shared jobs run one composite action each, under
    `.meta/actions/`, so their steps are typed once and cannot drift. What is
    compared here is the residue no mechanism of GitHub's shares: the
    triggers, the permissions, and the two stubs of checkout and `uses:`.

    All of each stub but `runs-on:` (solorepo's DR-140). This repository's gate
    runs on a self-hosted scale set named on one machine; a portfolio cloned
    from the seed has no cluster and `ubuntu-latest`. Held equal, one of the two
    would have to name a runner it does not have — and a job queued forever on a
    scale set nobody deployed is the seeded gate silently never running, which is
    not the drift this step was written against but is the same thing going wrong
    in the same place. What the two still share is every step, which is what "a
    version behind" meant in solorepo's #113.
    """
    ours = ROOT / ".github" / "workflows" / "gate.yml"
    seed = TEMPLATE / ".github" / "workflows" / "gate.yml"
    if not (ours.is_file() and seed.is_file()):
        return CouldNotRun("either ours or template workflow is absent")
    a = yaml.safe_load(ours.read_text()) or {}
    b = yaml.safe_load(seed.read_text()) or {}
    # YAML 1.1 reads the bare key `on` as the boolean True, and pyyaml is 1.1.
    shared = {"on": (a.get(True, a.get("on")), b.get(True, b.get("on"))),
              "permissions": (a.get("permissions"), b.get("permissions"))}
    jobs_a, jobs_b = a.get("jobs") or {}, b.get("jobs") or {}
    problems = []
    for name in SHARED_JOBS:
        for path, jobs in ((ours, jobs_a), (seed, jobs_b)):
            if name not in jobs:
                problems.append(f"jobs.{name}: not in {path.relative_to(ROOT)}, "
                                "and it is a job both gate workflows define")
        if name in jobs_a and name in jobs_b:
            shared[f"jobs.{name}"] = tuple(
                {k: v for k, v in jobs[name].items() if k not in NOT_SHARED}
                for jobs in (jobs_a, jobs_b))
    for name in jobs_b:
        if name not in SHARED_JOBS + SEED_OWN_JOBS:
            problems.append(f"jobs.{name}: in {seed.relative_to(ROOT)} and neither shared "
                            f"nor the seed's own; the seed's jobs are {', '.join(SEED_OWN_JOBS)} "
                            f"and the shared {', '.join(SHARED_JOBS)}")
    for label, (x, y) in shared.items():
        found = _first_difference(x, y, label)
        if found:
            where, how = found
            problems.append(f"{where}: {how} — {ours.relative_to(ROOT)} and "
                            f"{seed.relative_to(ROOT)} share this half, and it is held equal")
    if problems:
        return Found(problems)
    return Passed(f"{ours.relative_to(ROOT)} and {seed.relative_to(ROOT)} agree")


@check("template conventions agree")
def template_conventions_agree():
    """The scaffold's root instructions and the seeded template instructions agree on core conventions (solorepo's DR-183).

    solorepo's #11 establishes that an edit to one statement cannot leave
    another behind — either the second copy derives, or the gate names it.
    `template/AGENTS.md` and `template/.meta/README.md` are the seed files
    copied into new portfolios by Specialization. When operational conventions
    evolved at the root (`CLAUDE.md` and `GEMINI.md` symlinks, `move mint` for
    settling decisions, `just --list` as operator surface, PR First
    handoff/watch/sweep semaphores, `just next` for finding ripe work, and the
    ban on harness memory files), the template copies drifted.

    This step checks that the essential operational conventions present in root
    `AGENTS.md` and `.meta/README.md` are also stated in `template/AGENTS.md` and
    `template/.meta/README.md`. A portfolio has no `template/`, so there it
    passes on an empty scope.
    """
    if not TEMPLATE.is_dir():
        return Passed("no template/ in portfolio")

    ours_agents = ROOT / "AGENTS.md"
    seed_agents = TEMPLATE / "AGENTS.md"
    ours_readme = META / "README.md"
    seed_readme = TEMPLATE / ".meta" / "README.md"

    if not (ours_agents.is_file() and seed_agents.is_file() and
            ours_readme.is_file() and seed_readme.is_file()):
        return CouldNotRun("one or more required convention files are absent")

    agents_conventions = (
        ("symlinks to AGENTS.md", ("`CLAUDE.md` and `GEMINI.md` are symlinks",)),
        ("minting decisions", (".meta/say/move mint",)),
        ("operator surface", ("`just --list`",)),
        ("review handoff", (".meta/say/move request-review",)),
        ("watch semaphore", ("just watch",)),
        ("sweep semaphore", ("just sweep",)),
        ("next issue", ("`just next`",)),
        ("harness memory prohibition", ("harness's memory",)),
        ("empty directory README", ("empty directory carries a README",)),
    )

    readme_conventions = (
        ("next issue", ("`just next`",)),
        ("minting decisions", (".meta/say/move mint",)),
        ("operator surface", ("`just --list`",)),
    )

    problems = []

    def _check_file(path, conventions):
        """Verifies that all specified convention phrases exist in a file."""
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        rel = path.relative_to(ROOT)
        for label, phrases in conventions:
            if not any(phrase in text for phrase in phrases):
                problems.append(f"{rel}: missing convention for '{label}' (expected {phrases[0]!r})")

    for path, convs in ((ours_agents, agents_conventions),
                        (seed_agents, agents_conventions),
                        (ours_readme, readme_conventions),
                        (seed_readme, readme_conventions)):
        _check_file(path, convs)

    if problems:
        return Found(problems)
    return Passed(f"{seed_agents.relative_to(ROOT)} and {seed_readme.relative_to(ROOT)} agree with root conventions")


@functools.cache
def rendering():
    """The render the three steps below read, run once and shared between them.

    `render.ASKED` is filled as the render runs, so what `inherited prose`
    reads exists only after it. Both steps name a source off this rather than
    rendering for themselves, so the gate builds the pages once and the two
    agree about which render they are describing.
    """
    sys.path.insert(0, str(META))
    import render
    return render, render.rendered()


def declared(rel):
    """The Artifacts one assertion file holds, by path."""
    path = META / "assertions" / rel
    data = (yaml.safe_load(path.read_text()) if path.is_file() else None) or {}
    return {a["path"]: a for a in data.get("artifacts") or []}


def asserts(entry, slot, block):
    """Whether this entry carries that prose: the slot, or the named block in it."""
    if not entry or not entry.get(slot):
        return False
    if not block:
        return True
    return any(p.get("name") == block for p in entry[slot])


@check("inherited prose")
def inherited_prose(asked):
    """Prose a generator reads is asserted where Specialization copies it.

    `Artifact.preamble` moved the framing prose of the generated pages out of
    `render.py` (solorepo's DR-144). `assertions/structure.yaml` is the wrong
    home for it: its own first line says the file is the portfolio's and never
    synced, and step three of Specialization replaces it with `template/`'s,
    which declares one Artifact. The renderer is inherited and would then ask
    every portfolio for prose nothing asserts — a portfolio red on its first
    render, found by nothing here, because the scaffold's own copy has the
    entries.

    `asked` is what a render actually asked for, collected by `authored()` as
    it ran. Not the slots by name: a slot named here that no generator reads
    would fail an Artifact for prose nothing wants, and `description` is
    `WorkEntity`'s, carried by most of what `assertions/` declares as plain
    documentation. Not a list typed beside the call sites either, which would
    be the second copy this change exists to remove.

    `SPECIALIZE.md` is the exception the copy set already names: a portfolio
    specializes nothing and renders no such page, so its prose is the
    scaffold's own and stays one level up.
    """
    own = declared("structure.yaml")
    return [f"{own[rel]['id']} asserts the "
            f"{f'{slot} block {block!r}' if block else slot} render.py reads for "
            f"{rel}, which a portfolio renders, in the file Specialization "
            f"replaces — move it to assertions/imported/structure.yaml"
            for rel, slot, block in sorted(asked)
            if asserts(own.get(rel), slot, block) and not rel.startswith(SCAFFOLD_ONLY)]


@check("unread prose")
def unread_prose(asked):
    """Prose asserted that no render asks for (solorepo's DR-152).

    A8's other half, for the prose solorepo's DR-144 and solorepo's DR-152 moved
    out of `render.py`.
    `inherited prose` holds where a block is asserted; this holds whether
    anything reads it at all. Without it, a generator that stops reading a block
    — renamed, reworded into the derived part, dropped with the section it
    framed — leaves the block behind in the assertions, saying something about a
    page that no longer says it. That residue is invisible: the page still
    renders, the byte-compare still passes, and the only reader left is whoever
    opens the assertion and believes it.

    Only the three slots minted to be read by a generator, and never
    `description`: that one is `WorkEntity`'s, and most of what `assertions/`
    declares carries one as documentation for a reader rather than for a render.
    """
    entries = []
    for rel in ("imported/structure.yaml", "structure.yaml"):
        entries.extend(declared(rel).values())
    for rel in ("imported/disciplines.yaml", "disciplines.yaml"):
        path = META / "assertions" / rel
        data = (yaml.safe_load(path.read_text()) if path.is_file() else None) or {}
        entries.extend(data.get("disciplines") or [])
    problems = []
    for entry in entries:
        host = entry.get("path") or entry.get("id")
        for slot in ("preamble", "postamble"):
            if entry.get(slot) and (host, slot, "") not in asked:
                problems.append(f"{entry['id']} asserts a {slot} no render asks for")
        for prose in entry.get("woven") or []:
            if (host, "woven", prose["name"]) not in asked:
                problems.append(f"{entry['id']} asserts a woven block named "
                                f"{prose['name']!r} no render asks for")
    return problems


def without_comments(text: str) -> str:
    """Text with every `<!-- ... -->` comment removed (solorepo's DR-171)."""
    first, *rest = text.split("<!--")
    return first + "".join(piece.split("-->", 1)[1] for piece in rest if "-->" in piece)


def history_entries_of(text: str) -> list[tuple[str, str | None]]:
    """The (title, receipt) pairs of a history log (solorepo's DR-171)."""
    entries: list[tuple[str, str | None]] = []
    for line in without_comments(text).splitlines():
        if line.startswith("### "):
            entries.append((line[4:].strip(), None))
        elif line.strip().startswith("Receipt:") and entries:
            parts = line.split("`")
            entries[-1] = (entries[-1][0], parts[1].strip() if len(parts) > 1 else None)
    return entries


@check("meta history orphans")
def meta_history_orphans():
    """Every .history.md under .meta/ has a companion script that names it in its docstring (solorepo's DR-171)."""
    problems = []
    counted = 0

    for history in sorted(META.rglob("*.history.md")):
        counted += 1
        stem = history.name[:-len(".history.md")]
        candidate_py = history.parent / f"{stem}.py"
        candidate_bin = history.parent / stem

        companion = candidate_py if candidate_py.is_file() else (candidate_bin if candidate_bin.is_file() else None)
        if not companion:
            problems.append(f"{history.relative_to(META)}: no companion {stem}.py or {stem} found")
            continue

        try:
            tree = ast.parse(companion.read_text(encoding="utf-8"))
            docstring = ast.get_docstring(tree) or ""
        except SyntaxError as e:
            problems.append(f"{companion.relative_to(META)}: failed to parse for docstring: {e}")
            continue

        if history.name not in docstring:
            problems.append(
                f"{companion.relative_to(META)}: module docstring does not name companion {history.name}"
            )

    if problems:
        return Found(problems)
    return Passed(f"{counted} history files under .meta/, each named by companion module docstring")


@check("meta history receipts")
def meta_history_receipts():
    """Every entry in a .meta/ history log names a check or probe that exists (solorepo's DR-171)."""
    problems = []
    logs = 0
    entries = 0

    for history in sorted(META.rglob("*.history.md")):
        logs += 1
        text = history.read_text(encoding="utf-8")
        for title, receipt in history_entries_of(text):
            entries += 1
            if not receipt:
                problems.append(f"{history.relative_to(META)}: '{title}' names no receipt")
                continue
            if "::" not in receipt:
                problems.append(
                    f"{history.relative_to(META)}: '{title}' receipt `{receipt}` "
                    "does not have <path>::<symbol> format"
                )
                continue
            path_str, symbol = receipt.split("::", 1)
            target = (ROOT / path_str).resolve() if (ROOT / path_str).is_file() else (META / path_str).resolve()
            if not target.is_file():
                problems.append(
                    f"{history.relative_to(META)}: '{title}' receipt `{receipt}` "
                    f"file '{path_str}' does not exist"
                )
                continue
            try:
                tree = ast.parse(target.read_text(encoding="utf-8"))
            except SyntaxError as e:
                problems.append(
                    f"{history.relative_to(META)}: '{title}' receipt `{receipt}` "
                    f"failed to parse '{path_str}': {e}"
                )
                continue
            symbols = set()
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.add(node.name)
                    if isinstance(node, ast.ClassDef):
                        for sub in node.body:
                            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                symbols.add(f"{node.name}.{sub.name}")
                    for dec in getattr(node, "decorator_list", []):
                        if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
                            symbols.add(str(dec.args[0].value))
            if symbol not in symbols:
                problems.append(
                    f"{history.relative_to(META)}: '{title}' names `{receipt}`, "
                    f"which does not exist in {path_str}"
                )

    if problems:
        return Found(problems)
    return Passed(f"{entries} entries across {logs} history logs, each naming a receipt that exists")


NOQA = re.compile(r"#\s*noqa(?::\s*[A-Z0-9,\s]+)?(?P<rest>.*)$")
TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore(?:\[[^\]]*\])?(?P<rest>.*)$")
REASON = re.compile(r"#\s*reason:\s*\S")


@check("meta lints")
def meta_lints():
    """No linter rule is switched off in configuration, and every site suppression carries a reason (A2, solorepo's DR-177).

    An `ignore` in `.meta/ruff.toml` switches a rule off where nobody reads it.
    At a site, a `# noqa` or `# type: ignore` without an explanatory `# reason:`
    is a configuration ignore with extra steps. This holds .meta/ tooling to the
    same discipline the Python bootstrap enforces on portfolio code.
    """
    config = META / "ruff.toml"
    if not config.is_file():
        return CouldNotRun(".meta/ruff.toml is missing")
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        return Found((f".meta/ruff.toml: does not parse — {error}",))
    problems = []
    lint = data.get("lint", {})
    for key in ("ignore", "extend-ignore"):
        if lint.get(key):
            problems.append(f".meta/ruff.toml: `{key}` switches {len(lint[key])} rules off in configuration")
    sources = [
        p for p in META.rglob("*.py")
        if not any(part.startswith(".") and part != "." for part in p.relative_to(META).parts)
        and "__pycache__" not in p.parts
    ]
    suppressions = 0
    for source in sorted(sources):
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            for pattern, what in ((NOQA, "noqa"), (TYPE_IGNORE, "type: ignore")):
                match = pattern.search(line)
                if match is None:
                    continue
                suppressions += 1
                if not REASON.search(match.group("rest")):
                    problems.append(f"{source.relative_to(ROOT).as_posix()}:{number}: `{what}` gives no reason")
    if problems:
        return Found(tuple(problems))
    return Passed(
        f"{suppressions} suppressions across {len(sources)} files, each with a reason; "
        ".meta/ruff.toml switches no rule off"
    )


@check("meta ruff")
def meta_ruff():
    """Ruff check over .meta/ against the ruleset declared in .meta/ruff.toml (solorepo's DR-177).

    Runs `ruff check` on the repository staging directory using the configured
    ruleset. A violation fails the gate with the offending rule and location.
    """
    config = META / "ruff.toml"
    if not config.is_file():
        return CouldNotRun(".meta/ruff.toml is missing")
    ruff_bin = shutil.which("ruff")
    cmd = [ruff_bin, "check", "--config", str(config), str(META)] if ruff_bin else None
    if not cmd:
        try:
            res = subprocess.run([sys.executable, "-m", "ruff", "--version"], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                cmd = [sys.executable, "-m", "ruff", "check", "--config", str(config), str(META)]
        except OSError:
            pass
    if not cmd:
        uvx = shutil.which("uvx")
        if uvx:
            cmd = [uvx, "--from", "ruff==0.14.0", "ruff", "check", "--config", str(config), str(META)]
    if not cmd:
        return CouldNotRun("neither ruff nor uvx is installed")
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if out.returncode == 0:
        return Passed("ruff check passed over .meta/")
    lines = [line.strip() for line in (out.stdout + "\n" + out.stderr).splitlines() if line.strip()]
    return Found(tuple(lines))


@check("meta doc")
def meta_doc():
    """Every module and script under .meta/, and every public function, class and method, has a docstring (A2, solorepo's DR-179).

    Extends the Python Bootstrap's missing_docs requirement to the repository's
    own tooling and scripts under .meta/. Holds inherited and scaffolding Python
    to the same literate programming standards enforced on product code.
    """
    problems = []
    counted = 0
    modules = 0

    def is_py(path: pathlib.Path) -> bool:
        if any(part.startswith(".") and part != "." for part in path.relative_to(META).parts):
            return False
        if "__pycache__" in path.parts:
            return False
        if path.suffix == ".py":
            return True
        if not path.suffix and path.is_file():
            try:
                with path.open("rb") as handle:
                    first = handle.readline().decode("latin1", "ignore")
                    return first.startswith("#!") and "python" in first
            except OSError:
                pass
        return False

    sources = sorted(p for p in META.rglob("*") if is_py(p))
    for source in sources:
        modules += 1
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except SyntaxError as error:
            problems.append(f"{source.relative_to(ROOT)}: does not parse — {error}")
            continue
        counted += 1
        if ast.get_docstring(tree) is None:
            problems.append(f"{source.relative_to(ROOT)}: module has no docstring")
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and not node.name.startswith("_")
            ):
                counted += 1
                if ast.get_docstring(node) is None:
                    problems.append(f"{source.relative_to(ROOT)}:{node.lineno}: `{node.name}` has no docstring")
                if isinstance(node, ast.ClassDef):
                    for member in node.body:
                        if (
                            isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and not member.name.startswith("_")
                        ):
                            counted += 1
                            if ast.get_docstring(member) is None:
                                problems.append(
                                    f"{source.relative_to(ROOT)}:{member.lineno}: `{node.name}.{member.name}` has no docstring"
                                )

    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} public items across {modules} files, each with a docstring")


# Registered last, because this is the one step that reads what the others'
# subject is rendered into, and a reader watching the gate wants it under them.
@check("rendered prose")
def rendered_prose(pages):
    """Every page render.py writes is the render of what it is written from.

    A generated page is data twice over, and the copy in the tree is the one a
    reader opens; stale, it is prose asserting something the record no longer
    says. What is compared is every target `render.py` names, including the
    templates, so the mark says what it covered.
    """
    render, _ = rendering()
    # `unrendered` answers by page name, so the sentence that says what is wrong
    # with that page is written here rather than carried out of the render.
    stale = [f"{name} exists but nothing renders it" for name in render.unrendered()]
    stale += [name for name, text in pages.items()
              if not (META / name).exists()
              or (META / name).read_text() != text.rstrip("\n") + "\n"]
    return stale
