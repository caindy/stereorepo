"""The routing policy and the prompt forms behind `on`, and its `between` phase over a fake ladder.

One module for one subject's probes (solorepo's DR-209): the chain a door
resolves for a Role, pass and level, the step outputs it names the chain
by, the prompt a rung is rendered from its pass's form, and the phase
between two rungs that says whether the next runs (solorepo's DR-281).
"""
import contextlib
import functools
import json
import os
import pathlib
import re
import tempfile
from collections.abc import Iterator
from typing import Any, NamedTuple

import yaml

from checks.collect import ROOT, check
from checks.probes.harness import environment, load_channel, outcome, stood_in

FORMS = ROOT / ".meta" / "templates" / "prompts"
"""Where the prompt forms are."""

FIELDS = {"number": "7", "repository": "o/r", "level": "medium", "branch_prefix": "claude",
          "resume": "No run has taken this Issue before.", "branch": "claude/issue-7",
          "base": "main", "issue": "7", "stop": "`.meta/say/move stop 7` with why on stdin.",
          "login": "o-r-reviewer", "head": "abc123", "agents": "3"}
"""Every field any door fills, with a value a rendering can be read for."""

FIELDS_BY_PASS: dict[tuple[str, str], tuple[str, ...]] = {
    ("coder", "take"): ("number", "repository", "level", "branch_prefix", "resume"),
    ("coder", "rebase"): ("number", "repository", "branch", "base", "issue"),
    ("coder", "answer"): ("number", "repository", "branch", "base", "issue", "stop"),
    ("coder", "promote"): ("number", "repository", "branch", "base", "issue"),
    ("reviewer", "review"): ("number", "repository", "head", "login", "agents"),
    ("reviewer", "read"): ("number", "repository", "login"),
}
"""The fields each door writes on each pass, as `coder_door.coder_before`, `pull_fields`,
`review.review_before` and `common.reading_before` fill them: the contract a form is rendered
against, and not the union."""

DELIBERATE = {("reviewer", "read"): ("level",)}
"""Angle brackets that survive rendering on purpose: the reading form's `<level>` is the verdict
the session is there to decide, shown in the command it will type."""

PROMPT_STEPS = {
    "coder.yml": {"take_claude": ("coder", "take", "claude"),
                  "take_gemini": ("coder", "take", "gemini"),
                  "rebase_claude": ("coder", "rebase", "claude"),
                  "rebase_gemini": ("coder", "rebase", "gemini"),
                  "answer_claude": ("coder", "answer", "claude"),
                  "answer_gemini": ("coder", "answer", "gemini"),
                  "promote_claude": ("coder", "promote", "claude"),
                  "promote_gemini": ("coder", "promote", "gemini")},
    "review.yml": {"review_claude": ("reviewer", "review", "claude"),
                   "review_gemini": ("reviewer", "review", "gemini"),
                   "review_jules": ("reviewer", "review", "jules")},
    "triage.yml": {"read_claude": ("reviewer", "read", "claude"),
                   "read_gemini": ("reviewer", "read", "gemini")},
}
"""Each workflow step whose prompt a form was extracted from, and the Role, pass and harness the
form is rendered for. Held while both copies exist, which is until the second layer of
solorepo's DR-281 points the workflows at the forms."""

EXPRESSIONS = {
    "github.event.issue.number || inputs.issue": "number",
    "github.event.issue.number": "number",
    "github.event.pull_request.number": "number",
    "github.event.pull_request.head.sha": "head",
    "github.repository": "repository",
    "steps.before.outputs.level": "level",
    "steps.before.outputs.turns": "turns",
    "steps.before.outputs.minutes": "minutes",
    "steps.before.outputs.effort": "effort",
    "steps.before.outputs.agents": "agents",
    "steps.before.outputs.branch_prefix": "branch_prefix",
    "steps.before.outputs.number": "number",
    "steps.before.outputs.branch": "branch",
    "steps.before.outputs.base": "base",
    "steps.before.outputs.issue": "issue",
}
"""Each GitHub expression a workflow prompt interpolates, and the field the form names it by."""

