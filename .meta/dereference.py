#!/usr/bin/env -S uvx --with linkml --with pyyaml python
"""The reading of a citation, run before the hand-off (solorepo's DR-134).

    just dereference                 what this branch wrote, against origin/main
    just dereference --all           every citation in the durable set: uncapped,
                                     and about fifteen hundred questions
    .meta/dereference.py --pairs     the deterministic half alone, asking nothing

A12 asks that a citation carry the claim it names. solorepo's DR-130 checked the
four shapes of that claim a string search reaches and said the rest was a
reading and nobody's check; this is the rest, and it is somebody's — the
coder's, before the review is requested, with the reviewer still behind it.
Each pair is a sentence that cites an entry and the entry itself, and the
question asked of each is the one a reviewer asks: does the target support this
sentence, and which of its words say so.

**Not a gate.** It prints A21's three marks because that is the shape a reader
here reads, and it is in no Project's `gate` string. A gate's red is a fact a
re-run cannot overturn; this one's is a model's reading, which the same input
can answer differently, and solorepo's DR-134 says why that may not be where a
merge is decided. Its `x` is a finding the coder answers — by fixing the
sentence, or by leaving it and saying why — and nothing requires the step.

What it reads, and what it leaves alone. The durable set, the shape of a
citation and the entry a citation names are `check.py`'s, imported rather than
written again: two extractors would drift about what a citation is, which is the
seam solorepo's DR-132 closed between the two checkers. What is this file's own
is the unit — a sentence, because that is what a reader reads and what a claim
is made in, where `check.py` needs a whole file flattened to one string. A citation of an Issue is left out — its target is GitHub's and
`check_pr.py` resolves the number — because every paraphrase failure this was
built for named an entry, and a step that reaches two systems fails in two ways.

The scope is the diff. About fifteen hundred citations stand in the durable set,
and reading them all is a bill nobody wants twice a day; what anyone wants read
is what this branch wrote. So a changed file's citation-bearing sentences are
taken, the ones its merge base already held are subtracted, and the remainder is
the scope. `--all` is there for the run that wants the record.
"""
import argparse
import concurrent.futures
import importlib.util
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from importlib.machinery import SourceFileLoader

import yaml

META = pathlib.Path(__file__).resolve().parent
ROOT = META.parent
CREDENTIAL = pathlib.Path(
    os.environ.get("SOLOREPO_MODEL_ENV", "~/.config/solorepo/claude.env")).expanduser()
MODEL = "claude-sonnet-5"

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


def citations():
    """`.meta/checks/citations.py`, imported for its extraction and nothing else.

    Importing runs nothing — everything it does is under `main()` — and the
    functions used here read files. It is imported the way `check.py` imports
    `check_pr.py`, and for the same reason: what a citation is, and which files
    hold one durably, is one fact, and a copy of it here would be a second
    answer that drifts.

    The gate's steps moved out of `check.py` into `.meta/checks/`
    (solorepo's DR-150), so what this reaches for now has a name: the citation
    grammar and the copy set are `citations.py`'s, and nothing else in the gate
    is wanted here. Its own siblings are imported by plain name, so the
    directory goes on `sys.path` first.
    """
    if str(CHECKS) not in sys.path:
        sys.path.insert(0, str(CHECKS))
    loader = SourceFileLoader("citations", str(CHECKS / "citations.py"))
    spec = importlib.util.spec_from_loader("citations", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def git(*args, default=None):
    out = subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT)
    if out.returncode:
        if default is None:
            sys.exit(f"dereference: git {' '.join(args[:2])}: {out.stderr.strip()}")
        return default
    return out.stdout


def articles():
    """Every Article, by number, as the entry a citation of it names."""
    charter = yaml.safe_load(
        (META / "assertions" / "imported" / "charter.yaml").read_text()) or {}
    return {int(a["id"].rsplit("/", 1)[-1]): a for a in charter.get("articles") or []}


def target(cite, index):
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


