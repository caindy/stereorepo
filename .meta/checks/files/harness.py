"""
What a loop workflow's steps owe the harness they start: a signed run names the
harness under the variable the channel reads (solorepo's DR-233), an agy call
site passes a harness rather than the empty string, each coder prompt names the
caps its own step binds, a workflow that reads the fallback exports it
(solorepo's DR-245), and the take pass's second prompt reads the branch as the
step before it found it.

History in files.history.md (solorepo's DR-171).
"""

import re
from typing import Any

import yaml

from checks.collect import (
    ROOT,
    CouldNotRun,
    Found,
    Passed,
    StepOutcome,
    check,
)
from checks.files.workflows import WORKFLOWS, workflow_files

WRITES_AGENT = re.compile(r"\bAI_AGENT=")
"""A workflow naming the harness in the variable the harness itself overwrites."""


WRITES_RUN_AGENT = re.compile(r"\bACTOR_AGENT=")
"""A workflow naming the harness in the variable it writes before the harness starts,
which is the one the channel signs with in a run (solorepo's DR-233)."""


@check("signed runs name their harness")
def signed_runs_name_their_harness() -> StepOutcome:
    """A workflow writes `ACTOR_AGENT` wherever it writes `AI_AGENT` (solorepo's DR-233).

    `channel.agent()` does not read `AI_AGENT` in a run, because the harness
    overwrites that name with its own build string and a value the agent's shell
    typed there cannot be told from the ordinary one. `ACTOR_AGENT` is what the
    workflow writes before the harness starts, and a run that carries none signs
    with the step GitHub attests instead — which says which step spoke and not
    which harness. So the two names are written together, in the fallback steps
    as much as in the step that chooses, and this fails where a file writes one
    without the other.

    Returns:
        Passed | Found | CouldNotRun: The counts per workflow, or each file
        whose two names are written a different number of times.
    """
    if not WORKFLOWS.is_dir():
        return CouldNotRun(f"{WORKFLOWS.relative_to(ROOT).as_posix()} is missing")
    problems, counted = [], 0
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        chosen, signed_with = len(WRITES_AGENT.findall(text)), len(WRITES_RUN_AGENT.findall(text))
        counted += chosen
        if chosen != signed_with:
            problems.append(f"{path.relative_to(ROOT)}: writes `AI_AGENT` {chosen} time(s) and "
                            f"`ACTOR_AGENT` {signed_with}; the channel signs a run with the "
                            "second, so every write of the first has one beside it")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} harness names written, each under both variables")


AGENT_FROM_STEP = re.compile(r"^\s*(ACTOR_AGENT|AI_AGENT):\s*(\$\{\{.*steps\..*\}\})\s*$", re.M)
"""A step naming its harness from another step's output, which is empty when that step
did not run or took a branch that wrote no such output."""


@check("harness names from step outputs have a default")
def harness_names_from_step_outputs_have_a_default() -> StepOutcome:
    """A step `env:` naming its harness from a step output supplies a fallback (solorepo's #836).

    A step-level `env:` beats the job environment `name_harness` wrote, and it
    beats it with the empty string as readily as with a name: a step output is
    the empty string wherever the emitting step was skipped or took a branch
    that wrote no such key. `channel.agent()` then falls through to the step
    GitHub attests, which says which step spoke and not which harness — the
    degraded reading solorepo's DR-233 names. So an expression of this shape
    carries `|| <the chosen harness's name>`, and this fails where one does not.

    Returns:
        Passed | Found | CouldNotRun: The expressions counted, or each file and
        variable whose expression can resolve to nothing.
    """
    files = sorted(workflow_files())
    if not files:
        return CouldNotRun("no workflows or composite actions found to scan")
    problems, counted = [], 0
    for path in files:
        for name, expression in AGENT_FROM_STEP.findall(path.read_text(encoding="utf-8")):
            counted += 1
            if "||" in expression:
                continue
            problems.append(f"{path.relative_to(ROOT)}: sets `{name}` to `{expression}`, which is "
                            "the empty string wherever that step wrote no such output, and an "
                            "empty step `env:` unnames the run as surely as a wrong one; give it "
                            "`|| <the chosen harness's name>`")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} harness name(s) taken from a step output, each with a default")