UNIFIED = (("`AGENTS.md` (and `GEMINI.md`)", "`AGENTS.md`"), ("<n>", "<number>"),
           ("(claude|gemini)/issue-*", "claude/issue-*"),
           ("enforced by solorepo's DR-176", "solorepo's DR-176"))
"""What the forms say one way where the two workflow prompts said it two ways, each read as the
same words on both sides: the conventions file both harnesses read, the pull request's number
where one prompt wrote `<n>`, the branch shapes both loops cut, and a citation corrected."""

LOGIN = "${{ github.repository_owner }}-${{ github.event.repository.name }}-reviewer"
"""How a workflow prompt spells the reviewer's login, which the form names `<login>`."""

JULES_LINE = f"Review pull request #{FIELDS['number']}"
"""The one line the review form is on Jules."""

PASSES = (("coder", "take"), ("coder", "rebase"), ("coder", "answer"), ("coder", "promote"),
          ("reviewer", "review"), ("reviewer", "read"))
"""Each Role's passes, which is each form."""

OFF: dict[str, str | None] = {"GEMINI_FALLBACK": None, "JULES_FALLBACK": None}
"""No fallback toggled."""

ON: dict[str, str | None] = {"GEMINI_FALLBACK": "true", "JULES_FALLBACK": "true"}
"""Every fallback toggled."""

OPEN = "12"
"""The pull request a take's branch already holds, in the cases that say one does."""


@check("routing probes", pre=True)
def routing_probes() -> list[str]:
    """The chain, its outputs, every form on every harness, and `between` (solorepo's DR-281).

    The coder's chain is Claude Code alone with nothing toggled, Claude Code
    then the Antigravity CLI with the Gemini toggle on, and the Antigravity
    CLI first where a label chose it, Claude Code following without any
    toggle, since Claude Code is the harness every portfolio has. The
    reviewer's runs three deep with both toggles on, Jules last, and a Jules
    primary is followed by Claude Code and then the Antigravity CLI. The
    depth is by pass first and level after, and no number differs from the
    ones the doors emitted before the policy held them. The outputs carry
    `tiers` and `tier_<n>_<field>` for each rung from one.

    Every form renders for Claude Code and for the Antigravity CLI: the
    block of the other harness is gone, no marker survives, no field the
    door fills survives as an angle bracket, and the budget sentence names
    the turn cap on Claude Code and the clock alone on the Antigravity CLI.
    The review form on Jules is its one line.

    `between`, handed the chain `before` wrote: a rung that failed with a
    rung after it answers `run=true` and writes the next rung's prompt, a
    rung that finished answers `run=false`, a cancelled one likewise, and
    the last rung failing answers `run=false` since nothing follows. On a
    take the branch is read again and the prompt's resume clause follows
    what it found; a pass other than a take is answered too once a rung is
    named, and refused only on the older question that names none.
    """
    _, _, programs = load_channel()
    on = programs["on"]
    return (_chain_cases(on) + _output_cases(on) + _form_cases(on) + _parity_cases(on)
            + _between_cases(on))