def spans(chk, path):
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
    which is the failure solorepo's DR-134 names as its falsifier, arriving by
    construction.
    """
    if path.suffix in (".yaml", ".yml"):
        return chk.prose(path)
    try:
        text = chk.BLOCK.sub(" ", path.read_text())
    except (UnicodeDecodeError, OSError):
        return []
    found = []
    for block in re.split(r"\n\s*\n", text):
        item = []
        for line in block.splitlines():
            if ITEM.match(line) and item:
                found.append(chk.flat(" ".join(item)))
                item = []
            item.append(line)
        if item:
            found.append(chk.flat(" ".join(item)))
    return [span for span in found if span.strip()]


def sentences(chk, path):
    """Every sentence of a file that cites an entry, with the span around it.

    A citation inside a code span is the shape of one and not one, and is
    dropped the way `cited articles` drops it. The word boundaries are this
    file's: `check.py` puts them where each of its patterns needs them, and a
    bare `CITE` would read the `A1` inside a token that merely contains one.
    """
    cites = re.compile(rf"\b{chk.CITE}\b")
    found = []
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


def as_it_was(chk, path, text):
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


def scope(chk, base, everything):
    """The pairs to ask about: a sentence, the span it sits in, the citation and
    what the citation names.

    Everything, or what this branch wrote. The second is a set difference over
    sentences rather than a read of the diff's line numbers: a folded scalar
    wraps where the line ended and not where the sentence did, so a line-based
    scope would report a claim whose only change was the width of its wrap, and
    would miss one edited across a fold.

    A pair is asked once. The same sentence citing the same entry in two files
    is one question with one answer, and paying twice for it is paying for the
    copy rather than the claim.
    """
    index = articles()
    durable = set(chk.durable(chk.copied_files()))
    if everything:
        paths, before = sorted(durable), {}
    else:
        # Changed and not yet committed both. A new file is the normal shape of
        # a decision entry, and a run before the hand-off that read only what
        # git had already been told about would skip the file the branch exists
        # to add.
        named = git("diff", "--name-only", base).split()
        named += git("ls-files", "--others", "--exclude-standard", default="").split()
        changed = [(ROOT / name) for name in dict.fromkeys(named)]
        paths = sorted(p for p in changed if p in durable and p.is_file())
        before = {p: git("show", f"{base}:{p.relative_to(ROOT)}", default="") for p in paths}
    pairs, seen = [], set()
    for path in paths:
        held = set() if everything else as_it_was(chk, path, before[path])
        for sentence, around, named in sentences(chk, path):
            if sentence in held:
                continue
            for cite in named:
                body = target(cite, index)
                if body is None or (cite, sentence) in seen:
                    continue
                seen.add((cite, sentence))
                pairs.append({"path": str(path.relative_to(ROOT)), "cite": cite,
                              "sentence": sentence, "context": around, "body": body})
    return pairs


QUESTION = """You are checking one citation, the way a reviewer checks one.

Below is a sentence from `{path}` that cites {cite}, the span it sits in, and \
the whole of what {cite} says. Decide whether {cite} supports what the sentence \
says about it.

Answer with exactly one line, and nothing else:

  ok <the words of {cite} that support it>
  x <what the sentence claims that {cite} does not say>
  ? <what you would have to know to decide>

Rules. Judge only the claim the sentence makes about {cite}. A sentence that \
names {cite} as a pointer, asserting nothing about its content, is `ok`. A \
faithful paraphrase is `ok` even where no words match. A count, a date, a name \
or a derivation attributed to {cite} is `x` where {cite}'s own text gives a \
different one. Where the claim is about something outside {cite} — another \
entry, a file, the world — answer `?`, because that is not yours to decide from \
what you have. Prefer `?` to a guess.

THE SENTENCE
{sentence}

THE SPAN IT SITS IN
{context}

