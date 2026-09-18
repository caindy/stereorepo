# History

### Verdict recorded against a head the run never read

GitHub records a review against whatever the pull request's head is when the
review lands, not against the commit the run read, and nothing compared the two
(solorepo's #566). On solorepo's #563 a verdict requesting changes, opening
"The head, 7f71793, is unchanged" and concluding "no commit has landed since
the prior verdict", was recorded against `b30d836`, the commit that had landed
fifteen seconds earlier and was the answer to the verdict before it. That left
a standing request for changes no push could clear: GitHub holds a request for
changes on a pull request until the same reviewer posts again, and the push
that would have asked for that is the one already in, so to anyone reading the
branch the request had been answered while it went on standing. It also left a
record a reader resolving to a diff finds the verdict never mentions.
Established: `refuse_if_head_moved()` compares the
head in `SOLOREPO_REVIEW_HEAD` against the head GitHub reports, and `review()`
posts nothing where they differ.

Receipt: `.meta/checks/probes/channel/verdict.py::verdict_probes`
