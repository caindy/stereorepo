"""The extension a `gh stack` call needs, and the account a call gives of itself (solorepo's #797).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import subprocess
import types
from typing import Any

from checks.collect import check
from checks.probes.harness import (
    load_channel,
    outcome,
    stood_in,
)


def _gh_subprocess(calls: list[tuple[str, ...]], installed: bool, extension: str,
                   answers: dict[tuple[str, ...], tuple[int, str, str]],
                   envs: list[dict[str, str]] | None = None) -> Any:
    """As much of `subprocess` as `channel.gh` uses, over a machine holding the extension or not.

    Each invocation is recorded in `calls` as the arguments `gh` was given,
    without the program name, so a probe reads the order the calls were made
    in. A call `answers` names is answered from it, keyed on its arguments,
    the listing included, so a machine that will not say what it holds is a
    machine this stands in for. Otherwise `extension list` answers a listing
    naming `extension` once the machine holds it and an empty one before that;
    `extension install` installs it and answers as the CLI does, on standard
    error. Every other call exits 0 having printed nothing — which is the shape
    this probe is about.
    """
    state = {"installed": installed}

    def run(cmd: list[str], **kwargs: Any) -> Any:
        args = tuple(cmd[1:])
        calls.append(args)
        if envs is not None:
            envs.append(dict(kwargs.get("env") or {}))
        if args in answers:
            code, out, err = answers[args]
            return subprocess.CompletedProcess(cmd, code, stdout=out, stderr=err)
        if args[:2] == ("extension", "list"):
            listed = f"gh stack\t{extension}\tv0.1.1" if state["installed"] else ""
            return subprocess.CompletedProcess(cmd, 0, stdout=listed, stderr="")
        if args[:2] == ("extension", "install"):
            state["installed"] = True
            return subprocess.CompletedProcess(
                cmd, 0, stdout="", stderr=f"Successfully installed {extension}")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return types.SimpleNamespace(run=run, TimeoutExpired=subprocess.TimeoutExpired,
                                 CalledProcessError=subprocess.CalledProcessError,
                                 CompletedProcess=subprocess.CompletedProcess)


@check("gh stack extension probes", pre=True)
def gh_stack_extension_probes() -> list[str]:
    """`channel.gh` over a machine without `gh stack`, and over a call told to relay what it said.

    `gh stack` is an extension rather than part of the CLI, and the CLI
    installs it on first use: on a machine without it, `gh stack merge 793
    --squash --yes` prints `Successfully installed github/gh-stack`, exits 0
    and never merges. A runner is such a machine every time it starts, so the
    invocation the install consumes is whichever stack call the job makes
    (solorepo's #797).

    Five cases over a `subprocess` whose `run` answers rather than executes.
    The first asserts the cure: a stack call on a machine without the extension
    installs it and then makes the call, in that order, so the install has
    nothing left to consume. The second asserts the cost of the cure is one
    read — the extension already installed, no install is attempted — and that
    a call which is not a stack call carries no preflight at all, since every
    verb of the channel would otherwise pay for a path only five calls take.
    The third asserts what a machine that will not answer the listing gets: a
    listing read that exits non-zero installs rather than exiting, so the
    preflight cannot end a run over a question it asked itself.

    The fourth and fifth are the instrumentation. `echo=True` relays the exit
    status and both streams on standard error, so a merge that exits 0 saying
    only that it installed an extension names itself, where `merge()`'s
    read-back in `.meta/lib/move/pull_requests.py` says only that the pull
    request is still open and reads as GitHub being slow. A call that printed
    nothing at all is relayed as having said nothing, which is a different
    report from no report; and a call not asked to echo still says nothing,
    because the relay is for the few calls whose success is read back from
    GitHub rather than for every call the channel makes.

    `role_credential` is stood in as well, so the cases turn on the extension
    rather than on whether the machine running them holds a Role's key.
    A `gh stack rebase` invocation sets `rebase.empty = keep` in the environment
    so that zero-diff Seed Commits on draft layers survive cascading rebases
    (solorepo's DR-273, solorepo's #1006).
    """
    channel, _, _ = load_channel()
    problems: list[str] = []
    extension = channel.STACK_EXTENSION
    merge = ("stack", "merge", "7", "--squash", "--yes")
    listing = ("extension", "list")
    install = ("extension", "install", extension)

    absent: list[tuple[str, ...]] = []
    with stood_in(channel, subprocess=_gh_subprocess(absent, False, extension, {}),
                  role_credential=lambda: {}):
        outcome(lambda: channel.gh(*merge, parse=False, timeout=None))

    present: list[tuple[str, ...]] = []
    with stood_in(channel, subprocess=_gh_subprocess(present, True, extension, {}),
                  role_credential=lambda: {}):
        outcome(lambda: channel.gh(*merge, parse=False, timeout=None))
        outcome(lambda: channel.gh("pr", "view", "7", parse=False))

    mute: dict[tuple[str, ...], tuple[int, str, str]] = {
        listing: (1, "", "gh: could not list extensions")}
    unlisted: list[tuple[str, ...]] = []
    with stood_in(channel, subprocess=_gh_subprocess(unlisted, False, extension, mute),
                  role_credential=lambda: {}):
        unanswered = outcome(lambda: channel.gh(*merge, parse=False, timeout=None))

    consumed: dict[tuple[str, ...], tuple[int, str, str]] = {
        merge: (0, "", f"Successfully installed {extension}")}
    said: list[tuple[str, ...]] = []
    envs: list[dict[str, str]] = []
    with stood_in(channel, subprocess=_gh_subprocess(said, True, extension, consumed, envs),
                  role_credential=lambda: {}):
        relayed = outcome(lambda: channel.gh(*merge, parse=False, timeout=None, echo=True))
        nothing = outcome(
            lambda: channel.gh("stack", "rebase", parse=False, timeout=None, echo=True))
        quiet = outcome(lambda: channel.gh(*merge, parse=False, timeout=None))

    if absent != [listing, install, merge]:
        problems.append(f"gh: a stack call on a machine without {extension} made "
                        f"{absent}, where the install has to precede the call it would "
                        "otherwise be made instead of")
    if present != [listing, merge, ("pr", "view", "7")]:
        problems.append(f"gh: a stack call on a machine holding {extension} made "
                        f"{present}, where one read settles it and a call that is not "
                        "a stack call asks nothing about extensions at all")
    if unlisted != [listing, install, merge] or unanswered.code is not None:
        problems.append(f"gh: a stack call on a machine whose listing read failed made "
                        f"{unlisted} and came to {unanswered.code!r}, where a machine that "
                        "will not say what it holds is one to install on rather than one "
                        "to end the run over")
    if (f"gh {' '.join(merge)}: exit 0" not in relayed.err
            or "Successfully installed" not in relayed.err):
        problems.append(f"gh: a call told to echo relayed {relayed.err!r}, which names neither "
                        "the call and its exit status nor what the call said, and a merge that "
                        "exits 0 without merging is read off those words or off nothing")
    if "gh stack rebase: exit 0 and said nothing" not in nothing.err:
        problems.append(f"gh: a call that printed nothing relayed {nothing.err!r}, where a call "
                        "silent on both streams is a finding rather than an absence of one")
    if quiet.err:
        problems.append(f"gh: a call not asked to echo relayed {quiet.err!r}, and a channel that "
                        "narrates every call has nowhere left to say the one thing that matters")
    rebase_envs = [env for call, env in zip(said, envs, strict=True)
                   if call[:2] == ("stack", "rebase")]
    if (not rebase_envs or rebase_envs[0].get("GIT_CONFIG_KEY_0") != "rebase.empty"
            or rebase_envs[0].get("GIT_CONFIG_VALUE_0") != "keep"):
        problems.append("gh: stack rebase did not set rebase.empty = keep "
                        "in git environment (solorepo's #1006)")
    merge_envs = [env for call, env in zip(said, envs, strict=True)
                  if call[:2] == ("stack", "merge")]
    if any("GIT_CONFIG_KEY_0" in env for env in merge_envs):
        problems.append("gh: stack merge call unexpectedly set git rebase configuration")
    return problems



