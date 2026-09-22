"""The Issue lifecycle: labels and levels, the reviewer's reading, filing, blockers, the
claim, the hand-back, and the closes that are not a merge (solorepo's DR-264)."""
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from typing import Any, cast

import channel
from lib.move import advance, common, pull_requests
from lib.search import bm25

# The line both Issue forms open with, and an Issue reference in either of the
# two spellings GitHub renders: bare, and qualified by `owner/repo`.
WAITS_LINE = re.compile(r"^\*\*Waits on\.\*\*(?P<text>.*)$", re.M)


ISSUE_REF = re.compile(r"(?:[\w.-]+/[\w.-]+)?#(\d+)")


# What a `**Waits on.**` line may hold besides its references and still be one
# this program can rewrite: the words that join references, and the words for
# none of them.
WAITS_FILLER = frozenset(("and", "nothing", "none", ""))


NO_WAITS_LINE = "no `**Waits on.**` line"
"""What rewriting a blocker line raises where the Issue body holds none."""


NOT_AN_ISSUE = "{item!r} is not an Issue number"
"""What the `--on`/`--off` parser raises for an item that is not digits."""


def labels_of(issue: str | int) -> list[str]:
    """Retrieve the set of label names attached to an Issue.

    Parameters:
        issue (int | str): Issue number to inspect.

    Returns:
        list[str]: List of label names attached to the issue.
    """
    return [str(lbl["name"]) for lbl in channel.gh("issue", "view", str(issue), "--json", "labels")["labels"]]


def assignees_of(issue: str | int) -> list[str]:
    """The logins an Issue is assigned to, as GitHub lists them now.

    Parameters:
        issue (int | str): Issue number to inspect.

    Returns:
        list[str]: The assignees' logins.
    """
    view = channel.gh("issue", "view", str(issue), "--json", "assignees")
    return [str(a["login"]) for a in view["assignees"]]


def relabel(issue: str | int, add: Sequence[str] = (),
            remove: Sequence[str] = ()) -> list[str]:
    """Update an Issue's labels, settled: the labels GitHub lists once it shows the edit.

    Parameters:
        issue (int | str): Issue number to update.
        add (tuple[str, ...]): Labels to attach to the issue.
        remove (tuple[str, ...]): Labels to detach from the issue.

    Returns:
        list[str]: The label names on the Issue once GitHub shows the edit.

    Raises:
        SystemExit: If GitHub does not show the edit within the channel's wait.
    """
    cmd = ["issue", "edit", str(issue)]
    for name in add:
        cmd += ["--add-label", name]
    for name in remove:
        cmd += ["--remove-label", name]

    def missing(now: list[str]) -> list[str]:
        return [n for n in add if n not in now] + [n for n in remove if n in now]

    _, now = channel.act(
        lambda: channel.gh(*cmd, parse=False), lambda: labels_of(issue),
        lambda now: not missing(now),
        lambda now: f"say: GitHub shows #{issue} labelled {now} after the call; "
                    f"{missing(now)} did not take")
    return now


def challenge_labels(issue: str | int) -> list[str]:
    """Validate that an Issue carries the `challenge` label and return its labels.

    Parameters:
        issue (int | str): Issue number to validate.

    Returns:
        list[str]: Current labels attached to the challenge issue.
    """
    now = labels_of(issue)
    if "challenge" not in now:
        sys.exit(f"say: #{issue} is not a Challenge (labelled {now or 'nothing'}); a difficulty "
                 "is a Challenge's, and a loop reads it only beside `challenge`. "
                 "`move triage` makes it one, at a level, in one act.")
    return now


def refuse_a_level_from_a_run(level: str | None, instead: str) -> None:
    """Refuse a level a run would land on a Challenge, `RUN_LEVEL` excepted (solorepo's DR-235).

    The reviewer reads every Challenge and its verdict is the label
    (solorepo's DR-230), so a level landed anywhere else is a reading that did
    not happen: it routes the work — to a loop at `easy` or `medium`, to the
    solo at `hard` — without the one reader who has no stake in the answer. A
    level landed at filing is the solo's verdict given in advance, and a run is
    where that mandate cannot be: the solo is not beside it. A session may be,
    and is not read here, which is the same line `move claim` draws
    (solorepo's DR-148).

    `RUN_LEVEL` is not a way round the refusal. `human` starts no Job and asks
    for the solo, which is what a run has to be able to say the moment it finds
    a decision owed or work it cannot finish — PR First's fourth step, whose
    bar is deliberately low (solorepo's DR-226).

    Parameters:
        level (str | None): The level the call would land, or None where it lands none.
        instead (str): What this caller does instead, named in the refusal so a
            run told only that it may not land a level is not left without an
            act (solorepo's DR-221).

    Raises:
        SystemExit: If a run asks for any level but `RUN_LEVEL`.
    """
    if not level or level == common.RUN_LEVEL or not channel.in_a_run():
        return
    sys.exit(f"say: `{level}` is a verdict and this is a run: the reviewer reads every "
             "Challenge and its verdict is the label, so a level landed here is a reading "
             "nobody did (solorepo's DR-230, solorepo's DR-235).\n"
             f"     Nothing was written. {instead}\n"
             f"     `{common.RUN_LEVEL}` is the one level a run lands, where the next step is the "
             "solo's rather than a Job's — a decision owed, or work this Job could not "
             "finish, which on a Challenge this Job holds is `move stop`.")


def difficulty(issue: str | int, level: str) -> None:
    """Move a level already standing on a Challenge, which is a verdict standing.

    The solo's move of the reviewer's verdict (solorepo's DR-230), and the act
    that takes a Challenge from the loop at `hard` so a session can hold its
    branch (solorepo's DR-142). A run moves one to `RUN_LEVEL` and no further:
    see `refuse_a_level_from_a_run`.

    Parameters:
        issue (int | str): Challenge issue number.
        level (str): Difficulty level to apply (`easy`, `medium`, `hard`, `human`).

    Raises:
        SystemExit: If a run asks for a level that is a verdict, or the Issue is
            not a Challenge.
    """
    refuse_a_level_from_a_run(level, "The level standing on the Issue is unmoved, and the "
                                     "verdict that moves it is the reviewer's or the solo's.")
    now = challenge_labels(issue)
    stale = [lbl for lbl in now if lbl in common.DIFFICULTIES and lbl != level]
    now = relabel(issue, add=[level], remove=stale)
    print(f"#{issue} is labelled {', '.join(now)}")


