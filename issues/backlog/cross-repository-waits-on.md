# Stop matching a cross-repository `waits_on` against this board

`purpose.yaml` says a `waits_on` entry naming an Issue in another repository is
written `<repository>:<slug>`. `pair/board.py` (`next_ready`) strips the
repository and checks the bare slug against this board's `done` stage, so such
an entry is satisfied by an unrelated local Issue with the same slug, and
otherwise it never is: the Issue waits forever.

Found while grooming `check-board-front-matter`, which leaves `board.py` alone.
Decide what a cross-repository entry should do (block until the developer
clears it, or be ignored by the loop), then make `board.py` do it and cover it
in `pair/test_pair.py`.
