"""Invariants over the tree: what is on disk, and what two files owe each other.

Steps that read the working tree rather than the index — a placeholder that
survived, a link that resolves to nothing, a path that is the scaffold's alone,
a generated page that is behind its assertions or whose framing prose a
portfolio would not inherit, and the half the two gate workflows hold equal.
`tree()` is here because it is the tree as git sees it, which is the only list
of files the gate trusts, and `citations.py` reads prose out of it
(solorepo's DR-150).
"""
import functools
import os
import pathlib
import re
import subprocess
import sys

import yaml

from collect import META, ROOT, TEMPLATE, TOKEN, check, view_for


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

    def scan(paths, names):
        for path in paths:
            if path.suffix not in (".md", ".yaml", ".yml") or not path.is_file():
                continue
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
    return problems


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
        for i, (x, y) in enumerate(zip(a, b)):
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
        return []
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
    return problems


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
    stale = render.unrendered()
    stale += [name for name, text in pages.items()
              if not (META / name).exists()
              or (META / name).read_text() != text.rstrip("\n") + "\n"]
    return stale