WHAT {cite} SAYS
{body}
"""


def credential():
    """The model token, on the terms the channel holds a Role's: outside the
    working tree, refused where others can read it, and handed to one child
    process rather than exported.

    The environment wins where a shell has the token. CI's agent shell does
    not have it — `claude-code-action` hands that shell no
    `CLAUDE_CODE_OAUTH_TOKEN`, whatever `env:` block of the workflow's holds
    it, while an ordinary variable of the workflow's does cross — so
    `coder.yml` writes the file in a step of its own, and that step is what CI
    asks with. Written here rather than taken from `channel.py` because
    the two read different files for different keys and share only the rules,
    and a credential the channel never speaks with does not belong in it.

    Absent, the ambient one will do, loudly — the channel's own term for a
    missing Role credential, and the right one here for a different reason. A
    Role's file exists so that GitHub can tell the Role from the solo, and
    nothing attributes a model's reading to anybody; any `claude` that is logged
    in can answer. Refusing before trying would buy no better message than
    trying does: a `claude` that cannot authenticate exits non-zero and `ask`
    turns that into `?` with its own words on it. It would also leave the file
    as the only way in, and nothing creates one on the machine `just
    dereference` is typed on — CI writes its own — so the step would read a
    citation in exactly one place in the world, which is not what A12 now says
    it does.

    Returns the environment to add, or `{}` where the ambient one is what is
    used.
    """
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return {}
    if not CREDENTIAL.exists():
        print(f"dereference: no {CREDENTIAL}; asking with ambient auth, which is "
              "whatever `claude` on this machine is logged in as", file=sys.stderr)
        return {}
    mode = CREDENTIAL.stat().st_mode
    if mode & 0o077:
        sys.exit(f"dereference: {CREDENTIAL} is readable by others "
                 f"(mode {mode & 0o777:o}); refusing to use it. chmod 600 it.")
    for line in CREDENTIAL.read_text().splitlines():
        line = line.strip().removeprefix("export ").strip()
        if line.startswith("CLAUDE_CODE_OAUTH_TOKEN=") and (
                value := line.split("=", 1)[1].strip().strip("\"'")):
            return {"CLAUDE_CODE_OAUTH_TOKEN": value}
    print(f"dereference: {CREDENTIAL} holds no CLAUDE_CODE_OAUTH_TOKEN; asking with "
          "ambient auth", file=sys.stderr)
    return {}


def ask(pair, token, model, seconds=120):
    """One question, answered by a model with no tools and the target in hand.

    No tools on purpose: everything the question turns on is in the prompt, so
    the answer is a reading of text that was extracted deterministically rather
    than a search that might land anywhere. `ANTHROPIC_BASE_URL` is dropped for
    the child, because an ambient one belongs to whatever session set it and
    this asks the credential's own endpoint.

    An answer that is not one of the three marks is `?`. A model told to print
    one line and printing a paragraph has not answered, and reading a verdict
    out of the paragraph would be this step guessing on the model's behalf.

    A question that does not come back is `?` too, and that is why there is a
    timeout on it. Every subprocess `check.py` runs carries one, and those reach
    at most a remote; this reaches a model, six at a time, and the caller blocks
    on the last of them. The step is documented as unable to fail the run that
    holds it, and one that hangs stops it instead — inside `coder.yml` it would
    spend a step budget that ends with the Issue claimed and the pull request
    open, which is the state that file's own comment exists to prevent.

    A refused run's reason is read from stdout before stderr: `claude -p`
    refusing prints the reason there, and keeps stderr for warnings that are
    true whether the run succeeded or not — solorepo's #171 read the ordering
    the other way and reported the warning as the reason.
    """
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_BASE_URL"}
    env.update(token)
    try:
        out = subprocess.run(["claude", "-p", "--model", model],
                             input=QUESTION.format(**pair), capture_output=True,
                             text=True, env=env, timeout=seconds)
    except subprocess.TimeoutExpired:
        return "?", f"the model did not answer within {seconds}s"
    if out.returncode:
        why = (out.stdout.strip() or out.stderr.strip() or "the model could not be reached")
        return "?", why.splitlines()[-1][:160]
    line = next((s.strip() for s in out.stdout.splitlines() if s.strip()), "")
    for mark in ("ok", "x", "?"):
        if line == mark or line.startswith(mark + " "):
            return mark, line[len(mark):].strip()
    return "?", f"the answer was not one of the three marks: {line[:120]!r}"


def report(answers, pairs, where, everything):
    """A21's three lines, from a step that is not a gate.

    One step, one mark. `x` where any pair failed, and the undecided are listed
    under it too, because a run that found one false citation and left four
    unanswered has said two things and a reader needs both. `?` where none
    failed and some could not be decided, which exits zero: the outcome A6
    leaves unmarked is what a step says when it could not answer, and a step
    that answered none of its pairs has found nothing.
    """
    scoped = "the durable set" if everything else f"what this branch wrote over {where}"
    bad = [(p, why) for (mark, why), p in zip(answers, pairs) if mark == "x"]
    held = [(p, why) for (mark, why), p in zip(answers, pairs) if mark == "?"]

    def lines(items, mark):
        for pair, why in items:
            print(f"     {mark} {pair['path']}: {pair['cite']} — {why}")
            print(f"       “{pair['sentence'][:160]}”")

    if bad:
        print(f"x  dereference ({len(bad)})")
        lines(bad, "x")
        lines(held, "?")
        return 1
    if held:
        print(f"?  dereference: {len(held)} of {len(pairs)} citation(s) undecided in {scoped}")
        lines(held, "?")
        return 0
    print(f"ok dereference — {len(pairs)} citation(s) in {scoped}, "
          "each supported by what it names")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--all", action="store_true",
                    help="every citation in the durable set, not only this branch's")
    ap.add_argument("--base", default="origin/main",
                    help="what this branch is read against (default origin/main)")
    ap.add_argument("--model", default=MODEL, help=f"the model asked (default {MODEL})")
    ap.add_argument("--limit", type=int, default=None,
                    help="the most pairs to ask about; above it the step does not run "
                         "(default 60 over a branch, and no cap under --all)")
    ap.add_argument("--workers", type=int, default=6, help="questions asked at once")
    ap.add_argument("--timeout", type=int, default=120,
                    help="seconds one question may take before it answers `?`")
    ap.add_argument("--pairs", action="store_true",
                    help="print the pairs and ask nothing: the deterministic half alone")
    args = ap.parse_args(argv)

    chk = citations()
    base = git("merge-base", "HEAD", args.base, default="").strip() or args.base
    pairs = scope(chk, base, args.all)
    if args.pairs:
        for pair in pairs:
            print(f"{pair['path']}: {pair['cite']} — {pair['sentence'][:160]}")
        print(f"{len(pairs)} pair(s)")
        return 0
    if not pairs:
        print("ok dereference — no citation written on this branch")
        return 0
    # Could not run, in both of the ways that happens here: too much to ask, and
    # nothing to ask through. Loud, unmarked and exiting zero, which is what A6
    # asks of that outcome — and a step that blocks nothing must not be able to
    # fail the run that holds it either. There is no third: `credential` always
    # returns something to ask with, and says on stderr which.
    # The cap guards a bill nobody meant to run up, and `--all` is nobody's
    # accident: it is the word for asking the whole record, so it is not capped
    # by a number chosen for a branch. The usage block says what that costs.
    limit = args.limit if args.limit is not None else (None if args.all else 60)
    if limit is not None and len(pairs) > limit:
        print(f"?  dereference: {len(pairs)} pairs in scope, above the limit of {limit}; "
              "narrow the scope with --base, raise --limit, or ask the record with --all")
        return 0
    if not shutil.which("claude"):
        print("?  dereference: `claude` is not on PATH, and the question is asked through it")
        return 0
    token = credential()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        answers = list(pool.map(
            lambda pair: ask(pair, token, args.model, args.timeout), pairs))
    return report(answers, pairs, base, args.all)


if __name__ == "__main__":
    sys.exit(main())
