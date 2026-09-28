# Hold the board's front matter to the Issue class

The ontology's `Issue` class (`.meta/work/purpose.yaml`) is the shape of an
Issue file's front matter: `difficulty` from the `Difficulty` enum, and
optionally `waits_on` and `parent`. Nothing reads it yet, so a typo such as
`dificulty: easy` or `difficulty: trivial` passes silently, and the loop treats
the Issue as ungroomed.

Add a gate step that reads every file under `issues/` on the tree and holds its
front matter to the class: no key the class does not declare, a `difficulty`
the enum holds, and a `waits_on` or `parent` that names an Issue on the board,
or one in another repository written `<repository>:<slug>`. `README.md` files
are not Issues.

Done when each of those mistakes fails the step with the file and the key, a
probe covers them, and `just gate` passes on this board.
