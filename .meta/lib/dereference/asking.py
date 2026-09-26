"""The question asked of each pair, its credential, and the model's answer.

solorepo's DR-134.
"""

import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Mapping
from typing import Any

from lib.on import routing

CREDENTIAL = pathlib.Path(
    os.environ.get("SOLOREPO_MODEL_ENV", routing.provider("claude").credential_file)
).expanduser()


MODEL = routing.READING_DEPTH.model


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


def credential(provider: routing.Provider) -> dict[str, str]:
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
    if not provider.credential_environment:
        return {}
    if os.environ.get(provider.credential_environment):
        return {}
    if not CREDENTIAL.exists():
        print(
            f"dereference: no {CREDENTIAL}; asking with ambient auth, which is "
            "whatever `claude` on this machine is logged in as",
            file=sys.stderr,
        )
        return {}
    mode = CREDENTIAL.stat().st_mode
    if mode & 0o077:
        sys.exit(
            f"dereference: {CREDENTIAL} is readable by others "
            f"(mode {mode & 0o777:o}); refusing to use it. chmod 600 it."
        )
    for line in CREDENTIAL.read_text().splitlines():
        line = line.strip().removeprefix("export ").strip()
        if line.startswith(f"{provider.credential_environment}=") and (
            value := line.split("=", 1)[1].strip().strip("\"'")
        ):
            return {provider.credential_environment: value}
    print(
        f"dereference: {CREDENTIAL} holds no {provider.credential_environment}; asking with "
        "ambient auth",
        file=sys.stderr,
    )
    return {}


def providers(
    model: str = MODEL, environ: Mapping[str, str] = os.environ
) -> tuple[routing.Tier, ...]:
    """The enabled reviewer-reading tiers that may answer a citation.

    Parameters:
        model: The primary Claude model, retained for the command-line override.
    """
    depth = routing.Depth(
        model,
        routing.READING_DEPTH.effort,
        routing.READING_DEPTH.turns,
        routing.READING_DEPTH.minutes,
    )
    return routing.chain("claude", routing.READING_FALLBACKS, depth, environ=environ)


def available(tiers: tuple[routing.Tier, ...]) -> bool:
    """Whether any tier in `tiers` has its configured executable on PATH."""
    return any(shutil.which(routing.provider(tier.harness).executable) for tier in tiers)


def invoke(
    pair: dict[str, Any],
    tier: routing.Tier,
    seconds: int = 120,
) -> tuple[str, str, bool]:
    """Ask one routed provider and report whether its invocation failed.

    Everything the question turns on is in the prompt, so the model reads
    extracted text rather than searching. A valid `?` is the provider's answer;
    a timeout, missing executable, non-zero exit, or malformed output is an
    invocation failure that lets the next routed provider try.
    """
    provider = routing.provider(tier.harness)
    if not shutil.which(provider.executable):
        return "?", f"`{provider.executable}` is not on PATH", True

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_BASE_URL"}
    env.update(credential(provider))
    try:
        out = subprocess.run(
            [provider.executable, provider.prompt_flag, provider.model_flag, tier.model],
            check=False,
            input=QUESTION.format(**pair),
            capture_output=True,
            text=True,
            env=env,
            timeout=seconds,
        )
    except subprocess.TimeoutExpired:
        return "?", f"{tier.harness} did not answer within {seconds}s", True
    if out.returncode:
        why = out.stdout.strip() or out.stderr.strip() or "the model could not be reached"
        return "?", f"{tier.harness}: {why.splitlines()[-1][:160]}", True
    line = next((s.strip() for s in out.stdout.splitlines() if s.strip()), "")
    for mark in ("ok", "x", "?"):
        if line == mark or line.startswith(mark + " "):
            return mark, line[len(mark) :].strip(), False
    return "?", f"{tier.harness} answered outside the three-mark protocol: {line[:120]!r}", True


def ask(
    pair: dict[str, Any],
    tiers: tuple[routing.Tier, ...],
    seconds: int = 120,
) -> tuple[str, str]:
    """Ask routed providers in order until one answers the citation.

    A provider's valid `?` is a completed reading and does not fail over. Only
    an invocation failure advances to the next eligible tier.
    """
    failures = []
    for tier in tiers:
        mark, detail, failed = invoke(pair, tier, seconds)
        if not failed:
            return mark, detail
        failures.append(detail)
    return "?", "; ".join(failures) or "no provider was configured"
