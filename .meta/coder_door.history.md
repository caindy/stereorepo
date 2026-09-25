# History

### Take pass cut by its turn cap read as one that finished

A coder take pass that exhausted its turn cap ended with
`claude-code-action` reporting the step as `success`, because the process
exits in an orderly way when the model's turn ends at the cap. `coder_after`
read the step conclusion alone, so the hand-back was a branch a capped pass
never entered: the run logged "nothing to hand back", and the green pull
request it left reached a reader only through the half-hourly sweep, the
second half solorepo's DR-129 built for exactly the case where the handler is skipped
(solorepo's DR-129, solorepo's DR-277, solorepo's #845). Established:
`cut_by_cap()` reads the cap and the turns off
the execution transcript the workflow hands the door, a capped pass reaches
`hand_back()` beside one whose step failed, and the account names the cap
rather than the step conclusion, so the reviewer reads a draft it has been
told is a draft.

Evidence: `.meta/checks/probes/channel/on_coder.py::coder_door_probes`

### Second turn cap on the same pull request offered to the reviewer again

A resumed take pass cut by the cap a second time would have posted a second
cap account and requested review again, offering the reviewer a draft it had
already read once (solorepo's DR-277, solorepo's #845). Established:
`cut_before()` reads the account the first cap posted off the pull request,
and a second cap hands the Challenge to the solo through `stop`, because a
Challenge that does not fit twice is not the loop's.

Evidence: `.meta/checks/probes/channel/on_coder.py::coder_door_probes`

### Direct invocation failed to import channel module

Commit a043bdc8 extracted the coder door into `.meta/coder_door.py` and
`.meta/lib/coder_door/`. Direct invocation of `.meta/coder_door.py` from workflow
runners failed with `ModuleNotFoundError: No module named 'channel'` because
`.meta/say/` was not in `sys.path`. Established: `.meta/coder_door.py` inserts
`.meta/say/` at the front of `sys.path` so submodules importing `channel`
resolve cleanly in standalone subprocesses.

Evidence: `.meta/checks/probes/channel/on_coder.py::coder_door_probes`

### Unpushed coder run modifications lost upon runner teardown and empty diff reviewed

When a coder loop pass was cut off by turn cap or runner timeout before pushing,
uncommitted working tree modifications were destroyed upon container teardown.
Additionally, when a pull request contained only an initial plan commit,
`hand_back` found the head green and clean and requested review of an empty diff
(solorepo's #946). Established: `coder_rescue` commits uncommitted working tree
modifications using `[rescue] Uncommitted session work on Challenge #<n>` and
pushes commits directly to the active PR branch before teardown; `hand_back`
skips requesting review and records that the pull request needs continuation when
it contains only the initial plan commit (solorepo's DR-264, solorepo's #946).

Evidence: `.meta/checks/probes/channel/rescue.py::coder_rescue_probes`
