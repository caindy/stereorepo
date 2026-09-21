#!/usr/bin/env python3
"""The channel: the credential and the Trailer, and nothing else.

Every comment an agent writes here is posted under its Role's account, so which
Job wrote it is carried by an `Actor:` Trailer and by nothing else. The channel
composes and appends the Trailer itself from the environment, ensuring signing
is an intrinsic property of the channel rather than a manual act that can be
omitted (solorepo's DR-069). History in channel.history.md.

Identity is derived directly from the environment; callers do not supply
identity arguments manually (solorepo's DR-175).

It is a module, not a verb surface. The programs beside it import it, and each
holds one concern (solorepo's DR-117): `post` says things — comments, threads, answers,
what landed, the reviewer's verdict; `move` changes what GitHub holds — claims,
levels, layers, merges, handoffs; `commit` is git's; `whoami` answers which
login this speaks as. None of them reads a credential or composes a Trailer:
each speaks through here, or not at all. Which Role holds which verb is asserted
once, in `.meta/say/verbs.yaml`, and a Role's reading of PR
First is compiled from it, so `/pr-first` lists the coder's verbs and
`/pr-first-reviewer` the reviewer's. A program's `--help` lists its own.

`--role` names which Role speaks, coder by default: its credential is
`~/.config/solorepo/<role>.env`, and its login is `<owner>-<repo>-<role>`, so a
Role is one word said once (solorepo's DR-107). `SOLOREPO_ROLE_ENV` names a file outright
and wins.

Bodies are read from stdin rather than command-line arguments to preserve
multiline text and quotes without shell escaping issues.
"""
import argparse
import json
import os
import pathlib
import select
import subprocess
import sys
import types
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent

ROLE_DIR = pathlib.Path("~/.config/solorepo").expanduser()
"""Path to external role credential directory outside the working tree (solorepo's DR-073)."""

ROLE_ENV = pathlib.Path(os.environ.get("SOLOREPO_ROLE_ENV", ROLE_DIR / "coder.env")).expanduser()
"""Path to the active role credential file, overridable via SOLOREPO_ROLE_ENV."""

ENV_AGENT = ("AI_AGENT",)
"""Environment variable names evaluated to detect local agent harness identity."""

ENV_SESSION = ("CLAUDE_CODE_SESSION_ID", "ACTOR_SESSION")
"""Environment variable names evaluated to detect local session identifiers."""

RUN_MARK = "gha-"
"""Workflow run identifier prefix for ACTOR_SESSION to distinguish CI runs from local sessions (solorepo's DR-148)."""

ENV_RUN_ID = "GITHUB_RUN_ID"
"""Environment variable containing the attested GitHub Actions run identifier (solorepo's DR-233)."""

ENV_RUN_AGENT = "ACTOR_AGENT"
"""Environment variable containing the workflow-attested agent name (solorepo's DR-233)."""

ENV_RUN_STEP = ("GITHUB_WORKFLOW", "GITHUB_ACTION")
"""Fallback workflow step environment variables identifying caller provenance."""

READING = ("`.meta/say/verbs.yaml` says what each verb does and which "
           "Role holds it; /pr-first is the coder's reading of PR First and "
           "/pr-first-reviewer the reviewer's. Every body arrives on stdin.")


def parser(doc: str) -> argparse.ArgumentParser:
    """Creates a base argument parser configured with shared channel options.

    Parameters:
        doc: Command description string.

    Returns:
        argparse.ArgumentParser: Parser initialized with standard `--role` option.
    """
    ap = argparse.ArgumentParser(description=doc, epilog=READING,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", default="coder",
                    help="which Role speaks: ~/.config/solorepo/<role>.env (default coder)")
    return ap


def speak_as(role: str) -> None:
    """Configures the active role credential file path unless overridden by environment.

    Parameters:
        role: Role name identifying the credential file (~/.config/solorepo/<role>.env).
    """
    global ROLE_ENV
    if not os.environ.get("SOLOREPO_ROLE_ENV"):
        ROLE_ENV = ROLE_DIR / f"{role}.env"