def _chain_cases(on: Any) -> list[str]:
    """The chain by Role, primary and toggles, and the depth by pass and level."""
    problems = []
    routing = on.routing
    cases: tuple[tuple[str, tuple[str, ...], dict[str, str | None], tuple[str, ...]], ...] = (
        ("coder", ("claude", "take", "medium"), OFF, ("claude",)),
        ("coder", ("claude", "take", "medium"), ON, ("claude", "gemini")),
        ("coder", ("gemini", "take", "easy"), OFF, ("gemini", "claude")),
        ("coder", ("gemini", "answer", "medium"), ON, ("gemini", "claude")),
        ("reviewer", ("claude",), OFF, ("claude",)),
        ("reviewer", ("claude",), ON, ("claude", "gemini", "jules")),
        ("reviewer", ("jules",), ON, ("jules", "claude", "gemini")),
        ("reviewer", ("gemini",), {"GEMINI_FALLBACK": None, "JULES_FALLBACK": "true"},
         ("gemini", "claude", "jules")),
        ("reading", ("claude",), OFF, ("claude",)),
        ("reading", ("gemini",), ON, ("gemini", "claude")),
    )
    for role, asked, toggles, expected in cases:
        environ = {name: value for name, value in toggles.items() if value is not None}
        if role == "coder":
            tiers = routing.coder_chain(*asked, environ=environ)
        elif role == "reviewer":
            tiers = routing.review_chain(asked[0], routing.REVIEW_DEPTHS["deep"],
                                         routing.GEMINI_MODEL, environ=environ)
        else:
            tiers = routing.reading_chain(asked[0], environ=environ)
        found = tuple(rung.harness for rung in tiers)
        if found != expected:
            problems.append(f"routing: the {role}'s chain for {asked!r} under {toggles!r} is "
                            f"{found!r}, not {expected!r}")
        for rung in tiers:
            if rung.agent != routing.AGENTS[rung.harness]:
                problems.append(f"routing: rung {rung!r} is signed by {rung.agent!r}")
    depths = (("take", "medium", ("claude-opus-5", "high", "120", "60")),
              ("take", "easy", ("claude-sonnet-5", "medium", "60", "30")),
              ("rebase", "medium", ("claude-opus-5", "high", "60", "30")),
              ("answer", "medium", ("claude-opus-5", "high", "120", "60")),
              ("promote", "medium", ("claude-sonnet-5", "medium", "30", "15")))
    for task, level, numbers in depths:
        depth = tuple(routing.coder_depth(task, level))
        if depth != numbers:
            problems.append(f"routing: the coder's depth on {task} at {level} is {depth!r}, "
                            f"not {numbers!r}")
    for name, config in (("deep", on.depth.DEEP_CONFIG), ("standard", on.depth.STANDARD_CONFIG)):
        held = routing.Depth(config.model, config.effort, str(config.turns), str(config.minutes))
        if held != routing.REVIEW_DEPTHS[name] or config.agents != routing.REVIEW_FANOUT[name] \
                or config.gemini_model != routing.GEMINI_MODEL:
            problems.append(f"routing: depth.py's {name} tier {config!r} differs from the "
                            f"policy's {routing.REVIEW_DEPTHS[name]!r}, which it is held equal "
                            "to until the layer that reads it from there (solorepo's DR-281)")
    gemini = routing.tier("gemini", routing.REVIEW_DEPTHS["standard"], "gemini-x")
    jules = routing.tier("jules", routing.REVIEW_DEPTHS["standard"])
    if gemini.model != "gemini-x" or jules.model != "":
        problems.append(f"routing: the Antigravity rung runs {gemini.model!r} where a depth hook "
                        f"chose gemini-x, and the Jules rung runs {jules.model!r} where it "
                        "chooses its own")
    return problems


def _output_cases(on: Any) -> list[str]:
    """The chain as step outputs: `tiers`, and every field of every rung by number."""
    routing = on.routing
    tiers = routing.coder_chain("claude", "take", "medium", environ=dict(ON))
    named = routing.outputs(tiers)
    expected = {"tiers": "2", "tier_1_harness": "claude", "tier_1_model": "claude-opus-5",
                "tier_1_turns": "120", "tier_1_agent": "anthropics/claude-code-action@v1",
                "tier_2_harness": "gemini", "tier_2_model": routing.GEMINI_MODEL,
                "tier_2_minutes": "60", "tier_2_agent": "antigravity-cli"}
    missing = {key: value for key, value in expected.items() if named.get(key) != value}
    if missing:
        return [f"routing: the outputs {named!r} do not carry {missing!r}"]
    return []


