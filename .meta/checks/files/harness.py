"""
What a loop workflow's steps owe the harness they start: a signed run names the
harness under the variable the channel reads (solorepo's DR-233), an agy call
site passes a harness rather than the empty string, every coder form carries
the budget the door fills and the runner binds the turn cap on Claude Code
alone, a workflow that runs the runner exports the toggles the chain reads
(solorepo's DR-245, solorepo's DR-246), and each ladder stands as the door
needs it, a `between` before every rung after the first (solorepo's DR-281).

History in files.history.md (solorepo's DR-171).
"""

import re
from typing import Any

import yaml

from checks.collect import (
    META,
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


FALLBACK_ENV_EXPORT = re.compile(r"^\s*GEMINI_FALLBACK:\s*\${{\s*vars\.GEMINI_FALLBACK\b", re.M)
"""A workflow that runs the harness runner exports GEMINI_FALLBACK from vars.GEMINI_FALLBACK in
its job env, which is where the door reads the toggle for the chain (solorepo's DR-245,
solorepo's DR-281)."""


JULES_ENV_EXPORT = re.compile(r"^\s*JULES_FALLBACK:\s*\${{\s*vars\.JULES_FALLBACK\b", re.M)
"""The reviewer workflows export JULES_FALLBACK for their Jules rungs."""


COPILOT_ENV_EXPORT = re.compile(r"^\s*COPILOT_FALLBACK:\s*\${{\s*vars\.COPILOT_FALLBACK\b", re.M)
"""The coder workflow exports COPILOT_FALLBACK, which controls Copilot CLI's fallback rung."""

CODEX_ENV_EXPORT = re.compile(r"^\s*CODEX_FALLBACK:\s*\${{\s*vars\.CODEX_FALLBACK\b", re.M)
"""Each harness workflow exports CODEX_FALLBACK, which controls the Codex CLI rung."""


HARNESS_ACTION = "./.meta/actions/harness"
"""The harness runner's `uses:` path, as every attempt step names it."""


@check("fallback workflows export the toggles")
def fallback_workflows_export_gemini_fallback() -> StepOutcome:
    """Workflows running the harness runner export the fallback toggles (solorepo's DR-245, DR-246).

    GitHub Actions does not populate repository variables into runner environments
    automatically. Without an explicit mapping under job-level `env:`, the door's
    routing policy sees `GEMINI_FALLBACK` unset and resolves a chain of one rung,
    silently disabling fallback on quota exhaustion even when configured in the
    repository. The reviewer workflows export `JULES_FALLBACK` for their Jules rungs.

    Returns:
        Passed | Found | CouldNotRun: Validation result checking that workflows
        running the harness runner export the toggles the chain reads.
    """
    if not WORKFLOWS.is_dir():
        return CouldNotRun(f"{WORKFLOWS.relative_to(ROOT).as_posix()} is missing")
    problems = []
    checked = 0
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if HARNESS_ACTION not in text and "actions/agy" not in text:
            continue
        checked += 1
        if not FALLBACK_ENV_EXPORT.search(text):
            problems.append(
                f"{path.relative_to(ROOT)}: runs the harness runner but does not export "
                "`GEMINI_FALLBACK: ${{ vars.GEMINI_FALLBACK ... }}` in job `env:`"
            )
        if path.name == "coder.yml" and not COPILOT_ENV_EXPORT.search(text):
            problems.append(
                f"{path.relative_to(ROOT)}: runs the coder's Copilot CLI rung but does not export "
                "`COPILOT_FALLBACK: ${{ vars.COPILOT_FALLBACK ... }}` in job `env:`"
            )
        if path.name in ("review.yml", "triage.yml") and not JULES_ENV_EXPORT.search(text):
            problems.append(
                f"{path.relative_to(ROOT)}: runs a reviewer ladder but does not "
                "export `JULES_FALLBACK: ${{ vars.JULES_FALLBACK ... }}` in job `env:`"
            )
        if not CODEX_ENV_EXPORT.search(text):
            problems.append(
                f"{path.relative_to(ROOT)}: runs the harness runner but does not export "
                "`CODEX_FALLBACK: ${{ vars.CODEX_FALLBACK ... }}` in job `env:`"
            )
    if problems:
        return Found(tuple(problems))
    return Passed(f"{checked} fallback workflow{'s' if checked != 1 else ''} export the toggles")


LADDERS = {"coder.yml": ("coder", 4), "review.yml": ("reviewer", 4), "triage.yml": ("reviewer", 3)}
"""Each loop workflow, the job its ladder stands in, and how many rungs the ladder has: as many
as the longest chain the routing policy resolves for that door (solorepo's DR-281)."""


FORMS = ROOT / ".meta" / "templates" / "prompts"
"""Where the prompt forms are, one per Role and pass."""


def _steps_by_id(job: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The job's steps that carry an `id`, by it, in the order the job runs them."""
    return {step["id"]: step for step in job.get("steps") or [] if isinstance(step, dict)
            and step.get("id")}


def _attempt_problems(where: str, attempt: dict[str, Any], rung: int) -> list[str]:
    """Each way `attempt_<rung>` in `where` fails to stand as the door needs it."""
    problems = []
    if attempt.get("uses") != HARNESS_ACTION:
        problems.append(f"{where}: `attempt_{rung}` does not use {HARNESS_ACTION}, which is "
                        "the one place a harness is named")
    if str(attempt.get("name") or "") != f"attempt {rung}":
        problems.append(f"{where}: `attempt_{rung}` is not named `attempt {rung}`, which is "
                        "the one name `.meta/arc/watch` reads a rung by; an expression in the "
                        "name would render only when the step runs and show as the template "
                        "on a skipped rung")
    if attempt.get("continue-on-error") is not True:
        problems.append(f"{where}: `attempt_{rung}` carries no `continue-on-error: true`; a "
                        "failed rung would end the job before the next rung and the door")
    given = attempt.get("with") or {}
    for field in ("harness", "model", "effort", "turns", "minutes", "agent"):
        if f"tier_{rung}_{field}" not in str(given.get(field) or ""):
            problems.append(f"{where}: `attempt_{rung}` does not pass `{field}` off "
                            f"`tier_{rung}_{field}`")
    wanted = f"steps.between_{rung - 1}.outputs.run == 'true'"
    if rung > 1 and wanted not in str(attempt.get("if") or ""):
        problems.append(f"{where}: `attempt_{rung}` does not run on `{wanted}`, which is the "
                        "door's word on whether it runs")
    return problems


def _between_problems(where: str, steps: dict[str, dict[str, Any]], rung: int) -> list[str]:
    """Each way `between_<rung>` in `where` fails to stand between its two rungs."""
    between = steps.get(f"between_{rung}")
    if between is None:
        return [f"{where}: no step is `between_{rung}`, and rung {rung + 1} has nothing to read "
                "whether it runs off"]
    problems, order = [], list(steps)
    if f"attempt_{rung + 1}" in order and not order.index(f"attempt_{rung}") \
            < order.index(f"between_{rung}") < order.index(f"attempt_{rung + 1}"):
        problems.append(f"{where}: `between_{rung}` does not stand between `attempt_{rung}` "
                        f"and `attempt_{rung + 1}`; a step's outputs read as the empty string "
                        "until it has run")
    run = str(between.get("run") or "")
    if " between " not in run or f"--attempt {rung}" not in run or "--outcome" not in run:
        problems.append(f"{where}: `between_{rung}` does not run the door's `between` with "
                        f"`--attempt {rung}` and `--outcome`")
    if f"steps.attempt_{rung}.outcome != 'skipped'" not in str(between.get("if") or ""):
        problems.append(f"{where}: `between_{rung}` does not run wherever `attempt_{rung}` ran")
    if between.get("continue-on-error") is not True:
        problems.append(f"{where}: `between_{rung}` carries no `continue-on-error: true`; an "
                        "`if:` naming no status-check function carries an implicit `success()`, "
                        "so a red reading would end the job")
    return problems


def _chain_name(last: int) -> str:
    """The `chain` step's name for a ladder of `last` rungs: each rung's harness output."""
    return "chain " + ",".join(f"${{{{ steps.before.outputs.tier_{n}_harness }}}}"
                               for n in range(1, last + 1))


def _chain_problems(where: str, steps: dict[str, dict[str, Any]], last: int) -> list[str]:
    """Each way the `chain` step in `where` fails to show the chain in the run's step list."""
    chain = steps.get("chain")
    if chain is None:
        return [f"{where}: no step is `chain`, and the run's step list would not say which "
                "harness each rung runs while the run is live"]
    problems = []
    if str(chain.get("name") or "") != _chain_name(last):
        problems.append(f"{where}: `chain` is not named `{_chain_name(last)}`, which is the "
                        "name `.meta/arc/watch` reads the chain off")
    order = list(steps)
    if "before" not in order:
        return [*problems, f"{where}: no step is `before`, and `chain` is named off its outputs"]
    if "attempt_1" in order and not order.index("before") < order.index("chain") \
            < order.index("attempt_1"):
        problems.append(f"{where}: `chain` does not stand between `before` and `attempt_1`; "
                        "its name is rendered when it runs, and must be by the first rung")
    return problems


def _rung_problems(where: str, steps: dict[str, dict[str, Any]], rung: int,
                   last: int) -> list[str]:
    """Each way rung `rung` of the ladder in `where` fails to stand as the door needs it."""
    attempt = steps.get(f"attempt_{rung}")
    if attempt is None:
        return [f"{where}: no step is `attempt_{rung}`, and the ladder runs {last} rungs"]
    problems = _attempt_problems(where, attempt, rung)
    if rung < last:
        problems.extend(_between_problems(where, steps, rung))
    return problems


@check("the ladders stand as the door needs them")
def ladders_stand() -> StepOutcome:
    """Each loop workflow runs a ladder of attempt steps on the runner (solorepo's DR-281).

    The door resolves a chain and emits it as `tier_<n>_*`; the workflow
    realizes it as rungs read by number. A `chain` step between the door and
    the first rung is named from the door's `tier_<n>_harness` outputs, so
    the run's step list says which harness each rung runs while the run
    is live, on trunk's door as on the head's.
    Every rung uses the runner, is named plainly, carries
    `continue-on-error`, and takes its six fields off its tier; every rung
    after the first runs on the door's
    `run`; and every `between` stands between its two rungs, runs the door
    with `--attempt` and `--outcome`, runs wherever its rung ran, and
    carries `continue-on-error`. Placement is the property that makes the
    reading fresh: a step's outputs read as the empty string until it has
    run, so a `between` after its reader is no reading at all
    (solorepo's #835).

    Returns:
        Passed | Found | CouldNotRun: The rungs counted, or each way the
        `chain` step, a rung or a `between` fails to stand as the door needs
        it: the `chain` step missing, not named off the door's outputs, or
        not between the door and the first rung.
    """
    problems, counted = [], 0
    for name, (job_name, last) in LADDERS.items():
        path = WORKFLOWS / name
        if not path.is_file():
            return CouldNotRun(f"{path.relative_to(ROOT).as_posix()} is missing")
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        steps = _steps_by_id((loaded.get("jobs") or {}).get(job_name) or {})
        problems.extend(_chain_problems(name, steps, last))
        for rung in range(1, last + 1):
            counted += 1
            problems.extend(_rung_problems(name, steps, rung, last))
    if problems:
        return Found(tuple(problems))
    return Passed(f"{counted} rungs across {len(LADDERS)} ladders, each standing as the door needs")


TURN_CAP = "--max-turns"
"""The argument that binds a turn cap, which Claude Code takes and the Antigravity CLI does
not: `.meta/run_agy.py` builds its argument vector with `--print-timeout` alone, so a turn
number told to an `agy` session binds nothing."""


@check("coder forms name their budget")
def coder_prompts_name_turn_budget() -> StepOutcome:
    """Every coder form carries `<budget>`, and the runner binds the turn cap on Claude Code alone.

    The door fills `<budget>` with the sentence naming the caps the rung's
    harness binds (solorepo's DR-281): the turn cap and the minutes on Claude
    Code, the minutes alone elsewhere. A form without it leaves the session
    unable to pace itself or to hand off before the cap. The runner passes
    `--max-turns` to the Claude Code step alone: a turn number told to the
    Antigravity CLI binds nothing there and would teach that session to
    discount the cap that does bind.

    Returns:
        Passed | Found | CouldNotRun: The forms counted, or each form without
        `<budget>` and each runner step binding the cap where it should not.
    """
    forms = sorted(FORMS.glob("coder-*.md"))
    runner = META / "actions" / "harness" / "action.yml"
    if not forms or not runner.is_file():
        return CouldNotRun("no coder forms under .meta/templates/prompts/, or no harness runner")
    problems = [f"{form.relative_to(ROOT)}: does not carry `<budget>`" for form in forms
                if "<budget>" not in form.read_text(encoding="utf-8")]
    loaded = yaml.safe_load(runner.read_text(encoding="utf-8")) or {}
    for step in (loaded.get("runs") or {}).get("steps") or []:
        given = (step.get("with") or {}) if isinstance(step, dict) else {}
        binds = TURN_CAP in str(given.get("claude_args") or "")
        if step.get("id") == "claude" and not binds:
            problems.append(f"{runner.relative_to(ROOT)}: the Claude Code step passes no "
                            f"{TURN_CAP}, so the cap the policy chose binds nothing")
        if step.get("id") != "claude" and (binds or "turns" in given):
            problems.append(f"{runner.relative_to(ROOT)}: step `{step.get('id')}` is told a "
                            "turn number that binds nothing there")
    if problems:
        return Found(tuple(problems))
    return Passed(f"{len(forms)} coder forms carry the budget, and the runner binds the cap on "
                  "Claude Code alone")
