"""The tools beside the gate, run against the answers they exist to give (solorepo's DR-209).

`timing.py`'s percentile and its degrade (solorepo's DR-157), `depth.py`'s
four layers (solorepo's DR-188), `agents.py`'s count against the fan-out
ceiling (solorepo's DR-191), `dereference.py`'s scopes and report
(solorepo's DR-134, solorepo's DR-192), `search.py`'s index and benchmark
(solorepo's DR-103), and the detectors of `comments.py` that the comment
steps read through (solorepo's DR-207). Five are scripts under `.meta/` that
no step of the gate runs, so a wrong answer from one shows nowhere else; the
sixth is read by those steps, so a wrong answer from it shows as a wrong
verdict rather than as a failure. Each is loaded and asked one case at a
time, and a failure names the case. The steps register here rather than
beside the tools they exercise, because the gate over assertions should not
take its imports from a test suite (solorepo's DR-150).
"""
import contextlib
import io
import json
import pathlib
import tempfile

import citations
from collect import META, ROOT, against_baseline, check
from probes.harness import load_module, outcome


@contextlib.contextmanager
def _written(suffix, text):
    """A file holding `text` under a temporary name ending in `suffix`, closed before the block and deleted after it, whatever the block did."""
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as handle:
        handle.write(text)
        path = pathlib.Path(handle.name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


@check("timing probes", pre=True)
def timing_probes():
    """`timing.pick` over the lengths where nearest-rank ties, and `timing.gh` over the one default a caller can ask for (solorepo's DR-157).

    Nearest-rank: the median of `n` values is the `ceil(n/2)`-th smallest,
    which is a value that occurred. Each case is the run `1..n`, so the value
    and its rank are the same number and the expectation reads without
    arithmetic. Three of the lengths, 5, 9 and 13, are those where `0.5 * n`
    is a half with an even integer part, which `round`, being half-to-even,
    rounds down: a `pick` written with `round` answers one rank low on each,
    and five is `--deep`'s default. The fourth, 4, is the even length on which
    the two agree. The p95 of five runs is the slowest of them, and no runs is
    no figure.

    The degrade path is asked through a `gh` subcommand that does not exist,
    so the failure is a real one and not a stand-in. A caller that gives a
    default of `None` gets `None` — the default `runs_of` gives, on the token
    with no Actions scope the program is shaped around, and the one a sentinel
    of `None` cannot tell from no default — and a caller that gives `{}` gets
    `{}`. A caller that gives no default is not asked, because what it does
    is exit. `SystemExit` is caught and reported as the case's own finding:
    uncaught, a read that exits instead of degrading would take the gate down
    with every step before this one reported ok and the gate exited 1, naming
    neither the step nor the reason, because `check.py`'s precheck guard
    catches `Exception` and `SystemExit` is not one.
    """
    timing = citations.load_timing()
    problems = []
    for n in (4, 5, 9, 13):
        want = -(-n // 2)
        got = timing.pick(list(range(1, n + 1)), 0.5)
        if got != want:
            problems.append(f"timing: the median of {n} run(s) is the {want}\u2011th, "
                            f"and `pick` answered the {got}\u2011th")
    if timing.pick([1, 2, 3, 4, 5], 0.95) != 5:
        problems.append("timing: p95 of five runs is the slowest of them, "
                        "and `pick` answered otherwise")
    if timing.pick([], 0.5) is not None:
        problems.append("timing: no runs is no figure, and `pick` answered one")
    for default, want in ((None, None), ({}, {})):
        try:
            got = timing.gh("timing-probe-no-such-subcommand", default=default)
        except SystemExit:
            problems.append(f"timing: a read that fails and was given a default of "
                            f"{default!r} exited instead of degrading to it")
            continue
        if got != want:
            problems.append(f"timing: a read that fails and was given a default of "
                            f"{default!r} answered {got!r}")
    return problems


@check("depth probes", pre=True)
def depth_probes():
    """`depth.evaluate` answers from the first of its four layers that speaks, one case per layer and one per precedence between them (solorepo's DR-188).

    Layer 1 is the scaffold boundary: each of the four boundary files alone
    takes the deep tier, and the reason says so. Layer 4 is the standard path
    that files matching nothing take, with the real `structure.yaml` and no
    hook. Layer 2 is read from a `structure.yaml` written for the case, whose
    one project declares two `critical_paths` globs: a file under one takes
    the deep tier with the declared reason, and a file under neither falls
    through to standard. Layer 3 is read from a hook written for the case,
    which answers a two-agent, ninety-turn configuration for a file whose
    name holds `custom_trigger` and `None` for any other; a boundary file
    beside that name still takes layer 1, because the layers answer in order
    and a hook cannot talk a boundary out of deep review. Last,
    `.meta/hooks/depth.py.example` must exist and, run as the hook, must put
    a migration on the deep tier and a README on the standard one.
    """
    depth = load_module(META / "depth.py", "depth_module")
    problems = []
    opus, sonnet = "claude-opus-5", "claude-sonnet-5"

    def expect(case, cfg, **want):
        """One problem naming `case` when any field of `cfg` differs from `want`; `reason_has` asks that the reason contain a phrase rather than equal one."""
        phrase = want.pop("reason_has", None)
        if any(getattr(cfg, field) != value for field, value in want.items()) or (
                phrase is not None and phrase not in cfg.reason):
            asked = [f"{field}={value!r}" for field, value in want.items()]
            if phrase is not None:
                asked.append(f"reason containing {phrase!r}")
            problems.append(f"depth: {case} expected {', '.join(asked)}, got {cfg}")

    for boundary in (".meta/say/post", ".meta/hooks/worktree_only.py",
                     ".claude/settings.json", ".github/workflows/gate.yml"):
        cfg = depth.evaluate([boundary])
        expect(f"scaffold boundary {boundary}", cfg, model=opus, agents=3)
        expect(f"scaffold boundary {boundary}", cfg, reason_has="scaffold boundary")
    standard = depth.evaluate(["src/main.rs", "docs/guide.md"])
    expect("standard files", standard, model=sonnet, agents=1)
    expect("standard files", standard, reason="standard path")

    structure = (
        "projects:\n"
        "  - id: work:project/billing\n"
        "    critical_paths:\n"
        "      - 'services/billing/**'\n"
        "      - 'migrations/*.sql'\n"
    )
    with _written(".yaml", structure) as declared:
        critical = depth.evaluate(["services/billing/ledger.rs"], structure_file=declared)
        expect("declared critical path", critical, model=opus, agents=3)
        expect("declared critical path", critical, reason_has="declared critical path")
        other = depth.evaluate(["services/auth/token.rs"], structure_file=declared)
        expect("a file matching no declared critical path", other, model=sonnet, agents=1)

    hook = (
        "def evaluate_depth(pr_meta, files, diff):\n"
        "    if any('custom_trigger' in f for f in files):\n"
        "        return {'model': 'claude-opus-5', 'gemini_model': 'gemini-3.8-flash', "
        "'effort': 'high', 'turns': 90, 'minutes': 30, 'agents': 2, 'reason': 'custom rule'}\n"
        "    return None\n"
    )
    with _written(".py", hook) as programmatic:
        hooked = depth.evaluate(["apps/custom_trigger.py"], hook_file=programmatic)
        expect("programmatic hook", hooked, agents=2, turns=90, reason="custom rule")
        overridden = depth.evaluate([".meta/say/post", "apps/custom_trigger.py"], hook_file=programmatic)
        expect("scaffold boundary over the programmatic hook", overridden,
               agents=3, reason_has="scaffold boundary")

    example = ROOT / ".meta" / "hooks" / "depth.py.example"
    if not example.is_file():
        problems.append("depth: .meta/hooks/depth.py.example is missing")
    else:
        expect("the example hook on a migration",
               depth.evaluate(["migrations/001_initial.sql"], hook_file=example), model=opus, agents=3)
        expect("the example hook on a README",
               depth.evaluate(["README.md"], hook_file=example), model=sonnet, agents=1)
    return problems


@check("agents probes", pre=True)
def agents_probes():
    """`agents.py` counts the `Agent` calls a review transcript records, in each shape a transcript takes, and holds the count to the ceiling (solorepo's DR-191).

    Nothing — an empty string, whitespace, an empty dict, an empty list —
    counts no agent. One assistant turn holding an `Agent` call beside a
    `Read` call counts one, with the call's own id and name. Three `Agent`
    calls in one turn, which is the concurrent dispatch solorepo's DR-189
    asks for, count three. A `tool_use` id a stream emits twice counts once.
    A JSON Lines stream and a raw log quoting `tool_use` blocks between plain
    lines each count their two. The ceiling passes a count at or under it,
    passes any count when there is none, and refuses one over it naming the
    breach. A path that does not exist reads as empty, quietly, and a
    transcript written to a file reads back to the count it held.
    """
    agents = load_module(META / "agents.py", "agents_module")
    problems = []
    for case, given in (("an empty string", ""), ("a whitespace string", "   \n\t  "),
                        ("an empty dict", {}), ("an empty list", [])):
        if agents.parse_agents(given) != []:
            problems.append(f"agents: expected [] for {case}")

    single_turn = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Dispatching agents"},
            {"type": "tool_use", "id": "toolu_01", "name": "Agent",
             "input": {"description": "Review boundary path", "subagent_type": "general-purpose"}},
            {"type": "tool_use", "id": "toolu_02", "name": "Read",
             "input": {"file_path": "README.md"}},
        ],
    }
    found = agents.parse_agents(single_turn)
    if len(found) != 1 or found[0].id != "toolu_01" or found[0].name != "Agent":
        problems.append(f"agents: expected 1 agent for one turn with one Agent call, got {found}")

    concurrent_turn = [{
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": "toolu_01", "name": "Agent",
             "input": {"description": "Review boundary hooks"}},
            {"type": "tool_use", "id": "toolu_02", "name": "Agent",
             "input": {"description": "Review timing metrics"}},
            {"type": "tool_use", "id": "toolu_03", "name": "Agent",
             "input": {"description": "Review assertions"}},
        ],
    }]
    duplicate_turn = [
        {"type": "tool_use", "id": "toolu_dup", "name": "Agent", "input": {"description": "First emission"}},
        {"type": "tool_use", "id": "toolu_dup", "name": "Agent", "input": {"description": "Stream update"}},
        {"type": "tool_use", "id": "toolu_other", "name": "Agent", "input": {"description": "Distinct agent"}},
    ]
    ndjson = (
        '{"event": "start"}\n'
        '{"type": "tool_use", "id": "toolu_ndjson_1", "name": "Agent", "input": {"description": "Line 1"}}\n'
        '{"type": "tool_use", "id": "toolu_ndjson_2", "name": "Agent", "input": {"description": "Line 2"}}\n'
    )
    raw_log = (
        "Runner log output:\n"
        '{"type": "tool_use", "id": "toolu_log_1", "name": "Agent"}\n'
        "Some intervening non-json log lines\n"
        '{"type": "tool_use", "id": "toolu_log_2", "name": "Agent"}\n'
    )
    for case, transcript, count in (
        ("three concurrent Agent calls in one turn", concurrent_turn, 3),
        ("a tool_use id emitted twice", duplicate_turn, 2),
        ("a JSON Lines stream", ndjson, 2),
        ("a raw log quoting tool_use blocks", raw_log, 2),
    ):
        seen = agents.parse_agents(transcript)
        if len(seen) != count:
            problems.append(f"agents: expected {count} agents for {case}, got {len(seen)}")

    for count, ceiling, passes, says in ((2, 3, True, ""), (3, 3, True, ""),
                                         (4, 3, False, "breaching the fan-out ceiling of 3"),
                                         (5, None, True, "")):
        ok, message = agents.evaluate_ceiling(count, ceiling)
        if ok != passes or says not in message:
            wanted = f"{passes} saying {says!r}" if says else f"{passes}"
            problems.append(f"agents: evaluate_ceiling({count}, {ceiling}) expected {wanted}, "
                            f"got {ok}, {message!r}")

    missing = agents.read_content("/nonexistent/file/path/here.json", quiet=True)
    if missing != "":
        problems.append(f"agents: read_content on a missing file expected '', got {missing!r}")
    with _written(".json", json.dumps(single_turn)) as transcript_file:
        from_file = agents.parse_agents(agents.read_content(str(transcript_file)))
        if len(from_file) != 1:
            problems.append(f"agents: read_content from a written file expected 1 agent, got {len(from_file)}")
    return problems


