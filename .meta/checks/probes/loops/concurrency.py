"""Concurrency key evaluation and failure observation for coder and review workflows (solorepo's DR-112, solorepo's #472).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import re
from collections.abc import Mapping, Sequence
from typing import Any

import yaml

from checks.collect import ROOT, check

EXPR_PATTERN = re.compile(r"'[^']*'|&&|\|\||!=|!|\btrue\b|\bfalse\b|\bnull\b")


class NullContext:
    """Represents a null or absent property in GitHub Actions expressions."""

    def __getattr__(self, name: str) -> "NullContext":
        return self

    def __getitem__(self, name: str) -> "NullContext":
        return self

    def __eq__(self, other: object) -> bool:
        return other is None or other is False or other == ""

    def __bool__(self) -> bool:
        return False

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        return "null"


class SafeContext:
    """Wraps dictionary contexts with GitHub Actions expression evaluation semantics."""

    def __init__(self, data: Mapping[str, Any] | None = None) -> None:
        self._data: Mapping[str, Any] = data if isinstance(data, dict) else {}

    def __getattr__(self, name: str) -> Any:
        val = self._data.get(name, None)
        if isinstance(val, dict):
            return SafeContext(val)
        if val is None:
            return NullContext()
        return val

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __eq__(self, other: object) -> bool:
        return self._data == other

    def __bool__(self) -> bool:
        return bool(self._data)

    def __str__(self) -> str:
        return str(self._data)


def evaluate_gh_expr(expr_str: str, context: Mapping[str, Any]) -> Any:
    """Evaluate a single GitHub Actions expression string under given context variables.

    Parameters:
        expr_str: The raw expression without enclosing ${{ and }}.
        context: Context mapping containing `github`, `inputs`, or `vars`.

    Returns:
        Any: Evaluated result conforming to GitHub Actions truthiness and operand semantics.
    """
    def replacer(match: re.Match[str]) -> str:
        tok = match.group(0)
        if tok == "&&":
            return " and "
        if tok == "||":
            return " or "
        if tok == "!=":
            return " != "
        if tok == "!":
            return " not "
        if tok == "true":
            return "True"
        if tok == "false":
            return "False"
        if tok == "null":
            return "None"
        return tok

    py_expr = EXPR_PATTERN.sub(replacer, expr_str)
    env: dict[str, Any] = {
        "github": SafeContext(context.get("github", {})),
        "inputs": SafeContext(context.get("inputs", {})),
        "vars": SafeContext(context.get("vars", {})),
        "format": lambda fmt, *args: fmt.format(*(str(a) for a in args)),
        "contains": lambda seq, item: item in (seq or []),
        "startsWith": lambda s, prefix: str(s or "").startswith(prefix),
        "endsWith": lambda s, suffix: str(s or "").endswith(suffix),
    }
    res = eval(py_expr, {"__builtins__": {}}, env)
    if isinstance(res, NullContext):
        return None
    return res


def evaluate_template(template_str: str, context: Mapping[str, Any]) -> str:
    """Interpolate all ${{ ... }} expressions in a workflow template string.

    Parameters:
        template_str: The workflow string containing optional expressions.
        context: Context mapping containing `github`, `inputs`, or `vars`.

    Returns:
        str: Fully interpolated string.
    """
    def eval_match(m: re.Match[str]) -> str:
        expr = m.group(1).strip()
        val = evaluate_gh_expr(expr, context)
        return str(val) if val is not None else ""

    return re.sub(r"\$\{\{\s*(.*?)\s*\}\}", eval_match, template_str)


def evaluate_concurrency(workflow_path: str, context: Mapping[str, Any]) -> tuple[str, bool]:
    """Load workflow concurrency settings and evaluate group and cancellation under context.

    Parameters:
        workflow_path: Path to workflow file relative to repository root.
        context: Webhook event and runner contexts.

    Returns:
        tuple[str, bool]: Evaluated concurrency group name and cancel-in-progress boolean.
    """
    path = ROOT / workflow_path
    data = yaml.safe_load(path.read_text()) or {}
    concurrency = data.get("concurrency", {})
    group_tpl = str(concurrency.get("group", ""))
    cancel_tpl = concurrency.get("cancel-in-progress", False)

    group = evaluate_template(group_tpl, context)
    if isinstance(cancel_tpl, bool):
        cancel = cancel_tpl
    else:
        cancel = bool(evaluate_gh_expr(re.sub(r"^\$\{\{\s*(.*?)\s*\}\}$", r"\1", str(cancel_tpl).strip()), context))
    return group, cancel


def _run_matrix_eval(group_tpl: str, cancel_tpl: Any, cases: Sequence[tuple[Mapping[str, Any], str, bool]]) -> list[str]:
    """Evaluate cases against explicit group and cancel templates and return detected errors."""
    failures: list[str] = []
    for ctx, expected_group, expected_cancel in cases:
        group = evaluate_template(group_tpl, ctx)
        if isinstance(cancel_tpl, bool):
            cancel = cancel_tpl
        else:
            cancel = bool(evaluate_gh_expr(re.sub(r"^\$\{\{\s*(.*?)\s*\}\}$", r"\1", str(cancel_tpl).strip()), ctx))
        if group != expected_group:
            failures.append(f"group expected {expected_group!r}, got {group!r}")
        if cancel != expected_cancel:
            failures.append(f"cancel expected {expected_cancel!r}, got {cancel!r}")
    return failures


@check("concurrency probes", pre=True)
def concurrency_probes() -> list[str]:
    """Verify coder and review workflow concurrency keys and mutation-probe their failure modes (A4, solorepo's #472).

    Validates that:
    1. Coder passes on the same subject separate cleanly (approved vs changes_requested vs rebase vs take).
    2. Non-taking label deliveries (`challenge`, `roadmap`, `harness:*`) do not share the `take` group,
       closing Residual 3 so pending difficulty deliveries are never cancelled by skipped deliveries.
    3. Difficulty deliveries (`easy`, `medium`) coalesce in the `take` group.
    4. Review workflow cancels in flight only on coder synchronizes, never on reviewer pushes or review requests.
    5. Deliberate regressions (omitting label qualification, dropping rebase tasks, breaking review cancellation)
       are actively observed to fail the probe under Article 4.

    Returns:
        list[str]: Discrepancies and unobserved failures detected during evaluation.
    """
    problems: list[str] = []

    coder_cases: list[tuple[Mapping[str, Any], str, bool]] = [
        ({"github": {"event": {"issue": {"number": 472}, "label": {"name": "easy"}}}}, "coder-472-take", False),
        ({"github": {"event": {"issue": {"number": 472}, "label": {"name": "medium"}}}}, "coder-472-take", False),
        ({"github": {"event": {"issue": {"number": 472}, "label": {"name": "challenge"}}}}, "coder-472-challenge", False),
        ({"github": {"event": {"issue": {"number": 472}, "label": {"name": "roadmap"}}}}, "coder-472-roadmap", False),
        ({"github": {"event": {"issue": {"number": 472}, "label": {"name": "harness:claude"}}}}, "coder-472-harness:claude", False),
        ({"github": {"event": {"issue": {"number": 472}, "label": {"name": "hard"}}}}, "coder-472-hard", False),
        ({"github": {"event": {"issue": {"number": 472}, "label": {"name": "human"}}}}, "coder-472-human", False),
        ({"github": {"event": {"pull_request": {"number": 475}, "review": {"state": "approved"}}}}, "coder-475-approved", False),
        ({"github": {"event": {"pull_request": {"number": 475}, "review": {"state": "changes_requested"}}}}, "coder-475-changes_requested", False),
        ({"github": {"event": {"pull_request": {"number": 475}, "review": {"state": "commented"}}}}, "coder-475-commented", False),
        ({"inputs": {"pull_request": 475, "task": "rebase"}}, "coder-475-rebase", False),
        ({"inputs": {"pull_request": 475, "task": "review"}}, "coder-475-changes_requested", False),
    ]

    coder_workflow = ROOT / ".github" / "workflows" / "coder.yml"
    coder_data = yaml.safe_load(coder_workflow.read_text()) or {}
    coder_concurrency = coder_data.get("concurrency", {})
    coder_group_tpl = str(coder_concurrency.get("group", ""))
    coder_cancel_tpl = coder_concurrency.get("cancel-in-progress", False)

    coder_errs = _run_matrix_eval(coder_group_tpl, coder_cancel_tpl, coder_cases)
    for err in coder_errs:
        problems.append(f"coder concurrency: {err}")

    review_cases: list[tuple[Mapping[str, Any], str, bool]] = [
        ({"github": {"event": {"pull_request": {"number": 475}, "action": "review_requested"}}}, "review-475", False),
        ({
            "github": {
                "event": {"pull_request": {"number": 475}, "action": "synchronize", "repository": {"name": "solorepo"}},
                "repository_owner": "caindy",
                "actor": "caindy-solorepo-coder",
            }
        }, "review-475", True),
        ({
            "github": {
                "event": {"pull_request": {"number": 475}, "action": "synchronize", "repository": {"name": "solorepo"}},
                "repository_owner": "caindy",
                "actor": "caindy-solorepo-reviewer",
            }
        }, "review-475", False),
    ]

    review_workflow = ROOT / ".github" / "workflows" / "review.yml"
    review_data = yaml.safe_load(review_workflow.read_text()) or {}
    review_concurrency = review_data.get("concurrency", {})
    review_group_tpl = str(review_concurrency.get("group", ""))
    review_cancel_tpl = review_concurrency.get("cancel-in-progress", False)

    review_errs = _run_matrix_eval(review_group_tpl, review_cancel_tpl, review_cases)
    for err in review_errs:
        problems.append(f"review concurrency: {err}")

    mutated_unseparated = (
        "coder-${{ github.event.issue.number || github.event.pull_request.number || inputs.pull_request }}"
        "-${{ github.event.review.state || (inputs.task == 'rebase' && 'rebase') || (inputs.pull_request && 'changes_requested') || 'take' }}"
    )
    unseparated_fails = _run_matrix_eval(mutated_unseparated, False, coder_cases)
    if not unseparated_fails:
        problems.append("concurrency probe mutation 1: unseparated take fallback was not observed to fail")

    mutated_no_rebase = (
        "coder-${{ github.event.issue.number || github.event.pull_request.number || inputs.pull_request }}"
        "-${{ github.event.review.state || (inputs.pull_request && 'changes_requested') || 'take' }}"
    )
    no_rebase_fails = _run_matrix_eval(mutated_no_rebase, False, coder_cases)
    if not no_rebase_fails:
        problems.append("concurrency probe mutation 2: missing rebase task branch was not observed to fail")

    unconditional_review_fails = _run_matrix_eval(review_group_tpl, False, review_cases)
    if not unconditional_review_fails:
        problems.append("concurrency probe mutation 3: unconditional review cancel-in-progress False was not observed to fail")

    return problems
