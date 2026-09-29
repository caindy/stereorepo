# Publish the loop's status by a convention a cockpit can read

A cockpit across repositories comes later (`WHY_FORK.md`, section 7). What it
needs from each repository now is one convention for publishing what the loop
knows: for each repository, the Issue in flight, its stage, its round, whether
it needs the developer, and why — a desk check, an Issue sent back to the roadmap,
a seat that failed twice, a fast-forward that was refused.

Everything the loop knows is already in `.pair/` and git. Have the supervisor
also write a read-only projection of it to one well-known place per
repository, for example `~/.pairs/<repo>.json`, whenever its state changes, and
document the schema. It holds nothing the board and `.pair/` do not; a cockpit
reads it and writes nothing back.

Done when `just pair-status` and the published file agree for every state the
pair tests reach, and the schema is written down where a cockpit's author will
find it.