@check("dereference probes", pre=True)
def dereference_probes():
    """`dereference.py` extracts citation pairs across the diff, sample and ground-moved scopes, and heads its report by the scope it read (solorepo's DR-134, solorepo's DR-192).

    The sample scope, asked for four pairs of the durable set, answers four,
    each carrying its path, citation, sentence and body; asked twice for
    three, it answers the same sentences both times, because the rotation is
    keyed to the commit count and not to a clock. The report, handed one pair
    marked as ground moved, heads itself with what this branch wrote or
    affected; handed the same pair as a sample, with a rotating sample. The
    report's printing is captured, and what it exited with, if it did, is
    reported beside the case.
    """
    deref = load_module(META / "dereference.py", "dereference", register=False)
    citations_mod = deref.citations()
    problems = []

    def heading(case, call, header):
        """One problem naming `case` unless the report `call` prints carries `header`."""
        shown = outcome(call)
        if header not in shown.out:
            exited = f" (exited {shown.code})" if shown.code is not None else ""
            problems.append(f"dereference: the report of {case} expected {header!r}, "
                            f"got {shown.out!r}{exited}")

    four = deref.scope(citations_mod, "origin/main", False, sample=4)
    if len(four) != 4:
        problems.append(f"dereference: sample=4 expected 4 pairs, got {len(four)}")
    for pair in four:
        if not ("path" in pair and "cite" in pair and "sentence" in pair and "body" in pair):
            problems.append(f"dereference: sample pair missing required keys: {pair}")
    first = deref.scope(citations_mod, "origin/main", False, sample=3)
    again = deref.scope(citations_mod, "origin/main", False, sample=3)
    if [p["sentence"] for p in first] != [p["sentence"] for p in again]:
        problems.append("dereference: identical sample queries produced different results")

    pairs = [{"path": "foo.md", "cite": "solorepo's DR-001", "sentence": "Testing claim.",
              "context": "Span", "body": "Body", "ground_moved": True}]
    heading("a ground-moved pair",
            lambda: deref.report([("ok", "claim")], pairs, "origin/main", False),
            "what this branch wrote or affected")
    heading("a sampled pair",
            lambda: deref.report([("ok", "claim")], pairs, "origin/main", False, sample=True),
            "a rotating sample")
    return problems


