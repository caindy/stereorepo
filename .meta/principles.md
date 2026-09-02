## Design principles

_The reasoning that keeps recurring, stated once._

**Keep the axes clean.** Expressiveness comes from the *product* of Capability ×
Securable, not from splitting one axis to encode the other. Never let an object
into a Capability name: "edit files" is a Capability, `.meta/**` is a Securable,
and the pair is a Permission. When tempted to add a dimension to Capability, ask
which axis it belongs to.

**Prefer derived over declared.** A summary that can drift from what it
summarises is worse than no summary, because people trust the flag over the
truth. This is why Capability carries no read/write dimension, and why
reification is likely to be delegated to a Dockerfile or nix expression that pins
its closure by construction.

**Role travels; Remit does not.** `Agency = Role + Remit`, and that is the
portability seam. A Remit's Permissions name Securables that exist only in the
host repo, so a package carries Role and Persona while the Remit is bound at
install time in the destination.

**Audit is Permission in the past tense.** Both are the same triple of
Capability, Securable and Actor — one as authority, one as fact. Diffing them
makes least privilege a report rather than a discipline: an ALLOWED record with
no authorising Permission is a violation, and a Permission with no matching
record is an over-grant. This matters more in a team of one, where no second
person is around to notice.

**Enforce what the schema can; comment the rest.** LinkML rules cover what is
expressible (a stopped Execution records its end time; a tool composes nothing).
Invariants crossing reference boundaries or deep paths are written as class
comments so the checker that must own them is at least identified.
