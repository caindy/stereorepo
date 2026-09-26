"""The reconciler's concurrency group and the merge manager's lock (solorepo's DR-267).

One module for one probe, so a history log's Evidence names the file holding it (solorepo's DR-209).
"""
import datetime
import re
from typing import Any

import yaml

from checks.collect import ROOT, check
from checks.probes.harness import FakeGitHub, load_channel, outcome, stood_in

WORKFLOWS = ROOT / ".github" / "workflows"

WORKFLOW_SUFFIXES = (".yml", ".yaml")
"""What GitHub reads a workflow from, both of which this probe reads too."""

RECONCILER = "reconcile.yml"
"""The workflow `_groups` holds to a concurrency group no other workflow declares."""

GROUP_LINE = re.compile(r"^(\s*group:\s*).*$", re.MULTILINE)
"""The workflow-level declaration one deliberate regression rewrites, before it is read again."""

FIRST_JOB = re.compile(r"^(jobs:\n)(\s+)(\S+:)\n", re.MULTILINE)
"""Where the other regression writes a job-level `concurrency`, which GitHub reads too."""

LOCK = "refs/tags/merge-manager-lock"
"""The ref the manager's mutual exclusion is taken on, as the fake's store keys it."""

RUNNING = "gha-11111"
"""A holder that names a workflow run GitHub still reports as in flight."""

STOPPED = "gha-22222"
"""A holder that names a workflow run GitHub reports as completed."""

SESSION = "a session at somebody's desk"
"""A holder that names no run, which is the holder `LOCK_STALE_MINUTES` is the whole test for."""

UNANSWERED = "gha-33333"
"""A holder that names a workflow run GitHub will not answer for, which falls to the clock."""

DATELESS = "a session whose lock carries no date"
"""A holder neither test reaches, there being no run to ask after and no date to measure."""

LOCK_READ = "/git/ref/tags/"
"""The endpoint a case makes GitHub refuse: the holder read, and not the create or the delete."""


def workflow_text() -> dict[str, str]:
    """The YAML of every workflow, by file name; `.yaml` counts, since GitHub reads it."""
    return {path.name: path.read_text() for path in sorted(WORKFLOWS.iterdir())
            if path.suffix in WORKFLOW_SUFFIXES}


def declared_in(block: Any) -> str:
    """The group one `concurrency` declares, written either as a mapping or as the group alone."""
    if isinstance(block, str):
        return block
    return str((block or {}).get("group") or "") if isinstance(block, dict) else ""


def groups(texts: dict[str, str]) -> dict[str, list[str]]:
    """Every concurrency group each workflow declares, by file name.

    Both places GitHub reads one are counted: the workflow's own `concurrency`
    and each job's, since a job-level group of the reconciler's puts the two
    managers back into one group as surely as a workflow-level one does.

    Parameters:
        texts (dict): The YAML to read, by file name. The deliberate regression
            passes mutated text here, so that it travels the reading it is
            meant to be observed failing.

    Returns:
        dict[str, list[str]]: The groups declared, by file name; a workflow
            declaring none is absent.
    """
    found: dict[str, list[str]] = {}
    for name, text in texts.items():
        workflow = yaml.safe_load(text) or {}
        blocks = [workflow.get("concurrency")]
        blocks += [job.get("concurrency") for job in (workflow.get("jobs") or {}).values()
                   if isinstance(job, dict)]
        if declared := [group for group in map(declared_in, blocks) if group]:
            found[name] = declared
    return found


def shared_with(declared: dict[str, list[str]], workflow: str) -> list[str]:
    """The other workflows in a group of `workflow`'s, whose runs may cancel its pending one."""
    mine = set(declared.get(workflow) or [])
    return sorted(name for name, groups_ in declared.items()
                  if name != workflow and mine.intersection(groups_))


def regressed(texts: dict[str, str], group: str) -> dict[str, str]:
    """The workflows with the reconciler's declared group rewritten to `group`.

    The mutation is made in the YAML and read back through `groups`, rather
    than in the dictionary `groups` answered: a mutation of the answer is true
    by construction and observes nothing (Article 4).

    Parameters:
        texts (dict): The workflows as they stand.
        group (str): The group to put the reconciler back into.

    Returns:
        dict[str, str]: The same workflows, the reconciler's text rewritten.
    """
    return {**texts, RECONCILER: GROUP_LINE.sub(rf"\g<1>{group}", texts[RECONCILER], count=1)}


def regressed_job(texts: dict[str, str], group: str) -> dict[str, str]:
    """The workflows with `group` declared on the reconciler's first job, its own group left alone.

    The reading counts both places GitHub reads a group from, so the sentence
    saying a job-level declaration puts the two managers back into one group is
    only evidence where a job-level declaration is what the mutation writes.

    Parameters:
        texts (dict): The workflows as they stand.
        group (str): The group to put the reconciler's job into.

    Returns:
        dict[str, str]: The same workflows, the reconciler's text rewritten.
    """
    written = FIRST_JOB.sub(rf"\g<1>\g<2>\g<3>\n\g<2>  concurrency: {group}\n",
                            texts[RECONCILER], count=1)
    return {**texts, RECONCILER: written}