def _form_cases(on: Any) -> list[str]:
    """Every form rendered with its own pass's fields, for every harness that takes it."""
    problems = []
    routing, prompts = on.routing, on.prompts
    depth = routing.Depth("claude-opus-5", "high", "120", "60")
    for (role, task), names in FIELDS_BY_PASS.items():
        form = FORMS / f"{role}-{task}.md"
        if not form.is_file():
            problems.append(f"prompts: {form.relative_to(ROOT)} is missing")
            continue
        fields = {name: FIELDS[name] for name in names}
        allowed = DELIBERATE.get((role, task), ())
        for harness in ("claude", "gemini"):
            text = prompts.render(role, task, routing.tier(harness, depth), fields)
            if "<!--" in text:
                problems.append(f"prompts: a block marker survives in {role}-{task} on {harness}")
            survivors = [name for name in FIELDS if f"<{name}>" in text and name not in allowed]
            if survivors:
                problems.append(f"prompts: {survivors!r} survive in {role}-{task} on {harness}, "
                                f"which the {role}'s door fills with {names!r} on that pass")
            if FIELDS["number"] not in text:
                problems.append(f"prompts: {role}-{task} on {harness} names no number")
            capped = "120 turns and 60 minutes" in text
            clocked = "60 minutes and no turn cap" in text
            if role == "coder" and (capped, clocked) != (harness == "claude", harness == "gemini"):
                problems.append(f"prompts: {role}-{task} on {harness} names the caps as "
                                f"capped={capped} clocked={clocked}")
            if harness == "gemini" and role == "coder" and task == "take" \
                    and "subagent" not in text.lower():
                problems.append("prompts: the take form on gemini does not refuse subagents "
                                "(solorepo's DR-257)")
            if harness == "claude" and "invoke_subagent" in text:
                problems.append(f"prompts: the Antigravity block survives in {role}-{task} on "
                                "claude")
    jules = routing.tier("jules", depth)
    if prompts.render("reviewer", "review", jules, FIELDS).strip() != JULES_LINE:
        problems.append("prompts: the review form on Jules did not render as its one line")
    if "turns" in prompts.budget(jules) or "Jules" not in prompts.budget(jules):
        problems.append(f"prompts: the budget sentence on Jules is {prompts.budget(jules)!r}, "
                        "where a harness binding no turn cap is told none")
    return problems


def _placeholders(prompt: str) -> tuple[str, list[str]]:
    """A workflow prompt with each GitHub expression read as the field the form names it by.

    Returns:
        tuple[str, list[str]]: The prompt over placeholders, and each expression the table
            does not know, which is a prompt that moved under the form.
    """
    unknown: list[str] = []
    text = prompt.replace(LOGIN, "<login>")

    def named(found: re.Match[str]) -> str:
        inner = " ".join(found.group(1).split())
        if "format(" in inner and "resume" in inner:
            return "<resume>"
        if "format(" in inner and "stop" in inner:
            return "<stop>"
        if inner in EXPRESSIONS:
            return f"<{EXPRESSIONS[inner]}>"
        unknown.append(inner)
        return f"<?{inner}?>"

    return re.sub(r"\$\{\{(.*?)\}\}", named, text, flags=re.S), unknown


def _same_words(text: str) -> str:
    """The text with the deliberate unifications applied and its whitespace collapsed."""
    for before, after in UNIFIED:
        text = text.replace(before, after)
    return " ".join(text.split())


def _parity_cases(on: Any) -> list[str]:
    """Each form says what the workflow prompt it was extracted from says, for its harness.

    The workflow prompt is read over placeholders, each GitHub expression
    replaced by the field the form names it by, and the form is rendered
    for the harness with every field left as its own angle bracket, so the
    two are the same text wherever the extraction was faithful. The
    unifications the forms made on purpose are read the same on both sides,
    and any other difference is reported at the first place it appears.
    """
    problems = []
    routing, prompts = on.routing, on.prompts
    same = routing.Depth("<model>", "<effort>", "<turns>", "<minutes>")
    for workflow, steps in PROMPT_STEPS.items():
        path = ROOT / ".github" / "workflows" / workflow
        if not path.is_file():
            problems.append(f"forms: {workflow} is missing, and the forms were extracted from it")
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        by_id = {step.get("id"): step for job in (loaded.get("jobs") or {}).values()
                 for step in job.get("steps") or [] if isinstance(step, dict)}
        for step_id, (role, task, harness) in steps.items():
            if step_id not in by_id:
                problems.append(f"forms: {workflow} has no step `{step_id}`; the form probe "
                                "reads the prompt there")
                continue
            prompt = str((by_id[step_id].get("with") or {}).get("prompt") or "")
            expected, unknown = _placeholders(prompt)
            for expression in unknown:
                problems.append(f"forms: {workflow} `{step_id}` interpolates `{expression}`, "
                                "which the probe cannot read as a field")
            rendered = prompts.render(role, task, routing.tier(harness, same),
                                      {name: f"<{name}>" for name in FIELDS})
            want, got = _same_words(expected), _same_words(rendered)
            if want != got:
                at = next((i for i, (a, b) in enumerate(zip(want, got, strict=False)) if a != b),
                          min(len(want), len(got)))
                problems.append(f"forms: {role}-{task} on {harness} differs from {workflow} "
                                f"`{step_id}` at {at}: form says {got[at:at + 90]!r}, workflow "
                                f"says {want[at:at + 90]!r}")
    return problems