AGY_ACTION = "./.meta/actions/agy"
"""The agy composite action's `uses:` path, as every call site names it."""


def _steps(doc: dict[str, Any]) -> list[Any]:
    """The steps a workflow job or a composite action's `runs:` declares."""
    steps: list[Any] = []
    for job in (doc.get("jobs") or {}).values():
        steps.extend(job.get("steps") or [])
    steps.extend((doc.get("runs") or {}).get("steps") or [])
    return steps


@check("agy callers pass a non-empty agent")
def agy_callers_pass_a_non_empty_agent() -> StepOutcome:
    """A step invoking the agy action supplies a non-empty `agent` input (solorepo's #836).

    `harness_names_from_step_outputs_have_a_default` proves the default inside
    the action reads `inputs.agent`; that default only closes solorepo's #836
    where every caller passes a non-empty value for it. This is the other half
    of the same invariant: a step whose `uses:` names the agy action, with no
    `agent:` input or one that is the empty string, hands `ACTOR_AGENT` and
    `AI_AGENT` the empty string on the direct-harness path regardless of what
    the action defaults to.

    Returns:
        Passed | Found | CouldNotRun: The call sites counted, or each file and
        step carrying no non-empty `agent` input.
    """
    files = sorted(workflow_files())
    if not files:
        return CouldNotRun("no workflows or composite actions found to scan")
    problems, counted = [], 0
    for path in files:
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        for step in _steps(doc):
            if not isinstance(step, dict) or step.get("uses") != AGY_ACTION:
                continue
            counted += 1
            if (step.get("with") or {}).get("agent"):
                continue
            problems.append(f"{path.relative_to(ROOT)}: a step using {AGY_ACTION} carries no "
                            "non-empty `agent:` input, which hands ACTOR_AGENT and AI_AGENT the "
                            "empty string on the direct-harness path; give it "
                            "`agent: ${{ steps.before.outputs.agent }}`")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} agy call site(s), each passing a non-empty agent")


CODER_WORKFLOW = WORKFLOWS / "coder.yml"
"""The coder Role's loop: its passes carry a minute cap and, on the harness that takes one, a
turn cap from `DEPTHS`, and its take pass runs two harness steps in turn (solorepo's DR-245)."""


TURN_CAP = "--max-turns"
"""The argument that binds a turn cap, which Claude Code takes and the Antigravity CLI does
not: `.meta/run_agy.py` builds its argument vector with `--print-timeout` alone, so a turn
number told to an `agy` session binds nothing."""


TURNS_OUTPUT, MINUTES_OUTPUT = "steps.before.outputs.turns", "steps.before.outputs.minutes"
"""The step outputs `coder_depth` emits the two caps as."""