def held_by(who: str, taken: datetime.datetime | None) -> dict[str, Any]:
    """The tag object a fake answers for a lock already held, which `quiet` points the ref at.

    Parameters:
        who (str): The holder the tag's message names.
        taken (datetime | None): When the lock was taken, or None for a tag
            carrying no date, which is the holder `lock_is_dead` breaks on
            sight because neither of its tests can be made on it.

    Returns:
        dict: The tag object, as GitHub's tags endpoint answers one.
    """
    tag: dict[str, Any] = {"sha": "held", "message": who}
    if taken is not None:
        tag["tagger"] = {"date": taken.isoformat()}
    return tag


def quiet(runs: dict[str, str | None] | None = None, holder: dict[str, Any] | None = None,
          standing_at: str | None = None, unreadable: dict[str, int] | None = None) -> FakeGitHub:
    """A GitHub with no open pull requests, so the manager's only act is the lock.

    The queue is empty on purpose: what these cases read is which manager gets
    as far as evaluating it, and an empty queue makes "idle — no open pull
    requests" the sentence that says one did.

    Parameters:
        runs (dict): The status GitHub answers for each run identifier,
            `in_progress` by default and None for a run it will not answer for.
        holder (dict): The tag object the lock is already held at, or None for a free lock.
        standing_at (str): A sha to point the ref at without writing the tag,
            which is the lock GitHub will not serve a holder for.
        unreadable (dict): Endpoint marks GitHub refuses with something that is
            not a 404, each with the number of reads answered first.

    Returns:
        FakeGitHub: The fake, its `git` store seeded.
    """
    fake = FakeGitHub({})
    fake.git.runs = dict(runs or {})
    fake.git.unreadable = dict(unreadable or {})
    if holder is not None:
        fake.git.tags[str(holder["sha"])] = holder
        fake.git.refs[LOCK] = str(holder["sha"])
    if standing_at is not None:
        fake.git.refs[LOCK] = standing_at
    return fake


@check("merge lock probes", pre=True)
def merge_lock_probes() -> list[str]:
    """The reconciler's group is its own, and the lock holds two managers apart (solorepo's DR-267).

    The group first, over the workflows as they stand: `reconcile.yml` shares
    its concurrency group with no other workflow, because GitHub holds at most
    one pending run per group and cancels the waiting one when a third arrives.
    Two deliberate regressions put the reconciler back into `merge.yml`'s group
    in the workflow's own YAML — one at the workflow's level and one at its
    job's, both of which GitHub reads — and read it again through the same
    parse, which is observed to fail, under Article 4.

    Then the lock, over a GitHub with an empty queue, so that reaching the
    evaluation at all is the outcome read: a manager finding the lock free
    takes it, evaluates, and gives it back, leaving the ref gone; a second
    manager finding it held by a run still in flight stands down without
    evaluating and leaves the holder's ref where it was; and one finding it
    held by a run GitHub reports completed, by a run GitHub will not answer
    for that is older than `LOCK_STALE_MINUTES`, by a session that took it as
    long ago, by a holder carrying no date, or by no tag GitHub will serve,
    breaks it and evaluates, since a run cancelled or crashed mid-merge
    releases nothing, and a lock nothing will release freezes every merge
    after it (solorepo's DR-264).

    Last, the reads GitHub refuses rather than answers, which are not the same
    fact as a lock that is absent and want the opposite act at each of the
    three places the lock is read.

    Returns:
        list[str]: Discrepancies and unobserved failures detected during evaluation.
    """
    return _groups() + _lock()


def _groups() -> list[str]:
    """The reconciler's group is its own, and sharing `merge.yml`'s is observed to fail."""
    problems: list[str] = []
    texts = workflow_text()
    declared = groups(texts)
    if RECONCILER not in declared:
        return [f"merge lock: {RECONCILER} declares no concurrency group"]
    if shared := shared_with(declared, RECONCILER):
        problems.append(f"merge lock: {RECONCILER} shares a group of {declared[RECONCILER]} with "
                        f"{', '.join(shared)}, whose runs can cancel its pending pass")
    if not (merge := declared.get("merge.yml")):
        return [*problems, "merge lock: merge.yml declares no concurrency group to regress into"]
    for where, regress in (("workflow", regressed), ("job", regressed_job)):
        mutated = regress(texts, merge[0])
        if mutated[RECONCILER] == texts[RECONCILER]:
            problems.append(f"merge lock: {RECONCILER}'s {where}-level group was not written, so "
                            "the regression observed nothing")
        elif not shared_with(groups(mutated), RECONCILER):
            problems.append(f"merge lock: the reconciler put into the merge workflow's group at "
                            f"{where} level was not observed to fail")
    return problems


