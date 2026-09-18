"""Where a Role's signing key is, and what the channel does when it is absent or readable by others.
"""
import pathlib
import tempfile

from checks.collect import check
from checks.probes.harness import (
    answered,
    environment,
    load_channel,
    stood_in,
)


@check("signing key probes", pre=True)
def signing_key_probes():
    """`channel.role_signing_key()` finds the Role's key, refuses one readable
    by others, and answers `None` for the solo (solorepo's DR-197).

    The cases, in the order the key is looked for, each later source taking
    precedence over the ones before: with no credential file at `ROLE_ENV`,
    the speaker is the solo and there is no key; with `coder.env` holding a
    token, the key is `<ROLE_DIR>/coder_signing.key`; that key with mode `0644`
    is refused, since a key readable by others is not a Role's; `GIT_SIGNING_KEY`
    in the credential file names the key instead; and `SOLOREPO_SIGNING_KEY` in
    the environment names it above both. Every file is written mode `0600` in a
    temporary directory stood in for `ROLE_DIR`, `ROLE_ENV` is stood in for
    beside it, and what the channel prints about the credential is captured.
    """
    channel, _, _ = load_channel()
    problems = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = pathlib.Path(tmpdir)
        with stood_in(channel, ROLE_ENV=tmppath / "empty.env"):
            key, code, _ = answered(channel.role_signing_key)
            if key is not None or code is not None:
                problems.append(f"signing_key: the solo: expected None, got {key!r} returned "
                                f"and {code!r} exited")
        role_env = tmppath / "coder.env"
        role_env.write_text("GH_TOKEN=fake_token_for_test\n")
        role_env.chmod(0o600)
        key_file = tmppath / "coder_signing.key"
        key_file.write_text("dummy-key\n")
        key_file.chmod(0o600)
        with stood_in(channel, ROLE_ENV=role_env, ROLE_DIR=tmppath):
            got, code, _ = answered(channel.role_signing_key)
            if code is not None or got != key_file:
                problems.append(f"signing_key: the Role's default key: expected {key_file}, "
                                f"got {got} returned and {code!r} exited")
            key_file.chmod(0o644)
            _, code, exited = answered(channel.role_signing_key)
            if not exited:
                problems.append(f"signing_key: a key readable by others (mode 0644): expected a "
                                f"refusal, got {code!r}")
            key_file.chmod(0o600)
            custom_key = tmppath / "custom.key"
            custom_key.write_text("custom-dummy-key\n")
            custom_key.chmod(0o600)
            role_env.write_text(f"GH_TOKEN=fake_token_for_test\nGIT_SIGNING_KEY={custom_key}\n")
            got, code, _ = answered(channel.role_signing_key)
            if code is not None or got != custom_key:
                problems.append(f"signing_key: GIT_SIGNING_KEY in the credential file: expected "
                                f"{custom_key}, got {got} returned and {code!r} exited")
            env_key = tmppath / "env.key"
            env_key.write_text("env-dummy-key\n")
            env_key.chmod(0o600)
            with environment(SOLOREPO_SIGNING_KEY=str(env_key)):
                got, code, _ = answered(channel.role_signing_key)
                if code is not None or got != env_key:
                    problems.append(f"signing_key: SOLOREPO_SIGNING_KEY in the environment: "
                                    f"expected {env_key}, got {got} returned and {code!r} exited")
    return problems