def reread(issue: str | int) -> None:
    """Hand a Challenge back to the reviewer by taking its level off (solorepo's DR-235).

    `triage.yml` runs the reader where a level leaves a Challenge as well as
    where `challenge` lands on one without a level (solorepo's DR-230), and
    until now nothing in the channel could deliver that event: `difficulty`
    replaces a level, `triage` refuses where one stands, and `stop` lands
    `human`. So a Challenge labelled without a reading — the levels a run
    landed before this Decision, and any the solo mandated and thought better
    of — had no way back to the reader that GitHub would notice.

    A run is refused it. Taking a level off is undoing a verdict, and a run that
    could do it would reach in two acts what `refuse_a_level_from_a_run` denies
    it in one: strip the level the solo mandated, and let the reading door land
    whatever it lands, which at `easy` or `medium` starts the loop on work that
    was being held back. A run hands work back by `move stop`, which says where
    it stopped and asks for the solo by name.

    A claimed Challenge is refused. The claim is what says a Job is standing on
    the work, and a level leaving hands the Challenge to a reader whose verdict
    would route it under that Job; `move stop` is how a Job gives up what it
    holds, and it says where it stopped as it goes.

    A closed Challenge is refused, because the door declines one:
    `triage.yml`'s job asks `github.event.issue.state == 'open'` before anything
    else. Stripping the level there would take the verdict off and queue no
    reader, and the verb would have reported the reading it did not cause.

    Parameters:
        issue (int | str): Challenge number to hand back to the reviewer.

    Raises:
        SystemExit: If a run types it, or the Issue is not a Challenge, carries
            no level, is closed, or is claimed.
    """
    if channel.in_a_run():
        sys.exit(f"say: taking the level off #{issue} undoes a verdict, and this is a run: it "
                 "would reach in two acts what a run may not do in one, since the door lands a "
                 "level of its own on what is stripped (solorepo's DR-235).\n"
                 "     Nothing was written. A run hands work back with `move stop <issue>`, "
                 "which says where it stopped and asks for the solo.")
    now = challenge_labels(issue)
    standing = [lbl for lbl in now if lbl in common.DIFFICULTIES]
    if not standing:
        sys.exit(f"say: #{issue} carries no level, so it is the reviewer's already; nothing "
                 "would be delivered by taking one off. `just next` lists an unread Challenge "
                 "under `unread`, and `python3 .meta/next.py --check` fails on one nothing has "
                 "touched for an hour, which is a door that did not fire.")
    seen = channel.gh("issue", "view", str(issue), "--json", "state,assignees")
    if str(seen.get("state", "")).upper() != "OPEN":
        sys.exit(f"say: #{issue} is {str(seen.get('state', 'not open')).lower()}, and the reading "
                 "door asks for an open Issue before anything else, so this would take the level "
                 "off and queue no reader. Reopen it first, if the Challenge is live.")
    who = [a["login"] for a in seen["assignees"]]
    if who:
        sys.exit(f"say: #{issue} is claimed by {', '.join(who)}, and a level leaving asks the "
                 "reviewer to route a Challenge a Job is standing on. `move stop <issue>` is "
                 "how a Job gives up what it holds, and this is typeable once nobody does.")
    now = relabel(issue, remove=standing)
    print(f"#{issue} is labelled {', '.join(now) or 'nothing'}; the reviewer reads it")


VERDICT = ("**Worth doing.**", "**Waits on.**", "**Already answered.**", "**Decision owed.**")
"""The four headings a triage verdict carries, one per question the reviewer asks of a Challenge
(solorepo's DR-230): a trigger or a cost that will land, the blockers on the first line, a
mechanism already in the tree, and whether the next step is a decision rather than an
implementation. A body lacking one is refused, so a level landed without a reading shows as one."""


def verdict_posted(issue: str | int) -> bool:
    """Whether this Actor has already posted a verdict on the Issue.

    A verdict is a comment ending in this channel's Trailer and carrying every
    heading in `VERDICT`. The Trailer names the run or session, so a retry
    inside one run finds its own verdict and a later reading, which is another
    Actor, does not. Every page of comments is read.

    Parameters:
        issue (int | str): Issue number to read.

    Returns:
        bool: True when such a comment stands on the Issue.
    """
    block = channel.trailers()
    page = 1
    while True:
        batch = channel.gh("api", f"repos/{channel.repo()}/issues/{issue}/comments"
                                  f"?per_page=100&page={page}") or []
        for c in batch:
            body = str(c.get("body") or "").rstrip()
            if body.endswith(block) and all(h in body for h in VERDICT):
                return True
        if len(batch) < 100:
            return False
        page += 1


def triage(issue: str | int, level: str, body: str) -> None:
    """Land the reviewer's verdict on a Challenge: what it checked, then the level.

    The body is posted on the Issue first and the level landed after, so the
    coder loop's take door, which fires on the label, opens on an Issue that
    already carries the reading. The body is held to `VERDICT`: a verdict
    that names no check is refused before anything is written
    (solorepo's DR-230).

    The two acts are not one transaction, so a verdict this Actor already
    posted is not posted again: a retry after the label failed to land posts
    nothing and lands the level, and one after the label did land is refused
    saying nothing more is owed. A reading by another Actor, which is what a
    Challenge handed back gets, posts its own verdict.

    A Challenge with no level takes the one given. An Issue that is not a
    Challenge becomes one at that level, any prior roadmap label stripped, in a
    single update (solorepo's DR-112). A Challenge whose level already stands is
    refused, because a level standing is a verdict standing and `difficulty` is
    the verb that moves one.

    This is the one verb that lands a level in a run, and it is guarded on
    identity rather than on location (solorepo's DR-235). `refuse_a_level_from_a_run`
    would refuse the reading door itself, since `triage.yml` writes the run
    mark like every other workflow; what a run may not do is land a level on a
    Challenge **it** raised, which is the raiser reading their own work. So the
    question asked here is whose credential is speaking: in a run, the
    reviewer's account and no other. `role_login` names it without touching its
    token (solorepo's DR-107), so the coder's promotion pass cannot type a
    verdict on the Issue it has just filed and then take it, which is
    solorepo's #608's symptom reached by a longer road. A session is not asked,
    as it is not asked anywhere else in this rule: the solo directs one.

    Parameters:
        issue (int | str): Issue number to triage.
        level (str): Difficulty level (`easy`, `medium`, `hard`, `human`).
        body (str): The verdict, signed, carrying every heading in `VERDICT`.

    Raises:
        SystemExit: If a run speaks as any account but the reviewer's, if the
            Challenge already carries a level, or the body lacks a heading of
            the verdict form.
    """
    if channel.in_a_run():
        reviewer = channel.role_login("reviewer")
        who = channel.login()
        if who != reviewer:
            sys.exit(f"say: a verdict is the reviewer's, and this run speaks as `{who}` rather "
                     f"than `{reviewer}`: a run landing a level on a Challenge it raised is the "
                     "raiser reading their own work, which is what the reading door exists to "
                     "prevent (solorepo's DR-230, solorepo's DR-235).\n"
                     "     Nothing was posted and no level landed. File or promote with no "
                     "level and the door queues the reviewer, which is the reading; `move stop` "
                     "hands the Challenge to the solo where the next step is his.")
    now = labels_of(issue)
    standing = [lbl for lbl in now if lbl in common.DIFFICULTIES]
    if "challenge" in now and standing:
        if verdict_posted(issue):
            sys.exit(f"say: #{issue} is read already: this Actor's verdict stands on it and "
                     f"it is at `{standing[0]}`, so nothing more is owed")
        sys.exit(f"say: #{issue} is a Challenge at `{standing[0]}` already, which is a "
                 "verdict standing; `move difficulty` moves its level")
    missing = [h for h in VERDICT if h not in body]
    if missing:
        sys.exit(f"say: the verdict names no check under {', '.join(missing)}; a level landed "
                 "without a reading shows as one (solorepo's DR-230). The body carries one "
                 "paragraph per heading, in the form's words.")
    if verdict_posted(issue):
        print(f"#{issue} already carries this Actor's verdict; landing the level only")
    else:
        channel.gh("api", f"repos/{channel.repo()}/issues/{issue}/comments", "-f", f"body={body}")
    if level in now:
        relabel(issue, remove=[level])
    stale = [lbl for lbl in now
             if lbl == "roadmap" or (lbl in common.DIFFICULTIES and lbl != level)]
    now = relabel(issue, add=["challenge", level], remove=stale)
    print(f"#{issue} is a Challenge, labelled {', '.join(now)}")