@check("search probes", pre=True)
def search_probes():
    """`search.py` indexes the assertions and the wiki, ranks by Okapi BM25F over three fields, and meets the retrieval benchmark (solorepo's DR-103, solorepo's DR-194, solorepo's DR-195).

    The index built over `.meta/assertions/` and `wiki/` holds at least a
    hundred documents. Asked who is allowed to push to trunk, the top five
    hold Article 18, solorepo's DR-100 or solorepo's DR-072; asked for
    leftover work, they hold the Concept noticed-and-not-done or
    solorepo's DR-195, the Decision that minted that ingress alias. The
    eighteen-query benchmark passes at hit@5 of fifteen or better; its
    printing is silenced, because its return value is the verdict. And a
    result's dictionary carries `id`, `score` and `source_file`.
    """
    search = load_module(META / "search.py", "search", register=False)
    problems = []
    index = search.build_index(META, ROOT)
    if len(index.docs) < 100:
        problems.append(f"search: index populated too few documents ({len(index.docs)})")

    results = index.search("who is allowed to push to trunk", top_k=5)
    ranked = [res.identifier for res in results]
    if not any(ident in ranked for ident in ("work:article/18", "work:decision/100", "work:decision/072")):
        problems.append("search: 'who is allowed to push to trunk' expected solorepo's Article 18, "
                        f"solorepo's DR-100, or solorepo's DR-072 in top 5, got {ranked}")
    leftover = [res.identifier for res in index.search("leftover work", top_k=5)]
    if "work:concept/noticed-and-not-done" not in leftover and "work:decision/195" not in leftover:
        problems.append(f"search: 'leftover work' expected noticed-and-not-done in top 5, got {leftover}")

    with contextlib.redirect_stdout(io.StringIO()):
        failed = search.run_benchmark(index)
    if failed != 0:
        problems.append(f"search: solorepo's DR-103 benchmark failed {failed} queries "
                        "below threshold (hit@5 >= 15/18)")

    if results:
        shown = results[0].to_dict()
        if not ("id" in shown and "score" in shown and "source_file" in shown):
            problems.append(f"search: SearchResult dictionary missing expected fields: {shown}")
    return problems


