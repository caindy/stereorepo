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
import sys

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


def _role_token():
    for role in ("reviewer.env", "coder.env"):
        p = pathlib.Path("~/.config/solorepo").expanduser() / role
        if p.exists():
            try:
                for line in p.read_text().splitlines():
                    line = line.strip().removeprefix("export ").strip()
                    if line.startswith("GH_TOKEN="):
                        return line.split("=", 1)[1].strip("\"'")
            except Exception:
                pass
    return None


def gh(*args):
    """Invokes the GitHub CLI with the role credential and parses JSON output."""
    env = None
    if "GH_TOKEN" not in os.environ:
        token = _role_token()
        if token:
            env = dict(os.environ, GH_TOKEN=token)
    out = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    if out.returncode:
        sys.exit(f"gh: {out.stderr.strip()}")
    return json.loads(out.stdout)


def repo():
    """Determines the current GitHub repository slug from environment, CLI, or git remote."""
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    if repo_name:
        return repo_name
    try:
        return gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    except (Exception, SystemExit):
        out = subprocess.run(["git", "remote", "get-url", "origin"],
                             capture_output=True, text=True, cwd=ROOT)
        if out.returncode == 0 and out.stdout.strip():
            url = out.stdout.strip()
            m = re.search(r"[:/]([^/:]+)/([^/:]+?)(?:\.git)?$", url)
            if m:
                return f"{m.group(1)}/{m.group(2)}"
        return "solo/repo"


def role_login(role):
    """The account a Role holds, by name and not by reading anything.

    `<owner>-<repo>-<role>` is the convention solorepo's DR-107 set.
    """
    return f"{repo().replace('/', '-')}-{role}"


def pull(ref):
    """Fetches all review threads and reviews for a pull request via GraphQL.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        dict: Pull request GraphQL node containing reviewThreads and reviews.
    """
    owner, name = gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"].split("/")
    number = gh("pr", "view", ref, "--json", "number")["number"]
    data = gh("api", "graphql", "-f", f"query={THREADS}",
              "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}")
    return data["data"]["repository"]["pullRequest"]


def threads(ref):
    """Fetches all review thread nodes for a pull request.

    Args:
        ref: Pull request number, URL, or head branch reference.

    Returns:
        list[dict]: Review thread nodes from GraphQL.
    """
    return pull(ref)["reviewThreads"]["nodes"]


def checks_of(node):
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
    return (rollup.get("contexts") or {}).get("nodes") or []


def rollup_of(number):
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


def rollups():
    """Fetches status check contexts across all open pull requests in a single GraphQL query.

    Returns:
        dict[int, list[dict]]: Mapping of pull request numbers to their check context lists.
    """
    owner, name = repo().split("/")
    data = gh("api", "graphql", "-f", f"query={ROLLUP_ALL}",
              "-F", f"owner={owner}", "-F", f"name={name}")
    return {pr["number"]: checks_of(pr)
            for pr in data["data"]["repository"]["pullRequests"]["nodes"]}


def from_github(ref):
    """Fetches the title and body of a pull request from GitHub."""
    data = gh("pr", "view", ref, "--json", "title,body")
    return data["title"], data["body"] or ""