def sibling(name: str) -> types.ModuleType:
    """Imports and caches a neighbouring executable script under .meta/say/ as a module.

    Parameters:
        name: Filename of the sibling script to load.

    Returns:
        types.ModuleType: Loaded module instance.

    Raises:
        ImportError: If the module specification cannot be created.
    """
    import importlib.util
    from importlib.machinery import SourceFileLoader

    if name in _siblings:
        return _siblings[name]
    loader = SourceFileLoader(name, str(HERE / name))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise ImportError(f"no module spec for {loader.path}")
    module = importlib.util.module_from_spec(spec)
    _siblings[name] = module
    loader.exec_module(module)
    return module


_siblings: dict[str, types.ModuleType] = {}
"""Cached sibling executable modules loaded by sibling()."""


def attested_run() -> str | None:
    """Returns the attested workflow run identity, or None outside a GitHub Actions run.

    Reads `GITHUB_RUN_ID` from the environment and prefixes it with `RUN_MARK`
    (solorepo's DR-233).

    Returns:
        Attested run identifier string (`gha-<run_id>`), or None if unset.
    """
    run = os.environ.get(ENV_RUN_ID)
    return f"{RUN_MARK}{run}" if run else None


def speaker() -> str | None:
    """Resolves the active session or run identifier from the environment (solorepo's #285).

    Evaluates attested run identity first, followed by `ACTOR_SESSION` prefixed
    with `RUN_MARK`, and finally session variables declared in `ENV_SESSION`.

    Returns:
        The resolved speaker identifier string, or None if no identifier is present.
    """
    run = attested_run()
    if run:
        return run
    declared = os.environ.get("ACTOR_SESSION") or ""
    if declared.startswith(RUN_MARK):
        return declared
    return next((os.environ[k] for k in ENV_SESSION if os.environ.get(k)), None)


def actor() -> str:
    """Returns the verified session identifier for the current Actor (solorepo's DR-086, solorepo's DR-233).

    In a workflow run, validates that `ACTOR_SESSION` matches `attested_run()`.
    Refuses execution if no valid speaker identifier is established.

    Returns:
        The verified Actor session identifier.

    Raises:
        SystemExit: If `ACTOR_SESSION` conflicts with the attested run ID or no
            speaker is found in the environment.
    """
    run, declared = attested_run(), os.environ.get("ACTOR_SESSION")
    if run and declared and declared != run:
        sys.exit(f"say: this is run {run} and `ACTOR_SESSION` says {declared}; "
                 "refusing to sign as a Job that is not this one")
    session = speaker()
    if not session:
        sys.exit("say: the environment does not say who is speaking "
                 f"(need one of {ENV_SESSION}); refusing to post")
    return session


def in_a_run() -> bool:
    """Returns True if execution occurs within a GitHub Actions workflow run.

    Detects workflow execution by verifying either the presence of an attested
    GITHUB_RUN_ID or an ACTOR_SESSION starting with the RUN_MARK prefix
    (solorepo's DR-148, solorepo's DR-233).

    Returns:
        bool: True if executing within a GitHub Actions workflow, False otherwise.
    """
    return bool(attested_run()) or (os.environ.get("ACTOR_SESSION") or "").startswith(RUN_MARK)


def agent() -> str:
    """Returns the identifier of the executing agent harness component (solorepo's DR-233).

    In a workflow run, reads `ENV_RUN_AGENT` (`ACTOR_AGENT`) or derives identity
    from workflow step metadata (`ENV_RUN_STEP`). Outside a run, returns `AI_AGENT`.

    Returns:
        The resolved agent harness component name.

    Raises:
        SystemExit: If the environment does not specify the executing agent.
    """
    if in_a_run():
        step = [os.environ.get(name) for name in ENV_RUN_STEP]
        run_agent = os.environ.get(ENV_RUN_AGENT) or "/".join(part for part in step if part)
        if not run_agent:
            sys.exit(f"say: this run does not say what is speaking "
                     f"(need {ENV_RUN_AGENT}, which the workflow writes); refusing to post")
        return run_agent
    who = next((os.environ[k] for k in ENV_AGENT if os.environ.get(k)), None)
    if not who:
        sys.exit(f"say: the environment does not say what is speaking "
                 f"(need one of {ENV_AGENT}); refusing to post")
    return who


def trailers() -> str:
    """Constructs the standard Actor and Agent attribution trailer block.

    Returns:
        Formatted multi-line attribution string.
    """
    return f"Actor: {actor()}\nAgent: {agent()}"


