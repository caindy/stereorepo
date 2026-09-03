# Pull request form

The pull request body. Written when the work **starts** — a body written at the
end is a summary of the diff, and git already holds the diff.

Route first. Where an artifact owns a paragraph it goes to the artifact, not
here: what a schema means goes to the schema, why a decision was taken goes to a
decision record, a rule goes to the Charter, a word goes to the vocabulary. What
is left is the residue, and the residue is what this form holds.

```markdown
## <a title someone would search for>

**What changed.** The shape of the change. Not the file list; the diff has that.

**What the ground looked like.** The context that will not be visible from the
code afterwards — what was already true, what was tried and abandoned, what
constraint made the obvious approach wrong.

**What would make this removable.** The condition under which this comes out
again. "Nothing would" means it is load-bearing forever, and that claim needs its
reason stated.
```

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
