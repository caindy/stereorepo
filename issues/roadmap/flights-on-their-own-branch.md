# Flights on their own branch, so a Flight can be deferred

A Flight's parts land on `main` as each is done, so by its desk check the
Flight is already in `main`: that is what lets it deploy to UAT, and why its
desk check does not hold the loop. But a desk check that goes badly can then
only be answered by rolling forward, with more parts, or by reverting the
Flight's commits as a unit. The Flight cannot be set aside while another,
perhaps better specified, is flown instead.

The alternative: a Flight's parts land on `flight/<slug>`, which `main` takes
as a whole when the developer accepts the Flight. Deferring is then leaving
the branch where it is and starting another Flight from `main`. Delivery to
UAT runs from the Flight branch. The cost is drift: the branch falls behind
`main` while it runs and while it is deferred, and a long deferral makes the
rebase that resumes it expensive.

This reverses the roll-forward model the `flights` Flight built, so it waits
for experience with that model, and for the pair-versus-single-seat
evaluation.