def signed(text: str) -> str:
    """Appends Actor and Agent attribution trailers to a comment or issue body."""
    body = text.rstrip("\n")
    block = trailers()
    return body if body.endswith(block) else f"{body}\n\n{block}\n"


def piped(timeout: float = 0.5) -> str:
    """Reads non-blocking piped content from standard input if available.

    Returns an empty string immediately when stdin is connected to a tty.
    Otherwise polls stdin via select up to the specified timeout to avoid
    hanging on open but unwritten pipes.

    Parameters:
        timeout: Maximum duration in seconds to wait for stdin readability.

    Returns:
        The stripped string content from standard input, or an empty string if
        no input is available within the timeout.
    """
    if sys.stdin.isatty():
        return ""
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return sys.stdin.read().strip() if ready else ""


def stdin_body() -> str:
    """Reads non-empty body text from piped stdin or exits with an error."""
    text = piped()
    if not text:
        sys.exit("say: nothing on stdin — pipe the body in, or redirect a file")
    return text


def role_credential() -> dict[str, str]:
    """Retrieves authentication tokens for the active role from the external configuration file.

    Loads credentials from ~/.config/solorepo/<role>.env (solorepo's DR-073).
    Enforces mode 0600 file permissions and validates that GH_TOKEN is present and
    non-empty.

    Returns:
        Dictionary mapping 'GH_TOKEN' to token value, or empty dict if speaking as solo.

    Raises:
        SystemExit: If the credential file permissions are invalid or GH_TOKEN is missing.
    """
    if not ROLE_ENV.exists():
        print(f"say: no {ROLE_ENV}; speaking with ambient auth, which is the solo",
              file=sys.stderr)
        return {}
    mode = ROLE_ENV.stat().st_mode
    if mode & 0o077:
        sys.exit(f"say: {ROLE_ENV} is readable by others (mode {mode & 0o777:o}); "
                 f"refusing to use it. chmod 600 it.")
    found: dict[str, str] = {}
    for line in ROLE_ENV.read_text().splitlines():
        line = line.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        found[key.strip()] = value.strip().strip("\"'")
    if not found.get("GH_TOKEN"):
        sys.exit(f"say: {ROLE_ENV} has no GH_TOKEN")
    print(f"say: speaking with the credential in {ROLE_ENV}", file=sys.stderr)
    return {"GH_TOKEN": found["GH_TOKEN"]}


GH_TIMEOUT = 60
"""Seconds one `gh` invocation is given before it is abandoned as hung (solorepo's #738).

The bound is the default and not the rule. A verb that waits on `gh` for a
single API call is bounded by it, and a minute is far longer than one of those
takes. The `gh stack` invocations in `.meta/say/move` are the exception and
pass `timeout=None`: rebasing and force-pushing every layer of a stack, or
merging every layer up to one, can take longer than a minute with nothing
wrong, and abandoned at a bound they would report a half-rewritten stack or a
merge whose landing nothing reconciled as a hang.
"""

TIMEOUT_RETURNCODE = 124
"""The `returncode` a tolerated timeout's `CalledProcessError` carries, which is what `timeout(1)` reports one under.

It is not an exit status of anything here: where failure is not tolerated a
timeout leaves through `sys.exit`, whose status is 1, so a shell tells a hang
from a refusal by the prose on standard error and not by `$?`.
"""


def gh(*args: str, parse: bool = True, tolerate_fail: bool = False,
       timeout: float | None = GH_TIMEOUT) -> Any:
    """Executes a gh CLI command using the role credential and parses JSON output.

    Args:
        args: Arguments passed to the `gh` CLI.
        parse: Whether to parse standard output as JSON.
        tolerate_fail: Whether a failure raises rather than exits.
        timeout: Seconds to wait for the invocation, `GH_TIMEOUT` by default;
            `None` waits indefinitely, which is what the `gh stack` calls pass.

    Returns:
        The parsed JSON where `parse` is set and `gh` wrote anything to standard
        output, and the stripped standard output otherwise — which is the empty
        string for a `gh` that wrote nothing, parsed or not.

    Raises:
        subprocess.CalledProcessError: The invocation failed or timed out and
            `tolerate_fail` is set; a timeout carries `TIMEOUT_RETURNCODE`, so
            `gh_with_retry` retries it as it retries any other failure.
        SystemExit: The invocation failed or timed out and `tolerate_fail` is not set.
    """
    try:
        out = subprocess.run(["gh", *args], capture_output=True, text=True,
                             env={**os.environ, **role_credential()}, timeout=timeout)
    except subprocess.TimeoutExpired as expired:
        hung = f"`gh {' '.join(args)}` answered nothing within {timeout}s"
        if tolerate_fail:
            raise subprocess.CalledProcessError(
                TIMEOUT_RETURNCODE, ["gh", *list(args)], output="", stderr=hung) from expired
        sys.exit(f"gh: {hung}")
    if out.returncode:
        if tolerate_fail:
            raise subprocess.CalledProcessError(out.returncode, ["gh", *list(args)], output=out.stdout, stderr=out.stderr)
        sys.exit(f"gh: {out.stderr.strip()}")
    return json.loads(out.stdout) if parse and out.stdout.strip() else out.stdout.strip()


