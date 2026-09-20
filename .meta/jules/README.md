# Google Labs Jules Autonomous Reviewer Harness

Integration and driver tooling for the Google AI Ultra **Jules API** as an autonomous reviewer fallback harness (Challenge [#681](https://github.com/caindy/solorepo/issues/681), solorepo's DR-246).

---

## 1. Architectural Overview

| Dimension | Self-Hosted ARC Runner (`review.yml`) | Google Labs Jules (`.meta/actions/jules`) |
|---|---|---|
| **Execution Host** | Local Kubernetes cluster (`kind` / WSL2 / Desktop) | Google Cloud sandboxed session (`jules.googleapis.com`) |
| **Compute Cost** | Workstation CPU/RAM; zero GitHub-hosted minutes | Zero local compute; cloud evaluation |
| **Model / Agent** | Claude Code or Antigravity CLI (`agy`) | Jules (Gemini 3 Pro) |
| **Billing / Quota** | Anthropic API tokens or personal subscription (`agy`) | Google AI Ultra Jules API allotment |
| **Filesystem / Shell** | Full access to `.meta/say/`, local git, tools | Ephemeral cloud session; diff and threads in prompt |
| **Turnaround** | Synchronous runner execution | Asynchronous session polled via REST activities |

---

## 2. Jules API Architecture: Source-Bound vs. Repoless Modes

The Jules REST API operates under base URL `https://jules.googleapis.com/v1alpha` authenticated via the `X-Goog-Api-Key` HTTP header. The API supports two distinct operational modes:

### A. Source-Bound Mode (Direct GitHub Mutations)
- **Mechanism**: The session payload provides `sourceContext` pointing to an authorized repository source (e.g. `sources/github/caindy/solorepo`).
- **Rejected Alternative**: Requires installing the Jules GitHub App. Direct cloud repository commits lack runner-attested Actor and Agent trailers and commit signatures, which was rejected in favor of repoless review execution (solorepo's DR-246).

### B. Repoless Mode (Pure Engine Sandbox Analysis)
- **Mechanism**: The session payload omits `sourceContext` entirely, as supported by [`@google/jules-sdk`](https://www.npmjs.com/package/@google/jules-sdk) and demonstrated by [`sanjay3290/jules-pr-reviewer`](https://github.com/sanjay3290/jules-pr-reviewer).
- **Prerequisite**: Zero GitHub App installation. Requires only an API key (`JULES_API_KEY`).
- **Workflow**: The runner fetches diffs, existing review threads, and CI checks, passes them inside `prompt`, and polls `/v1alpha/sessions/{id}/activities` for the reviewer's findings and recommended verdict.

---

## 3. Prerequisite Setup

To enable Jules fallback execution:

1. Generate a Jules API key at [jules.google.com/settings](https://jules.google.com/settings).
2. Set the `JULES_API_KEY` repository secret for GitHub Actions runs, or record it in `~/.config/solorepo/jules.env` for local workstation testing.
3. Enable the opt-in repository variable `vars.JULES_FALLBACK = true` to activate Jules fallback when Claude Code and Antigravity reviewer passes fail.

---

## 4. Solorepo Discipline Alignment

Repoless mode resolves friction with repository rules by keeping mutation and channel signing strictly on the runner:

### A. Attestation & Commit Attribution (Article 19, solorepo's DR-233)
- **Source-Bound Friction**: Jules commits created in Google's cloud lack an `Actor:` trailer naming their actor, which leaves them unattributable under Article 19.
- **Repoless Resolution**: Jules performs no direct git mutations. In the reviewer role, Jules returns review text and anchored findings, which the runner posts under the reviewer Role's account using `.meta/say/post` with workflow-attested identity variables.

### B. Quality Gates & CI Status
- **Verification Rule**: The merge manager lands what is green (solorepo's DR-161), so `review_pr` refuses to approve any head whose GitHub CI checks have failed.
- **Repoless Resolution**: `review_pr` queries `gh pr checks --json name,state,bucket` and `.meta/check_pr.py <pr>`. If any check has failed, or if open review threads remain unresolved (PR First step 8), approval is strictly refused.

### C. Pull Request Form Compliance
- **Verification Rule**: Pull requests must follow the mandatory 7-heading description template defined in `.github/PULL_REQUEST_TEMPLATE.md` (PR First, verified by `check_pr.py`).
- **Repoless Resolution**: `review_pr` passes the output of `python3 .meta/check_pr.py <pr>` directly to Jules, ensuring pull request form violations result in a changes-requested verdict.

---

## 5. Driver Tooling Reference

The module **[`client.py`](client.py)** provides the CLI interface and library for Jules interactions:

### Workflow Subcommands
- **`dispatch`**: Entry point invoked by [`.meta/actions/jules/action.yml`](../actions/jules/action.yml). Accepts `--role reviewer`, `--pr <number>`, `--prompt <text>`, and `--timeout-minutes <int>`.
- **`review-pr`**: Executes repoless PR review. Gathers diff and thread context, runs CI and form status queries, creates a Jules cloud session, extracts anchored line findings, and posts signed review verdicts via `.meta/say/post --role reviewer`.

### Inspection Subcommands
- **`sources`**: Lists connected repository sources:
  ```bash
  python3 .meta/jules/client.py sources --dry-run
  ```
- **`sessions`**: Lists recent session IDs and statuses:
  ```bash
  python3 .meta/jules/client.py sessions --page-size 5
  ```
- **`session <id>`**: Displays details for a specific session.
- **`activities <id>`**: Displays activity feed and messages for a specific session.
- **`create`**: Low-level session creation for experimental prompt evaluation. Operates in repoless sandbox mode by default (use `--repo <owner/repo>` to target an authorized GitHub source repository).
