"""The routing policy: which harnesses run a pass, in what order, and how deep (solorepo's DR-281).

Every model, effort, turn cap and timeout a door emits is a value in this
module, and nowhere else: the coder's by pass and level, the reviewer's by the
depth `.meta/depth.py` evaluates, the reading door's by itself. A chain is
the harnesses that may run a pass, in the order they are tried. Its first
tier is the primary, chosen by a `harness:` label or a dispatch input and
Claude Code where nothing says; every later tier is a fallback that runs
only where the tier before it failed, and only where the portfolio has
opted in to that harness by the toggle solorepo's DR-240, DR-245 and DR-246
name. Claude Code needs no toggle: it is the harness every portfolio has.

The module imports nothing from the package and nothing that reaches
GitHub, so `.meta/depth.py` takes its tier values from here whatever else
is loaded. One hazard follows from where the two files sit: `review.yml`
restores `.meta/lib/on/` from `origin/main` before the door runs and does
not restore `.meta/depth.py`, so a pull request's review runs trunk's copy
of this module against the head's `depth.py`. A change that renames a
symbol here and updates `depth.py` in the same commit is consistent locally
and fails its own review at import, on the attribute rather than on the
restore; such a rename lands in two pull requests, the module first.
"""

import os
from collections.abc import Mapping, Sequence
from typing import NamedTuple

AGENTS = {
    "agy": "antigravity-cli",
    "gemini": "antigravity-cli",
    "jules": "google-labs-jules",
    "claude": "anthropics/claude-code-action@v1",
    "copilot": "copilot-cli",
}
"""Each harness a door can choose, and the Agent the Trailer names it by (solorepo's DR-233)."""

TOGGLES = {
    "agy": "GEMINI_FALLBACK",
    "gemini": "GEMINI_FALLBACK",
    "jules": "JULES_FALLBACK",
    "copilot": "COPILOT_FALLBACK",
}
"""The repository variable that opts a portfolio in to each fallback harness; Claude Code has
none, being the harness every portfolio runs (solorepo's DR-240, DR-245, DR-246)."""

ENABLED = ("true", "1", "yes", "on", "enable", "enabled")
"""What a toggle's value reads as on, lowercased and stripped."""

CODER_FALLBACKS = ("claude", "agy", "copilot")
"""The coder's harnesses in the order a fallback is tried, after whichever is primary."""

REVIEW_FALLBACKS = ("claude", "agy", "jules")
"""The reviewer's harnesses in the order a fallback is tried, after whichever is primary."""

READING_FALLBACKS = ("claude", "agy", "jules")
"""The reading door's harnesses in the order a fallback is tried, after whichever is primary."""


class Provider(NamedTuple):
    """How a locally installed harness asks one model-reading question.

    Attributes:
        executable: The command that invokes the harness.
        prompt_flag: The flag placing a prompt on standard input.
        model_flag: The flag selecting the model.
        credential_environment: The environment variable carrying an optional credential.
        credential_file: The default outside-tree file carrying that credential.
    """

    executable: str
    prompt_flag: str
    model_flag: str
    credential_environment: str
    credential_file: str


PROVIDERS = {
    "claude": Provider(
        "claude", "-p", "--model", "CLAUDE_CODE_OAUTH_TOKEN", "~/.config/solorepo/claude.env"
    ),
    "agy": Provider("agy", "-p", "--model", "", ""),
    "gemini": Provider("agy", "-p", "--model", "", ""),
}
"""The local invocation and credential contracts of harnesses that read text."""


class Depth(NamedTuple):
    """How deep a pass runs on Claude Code: the model, and the caps every harness shares.

    Attributes:
        model: The Claude model.
        effort: The reasoning effort, `high` or `medium`.
        turns: The turn cap, which Claude Code alone binds.
        minutes: The minute cap, which `timeout-minutes` binds on every harness.
    """

    model: str
    effort: str
    turns: str
    minutes: str


class Tier(NamedTuple):
    """One rung of a chain: a harness and what it runs with.

    Attributes:
        harness: `claude`, `agy`, `copilot` or `jules`.
        model: The model this harness runs; empty for Jules, which chooses its own.
        effort: The reasoning effort.
        turns: The turn cap, told to every harness and bound by Claude Code alone.
        minutes: The minute cap.
        agent: The Agent the Trailer names this harness by.
    """

    harness: str
    model: str
    effort: str
    turns: str
    minutes: str
    agent: str


GEMINI_MODEL = "gemini-3.8-flash"
"""The model the Antigravity CLI runs, on every pass of every Role."""

COPILOT_MODEL = "gpt-5.3-codex"
"""The model GitHub Copilot CLI runs for autonomous coder passes."""

CODER_DEPTHS = {
    "rebase": Depth("claude-opus-5", "high", "60", "30"),
    "decompose": Depth("claude-opus-5", "high", "90", "45"),
    "medium": Depth("claude-opus-5", "high", "120", "60"),
    "easy": Depth("claude-sonnet-5", "medium", "60", "30"),
}
"""The coder's depth by the pass, or by the level a take is at.

`easy` is the smaller model and half an hour; `medium` the larger and the
whole budget, and an answering pass takes it whatever the label was, since
the threads it answers were written by the deeper reviewer. A rebase is
bounded by what it is, the larger model at half the budget, because a
conflict here is prose as often as code and a rebase taking an hour is not
a rebase.
"""

