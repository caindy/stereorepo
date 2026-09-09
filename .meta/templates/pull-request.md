# Pull request form

The pull request body. Written when the work **starts** — a body written at the
end is a summary of the diff, and git already holds the diff.

Route first. Where an artifact owns a paragraph it goes to the artifact, not
here: what a schema means goes to the schema, why a decision was taken goes to a
decision record, a rule goes to the Charter, a word goes to the vocabulary. What
is left is the residue, and the residue is what this form holds.

**This form is the only copy of what a body must contain.** `check_pr.py` reads
the fence below rather than a list of its own, so a heading added here is
required by that act alone.

```markdown
## <a title someone would search for>

**What changed.** The shape of the change. Not the file list; the diff has that.

**What the ground looked like.** The context that will not be visible from the
code afterwards — what was already true, what was tried and abandoned, what
constraint made the obvious approach wrong.

**What would make this removable.** The condition under which this comes out
again. "Nothing would" means it is load-bearing forever, and that claim needs its
reason stated.

**What was decided.** One link per item, to a DR. A decision taken inside a
change belongs in the same change; recorded afterwards, it is a decision only
its participants could cite for as long as the gap lasted. "None." is a complete
answer and often the true one.

- DR-<nnn> — <the question that demanded an answer, in one line>

**What it closes.** One item per Challenge this pull request finishes, written
with a closing keyword so the merge closes the Issue and nobody has to remember
to. "None." is allowed and is a question: PR First says a pull request exists
because a Challenge does.

- Closes #<n> — <the Challenge, in one line>

**What was noticed and not done.** One link per item, to an Issue, filled in at
**merge** — these are the conversations that survived the argument. Empty until
then, and often empty for good: an item the change overtook is answered in its
thread, not tracked.

- #<n> — <one line, so the list is readable without opening anything>
```

**The fourth heading is asked because it was forgotten.** A decision taken in a
change and recorded later is one that lived, for a while, only where it was
argued — which is A11's failure with a delay rather than an exemption. Nothing
can check whether a decision was taken; a form can put the question in front of
whoever would otherwise not think to ask it.

Optional, where they apply:

- **Evidence.** A measurement, with how it was taken and what the control was.
- **Supersedes.** Name the earlier pull request. Never rewrite it.

The third heading is the point of the form. It is Chesterton's Fence answered in
advance: a later reader deciding whether to remove something needs to know what
it was put there to hold, and that is exactly what nobody records at the time.

**Route every finding in the change that records it** (A13 — a finding that
exists only in a pull request has not been made). A rule established here goes to
the Charter in the same change; something foreclosed goes to a decision record.
The pull request is durable and searchable and still not authoritative.

**Commit messages stay short** (A14). If a message has begun explaining, the
explanation belongs in an artifact or here.

**The fifth heading closes the Issue.** GitHub reads `Closes #n` in a body and
closes the Issue when the pull request merges to the default branch, which is
the one act here that needs no verb: the merge is the act, and the body the form
already requires carries the link (DR-089). Write it only on the pull request
that finishes the Challenge; one that takes part of it up names the Issue
without the keyword. `check_pr.py` holds the shape, not the judgement.

**The sixth heading takes links, not text** (A15). Work noticed and not done is
a Challenge nobody has taken up, and it needs what an Issue has and prose does
not: an open and a closed, and a life longer than this body's.

Raise it first as a **conversation on the diff**, tagging the solo, opening with
`**Noticed and not done.**` so it is not mistaken for a point owed an answer, at
the moment you notice it. The **last** comment decides, so re-mark it if the
argument moves on and it is still parked — and simply reply without the marker
when the change has overtaken it. `.meta/say/post notice` signs it with the `Actor:` and `Agent:` trailers the
commits carry — the marker says what kind of thread it is, `Actor` says who is
speaking, and in a repository where every comment is posted under one account
nothing else can. An unresolved conversation blocks the merge, so nothing is walked
past silently, and the item keeps the context it was noticed in. Promote it to an
Issue at merge if it survived the argument, and resolve the thread with the link
— which is also what satisfies A16.

What earns an Issue is whether you can say **what would make it worth doing**. A
trigger, or a cost that will land. That is the same question as *what would make
this removable*, turned to face forward.
