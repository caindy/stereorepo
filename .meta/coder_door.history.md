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