@contextlib.contextmanager
def _workspace() -> Iterator[pathlib.Path]:
    """A temporary working directory with `GITHUB_OUTPUT` and `GITHUB_ENV` files, as a run has."""
    held = pathlib.Path.cwd()
    with tempfile.TemporaryDirectory() as where:
        root = pathlib.Path(where)
        (root / "output").touch()
        (root / "env").touch()
        os.chdir(root)
        try:
            with environment(GITHUB_OUTPUT=str(root / "output"), GITHUB_ENV=str(root / "env"),
                             GITHUB_SERVER_URL="https://github.com", GITHUB_REPOSITORY="o/r",
                             GITHUB_RUN_ID="99", ACTOR_SESSION="gha-99", ACTOR_AGENT=None):
                yield root
        finally:
            os.chdir(held)


class _Branch:
    """A stand-in for `loop_pull`, answering what is open on the Challenge's branch."""

    def __init__(self, pull: dict[str, Any] | None) -> None:
        self.pull = pull

    def __call__(self, issue: str | int, fields: str, default: Any = None) -> Any:
        return dict(self.pull) if self.pull else None


class _Rung(NamedTuple):
    """One `between` case: the pass, the chain, which rung ended and how, and what is open."""

    task: str
    tiers: tuple[str, ...]
    attempt: int | None
    ended: str
    pull: dict[str, Any] | None = None


def _between(on: Any, case: _Rung) -> tuple[Any, dict[str, str], str]:
    """`on coder between` after `before` wrote a chain: how it ended, the outputs, the prompt."""
    routing = on.routing
    depth = routing.coder_depth(case.task, "medium")
    with _workspace() as root, stood_in(on.check_pr.sweep, loop_pull=_Branch(case.pull)):
        chain = tuple(routing.tier(name, depth) for name in case.tiers)
        on.write_routing("coder", case.task, chain, FIELDS)
        (root / ".review" / "prompt.md").unlink()
        ended_as = outcome(lambda: on.coder(
            "between", FIELDS["number"], on.Delivery(case.task, "issues", ""),
            on.Ended("failure", "skipped", None, "claude"), on.Attempt(case.attempt, case.ended)))
        out = dict(line.split("=", 1) for line in (root / "output").read_text().splitlines()
                   if "=" in line)
        prompt = root / ".review" / "prompt.md"
        written = prompt.read_text() if prompt.is_file() else ""
    return ended_as, out, written


def _unnumbered_cases(on: Any) -> list[str]:
    """A rung not numbered from one, or an outcome that did not arrive, is refused on either Role.

    The reviewer's door reaches `fallback` with whatever the workflow handed,
    so each is put to it there: an `Attempt` with no number would otherwise
    place the primary as the rung that just ran and run it again, and one
    with no outcome would end the ladder green.
    """
    problems = []
    depth = on.routing.REVIEW_DEPTHS["deep"]
    chain = (on.routing.tier("claude", depth), on.routing.tier("gemini", depth))
    for handed, name in ((on.Attempt(None, "failure"), "no rung numbered"),
                         (on.Attempt(0, "failure"), "a rung numbered from zero"),
                         (on.Attempt(-1, "failure"), "a rung numbered below zero"),
                         (on.Attempt(1, None), "an outcome that did not arrive")):
        with _workspace() as root:
            on.write_routing("reviewer", "review", chain, FIELDS)
            (root / ".review" / "prompt.md").unlink()
            ended = outcome(functools.partial(on.reviewer, "between", FIELDS["number"],
                                              on.Session(None, None, None, ""), handed))
            out = (root / "output").read_text()
            written = (root / ".review" / "prompt.md").is_file()
        if ended.code is None or "not a ladder that quietly stops" not in str(ended.code) \
                or "run=" in out or written:
            problems.append(f"between: {name} ended {ended.code!r} with outputs {out!r} and a "
                            f"prompt written={written}, where the phase refuses rather than "
                            "placing the primary or ending the ladder green")
    return problems