@check("coder prompts name their turn budget")
def coder_prompts_name_turn_budget() -> StepOutcome:
    """Every coder prompt names the caps its own step binds, and no others.

    `.meta/say/on`'s `coder_depth` picks a pass's turn cap and minute cap from
    `DEPTHS` and emits them as step outputs. `timeout-minutes` binds the minute
    cap on every pass; `--max-turns` binds the turn cap on the Claude steps
    alone. A prompt naming neither leaves the session it runs unable to pace
    itself or to hand off before the cap, and one naming a cap its harness does
    not take teaches that session to discount the cap that does bind. So each
    prompt asks for the minute cap, and for the turn cap exactly where the step
    passes `--max-turns`. The steps are read out of the `coder` job rather than
    enumerated, so a pass or a harness given a prompt later is read the same.

    Returns:
        Passed | Found | CouldNotRun: Validation result naming any prompt that
        does not name the caps its own step binds.
    """
    if not CODER_WORKFLOW.is_file():
        return CouldNotRun(f"{CODER_WORKFLOW.relative_to(ROOT).as_posix()} is missing")
    data = yaml.safe_load(CODER_WORKFLOW.read_text(encoding="utf-8")) or {}
    steps = (data.get("jobs") or {}).get("coder", {}).get("steps") or []
    where, problems, counted = CODER_WORKFLOW.relative_to(ROOT), [], 0
    for step in steps:
        given = (step.get("with") or {}) if isinstance(step, dict) else {}
        prompt = str(given.get("prompt") or "")
        if not prompt:
            continue
        counted += 1
        named = step.get("id") or step.get("name") or "<unnamed>"
        binds_turns = TURN_CAP in str(given.get("claude_args") or "")
        if MINUTES_OUTPUT not in prompt:
            problems.append(f"{where}: step {named!r}'s prompt does not name {MINUTES_OUTPUT}, "
                            "so the session it runs cannot hand off before `timeout-minutes` "
                            "ends it")
        if binds_turns and TURNS_OUTPUT not in prompt:
            problems.append(f"{where}: step {named!r} passes {TURN_CAP} and its prompt does not "
                            f"name {TURNS_OUTPUT}, so the session it runs cannot pace itself "
                            "against the cap it is given")
        if not binds_turns and TURNS_OUTPUT in prompt:
            problems.append(f"{where}: step {named!r}'s prompt names {TURNS_OUTPUT} and the step "
                            f"passes no {TURN_CAP}, so it tells the session a number that binds "
                            "nothing")
    if not counted:
        return CouldNotRun(f"{where}'s `coder` job has no prompt-bearing step")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} coder prompts each name the caps their own step binds")


FALLBACK_ENV_EXPORT = re.compile(r"^\s*GEMINI_FALLBACK:\s*\${{\s*vars\.GEMINI_FALLBACK\b", re.M)
"""A workflow that invokes detect_fallback.py exports GEMINI_FALLBACK from vars.GEMINI_FALLBACK in job env (solorepo's DR-245)."""


@check("fallback workflows export GEMINI_FALLBACK")
def fallback_workflows_export_gemini_fallback() -> StepOutcome:
    """Workflows that run detect_fallback.py or actions/agy map vars.GEMINI_FALLBACK into job env (solorepo's DR-245, solorepo's #699).

    GitHub Actions does not populate repository variables into runner environments
    automatically. Without an explicit mapping under job-level `env:`,
    `.meta/detect_fallback.py` sees `GEMINI_FALLBACK` unset and defaults to false,
    silently disabling fallback on quota exhaustion even when configured in the
    repository.

    Returns:
        Passed | Found | CouldNotRun: Validation result checking that workflows
        invoking `detect_fallback.py` or `actions/agy` export `GEMINI_FALLBACK`.
    """
    if not WORKFLOWS.is_dir():
        return CouldNotRun(f"{WORKFLOWS.relative_to(ROOT).as_posix()} is missing")
    problems = []
    checked = 0
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if "detect_fallback.py" not in text and "actions/agy" not in text:
            continue
        checked += 1
        if not FALLBACK_ENV_EXPORT.search(text):
            problems.append(
                f"{path.relative_to(ROOT)}: runs `detect_fallback.py` or `actions/agy` but does not export "
                "`GEMINI_FALLBACK: ${{ vars.GEMINI_FALLBACK ... }}` in job `env:`"
            )
    if problems:
        return Found(tuple(problems))
    return Passed(f"{checked} fallback workflow{'s' if checked != 1 else ''} export GEMINI_FALLBACK")


RESUME_READS = (("take_claude", "steps.before.outputs.resume"),
                ("take_gemini", "steps.between.outputs.resume"))
"""Where each take step's prompt reads its resume clause, in the order the steps run: the first
harness step off the door's reading before the session, the second off the reading taken
immediately before it, which is the only one later than the first step (solorepo's #835)."""


BETWEEN_STEP = "between"
"""The id of the step reading the branch again immediately before the second harness step."""


BETWEEN_RUNS = "on coder between"
"""What that step must invoke: a step keeping the id while running something else writes no
`resume`, and an output no step wrote interpolates as the empty string."""