@check("comment probes", pre=True)
def comment_probes():
    """`comments.py`'s three detectors, against the comments they exist to catch and the comments they must let through.

    A heuristic over comment text is a boundary like any other, and the cost of
    a false positive here is a gate that refuses a licence header or a sentence
    of Reference prose. Every keep-exception has a case, and every detector has
    the innocent neighbour it must not catch (solorepo's DR-110,
    solorepo's DR-207).

    The ratchet the `inline commentary` step reads through is asked the same
    way: a count at its baseline, over it, under it, and an entry naming a file
    the tree no longer has. It is `collect.against_baseline` and is shared with
    the `meta types` step (solorepo's DR-210); both callers' site formatting
    (`comments.comment_site` and `files.mypy_errors`) and their baseline
    parameters are probed.
    """
    import comments
    problems = []

    def expect(kind, want, got, case):
        """One problem naming the detector `kind` and `case` when `got` is not `want`."""
        if want != got:
            problems.append(f"comment probes: {kind} answered {got!r} for {case!r}, expected {want!r}")

    for text in ("x = compute(1)", "return None", "import os", "del cache[key]",
                 "if ready: run()", "for item in rows:", "print(payload)",
                 "def helper(x):", "raise SystemExit(1)"):
        expect("python_code", True, comments.python_code(text), text)
    for text in ("the gate checks this", "TODO", "noqa: F401", "fmt: skip",
                 "type: ignore[attr-defined]", "reason: registration order is deliberate",
                 "Copyright 2026 the solo", "Registered last, and a reader wants it under them",
                 "one step, one line, in the shape A21 names", ""):
        expect("python_code", False, comments.python_code(text), text)

    for text in ("let x = 1;", "fn main() {", "}", "use std::io;",
                 "pub struct Seed {", "return value;"):
        expect("rust_code", True, comments.rust_code(text), text)
    for text in ("The seed crate exposes one example", "SPDX-License-Identifier: MIT",
                 "#[allow] is refused by clippy::allow_attributes", "see the xtask crate"):
        expect("rust_code", False, comments.rust_code(text), text)

    expect("keep_exception", "directive", comments.keep_exception("noqa: F401"), "noqa")
    expect("keep_exception", "notice", comments.keep_exception("Copyright 2026 the solo"), "copyright")
    expect("keep_exception", "notice", comments.keep_exception("SPDX-License-Identifier: MIT"), "spdx")
    expect("keep_exception", "citation", comments.keep_exception("GitHub collapses this, see solorepo's DR-171"), "DR")
    expect("keep_exception", "citation", comments.keep_exception("the API caps a page at 100, see https://docs.github.com/x"), "url")
    expect("keep_exception", "citation", comments.keep_exception("refused in the same words as A19, see Article 19"), "article")
    expect("keep_exception", None, comments.keep_exception("build the list first, then sort it"), "narration")

    bare = comments.suppressions("value = call()  # noqa\n")
    if not (len(bare) == 1 and bare[0][0] == 1 and "noqa" in bare[0][1]):
        problems.append(f"comment probes: bare `noqa` not caught, got {bare!r}")
    coded = comments.suppressions("value = call()  # noqa: F401  # reason: registers steps\n")
    if coded:
        problems.append(f"comment probes: `noqa: F401` should pass, got {coded!r}")
    bare_type = comments.suppressions("value = call()  # type: ignore\n")
    if not (len(bare_type) == 1 and "type: ignore" in bare_type[0][1]):
        problems.append(f"comment probes: bare `type: ignore` not caught, got {bare_type!r}")
    if comments.suppressions("value = call()  # type: ignore[attr-defined]\n"):
        problems.append("comment probes: `type: ignore[attr-defined]` should pass")
    allowed = comments.suppressions("#[allow(dead_code)]\nfn f() {}\n", rust=True)
    if not (len(allowed) == 1 and "expect" in allowed[0][1]):
        problems.append(f"comment probes: `#[allow(dead_code)]` not caught, got {allowed!r}")
    if not comments.suppressions("#![allow(clippy::all)]\n", rust=True):
        problems.append("comment probes: crate-level `#![allow(...)]` not caught")
    if comments.suppressions("#[expect(dead_code)]\nfn f() {}\n", rust=True):
        problems.append("comment probes: `#[expect(dead_code)]` should pass")
    if comments.suppressions("NOQA = re.compile(r\"#\\s*noqa\")\n"):
        problems.append("comment probes: a `noqa` inside a string literal is not a suppression")
    if comments.suppressions("/// Prefer `#[expect]`, because `#[allow(dead_code)]` outlives its cause.\n", rust=True):
        problems.append("comment probes: an `#[allow(...)]` inside a doc comment is not a suppression")
    beside = comments.suppressions("#[allow(dead_code)] // the trait is not built yet\n", rust=True)
    if not beside:
        problems.append("comment probes: an `#[allow(...)]` beside a comment is still a suppression")

    source = (
        "# a module-level comment, which is not body commentary\n"
        "URL = \"https://example.test/#not-a-comment\"\n"
        "def f():\n"
        "    \"\"\"A Reference docstring, which is a string and never a comment.\"\"\"\n"
        "    # narration, on two lines\n"
        "    # that is one block\n"
        "    value = 1  # SPDX-License-Identifier: MIT\n"
        "    other = 2  # the header caps at 100, see solorepo's DR-171\n"
        "    return value + other  # noqa: F401  # reason: a directive\n"
    )
    found = [b for b in comments.blocks(comments.python_comments(source))
             if b.inline and comments.keep_exception(b.text) is None]
    if len(found) != 1 or found[0].line != 5:
        problems.append(f"comment probes: expected one body comment at line 5, got "
                        f"{[(b.line, b.text) for b in found]!r}")
    if any(comments.python_code(c.text) for c in comments.python_comments(source)):
        problems.append("comment probes: a false positive for commented-out code in the sample")

    here = pathlib.Path(__file__).relative_to(ROOT).as_posix()
    one = [comments.comment_site(here, found[0])]
    if one[0] != f"{here}:5: `narration, on two lines that is one block`":
        problems.append(f"comment probes: comment_site gave {one[0]!r}")

    def ratcheted(counts, sites, recorded):
        """The shared ratchet, asked about counts under the `inline commentary` step's baseline."""
        return against_baseline(counts, sites, recorded, "body comments", comments.BASELINE)

    if ratcheted({here: 1}, {here: one}, {here: 1}):
        problems.append("comment probes: a file at its baseline should pass")
    grew = ratcheted({here: 2}, {here: one}, {here: 1})
    if not any("over its baseline of 1" in line for line in grew):
        problems.append(f"comment probes: a file over its baseline should fail, got {grew!r}")
    fell = ratcheted({here: 1}, {here: one}, {here: 2})
    if not any("under its baseline of 2" in line for line in fell):
        problems.append(f"comment probes: a file under its baseline should fail, got {fell!r}")
    if not any(f"     {one[0]}" in line for line in grew):
        problems.append(f"comment probes: a failing file should list its sites, got {grew!r}")
    stale = ratcheted({}, {}, {"no/such/file.py": 3})
    if not any("does not exist" in line for line in stale):
        problems.append(f"comment probes: a baseline entry for a missing file should fail, got {stale!r}")
    if ratcheted({}, {}, {}):
        problems.append("comment probes: an empty baseline over a clean tree should pass")

    import files
    mypy_sample = f"{here}:42: error: Need type annotation  [var-annotated]\n"
    type_counts, type_sites = files.mypy_errors(mypy_sample)
    if type_counts != {here: 1}:
        problems.append(f"comment probes: mypy_errors counts gave {type_counts!r}")
    expected_site = f"{here}:42: Need type annotation  [var-annotated]"
    if type_sites != {here: [expected_site]}:
        problems.append(f"comment probes: mypy_errors sites gave {type_sites!r}")
    type_grew = against_baseline({here: 1}, type_sites, {here: 0},
                                 "type errors", files.TYPES_BASELINE)
    if not any("1 type errors, over its baseline of 0" in line for line in type_grew):
        problems.append(f"comment probes: type errors over baseline should fail, got {type_grew!r}")
    if not any(f"     {expected_site}" in line for line in type_grew):
        problems.append(f"comment probes: type error site not formatted, got {type_grew!r}")

    rust = (
        "// A plain line comment.\n"
        "const URL: &str = \"https://example.test\";\n"
        "/* a block comment\n"
        "   over two lines */\n"
        "/// let doubled = lines(\" a \");\n"
        "fn f() {}\n"
    )
    seen = comments.rust_comments(rust)
    if [c.line for c in seen] != [1, 3, 4, 5]:
        problems.append(f"comment probes: rust_comments read lines {[c.line for c in seen]!r}, expected [1, 3, 4, 5]")
    if [c.doc for c in seen] != [False, False, False, True]:
        problems.append(f"comment probes: rust_comments marked {[c.doc for c in seen]!r} as doc, "
                        "expected only the `///` line")
    return problems
