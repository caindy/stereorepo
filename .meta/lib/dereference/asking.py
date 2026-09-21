"""The question asked of each pair, the credential it is asked with, and the model's answer (solorepo's DR-134).
"""
import os
import pathlib
import subprocess
import sys
from typing import Any

CREDENTIAL = pathlib.Path(
    os.environ.get("SOLOREPO_MODEL_ENV", "~/.config/solorepo/claude.env")).expanduser()


MODEL = "claude-sonnet-5"


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


def credential() -> dict[str, str]:
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


def ask(
    pair: dict[str, Any],
    token: dict[str, str],
    model: str,
    seconds: int = 120,
) -> tuple[str, str]:
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
                             check=False, input=QUESTION.format(**pair), capture_output=True,
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
