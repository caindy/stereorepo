"""What the gate asks GitHub, and how: the CLI, the credential, and the GraphQL it names.

The rollup queries are written out rather than taken from `gh --json`, because the
gate's token holds no `actions` scope and the CLI's own query would need one
(solorepo's DR-153).
"""

import json
import os
import pathlib
import re
import subprocess
from typing import Any

from lib import gh as lib_gh
from lib.check_pr import ROOT

THREADS = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          resolvedBy { login }
          isOutdated
          path
          line
          comments(first: 50) { nodes { author { login } body } }
        }
      }
      reviews(last: 100) {
        nodes { author { login } state submittedAt commit { abbreviatedOid } body }
      }
      comments(last: 100) { nodes { id databaseId author { login } body } }
    }
  }
}
"""

# The check states on a pull request's head, asked for by name, per
# solorepo's DR-153. `gh --json statusCheckRollup` answers the same question,
# but the CLI's own GraphQL for that field traverses `checkSuite.workflowRun`
# — an Actions resource — and the gate's token holds no `actions` scope, so the
# whole query fails rather than returning the field null. Every reader takes a
# name and a state, and the watcher takes the run's url and when it started;
# nothing here wants a workflow run. Written out, the fetch names its own
# fields, as `THREADS` above already does.
ROLLUP = """
      commits(last: 1) { nodes { commit { statusCheckRollup {
        contexts(first: 100) { nodes {
          ... on CheckRun { name status conclusion startedAt completedAt detailsUrl }
          ... on StatusContext { context state createdAt targetUrl }
        } }
      } } } }
"""

ROLLUP_ONE = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {%s}
  }
}
""" % ROLLUP  # noqa: UP031  # reason: GraphQL query templates have literal curly braces