def roadmap(issue: str | int) -> None:
    """Move an open Issue onto the roadmap.

    Applies the `roadmap` label and strips any `challenge` or difficulty labels,
    symmetric with the strip performed by `triage`.

    Parameters:
        issue (int | str): Issue number to move onto the roadmap.

    Raises:
        SystemExit: If invoked within a run, if the Issue is not open, if it is
            claimed by an Actor, or if it is on the roadmap already with no stale
            labels to strip.
    """
    if channel.in_a_run():
        sys.exit(f"say: moving #{issue} to the roadmap is the solo's: roadmap Issues are deferred "
                 "intent, and a run hands work back with `move stop <issue>`.")
    seen = channel.gh("issue", "view", str(issue), "--json", "state,assignees")
    if str(seen.get("state", "")).upper() != "OPEN":
        sys.exit(f"say: #{issue} is {str(seen.get('state', 'not open')).lower()}, and the roadmap "
                 "is for open intent; reopen it first, if it is live.")
    who = [a["login"] for a in seen.get("assignees", [])]
    if who:
        sys.exit(f"say: #{issue} is claimed by {', '.join(who)}; a Job cannot be working on a "
                 "roadmap Issue. `move stop <issue>` releases the claim first.")
    now = labels_of(issue)
    stale = [lbl for lbl in now if lbl == "challenge" or lbl in common.DIFFICULTIES]
    if "roadmap" in now and not stale:
        sys.exit(f"say: #{issue} is on the roadmap already")
    now = relabel(issue, add=["roadmap"], remove=stale)
    print(f"#{issue} is on the roadmap, labelled {', '.join(now)}")


SEMANTIC_DUPLICATE_RATIO = 1.79
"""Minimum leading-to-runner-up BM25F score ratio that refuses a filing (solorepo's DR-266)."""


def open_issue_queue() -> list[dict[str, Any]] | None:
    """List the open Issue queue, or return None when GitHub refuses the listing.

    Listed rather than searched. `gh issue list` reads the API, which answers
    with what was written a moment ago; `--search` reads the code search index,
    which lags by seconds to minutes, and the window this is asked about is a
    retry seconds after a filing (solorepo's DR-221). Bodies arrive in the same
    listing so solorepo's DR-266 can rank the live queue without a request per
    Issue.

    Returns:
        list[dict[str, Any]] | None: Up to 200 current open Issues, or None when
            GitHub refuses the listing. A refusal permits filing because this
            check is not a queue outage gate.

    Raises:
        SystemExit: The listing times out. A timeout supplies no result, unlike
            a refusal that definitively failed.
    """
    try:
        listed = channel.gh("issue", "list", "--state", "open", "--limit", "200",
                            "--json", "number,title,url,body", tolerate_fail=True)
    except subprocess.CalledProcessError as exc:
        if exc.returncode == channel.TIMEOUT_RETURNCODE:
            sys.exit(f"say: {exc.stderr}")
        return None
    return cast(list[dict[str, Any]], listed or [])