def _steps_by_id(job: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The job's steps that carry an `id`, by it, in the order the job runs them."""
    return {step["id"]: step for step in job.get("steps") or [] if isinstance(step, dict)
            and step.get("id")}


@check("the second take prompt reads the branch as the step before it found it")
def fallback_take_prompt_reads_between() -> StepOutcome:
    """The second take step reads its resume clause off the `between` step (solorepo's #835).

    The second harness step runs when the first failed, which the turn cap
    reaches after the work rather than before it, so a pull request the first
    step opened is already there to be continued under. `before` runs once,
    ahead of both harness steps, and a prompt interpolating its `resume` is
    told what was true at the start of the run. The `between` step reads the
    branch again immediately before the second harness step, on that step's
    own condition and running the door that writes `resume`, so that the
    reading happens exactly where it is read. Placement is the property that
    makes it fresh: GitHub resolves a step's `with:` before the step runs, and
    an output whose step has not run yet is the empty string, so a reading
    that sits after its reader reinstates the defect with every other
    assertion here still satisfied.

    Returns:
        Passed | Found | CouldNotRun: The step each prompt reads its resume
        clause from, or each take step reading the wrong one and each way the
        `between` step fails to stand where and as the step below needs it.
    """
    if not CODER_WORKFLOW.is_file():
        return CouldNotRun(f"{CODER_WORKFLOW.relative_to(ROOT).as_posix()} is missing")
    loaded = yaml.safe_load(CODER_WORKFLOW.read_text(encoding="utf-8")) or {}
    steps = _steps_by_id((loaded.get("jobs") or {}).get("coder") or {})
    problems = []
    for name, reads in RESUME_READS:
        if name not in steps:
            problems.append(f"coder.yml: no step is `{name}`, and the take pass runs two harness "
                            "steps one after the other")
            continue
        prompt = str((steps[name].get("with") or {}).get("prompt") or "")
        if reads not in prompt:
            problems.append(f"coder.yml: `{name}`'s prompt does not read `{reads}`, which is "
                            "the door's reading of the branch that is fresh where that step runs")
        for other, stale in RESUME_READS:
            if other != name and stale in prompt:
                problems.append(f"coder.yml: `{name}`'s prompt reads `{stale}`, which is "
                                f"`{other}`'s reading of the branch and not its own")
    problems.extend(_between_stands(steps))
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(RESUME_READS)} take prompts, each reading the branch as its step finds it")


def _between_stands(steps: dict[str, dict[str, Any]]) -> list[str]:
    """Each way the `between` step fails to stand where and as the step reading it needs it."""
    if BETWEEN_STEP not in steps:
        return [f"coder.yml: no step is `{BETWEEN_STEP}`, and the second harness step's prompt "
                "has nothing to read the branch off later than the first step"]
    step, problems = steps[BETWEEN_STEP], []
    order = list(steps)
    if all(name in steps for name, _ in RESUME_READS) and not (
            order.index("take_claude") < order.index(BETWEEN_STEP) < order.index("take_gemini")):
        problems.append(f"coder.yml: `{BETWEEN_STEP}` does not stand between `take_claude` and "
                        "`take_gemini`; a step's outputs read as the empty string until it has "
                        "run, so a reading placed after its reader is no reading at all")
    if BETWEEN_RUNS not in str(step.get("run") or ""):
        problems.append(f"coder.yml: `{BETWEEN_STEP}` does not run `{BETWEEN_RUNS}`, so nothing "
                        "writes the `resume` the step below reads")
    if "take_gemini" in steps and step.get("if") != steps["take_gemini"].get("if"):
        problems.append(f"coder.yml: `{BETWEEN_STEP}` runs on a different condition from "
                        "`take_gemini`; the reading is that step's, so it stands or is "
                        "skipped with it")
    if step.get("continue-on-error") is not True:
        problems.append(f"coder.yml: `{BETWEEN_STEP}` carries no `continue-on-error: true`; an "
                        "`if:` naming no status-check function carries an implicit `success()`, "
                        "so a red reading would skip the step it exists to inform")
    return problems
