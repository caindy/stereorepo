"""Review approval validation enforcing notice promotion (solorepo's DR-285)."""
import sys
from collections.abc import Sequence
from typing import Any

import channel
import check_pr

THREADS_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 50) {
            nodes {
              id
              body
            }
          }
        }
      }
    }
  }
}
"""


def unpromoted_coder_notices(threads: Sequence[dict[str, Any]]) -> list[str]:
    """Return list of thread IDs that carry unpromoted coder notices.

    A review thread that is unresolved and whose comments include a coder
    notice ('**Noticed and not done.**') must be promoted by the approving
    reviewer before submitting an approval verdict (solorepo's DR-285).

    Parameters:
        threads: Sequence of review thread node dictionaries.

    Returns:
        List of thread node IDs containing unpromoted coder notices.
    """
    notices: list[str] = []
    for t in threads:
        if t.get("isResolved"):
            continue
        comments_obj = t.get("comments")
        comments = comments_obj.get("nodes", []) if isinstance(comments_obj, dict) else []
        if any(check_pr.NOTICED.search(c.get("body") or "") for c in comments):
            notices.append(t["id"])
    return notices


def refuse_unpromoted_notices(pr: int | str) -> None:
    """Refuse approval if the pull request holds unresolved coder notices (solorepo's DR-285).

    Parameters:
        pr: The pull request number being reviewed.

    Raises:
        SystemExit: If unresolved coder notices are present on the pull request.
    """
    repo_slug = channel.repo()
    owner, name = repo_slug.split("/", 1)
    res = channel.graphql(THREADS_QUERY, owner=owner, name=name, number=int(pr))
    repo_data = (res.get("data") or {}).get("repository") or {}
    pr_data = repo_data.get("pullRequest") or {}
    nodes = (pr_data.get("reviewThreads") or {}).get("nodes", [])
    notices = unpromoted_coder_notices(nodes)
    if notices:
        ids = ", ".join(notices)
        sys.exit(f"say: cannot approve #{pr} — {len(notices)} coder notice(s) must be promoted "
                 f"via 'post promote' first (solorepo's DR-285): {ids}")