def gh_with_retry(*args: str, parse: bool = True, tries: int = 3, delay: float = 2,
                  backoff: float = 2, tolerate_fail: bool = False) -> Any:
    """Run gh, retrying on subprocess/API failure with exponential backoff.

    A call that answers nothing within `GH_TIMEOUT` seconds is a failure like
    any other here, so a hung invocation is abandoned and retried rather than
    waited on (solorepo's #738).
    """
    import time
    current_delay = delay
    for attempt in range(tries):
        try:
            return gh(*args, parse=parse, tolerate_fail=True)
        except subprocess.CalledProcessError as exc:
            if attempt == tries - 1:
                if tolerate_fail:
                    raise
                sys.exit(f"gh: {exc.stderr.strip()}")
            print(f"warning: gh {' '.join(args)} failed (attempt {attempt + 1}/{tries}): {exc.stderr.strip()}. Retrying in {current_delay}s...", file=sys.stderr)
            time.sleep(current_delay)
            current_delay *= backoff


def graphql(query: str, **variables: object) -> Any:
    """Executes a GitHub GraphQL query with provided variables."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args += ["-F", f"{key}={value}"]
    return gh(*args)


def repo() -> str:
    """Returns the nameWithOwner repository identifier for the current repo."""
    return str(gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"])


def login() -> str:
    """Queries GitHub API for the authenticated login name corresponding to the credential."""
    return str(gh("api", "user", "--jq", ".login", parse=False))


def role_login(role: str) -> str:
    """Derives the expected GitHub login name for a designated role (solorepo's DR-107).

    Parameters:
        role: The role name.

    Returns:
        The formatted login string `<owner>-<repo>-<role>`.
    """
    return f"{repo().replace('/', '-')}-{role}"


def role_identity() -> dict[str, str]:
    """Derives git author and committer environment variables for the active role.

    Returns:
        Dictionary of GIT_* environment variable bindings, or empty dict if speaking as solo.
    """
    if not role_credential():
        return {}
    who, ident = gh("api", "user", "--jq", ".login,.id", parse=False).split("\n")
    email = f"{ident}+{who}@users.noreply.github.com"
    return {"GIT_AUTHOR_NAME": who, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": who, "GIT_COMMITTER_EMAIL": email}


def role_signing_key() -> pathlib.Path | None:
    """Resolves the SSH signing key path for the active role (solorepo's DR-073, solorepo's DR-197).

    Validates that the key file exists and has permissions not readable by others (mode 0600).

    Returns:
        Path to the signing key file, or None if speaking as solo or key is not configured.

    Raises:
        SystemExit: If the key file exists but has permissions readable by others.
    """
    if not role_credential():
        return None
    key_path: pathlib.Path | None = None
    if os.environ.get("SOLOREPO_SIGNING_KEY"):
        key_path = pathlib.Path(os.environ["SOLOREPO_SIGNING_KEY"]).expanduser()
    elif ROLE_ENV.exists():
        for line in ROLE_ENV.read_text().splitlines():
            line = line.strip().removeprefix("export ").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "GIT_SIGNING_KEY":
                key_path = pathlib.Path(value.strip().strip("\"'")).expanduser()
                break
    if not key_path:
        key_path = ROLE_DIR / f"{ROLE_ENV.stem}_signing.key"
    if not key_path.exists():
        return None
    mode = key_path.stat().st_mode
    if mode & 0o077:
        sys.exit(f"say: {key_path} is readable by others (mode {mode & 0o777:o}); "
                 f"refusing to use it. chmod 600 it.")
    return key_path