def open_with_title(
    title: str, issues: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[str, str] | None:
    """Return the `(number, url)` of an open Issue with this exact title.

    When `issues` is omitted, the live queue is listed. None means either no
    title matched or GitHub refused the listing; the two cases are intentionally
    indistinguishable so filing remains available during a listing failure.

    Raises:
        SystemExit: If the queue listing times out.
    """
    for issue in (issues if issues is not None else open_issue_queue() or []):
        if issue.get("title") == title:
            return str(issue["number"]), str(issue.get("url", ""))
    return None


def semantic_body(body: str) -> str:
    """Remove Issue-form metadata that every Challenge shares before ranking prose."""
    return WAITS_LINE.sub("", body).strip()


def semantic_duplicate(issues: Sequence[Mapping[str, Any]], title: str,
                       body: str) -> Mapping[str, Any] | None:
    """Return the uniquely dominant semantic queue match for a proposed filing."""
    index = bm25.SearchIndex()
    documents: dict[str, Mapping[str, Any]] = {}
    query = f"{title}\n{semantic_body(body)}"
    for issue in issues:
        number = str(issue.get("number", ""))
        if not number:
            continue
        documents[number] = issue
        issue_title = str(issue.get("title", ""))
        issue_body = semantic_body(str(issue.get("body", "")))
        index.add_document(
            number,
            "issue",
            {"title": issue_title},
            str(issue.get("url", "")),
            {
                "title": bm25.tokenize(issue_title),
                "summary": [],
                "body": bm25.tokenize(issue_body),
            },
        )
    index.finalize()
    matches = index.search(query, top_k=2)
    if not matches:
        return None
    if len(documents) > 1 and len(matches) == 1:
        return documents[matches[0].identifier]
    if len(matches) > 1 and matches[0].score / matches[1].score >= SEMANTIC_DUPLICATE_RATIO:
        return documents[matches[0].identifier]
    return None


def refuse_if_semantic_duplicate(issues: Sequence[Mapping[str, Any]] | None,
                                 title: str, body: str) -> None:
    """Refuse a filing whose live queue match clears the solorepo's DR-266 cutoff."""
    if issues is None:
        return
    match = semantic_duplicate(issues, title, body)
    if not match:
        return
    number, url = str(match["number"]), str(match.get("url", ""))
    sys.exit(f"say: #{number} is the uniquely dominant semantic match for this Challenge: {url}\n"
             "     Nothing was filed. If this is distinct work, explain the distinction in "
             "the title and body, then file it again.")


def file_issue(title: str, body: str, level: str | None = None,
               roadmap: bool = False,
               blocked_by: Sequence[int | str] = ()) -> tuple[str, str]:
    """File a new Challenge or Roadmap Issue with required structural metadata.

    Enforces that the issue body opens with `**Waits on.**` (solorepo's DR-114) and
    sets the initial labels. The native blocked-by relationship is established from
    `blocked_by` alone, and the body's `**Waits on.**` line is rendered from it, so
    the line describes the relationship at the moment it is first written rather
    than standing beside it (solorepo's DR-213). A line naming an `#<n>` the flag
    omits is refused instead of rendered away, because such a caller is still
    treating the line as the input and is owed the refusal rather than a silent
    downgrade. Both records are read back from GitHub before the Issue is reported
    as filed.

    A Challenge filed with no level lands `challenge` alone, which is the
    reviewer's queue: the raiser proposes a level in the body and the reviewer's
    verdict lands the label. A level given here is the solo's verdict given in
    advance, and skips the reviewer on purpose (solorepo's DR-230). A run holds
    no such mandate, and is refused every level but `RUN_LEVEL`
    (solorepo's DR-235).

    Refuses when an open Issue already carries this title, so that a caller
    retried after a failure part-way through a larger act files nothing the
    first attempt already filed (solorepo's DR-221).

    Parameters:
        title (str): Issue title string.
        body (str): Issue body Markdown text.
        level (str | None): Difficulty level for a Challenge, or None to leave it to the reviewer.
        roadmap (bool): When True, creates a deferred roadmap issue instead of a Challenge.
        blocked_by (Sequence[int | str]): Issue numbers to record as blockers; the
            body's `**Waits on.**` line describes them and does not set them, and
            is rewritten to name them.

    Returns:
        tuple[str, str]: Issue number and URL.

    Raises:
        SystemExit: If a run asks for a level that is a verdict, if the body does
            not open with `**Waits on.**`, if an open Issue already carries this
            title, if the body's `**Waits on.**` line names an `#<n>` that
            `blocked_by` omits, if a blocker is not an open Issue, or if GitHub
            does not show the labels, the blocked-by relationships and the line
            the call asked for.
    """
    refuse_a_level_from_a_run(level, "Filed with no level it lands `challenge` alone, which "
                                     "is the reviewer's queue, and the level this run would "
                                     "have landed belongs under `**Difficulty.**` in the body, "
                                     "where it is a proposal the reader answers.")
    first = body.lstrip().split("\n", 1)[0]
    if not first.startswith("**Waits on.**"):
        sys.exit("say: the body does not open with `**Waits on.**`, which is the line "
                 f"`just next` reads; it opens with {first[:60]!r}. Both forms begin there.")
    issues = open_issue_queue()
    standing = open_with_title(title, issues) if issues is not None else None
    if standing:
        number, url = standing
        sys.exit(f"say: #{number} is open under this exact title, so this would be the "
                 f"second Issue for one Challenge: {url}\n"
                 "     Nothing was filed. If the act that reached here is a `post promote` "
                 "whose reply or resolve failed, the Issue exists and the thread is what is "
                 "unfinished: `post answer <thread-id>` with a body linking it, or "
                 "`post resolve <thread-id>` where the link is already posted. If this "
                 "Challenge is genuinely a second one, give it a title of its own.")
    refuse_if_semantic_duplicate(issues, title, body)
    refs = sorted({int(str(n).strip().lstrip("#")) for n in blocked_by})
    line_refs = sorted({int(n) for n in re.findall(r"#(\d+)", first)})
    missing_from_flags = set(line_refs) - set(refs)
    if missing_from_flags:
        sys.exit(f"say: the body names #{sorted(missing_from_flags)[0]} in its `**Waits on.**` line, "
                 "but `--blocked-by` was not given or omitted it. `--blocked-by` sets the "
                 "relationship (solorepo's DR-213); pass `--blocked-by "
                 f"{','.join(str(n) for n in line_refs)}`.")
    for n in refs:
        issue_of(n, as_blocker=True)
    body = retarget_waits(body, refs, issue=title)
    labels = ["roadmap"] if roadmap else ["challenge"] + ([level] if level else [])
    cmd = ["issue", "create", "--title", title, "--body", body]
    for name in labels:
        cmd += ["--label", name]
    if refs:
        cmd += ["--blocked-by", ",".join(str(n) for n in refs)]
    url = channel.gh(*cmd, parse=False)
    number = url.rstrip("/").rsplit("/", 1)[-1]
    channel.shown(lambda: labels_of(number), lambda now: all(lbl in now for lbl in labels),
                  lambda now: f"say: GitHub shows #{number} labelled {now} after the call, "
                              f"not {labels}")
    if refs:
        channel.shown(lambda: channel.gh("issue", "view", str(number), "--json", "body,blockedBy"),
                      lambda view: blockers_mismatch(view, number, refs) is None,
                      lambda view: blockers_mismatch(view, number, refs) or "")
    print(url)
    return number, url


def blockers_mismatch(view: dict[str, Any], issue: int | str, want: Sequence[int]) -> str | None:
    """Why an Issue as GitHub shows it does not carry the blockers wanted, or None where it does.

    Both sources are read: the relationship (solorepo's DR-213) and the
    `**Waits on.**` line, which must cite every blocker the relationship holds
    and say nothing where it holds none.

    Parameters:
        view (dict): The Issue as `gh issue view --json body,blockedBy` answers it.
        issue (int | str): The Issue's number, for the refusal's words.
        want (Sequence[int]): The blocker numbers wanted, in full.

    Returns:
        str | None: The refusal, or None where both sources show the blockers.
    """
    recorded = sorted(n["number"] for n in (view.get("blockedBy") or {}).get("nodes", [])
                      if "number" in n)
    wanted = sorted(want)
    if recorded != wanted:
        return f"say: GitHub shows #{issue} with blockedBy {recorded} after the call, not {wanted}"
    match = WAITS_LINE.search(view.get("body") or "")
    if not match:
        return f"say: GitHub shows #{issue} with no `**Waits on.**` line after the call"
    line_text = match.group(0)
    for n in wanted:
        if not re.search(rf"#{n}(?!\d)", line_text):
            return (f"say: GitHub shows #{issue} with the relationship set but the line "
                    f"not citing #{n}")
    if not wanted and not any(w in line_text.lower() for w in ("nothing", "none")):
        return f"say: GitHub shows #{issue} with no blockers but the line not saying nothing"
    return None


def issue_of(number: int | str, as_blocker: bool = False) -> dict[str, Any]:
    """The Issue GitHub holds at `number`, refusing what is not an open Issue.

    Parameters:
        number (int | str): Issue number to resolve.
        as_blocker (bool): When True, the refusals read as a blocker's rather
            than as the Issue being blocked.

    Returns:
        dict[str, Any]: GitHub's REST representation of the Issue.

    Raises:
        SystemExit: If `number` is not a number of this repository, is a pull
            request, or names an Issue GitHub reports as closed; and separately
            if the read answered nothing within `channel.GH_TIMEOUT`, which is
            reported as the hang it is rather than as the absence it is not.
    """
    try:
        found = channel.gh("api", f"repos/{channel.repo()}/issues/{number}", tolerate_fail=True)
    except subprocess.CalledProcessError as exc:
        if exc.returncode == channel.TIMEOUT_RETURNCODE:
            sys.exit(f"say: {exc.stderr}")
        sys.exit(f"say: {channel.repo()} has no #{number}" + (
            "; a blocker is an Issue's number, and what is not one belongs in the "
            "`**Waits on.**` line as the prose it is." if as_blocker else "."))
    if "pull_request" in found:
        sys.exit(f"say: #{number} is a pull request, not an Issue; GitHub holds a blocked-by "
                 "relationship between Issues, and a pull request's own waiting is its stack's.")
    if found.get("state") != "open":
        sys.exit(f"say: #{number} is closed, and " + (
            "a closed Issue blocks nothing: `just next` would read the relationship as "
            "satisfied the moment it was set." if as_blocker else
            "what a closed Issue waits on decides nothing."))
    return cast(dict[str, Any], found)


def native_blockers(issue: int | str) -> list[int]:
    """The Issue numbers GitHub records as blocking `issue`.

    Parameters:
        issue (int | str): Issue number to read.

    Returns:
        list[int]: Blocker Issue numbers, in GitHub's order.
    """
    view = channel.gh("issue", "view", str(issue), "--json", "blockedBy")
    return [n["number"] for n in (view.get("blockedBy") or {}).get("nodes", []) if "number" in n]


def refuse_on_cycle(issue: int, blocker: int) -> None:
    """Refuse a blocker `issue` already blocks, at any depth.

    Walks GitHub's blocked-by relationship out from `blocker`; reaching `issue`
    means the pair would wait on each other and neither would ever be ripe.

    Parameters:
        issue (int): Issue about to be blocked.
        blocker (int): Issue about to block it.

    Raises:
        SystemExit: If `issue` already blocks `blocker`, directly or through
            other Issues.
    """
    seen, frontier = set(), [blocker]
    while frontier:
        here = frontier.pop()
        if here in seen:
            continue
        seen.add(here)
        for further in native_blockers(here):
            if further == issue:
                sys.exit(f"say: #{issue} already blocks #{here}, so waiting on #{blocker} would "
                         "close a cycle and neither Issue would ever be ripe.")
            frontier.append(further)


def waits_line(blockers: Sequence[int], prose: Sequence[str] = ()) -> str:
    """The `**Waits on.**` line describing `blockers` and any surviving `prose` items.

    Parameters:
        blockers (Sequence[int]): Blocker Issue numbers.
        prose (Sequence[str]): Non-Issue prose items (Decisions, accounts).

    Returns:
        str: The line, naming each blocker/prose, or `Nothing.` for an empty sequence.
    """
    items = list(prose) + [f"#{n}" for n in blockers]
    return "**Waits on.** " + (", ".join(items) if items else "Nothing.")


def retarget_waits(body: str, want: Sequence[int],
                   removing: Sequence[int] = (),
                   issue: int | str = "") -> str:
    """`body` with its `**Waits on.**` line rewritten to describe `want`.

    The line is rewritten preserving non-Issue prose blockers (Decisions,
    accounts, the solo per solorepo's DR-170). If `removing` names a blocker
    embedded in an explanatory clause, the rewrite is refused rather than leaving
    a severed clause.

    Parameters:
        body (str): The Issue's body Markdown text.
        want (Sequence[int]): Blocker Issue numbers now recorded on GitHub.
        removing (Sequence[int]): Blocker Issue numbers being removed.
        issue (int | str): Issue number, for error messages.

    Returns:
        str: The rewritten body.

    Raises:
        LookupError: If `body` has no `**Waits on.**` line.
        SystemExit: If removing a blocker would sever an explanatory clause.
    """
    found = WAITS_LINE.search(body or "")
    if not found:
        raise LookupError(NO_WAITS_LINE)
    line_text = found.group("text").strip()
    raw_items = [p.strip().rstrip(".") for p in line_text.split(",") if p.strip()]
    prose_items = []
    for item in raw_items:
        cleaned = re.sub(r"[^\w\s]+", " ", ISSUE_REF.sub(" ", item)).lower().split()
        if not set(cleaned) <= WAITS_FILLER:
            prose_items.append(item)
    if removing and prose_items:
        sys.exit(f"say: the `**Waits on.**` line of #{issue} says {prose_items[0]!r} beside its "
                 f"citations, so taking #{removing[0]} off it is a rewrite and not a deletion. "
                 f"`move revise {issue}` writes the line, and this verb takes the relationship "
                 "off once the line no longer contradicts it.")
    new_line = waits_line(want, prose_items)
    return body[:found.start()] + new_line + body[found.end():]


def waits(issue: int | str, on: Sequence[int | str] | None = None,
          off: Sequence[int | str] | None = None, clear: bool = False) -> None:
    """Set, add, or drop what an Issue waits on, after it was filed.

    GitHub's blocked-by relationship is the record (solorepo's DR-213).
    `--on` replaces the relationship with the Issues given, `--off` drops the
    named blockers, and `--clear` removes every blocker. The `**Waits on.**` line
    is rewritten to follow, preserving non-Issue prose blockers (solorepo's DR-170).
    A line whose citations carry explanatory clauses is refused when dropping a
    blocker, rather than leaving a severed clause. Both sources are read back
    and verified before the call reports success.

    Parameters:
        issue (int | str): Issue whose blockers are being set.
        on (Sequence[int | str] | None): Blocker Issue numbers to set.
        off (Sequence[int | str] | None): Blocker Issue numbers to drop.
        clear (bool): When True, removes every blocker.

    Raises:
        SystemExit: If `issue` is not an open Issue, if a blocker is not an open
            Issue, if a blocker is `issue` itself or closes a cycle, if the
            `**Waits on.**` line is missing, or if GitHub does not reflect both
            sources after the call.
    """
    issue_num = int(str(issue).strip().lstrip("#"))
    issue_data = issue_of(issue_num)
    body = issue_data.get("body") or ""
    have = sorted(native_blockers(issue_num))

    if clear:
        want: list[int] = []
        removing = list(have)
    elif off is not None:
        drop = {int(str(n).strip().lstrip("#")) for n in off}
        want = sorted(set(have) - drop)
        removing = sorted(drop)
    elif on is not None:
        want = sorted({int(str(n).strip().lstrip("#")) for n in on})
        removing = sorted(set(have) - set(want))
    else:
        sys.exit("say: nothing to do — specify `--on`, `--off`, or `--clear`.")

    if issue_num in want:
        sys.exit(f"say: #{issue_num} cannot wait on itself.")
    for n in want:
        issue_of(n, as_blocker=True)
        refuse_on_cycle(issue_num, n)

    try:
        described = retarget_waits(body, want, removing=removing, issue=issue_num)
    except LookupError:
        sys.exit(f"say: #{issue_num} has no `**Waits on.**` line for this to rewrite, which both "
                 f"Issue forms open with. `move revise {issue_num}` writes one, and this runs after.")

    if have == want and described == body:
        print(f"#{issue_num} already {'waits on ' + ', '.join(f'#{n}' for n in want) if want else 'waits on nothing'}, "
              "in the relationship and on the line")
        return

    flags = [f for n in want if n not in have for f in ("--add-blocked-by", str(n))]
    flags += [f for n in have if n not in want for f in ("--remove-blocked-by", str(n))]

    def rewrite() -> None:
        """Both sources, each written only where it differs."""
        if flags:
            channel.gh("issue", "edit", str(issue_num), *flags, parse=False)
        if described != body:
            channel.gh("issue", "edit", str(issue_num), "--body", described, parse=False)

    channel.act(rewrite,
                lambda: channel.gh("issue", "view", str(issue_num), "--json", "body,blockedBy"),
                lambda view: blockers_mismatch(view, issue_num, want) is None,
                lambda view: blockers_mismatch(view, issue_num, want) or "")
    print(f"#{issue_num} waits on {', '.join(f'#{n}' for n in want) or 'nothing'}")


def claim(issue: str | int) -> None:
    """Assign an Issue to the authenticated Role account and verify assignment.

    Refuses a session's claim on a Challenge no reviewer has read, which is one
    carrying no level (solorepo's DR-230), and on an `easy` or `medium` Challenge,
    which is a loop's from the moment the label landed (solorepo's DR-112,
    solorepo's DR-148). A run reads no label: it arrives on the label's own
    event, so the Challenge it claims has been read and is its own.

    Parameters:
        issue (int | str): Issue number to claim.
    """
    if not channel.in_a_run():
        now = labels_of(issue)
        if "challenge" in now and not any(lbl in common.DIFFICULTIES for lbl in now):
            sys.exit(f"say: #{issue} is a Challenge no reviewer has read: it carries no level, "
                     "and the reviewer's verdict is what lands one (solorepo's DR-230). "
                     f"`move --role reviewer triage {issue} <level>` with the verdict on stdin "
                     f"reads it; a level the solo mandates is `move difficulty {issue} <level>`.")
        taken = next((lbl for lbl in now if lbl in common.LOOP_LEVELS), None)
        if taken and "challenge" in now:
            sys.exit(f"say: #{issue} is labelled `{taken}`, which is a loop's from the moment "
                     "the label landed, and this is a session: a claim here stands beside the "
                     f"run that was started for it. `move difficulty {issue} hard` takes the "
                     "Challenge from the loop — the level is what says whose a branch is — and "
                     "it can be claimed then.")
    login = channel.login()
    channel.act(
        lambda: channel.gh("issue", "edit", str(issue), "--add-assignee", login, parse=False),
        lambda: assignees_of(issue), lambda who: login in who,
        lambda who: f"say: GitHub shows #{issue} assigned to {who or 'nobody'} after the call, "
                    f"not {login}")
    print(f"claimed #{issue} as {login}")


def release(issue: str | int) -> None:
    """Remove the authenticated Role's assignment from an Issue, settled.

    Parameters:
        issue (int | str): Issue number to release.

    Raises:
        SystemExit: If GitHub still shows the Role assigned once the channel's
            wait is spent.
    """
    login = channel.login()
    _, who = channel.act(
        lambda: channel.gh("issue", "edit", str(issue), "--remove-assignee", login, parse=False),
        lambda: assignees_of(issue), lambda who: login not in who,
        lambda who: f"say: GitHub shows #{issue} still assigned to {login} after the call")
    print(f"released #{issue}; it is assigned to {', '.join(who) or 'nobody'}")


def _stop_check_challenge(issue: str | int) -> None:
    """Best-effort check that the issue is a challenge before stopping."""
    try:
        res = channel.gh_with_retry("issue", "view", str(issue), "--json", "labels", tolerate_fail=True)
        if res is not None:
            now = [lbl["name"] for lbl in res["labels"]]
            if "challenge" not in now:
                sys.exit(f"say: #{issue} is not a Challenge (labelled {now or 'nothing'}); a difficulty "
                         "is a Challenge's, and a loop reads it only beside `challenge`. "
                         "`move triage` makes it one, at a level, in one act.")
    except SystemExit:
        raise
    except common.UNREACHED as exc:
        print(f"warning: could not read labels of #{issue} to verify Challenge: {exc}", file=sys.stderr)


def _stop_post_comment(issue: str | int, body: str) -> None:
    """Best-effort posting of explanation comment when stopping."""
    try:
        made = channel.gh_with_retry("api", f"repos/{channel.repo()}/issues/{issue}/comments", "-f", f"body={body}", tolerate_fail=True)
        if made and "html_url" in made:
            print(made["html_url"])
    except common.UNREACHED as exc:
        print(f"warning: could not post comment on #{issue}: {exc}", file=sys.stderr)


def _stop_release_assignee(issue: str | int) -> None:
    """Best-effort removal of the current assignee when stopping."""
    try:
        login = channel.login()
        channel.gh_with_retry("issue", "edit", str(issue), "--remove-assignee", login, parse=False, tolerate_fail=True)

        def who_now() -> list[str]:
            """The assignees, read as tolerantly as the write was, so a refusal warns here."""
            seen = channel.gh_with_retry("issue", "view", str(issue), "--json", "assignees",
                                         tolerate_fail=True)
            return [str(a["login"]) for a in seen["assignees"]]

        who = channel.settled(who_now, lambda who: login not in who)
        if login in who:
            print(f"warning: GitHub shows #{issue} still assigned to {login} after release", file=sys.stderr)
        else:
            print(f"released #{issue}; it is assigned to {', '.join(who) or 'nobody'}")
    except common.UNREACHED as exc:
        print(f"warning: could not release assignee on #{issue}: {exc}", file=sys.stderr)


def _stop_move_human(issue: str | int) -> None:
    """Best-effort move of difficulty level to human when stopping."""
    try:
        res_diff = channel.gh_with_retry("issue", "view", str(issue), "--json", "labels", tolerate_fail=True)
        if res_diff is not None:
            now = [lbl["name"] for lbl in res_diff["labels"]]
            stale = [lbl for lbl in now if lbl in common.DIFFICULTIES and lbl != "human"]
            cmd = ["issue", "edit", str(issue), "--add-label", "human"]
            for name in stale:
                cmd += ["--remove-label", name]
            channel.gh_with_retry(*cmd, parse=False, tolerate_fail=True)

            def labels_now() -> list[str]:
                """The labels, read as tolerantly as the write was, so a refusal warns here."""
                seen = channel.gh_with_retry("issue", "view", str(issue), "--json", "labels",
                                             tolerate_fail=True)
                return [str(lbl["name"]) for lbl in seen["labels"]]

            now_back = channel.settled(
                labels_now, lambda back: "human" in back and not any(lbl in back for lbl in stale))
            print(f"#{issue} is labelled {', '.join(now_back)}")
    except common.UNREACHED as exc:
        print(f"warning: could not set difficulty of #{issue} to human: {exc}", file=sys.stderr)


def stop(issue: str | int, body: str) -> None:
    """Execute graceful loop hand-back to the human maintainer (solorepo's DR-112).

    Posts the explanatory hand-back comment, releases issue assignment, and adjusts
    difficulty to `human` while handling potential GitHub API transient errors gracefully.

    Parameters:
        issue (int | str): Issue number to hand back.
        body (str): Explanatory markdown body detailing why the run stopped.
    """
    _stop_check_challenge(issue)
    _stop_post_comment(issue, body)
    _stop_release_assignee(issue)
    _stop_move_human(issue)


OBVIATOR = re.compile(r"^#?(\d+)$")
"""What `--by` may name: an Issue or a pull request, as `nnn` or `#nnn`."""


def obviator(what: str, issue: str | int) -> tuple[str, str]:
    """Validate what is offered as an Issue's answer, and name it for the closing comment.

    An Issue is answered by an open Challenge that now owns its work, or by a pull
    request GitHub reports as merged (solorepo's DR-232).

    Parameters:
        what (str): Issue or pull request reference, as `nnn` or `#nnn`.
        issue (int | str): The Issue being closed, which nothing may name as its own answer.

    Returns:
        tuple[str, str]: The number, and the markdown reference the closing comment cites.

    Raises:
        SystemExit: If the reference does not parse, names the Issue itself, names an
            unmerged pull request, or names an Issue that is closed or is not a Challenge.
    """
    found = OBVIATOR.match(what.strip())
    if not found:
        sys.exit(f"say: --by takes an Issue or a pull request, as `nnn` or `#nnn`; {what!r} is "
                 "neither")
    number = found.group(1)
    if number == str(issue).strip().lstrip("#"):
        sys.exit(f"say: #{issue} cannot be its own answer. `--by` names where the work went: "
                 "the Challenge that owns it now, or the pull request that landed it.")
    if common.kind(number) == "pull request":
        pull = channel.gh("pr", "view", number, "--json", "state,title")
        if pull["state"] != "MERGED":
            sys.exit(f"say: #{number} is {pull['state'].lower()}, not merged, so the tree does "
                     f"not hold its answer yet and #{issue} is the only open record of the "
                     "need. A pull request still open closes an Issue by naming it with a "
                     f"closing keyword in its body; one that never lands would leave #{issue} "
                     "closed against nothing.")
        return number, f"#{number} — {pull['title']}"
    answer = channel.gh("issue", "view", number, "--json", "state,title,labels")
    if answer["state"] != "OPEN":
        sys.exit(f"say: #{number} is closed, so it owns nothing now and cannot be where "
                 f"#{issue}'s work went. Name the Challenge that holds the work today, or the "
                 "pull request that answered it.")
    labels = [str(lbl["name"]) for lbl in answer["labels"]]
    if "challenge" not in labels:
        sys.exit(f"say: #{number} is labelled {labels or 'nothing'} and not `challenge`, so "
                 "nothing is queued to answer it and no run will take it. Closing "
                 f"#{issue} against it would move the work out of the queue rather than "
                 f"across it. `move triage {number} <level>` makes it a Challenge, at a level.")
    return number, f"#{number} — {answer['title']}"


def obviate(issue: str | int, by: str, reason: str) -> None:
    """Close an Issue another Issue or a merged pull request has already answered.

    Posts the caller's account of where its work went as a signed comment on the
    Issue naming what answered it, closes the Issue as not planned, reads the
    state back from GitHub rather than taking it from what `gh` returned, and
    only then posts the backlink on what `--by` names, so the link is on both
    (solorepo's DR-232). In that order a close that fails leaves the Issue open
    with one comment to remove, and a backlink that fails leaves a closed Issue
    whose account is intact. The assignee is untouched: an Issue closed is
    offered to nobody, and the claim is the record of who held it.

    Parameters:
        issue (int | str): Issue number to close.
        by (str): What answered it: an open Challenge, or a merged pull request.
        reason (str): What part of the Issue went where.

    Raises:
        SystemExit: If the number is a pull request or an Issue that is not open, if
            what `--by` names does not qualify, or if the close does not register on
            GitHub as closed and not planned.
    """
    if common.kind(issue) == "pull request":
        sys.exit(f"say: #{issue} is a pull request, and a pull request another answer overtook "
                 f"closes by `move supersede {issue} --by <pr|DR>`, which reads the Challenge it "
                 "closes as the evidence that something else answered it.")
    before = channel.gh("issue", "view", str(issue), "--json", "state,title")
    if before["state"] != "OPEN":
        sys.exit(f"say: #{issue} is closed already")
    number, cited = obviator(by, issue)

    said = [reason.rstrip("\n"), "",
            f"**Obviated by {cited}.** Closed as not planned rather than by a merge, which is "
            "PR First's other exit for an Issue: what this one asked for is owned by "
            f"#{number} now, so no change of its own is owed and the queue should not "
            "offer it as ripe."]
    channel.sibling("post").conversation_comment(issue, channel.signed("\n".join(said)))
    channel.act(
        lambda: channel.gh("issue", "close", str(issue), "--reason", "not planned", parse=False),
        lambda: channel.gh("issue", "view", str(issue), "--json", "state,stateReason"),
        lambda after: after["state"] == "CLOSED" and after["stateReason"] == "NOT_PLANNED",
        lambda after: f"say: GitHub shows #{issue} {after['state'].lower()} as "
                      f"{(after['stateReason'] or 'nothing').lower()} after the call, not closed "
                      f"as not planned. The comment saying it was obviated by #{number} is "
                      f"already posted on #{issue} and now contradicts its state; delete it "
                      "before trying again, since a second run posts a second one. No backlink "
                      "was posted.")
    channel.sibling("post").conversation_comment(
        number, channel.signed(f"**#{issue} was obviated by this** — {before['title']}. It is "
                               "closed as not planned, and where each part of it went is said "
                               "there. This is the backlink, so the pair reads from either end."))
    print(f"obviated #{issue} by #{number} — {before['title']}")


def milestone(issue: str | int, title: str | None, clear: bool = False) -> None:
    """Put an Issue in a Milestone, creating the Milestone when it is new, and
    read back.

    A Milestone is where the priority between Issues is written once (solorepo's DR-114);
    `just next` lists the lowest-numbered open one as next. Creating one is an
    act GitHub records against an account, and `gh` has no verb for it, so it
    goes through here like every other write.
    """
    def milestone_of() -> dict[str, Any] | None:
        """The Milestone GitHub shows the Issue in now, or None."""
        found: dict[str, Any] | None = channel.gh("issue", "view", str(issue),
                                                  "--json", "milestone")["milestone"]
        return found

    if clear:
        channel.act(
            lambda: channel.gh("issue", "edit", str(issue), "--milestone", "", parse=False),
            milestone_of, lambda now: not now,
            lambda now: f"say: GitHub shows #{issue} still in {(now or {}).get('title')!r} "
                        "after the call")
        print(f"#{issue} is in no Milestone")
        return
    existing = [m["title"] for m in channel.gh("api", "repos/{owner}/{repo}/milestones?state=all&per_page=100")]
    if title not in existing:
        channel.gh("api", "repos/{owner}/{repo}/milestones", "-f", f"title={title}", parse=False)
        print(f"created Milestone {title!r}")
    channel.act(
        lambda: channel.gh("issue", "edit", str(issue), "--milestone", title or "", parse=False),
        milestone_of, lambda now: now is not None and now["title"] == title,
        lambda now: f"say: GitHub shows #{issue} in {now and now['title']!r} after the call, "
                    f"not {title!r}")
    print(f"#{issue} is in Milestone {title!r}")


def parse_waits_on(body: str | None) -> list[int]:
    """The blockers an Issue or PR declares: a list of numbers."""
    if not body:
        return []
    m = re.search(r"^\*\*Waits on\.\*\*\s*(.*?)\s*$", body, re.M) or \
        re.search(r"\*\*What it waits on\.\*\*\s*(.*?)(?:\n\s*\n|\Z)", body, re.S)
    if not m:
        return []
    text = m.group(1).strip()
    if text.lower().rstrip(".") in ("nothing", "none", ""):
        return []
    return [int(n) for n in re.findall(r"#(\d+)", text)]


def issue_blockers(issue: dict[str, Any]) -> list[int]:
    """Numbers that block an Issue: GitHub's `blockedBy`, which is the only record (solorepo's DR-213).

    Parameters:
        issue (dict[str, Any]): An Issue as `gh issue list --json blockedBy` returns it.

    Returns:
        list[int]: Blocker Issue numbers.
    """
    return [n["number"] for n in (issue.get("blockedBy") or {}).get("nodes", []) if "number" in n]


def ensure_autonomous_level(issue_number: str | int,
                            requested_level: str | None = None) -> tuple[str, bool]:
    """Ensure an Issue carries the `challenge` label and an autonomous difficulty.

    Strips any prior `roadmap` label and conflicting difficulty labels. If no explicit
    level is passed, retains an existing autonomous difficulty (`easy` or `medium`),
    defaults an unestimated Issue to `medium`, and refuses an Issue labelled `hard` or
    `human` without explicit confirmation. If the `challenge` label is missing, applies
    it alongside the difficulty.

    A run is refused the level this lands, as it is wherever a level is landed
    (solorepo's DR-235): delegating is the solo handing a Challenge to the loop,
    and a run that could type it would route its own work past the reviewer in
    one act — including by the `medium` default, which is why the refusal is
    asked on the level this settles on rather than on the one a caller named.

    Parameters:
        issue_number (int | str): Issue number to inspect and update.
        requested_level (str | None): Explicit difficulty level requested by caller.

    Returns:
        tuple[str, bool]: Target difficulty level and whether labels were changed.

    Raises:
        SystemExit: If the Issue is labelled `hard` or `human` and no explicit
            level was given, or if a run asks for a level at all.
    """
    now_labels = labels_of(issue_number)
    current_level = next((lbl for lbl in now_labels if lbl in common.DIFFICULTIES), None)

    if requested_level:
        target_level = requested_level
    elif current_level in common.LOOP_LEVELS:
        target_level = current_level
    elif current_level in ("hard", "human"):
        sys.exit(f"say: #{issue_number} is labelled '{current_level}'; pass --level to explicitly delegate")
    else:
        target_level = "medium"

    refuse_a_level_from_a_run(target_level, "Delegating is the solo handing a Challenge to the "
                                            "loop, and the reviewer's verdict is what opens that "
                                            "door on its own: a Challenge read at `easy` or "
                                            "`medium` is the loop's from the moment the label "
                                            "lands.")
    stale = [lbl for lbl in now_labels
             if lbl == "roadmap" or (lbl in common.DIFFICULTIES and lbl != target_level)]
    changed = False
    if "challenge" not in now_labels or current_level != target_level:
        relabel(issue_number, add=["challenge", target_level], remove=stale)
        print(f"#{issue_number} difficulty set/ensured to {target_level}")
        changed = True
    else:
        print(f"#{issue_number} already at autonomous-capable difficulty {target_level}")

    return target_level, changed


def _delegate_pull(pull: common.Pull, issue_number: str) -> None:
    """Delegate an open pull request by dispatching rebase or review."""
    pr_number = pull["number"]
    merges = pull_requests.mergeability(pull)
    reviewer_login = channel.role_login("reviewer")
    is_changes_requested = pull_requests.is_changes_requested_pull(
        pull, reviewer_login=reviewer_login)

    if merges == "CONFLICTING":
        advance.run_coder(pr_number, "rebase")
        print(f"delegated #{pr_number} (Issue #{issue_number}): open with merge conflicts; dispatched rebase pass.")
    elif is_changes_requested:
        advance.run_coder(pr_number, "review")
        print(f"delegated #{pr_number} (Issue #{issue_number}): open with changes requested; dispatched review pass.")
    else:
        sys.exit(f"say: #{pr_number} is clean and has no standing changes requested; nothing to delegate to coder loop")


def _delegate_issue(issue_number: str, target_level: str, changed: bool) -> None:
    """Delegate an Issue without an open pull request to the autonomous coder loop."""
    coder_login = channel.role_login("coder")
    channel.gh("issue", "edit", str(issue_number), "--add-assignee", coder_login, parse=False)
    assigned = [a["login"] for a in channel.gh("issue", "view", str(issue_number), "--json", "assignees")["assignees"]]
    if coder_login not in assigned:
        sys.exit(f"say: #{issue_number} could not be assigned to {coder_login}")

    if not changed:
        relabel(issue_number, remove=[target_level])
        relabel(issue_number, add=[target_level])
        print(f"delegated Issue #{issue_number}: assigned to {coder_login} and triggered coder loop via label re-addition.")
    else:
        print(f"delegated Issue #{issue_number}: assigned to {coder_login} and triggered coder loop via label change.")


def delegate(number: str | int, level: str | None = None) -> None:
    """Hand a Challenge or pull request to the autonomous coder loop.

    Ensures the associated Challenge carries the `challenge` label and an autonomous
    difficulty (`easy` or `medium`), refusing a `hard` or `human` Challenge unless
    `--level` is passed. For a pull request, or an Issue with an open pull request,
    dispatches `rebase` if conflicting, or `review` for a verdict standing unanswered;
    refuses a clean pull request with no changes requested. For an Issue without an
    open pull request, assigns the coder Role and triggers the coder loop.

    Parameters:
        number (int | str): Issue number or pull request number.
        level (str | None): Target autonomous difficulty level (`easy` or `medium`).

    Raises:
        SystemExit: If the Challenge is labelled `hard` or `human` and no explicit level
            was given, the pull request head branch is not a recognized loop branch, the
            pull request is clean with no standing changes requested, or the Issue cannot
            be assigned to the coder Role.
    """
    is_pr_num = False
    pull: common.Pull | None = None

    try:
        pull = channel.gh("pr", "view", str(number), "--json", f"{pull_requests.ADVANCE},reviews",
                          tolerate_fail=True)
        is_pr_num = True
        print(f"#{number} identified as a pull request.")
    except common.UNREACHED:
        pass

    if is_pr_num:
        assert isinstance(pull, dict)
        head_ref = pull["headRefName"]
        m = pull_requests.LOOPS_BRANCH.match(head_ref)
        if m:
            issue_number = m.group(1)
        else:
            sys.exit(f"say: #{number} head ref {head_ref} is not a loop branch; cannot determine associated issue")
    else:
        issue_number = str(number)
        print(f"#{number} identified as an issue.")
        open_now = channel.gh("pr", "list", "--state", "open", "--json",
                              f"{pull_requests.ADVANCE},reviews")
        if isinstance(open_now, list):
            for p in open_now:
                m = pull_requests.LOOPS_BRANCH.match(p["headRefName"])
                if m and m.group(1) == str(number):
                    pull = p
                    break

    target_level, changed = ensure_autonomous_level(issue_number, requested_level=level)

    if pull:
        _delegate_pull(pull, issue_number)
    else:
        _delegate_issue(issue_number, target_level, changed)
