# Count the shell commands a sandboxed seat is still refused

With Bash in Claude Code's sandbox (DR-302), a compound command built from
plain parts runs without a prompt. Claude Code still refuses, before running
it, a command it cannot analyse statically: a variable set from a command
substitution (`x=$(git rev-parse HEAD) && echo "$x"`), or a redirect to a path
built at run time (`echo hi > "$TMPDIR/f"`). In `-p` mode each refusal is a
denial, and the seat has to rewrite the command.

The `result` event of each turn carries `permission_denials`. Nothing reads it
yet, so nobody knows whether these refusals cost the seats much work.

## Wanted

- Record each turn's denial count, and the denied commands, in the loop's
  event log, so that `just pair-status` or the event log shows how often it
  happens.
- If the refusals turn out to be frequent, find out from the Claude Code
  documentation whether a setting allows them inside the sandbox, and decide
  with the developer.

## Out of scope

Changing the sandbox's write confinement or the deny list.