REVIEW_DEPTHS = {
    "deep": Depth("claude-opus-5", "high", "120", "45"),
    "standard": Depth("claude-sonnet-5", "medium", "120", "15"),
}
"""The reviewer's two tiers, which `.meta/depth.py` chooses between by what a change touches
(solorepo's DR-188)."""

REVIEW_FANOUT = {"deep": 3, "standard": 1}
"""The concurrent subagent ceiling of each review tier (solorepo's DR-189, DR-191)."""

READING_DEPTH = Depth("claude-sonnet-5", "medium", "60", "20")
"""The reading door's depth: one Challenge read by the smaller model in twenty minutes."""


def coder_depth(task: str, level: str) -> Depth:
    """The coder's depth for a pass, by the pass first and the level after.

    Parameters:
        task (str): `take`, `rebase`, `answer` or `decompose`.
        level (str): The level a take is at; ignored where the pass names its own depth.
    """
    return CODER_DEPTHS.get(task) or CODER_DEPTHS.get(level) or CODER_DEPTHS["easy"]


def toggled(harness: str, environ: Mapping[str, str] = os.environ) -> bool:
    """Whether the portfolio has opted in to `harness` as a fallback; Claude Code always.

    Parameters:
        harness (str): The harness.
        environ (Mapping[str, str]): The environment the toggles are read from.
    """
    name = TOGGLES.get(harness)
    if name is None:
        return True
    return (environ.get(name) or "").strip().lower() in ENABLED


def tier(
    harness: str, depth: Depth, gemini_model: str = GEMINI_MODEL, copilot_model: str = COPILOT_MODEL
) -> Tier:
    """The rung `harness` makes at `depth`.

    Parameters:
        harness (str): The harness.
        depth (Depth): The Claude model and the caps every harness shares.
        gemini_model (str): The model the Antigravity CLI runs, where a depth hook chose one.
        copilot_model (str): The model GitHub Copilot CLI runs.
    """
    model = {
        "claude": depth.model,
        "agy": gemini_model,
        "gemini": gemini_model,
        "copilot": copilot_model,
    }.get(harness, "")
    return Tier(harness, model, depth.effort, depth.turns, depth.minutes, AGENTS[harness])


def provider(harness: str) -> Provider:
    """The local model-reading contract for `harness`.

    Parameters:
        harness: A harness selected by a reading chain.

    Raises:
        KeyError: If the harness has no local text-reading contract.
    """
    return PROVIDERS[harness]


def chain(
    primary: str,
    fallbacks: Sequence[str],
    depth: Depth,
    gemini_model: str = GEMINI_MODEL,
    environ: Mapping[str, str] = os.environ,
) -> tuple[Tier, ...]:
    """The tiers that may run a pass: the primary first, then each toggled fallback in order.

    The primary runs whatever the toggles say, since a label or a dispatch
    asked for it by name; a fallback is a rung only where its toggle is on.

    Parameters:
        primary (str): The harness chosen by label, input or default.
        fallbacks (Sequence[str]): The harnesses in the order a fallback is tried.
        depth (Depth): The depth every tier runs at.
        gemini_model (str): The model the Antigravity CLI runs.
        environ (Mapping[str, str]): The environment the toggles are read from.
    """
    order = [primary, *(name for name in fallbacks if name != primary)]
    return tuple(
        tier(name, depth, gemini_model)
        for name in order
        if name == primary or toggled(name, environ)
    )


def coder_chain(
    primary: str, task: str, level: str, environ: Mapping[str, str] = os.environ
) -> tuple[Tier, ...]:
    """The coder's chain for a pass at a level, the primary first."""
    return chain(primary, CODER_FALLBACKS, coder_depth(task, level), environ=environ)


def review_chain(
    primary: str, depth: Depth, gemini_model: str, environ: Mapping[str, str] = os.environ
) -> tuple[Tier, ...]:
    """The reviewer's chain at the depth `.meta/depth.py` evaluated, the primary first.

    The depth arrives evaluated rather than named, since a portfolio's depth
    hook may answer a configuration that is neither tier (solorepo's DR-188).
    """
    return chain(primary, REVIEW_FALLBACKS, depth, gemini_model, environ)


def reading_chain(primary: str, environ: Mapping[str, str] = os.environ) -> tuple[Tier, ...]:
    """The reading door's chain, the primary first."""
    return chain(primary, READING_FALLBACKS, READING_DEPTH, environ=environ)


def outputs(tiers: Sequence[Tier]) -> dict[str, str]:
    """The chain as step outputs: `tiers`, and `tier_<n>_<field>` for each rung from one.

    An attempt step reads its rung by number, so a workflow's ladder is the
    same whatever harness each rung names; `tiers` is how many rungs the
    ladder has, so the step after the last knows there is no next; and a
    step named from the `tier_<n>_harness` outputs shows the chain in the
    run's step list while the run is live, where `.meta/arc/watch` reads a
    rung's harness.
    """
    named = {"tiers": str(len(tiers))}
    for position, rung in enumerate(tiers, 1):
        for field, value in rung._asdict().items():
            named[f"tier_{position}_{field}"] = str(value)
    return named