def _lock() -> list[str]:
    """One manager takes the lock and gives it back, a second stands down, an abandoned breaks."""
    problems: list[str] = []
    now = datetime.datetime.now(datetime.UTC)
    channel, _, programs = load_channel()
    move = programs["move"]
    stale = datetime.timedelta(minutes=move.manager.lock.LOCK_STALE_MINUTES + 1)

    free = quiet()
    with stood_in(channel, gh=free):
        took = run_manager(move)
    if "idle — no open pull requests" not in took.out:
        problems.append(f"merge lock: the lock was free and nothing evaluated:\n{took.out}")
    if free.git.refs:
        problems.append(f"merge lock: the manager kept the lock it took: {free.git.refs}")

    for who, holder in ((RUNNING, held_by(RUNNING, now)), (SESSION, held_by(SESSION, now))):
        busy = quiet(runs={RUNNING.removeprefix(channel.RUN_MARK): "in_progress"}, holder=holder)
        with stood_in(channel, gh=busy):
            stood = run_manager(move)
        if f"another manager holds the lock ({who})" not in stood.out:
            problems.append(f"merge lock: a manager met the lock held by {who}, not standing "
                            f"down to it:\n{stood.out}")
        if "idle — no open pull requests" in stood.out:
            problems.append("merge lock: the queue was evaluated under another's "
                            f"lock:\n{stood.out}")
        if busy.git.refs.get(LOCK) != "held":
            problems.append(f"merge lock: standing down moved the holder's lock: {busy.git.refs}")

    abandoned = ((quiet(runs={STOPPED.removeprefix(channel.RUN_MARK): "completed"},
                        holder=held_by(STOPPED, now)), f"breaking the lock {STOPPED}"),
                 (quiet(runs={UNANSWERED.removeprefix(channel.RUN_MARK): None},
                        holder=held_by(UNANSWERED, now - stale)),
                  f"breaking the lock {UNANSWERED}"),
                 (quiet(holder=held_by(SESSION, now - stale)), f"breaking the lock {SESSION}"),
                 (quiet(holder=held_by(DATELESS, None)), f"breaking the lock {DATELESS}"),
                 (quiet(standing_at="no tag was ever written for this"),
                  "stands at no tag GitHub will serve"))
    for dead, said in abandoned:
        with stood_in(channel, gh=dead):
            broke = run_manager(move)
        if said not in broke.out:
            problems.append(f"merge lock: an abandoned lock was not broken, expecting "
                            f"{said!r}:\n{broke.out}")
        if "idle — no open pull requests" not in broke.out:
            problems.append("merge lock: breaking a dead lock did not go on to "
                            f"evaluate:\n{broke.out}")
        if dead.git.refs:
            problems.append(f"merge lock: the manager kept the lock it broke: {dead.git.refs}")
    return problems + _unreadable(channel, move, now)


def _unreadable(channel: Any, move: Any, now: datetime.datetime) -> list[str]:
    """A lock GitHub refuses to read is not an absent one, at each of the three places it is read.

    The refusal is not a 404, which is the whole distinction: a read that fails
    answers nothing about who holds the lock, so a manager that cannot read a
    held one stands down rather than breaking it, and one that cannot read back
    its own take or its own release gives the ref away rather than leaving it
    for the staleness clock. Treating all three as an absent lock is the
    regression `LockUnreadableError` exists against.

    Parameters:
        channel (module): The channel the fake is stood in for, loaded once.
        move (module): The `move` program under test.
        now (datetime.datetime): The moment the holders are taken at.

    Returns:
        list[str]: Discrepancies and unobserved failures detected during evaluation.
    """
    problems: list[str] = []
    held = quiet(holder=held_by(RUNNING, now), unreadable={LOCK_READ: 0})
    with stood_in(channel, gh=held):
        blind = run_manager(move)
    if "would not say who holds the lock" not in blind.out:
        problems.append(f"merge lock: a held lock GitHub would not read was not stood down "
                        f"to:\n{blind.out}")
    if "idle — no open pull requests" in blind.out:
        problems.append(f"merge lock: the queue was evaluated under a lock nobody could "
                        f"read:\n{blind.out}")
    if held.git.refs.get(LOCK) != "held":
        problems.append(f"merge lock: a lock GitHub would not read was broken: {held.git.refs}")

    wrote = quiet(unreadable={LOCK_READ: 0})
    with stood_in(channel, gh=wrote):
        gave = run_manager(move)
    if "would not read the lock back" not in gave.out:
        problems.append(f"merge lock: a read-back GitHub refused was not stood down "
                        f"to:\n{gave.out}")
    if wrote.git.refs:
        problems.append(f"merge lock: the ref this run wrote was left behind: {wrote.git.refs}")

    took = quiet(unreadable={LOCK_READ: 1})
    with stood_in(channel, gh=took):
        released = run_manager(move)
    if "idle — no open pull requests" not in released.out:
        problems.append(f"merge lock: a readable lock was not taken:\n{released.out}")
    if "giving back the one this run took" not in released.out:
        problems.append(f"merge lock: a release GitHub would not read the holder for declined "
                        f"to release:\n{released.out}")
    if took.git.refs:
        problems.append(f"merge lock: the lock was kept where its holder could not be read: "
                        f"{took.git.refs}")
    return problems


def run_manager(move: Any) -> Any:
    """Run the lock probe without the separately probed Epic-maintenance act."""
    with stood_in(move.manager.epics, close_completed=lambda: None):
        return outcome(lambda: move.manager.merge_manager())
