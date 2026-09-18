"""The one registered step: the tables run against the hooks loaded from `.meta/hooks/`, and a failure that names the row.
"""
import io
import json
import sys

from collect import check
from probes.git import events, offers, verdicts
from probes.harness import exit_of, load_hook, stood_in


def _verdicts(hooks):
    """The rows of `VERDICTS` a hook did not answer as owed, each line naming the group, the hook and the call."""
    problems = []
    for group, name, rows in verdicts.VERDICTS:
        for want, *arguments in rows:
            answer = hooks[name].blocked(*arguments)
            held = bool(answer) if want == "refuse" else not answer
            if not held:
                shown = ", ".join(repr(argument) for argument in arguments)
                problems.append(f"{group}: {name} should {want} {shown} and did not")
    return problems


def _offers(worktree):
    """The rows of `OFFERS` whose refusal offered other than the row says, or offered a command the hook itself refuses."""
    problems = []
    for group, rows in offers.OFFERS:
        for command, want in rows:
            got = worktree.plain_form(command)
            if got != want:
                problems.append(f"{group}: the refusal for {command!r} should offer {want!r} and offered {got!r}")
            elif got is not None and worktree.command_allowed(got):
                problems.append(f"{group}: the refusal for {command!r} offers {got!r}, which the hook itself refuses")
    return problems


def _events(worktree):
    """The rows of `EVENTS` whose payload the hook's entry point did not exit as the row says.

    `main()` returns the code rather than exiting with it, so the call is wrapped
    in the `sys.exit` the program's last line performs, which is what `exit_of`
    reads.
    """
    problems = []
    for group, rows in events.EVENTS:
        for want, event in rows:
            with stood_in(sys, stdin=io.StringIO(json.dumps(event))):
                code = exit_of(lambda: sys.exit(worktree.main()))
            if code != ("2" if want == "refuse" else "0"):
                problems.append(f"{group}: a {event['hook_event_name']} for {event['tool_name']} "
                                f"should {want} and exited {code}")
    return problems


def _instead(worktree):
    """The rows of `INSTEAD` whose refusal does not name the tool the row says."""
    return [f"the refusal for {command!r} should name {name} as what to use instead"
            for command, name in offers.INSTEAD
            if name not in (worktree.command_allowed(command) or "")]


@check("hook probes", pre=True)
def hook_probes():
    """Both hooks' predicates against the calls they exist to refuse and the calls they must let through, and what a `worktree_only` refusal offers instead.

    Loads `signed_channel` and `worktree_only` afresh and runs four tables in
    order: `VERDICTS`, each call with the verdict its hook owes it; `OFFERS`,
    each refused command with the nearest command its refusal names, or `None`
    where none is derivable; `EVENTS`, each before-tool payload with the code
    the entry point owes it, Claude Code's envelope beside Gemini CLI's;
    `INSTEAD`, each program off the list with the tool
    its refusal names in its place. A line names the group and the call that
    gave way, so the report says which case a predicate no longer holds. Each
    refused call sits beside the innocent neighbour the predicate must not
    catch (solorepo's #86, solorepo's #98), so an edit to either predicate
    meets both before a run does (solorepo's DR-110).
    """
    hooks = {name: load_hook(name) for name in ("signed_channel", "worktree_only")}
    worktree = hooks["worktree_only"]
    return _verdicts(hooks) + _offers(worktree) + _events(worktree) + _instead(worktree)