# Every open pull request's head, the first hundred most recently touched.
# Which hundred those are is not necessarily the hundred `gh pr list` returns:
# that call takes its own default limit and orders by whatever the CLI orders
# by, which is a fact about `gh` this file would have to assert and cannot
# cite — and resting the sweep on what the CLI does on its behalf is the thing
# solorepo's DR-153 is about. So `sweep_all` pairs the two by number and names
# what this query did not answer for, rather than needing the two to agree.
ROLLUP_ALL = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 100,
                 orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes { number %s }
    }
  }
}
""" % ROLLUP  # noqa: UP031  # reason: GraphQL query templates have literal curly braces


UNSET = lib_gh.UNSET
GH_TIMEOUT = lib_gh.GH_TIMEOUT
GhTimeout = lib_gh.GhTimeout


def _role_token() -> str | None:
    for role in ("reviewer.env", "coder.env"):
        p = pathlib.Path("~/.config/solorepo").expanduser() / role
        if p.exists():
            try:
                for line in p.read_text().splitlines():
                    line = line.strip().removeprefix("export ").strip()
                    if line.startswith("GH_TOKEN="):
                        return line.split("=", 1)[1].strip("\"'")
            except OSError:
                pass
    return None


def gh(*args: str, default: Any = UNSET, timeout: float = GH_TIMEOUT) -> Any:
    """Invokes the GitHub CLI with the role credential and parses JSON output.

    Parameters:
        *args: Command arguments passed to gh.
        default: Fallback value returned if the command fails, prints nothing,
            or prints output that is not JSON. If default is omitted, any of
            the three exits the process.
        timeout: Seconds to wait for the invocation, GH_TIMEOUT by default.

    Returns:
        Any: Parsed JSON data or the fallback.

    Raises:
        SystemExit: If the read fails and no fallback was given.
        GhTimeout: `gh` answered nothing within `timeout`. It exits with prose no
            pattern in `polling.FATAL_POLL_PATTERNS` matches, so `watch` reads it
            as transient and retries it under backoff.
    """
    env = None
    if "GH_TOKEN" not in os.environ:
        token = _role_token()
        if token:
            env = dict(os.environ, GH_TOKEN=token)
    return lib_gh.gh(
        *args,
        default=default,
        env=env,
        timeout=timeout,
        prefix="gh",
        subprocess_module=subprocess,
    )


def reason(exc: SystemExit) -> str:
    """Names what `gh` refused with, on one line.

    Returns:
        str: The stderr `gh` exited on, its newlines and runs of space collapsed,
            so that a caller degrading rather than exiting spends one line on why.
    """
    return " ".join(str(exc.code).split())


def repo() -> str:
    """Determines the current GitHub repository slug from environment, CLI, or git remote.

    Raises:
        GhTimeout: `gh` answered nothing within its bound. The git remote is the
            fallback for a `gh` that will not answer this, and not for one that
            answers nothing at all: taking it there would spend the bound on
            every call and then degrade in silence, which is a watch that crawls
            without ever failing a poll (solorepo's #738).
    """
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    if repo_name:
        return repo_name
    try:
        return str(gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"])
    except GhTimeout:
        raise
    except (OSError, SystemExit, json.JSONDecodeError, KeyError):
        out = subprocess.run(["git", "remote", "get-url", "origin"],
                             check=False, capture_output=True, text=True, cwd=ROOT)
        if out.returncode == 0 and out.stdout.strip():
            url = out.stdout.strip()
            m = re.search(r"[:/]([^/:]+)/([^/:]+?)(?:\.git)?$", url)
            if m:
                return f"{m.group(1)}/{m.group(2)}"
        return "solo/repo"


def role_login(role: str) -> str:
    """The account a Role holds, by name and not by reading anything.

    `<owner>-<repo>-<role>` is the convention solorepo's DR-107 set.
    """
    return f"{repo().replace('/', '-')}-{role}"


def pull(ref: str | int) -> dict[str, Any]:
    """Fetches all review threads and reviews for a pull request via GraphQL.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        dict: Pull request GraphQL node containing reviewThreads and reviews.
    """
    owner, name = gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"].split("/")
    number = gh("pr", "view", str(ref), "--json", "number")["number"]
    data = gh("api", "graphql", "-f", f"query={THREADS}",
              "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}")
    node: dict[str, Any] = data["data"]["repository"]["pullRequest"]
    comments = (node.get("comments") or {}).get("nodes") or []
    node["reviewThreads"]["nodes"] += comment_threads(comments, role_login("reviewer"))
    return node


def comment_threads(comments: list[dict[str, Any]], reviewer: str) -> list[dict[str, Any]]:
    """The reviewer's top-level comments, each shaped as a review thread (solorepo's DR-273).

    A plan-only pull request has no line for a thread to sit on, so the
    reviewer's point on it is a top-level comment, which GitHub cannot resolve,
    and a reply carries no reference to what it answers. Each one reads as a
    thread marked `comment`, resolved once a later comment from an account other
    than the reviewer's links it (`#issuecomment-<id>`), and carrying that answer.
    Proximity is not an answer: the reviewer's own next run, or a notice posted
    in between, leaves the point owed.

    Args:
        comments: The pull request's top-level comment nodes, oldest first.
        reviewer: The reviewer Role's login.

    Returns:
        list[dict]: One thread-shaped node per comment the reviewer's account wrote.
    """
    def login(c: dict[str, Any]) -> str:
        return str((c.get("author") or {}).get("login", ""))

    shaped: list[dict[str, Any]] = []
    for i, c in enumerate(comments):
        if login(c) != reviewer:
            continue
        link = f"issuecomment-{c.get('databaseId')}"
        answer = next((a for a in comments[i + 1:]
                       if login(a) != reviewer and link in (a.get("body") or "")), None)
        shaped.append({
            "id": c.get("id"), "comment": True, "isResolved": answer is not None,
            "isOutdated": False, "resolvedBy": None, "path": None, "line": None,
            "comments": {"nodes": [c] + ([answer] if answer else [])},
        })
    return shaped


def threads(ref: str | int) -> list[dict[str, Any]]:
    """Fetches all review thread nodes for a pull request.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        list[dict]: Review thread nodes from GraphQL.
    """
    nodes: list[dict[str, Any]] = pull(ref)["reviewThreads"]["nodes"]
    return nodes


def checks_of(node: dict[str, Any]) -> list[dict[str, Any]]:
    """Extracts status check contexts from a pull request commit GraphQL node.

    Args:
        node: Pull request dictionary containing commits nodes.

    Returns:
        list[dict]: Flattened check run or status check context dictionaries.
    """
    commits = (node.get("commits") or {}).get("nodes") or []
    if not commits:
        return []
    rollup = commits[0]["commit"].get("statusCheckRollup") or {}
    nodes: list[dict[str, Any]] = (rollup.get("contexts") or {}).get("nodes") or []
    return nodes


def rollup_of(number: int) -> list[dict[str, Any]]:
    """Fetches status check contexts for the head commit of a specific pull request.

    Args:
        number: Pull request number.

    Returns:
        list[dict]: Check run or status context nodes.
    """
    owner, name = repo().split("/")
    data = gh("api", "graphql", "-f", f"query={ROLLUP_ONE}",
              "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}")
    return checks_of(data["data"]["repository"]["pullRequest"])


def rollups() -> dict[int, list[dict[str, Any]]]:
    """Fetches status check contexts across all open pull requests in a single GraphQL query.

    Returns:
        dict[int, list[dict]]: Mapping of pull request numbers to their check context lists.
    """
    owner, name = repo().split("/")
    data = gh("api", "graphql", "-f", f"query={ROLLUP_ALL}",
              "-F", f"owner={owner}", "-F", f"name={name}")
    return {int(pr["number"]): checks_of(pr)
            for pr in data["data"]["repository"]["pullRequests"]["nodes"]}


def from_github(ref: str | int) -> tuple[str, str]:
    """Fetches the title and body of a pull request from GitHub."""
    data = gh("pr", "view", str(ref), "--json", "title,body")
    return str(data["title"]), str(data["body"] or "")