def _between_cases(on: Any) -> list[str]:
    """Between two rungs: the next runs on a failure alone, and the take's resume clause."""
    problems = []
    ended, out, prompt = _between(on, _Rung("answer", ("claude", "gemini"), 1, "failure"))
    if ended.code is not None or out.get("run") != "true" or "no turn cap" not in prompt \
            or f"#{FIELDS['number']}" not in prompt:
        problems.append(f"between: rung 1 of 2 failing decided {out!r} with exit {ended.code!r} "
                        f"and wrote {prompt[:80]!r}, where rung 2 runs on the Antigravity CLI")
    for outcome_of_rung in ("success", "cancelled", "skipped"):
        ended, out, prompt = _between(on, _Rung("answer", ("claude", "gemini"), 1, outcome_of_rung))
        if ended.code is not None or out.get("run") != "false" or prompt:
            problems.append(f"between: rung 1 ending {outcome_of_rung} decided {out!r}, where "
                            "only a failure hands the pass on")
    ended, out, prompt = _between(on, _Rung("answer", ("claude", "gemini"), 2, "failure"))
    if ended.code is not None or out.get("run") != "false" or prompt:
        problems.append(f"between: the last rung failing decided {out!r}, where nothing follows")
    ended, out, prompt = _between(on, _Rung("take", ("gemini", "claude"), 1, "failure",
                                            {"number": int(OPEN)}))
    if ended.code is not None or out.get("run") != "true" or out.get("resume") != OPEN \
            or f"left pull request #{OPEN} open" not in prompt or "120 turns" not in prompt:
        problems.append(f"between: a take's rung 1 failing over open pull request {OPEN} decided "
                        f"{out!r} and wrote {prompt[:80]!r}, where rung 2 is Claude Code told to "
                        "resume")
    ended, out, prompt = _between(on, _Rung("take", ("claude", "gemini"), 1, "failure"))
    if out.get("resume") != "" or "No harness has left a pull request" not in prompt:
        problems.append(f"between: a take's rung 1 failing over nothing decided {out!r} and "
                        f"wrote {prompt[:80]!r}")
    ended, out, prompt = _between(on, _Rung("rebase", ("claude", "gemini"), None, "failure"))
    if ended.code is None or "named no rung" not in str(ended.code):
        problems.append(f"between: the rebase pass asked the older question ended {ended.code!r}, "
                        "where a pass whose prompt carries no resume clause is refused")
    with _workspace() as root:
        with contextlib.suppress(FileNotFoundError):
            (root / ".review").rmdir()
        ended = outcome(lambda: on.fallback(on.Attempt(1, "failure")))
    if ended.code is None or "nothing is there" not in str(ended.code):
        problems.append(f"between: with no chain written it ended {ended.code!r}, where the "
                        "phase refuses rather than guessing a ladder")
    problems += _unnumbered_cases(on)
    with _workspace() as root:
        on.write_routing("reviewer", "review", (on.routing.tier("claude",
                                                                on.routing.REVIEW_DEPTHS["deep"]),
                                                on.routing.tier("jules",
                                                                on.routing.REVIEW_DEPTHS["deep"])),
                         FIELDS)
        ended = outcome(lambda: on.reviewer("between", FIELDS["number"],
                                            on.Session(None, None, None, ""),
                                            on.Attempt(1, "failure")))
        out = dict(line.split("=", 1) for line in (root / "output").read_text().splitlines()
                   if "=" in line)
        prompt = (root / ".review" / "prompt.md").read_text()
        routed = json.loads((root / ".review" / "routing.json").read_text())
    if ended.code is not None or out.get("run") != "true" or prompt.strip() != JULES_LINE \
            or routed["tiers"][1]["harness"] != "jules":
        problems.append(f"between: the reviewer's rung 1 failing before Jules decided {out!r} "
                        f"and wrote {prompt!r}")
    return problems
