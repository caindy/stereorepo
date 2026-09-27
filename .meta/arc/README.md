# The self-hosted runner (ARC), in two layers

`coder.yml` and `review.yml` each run a Claude Code session for up to 75 and
50 minutes — the actual GitHub Actions minutes sink, since the runner sits
there the whole time. They ran on `ubuntu-latest` until this stood up
GitHub's Actions Runner Controller on Kubernetes; now they run here,
`runs-on: arc-runner-set`, scaled to zero when idle. `gate.yml` and
`advance.yml` followed (solorepo's DR-140), so every job in every workflow
of this repository runs on this cluster and nothing here spends
GitHub-hosted minutes. That includes `main`'s required status checks, which
solorepo's DR-137 deliberately left hosted: **a merge cannot go green while
this cluster is down**, so the machine being reachable is now the
repository's business and not only the loops'. `template/`'s seeded gate
runs on `ubuntu-latest` inside the published runner image (`container:
ghcr.io/caindy/solorepo-runner:2.337.0-5`), a portfolio having no cluster
of its own (solorepo's DR-160).

Two layers, separately invokable:

1. `just arc-cluster` — *optional*. A local `kind` cluster named
   `solorepo-arc`. Skip it entirely on a machine that already has a
   cluster some other way.
2. `just arc` — the runner itself. `helm upgrade --install` for the ARC
   controller and the runner scale set, against whatever
   `kubectl config current-context` already names. Never `kind`-specific,
   so the same command is layer one's cluster today and any other
   machine's cluster tomorrow — `kubectl config use-context` is the only
   thing that changes between them.

## One-time: the PAT

ARC needs a GitHub credential to register runners against
`caindy/solorepo`. Create it yourself — GitHub's UI only, nothing here can
do this for you:

1. https://github.com/settings/tokens → **Generate new token (classic)**.
2. Scope: **`repo`** — this is a repo-level scale set (`caindy/solorepo`
   only, not an org), so `repo` is enough; no `admin:org`.
3. Copy the token once, then either:
   - `export ARC_GITHUB_TOKEN=<token>` before running `just arc`, or
   - write it to `~/.config/solorepo/arc-runner.env` (create the
     directory if needed, `chmod 600` the file) as:
     ```
     ARC_GITHUB_TOKEN=<token>
     ```
     the same "outside the tree, per machine, mode 600" shape the coder
     and reviewer Role tokens already use (`.meta/say/channel.py`,
     solorepo's DR-073) — `deploy` refuses a world- or group-readable
     file the same way.

`deploy` never takes the token as a command-line argument or writes it
into a file this repository tracks; it goes straight into a Kubernetes
Secret via `kubectl apply -f -` over stdin.

## On a blank Windows machine (WSL2)

Windows 11 Home has no Hyper-V, so `kind` needs Docker under WSL2:

1. `wsl --install` (an elevated PowerShell prompt), then reboot if asked.
2. Install Docker Desktop for Windows with the WSL2 backend, or Docker
   Engine directly inside the WSL2 distro — either way, `docker info`
   should work from a WSL2 shell before continuing.
3. Install `kubectl`, `helm`, and `kind` inside that WSL2 shell (each
   ships a Linux binary; use their usual install instructions).
4. From that same WSL2 shell: `just arc-cluster` then `just arc`, exactly
   as above — nothing about the two layers is Windows-specific once WSL2
   has Docker.

## The runner image

`values-runnerset.yaml` pins the runner container image to
`ghcr.io/caindy/solorepo-runner:2.337.0-5` (solorepo's DR-156, solorepo's DR-160, solorepo's #775).
Defined in `.meta/arc/Dockerfile` on top of `ghcr.io/actions/actions-runner:2.337.0`
(which carries `python3` `3.12.3`), it pre-bakes `build-essential`, `gh`,
`jq`, `just`, `uv` (with CPython 3.13), `apm`, `rustup`, `node` / `npm`, `claude` (pinned
Claude Code 2.1.283), `gemini`, `copilot`, `codex` (pinned Codex CLI 0.157.0), and `agy` (pinned Antigravity CLI 1.2.7).

To build, load into a local `kind` cluster, and publish to GHCR:
```bash
docker build -t solorepo-runner:2.337.0-5 -t ghcr.io/caindy/solorepo-runner:2.337.0-5 -f .meta/arc/Dockerfile .meta/arc
kind load docker-image ghcr.io/caindy/solorepo-runner:2.337.0-5 --name solorepo-arc

# Publish to GHCR for hosted workflows and specialized portfolios:
echo "$ARC_GITHUB_TOKEN" | docker login ghcr.io -u <username> --password-stdin
docker push ghcr.io/caindy/solorepo-runner:2.337.0-5
```

The package on GHCR (`ghcr.io/caindy/solorepo-runner`) must remain configured as
**Public** so that workflows in external portfolio repositories can pull the
container image anonymously without authentication.

## Subscription credentials (Gemini / Antigravity)

Running autonomous loops under personal subscription quotas rather than
metered API billing (solorepo's DR-245, solorepo's #669) provisions
developer credentials into ephemeral runner pods:

1. Authenticate `agy` locally so credentials exist in `~/.gemini` (or
   `/mnt/c/Users/*/.gemini` under WSL2).
2. Run `just arc`. `.meta/arc/deploy` packages the OAuth tokens and settings
   into the `arc-gemini-credentials` Secret in namespace `arc-runners`.
3. Ephemeral runner pods copy the Secret into an isolated, writable
   `emptyDir` at `/home/runner/.gemini` with permissions restricted to
   `chmod 600`.

## Codex subscription credentials

Sign in to the Codex CLI with ChatGPT on the ARC host. The ARC deployer reads
the file-backed login from `~/.codex/auth.json`; if Codex stores credentials in
the system keyring, configure `cli_auth_credentials_store = "file"` and sign in
again so the login is available as a file. Keep the file mode at `600`.

`just arc` applies the ChatGPT login as the `arc-codex-credentials` Secret.
Runner pods copy `auth.json` into an isolated, mode-`600` `.codex` home. The
Codex harness accepts only a ChatGPT-authenticated login and removes API-key
environment variables before starting the CLI. It does not provision an OpenAI
API key. Set the repository variable `CODEX_FALLBACK` to `true` to add Codex as
a fallback in coder, reviewer and triage chains. Set `CODEX_MODEL` to select a
different model; the default is `gpt-5.3-codex`. A `harness:codex` label or coder
dispatch selects Codex as the primary.

## Verifying it worked

- `kubectl get pods -n arc-systems` — the controller, `Running`, and its
  image tag matching `CHART_VERSION` in `.meta/arc/deploy` (both charts are
  pinned to the same number).
- `kubectl get secret arc-gemini-credentials -n arc-runners` — the Gemini
  subscription Secret provisioned from host credentials.
- `kubectl get secret arc-codex-credentials -n arc-runners` — the Codex
  ChatGPT-login Secret provisioned from the host's `.codex` home.
- GitHub → `caindy/solorepo` → **Settings → Actions → Runners** —
  `arc-runner-set` listed, Idle or Listening.
- A workflow with `runs-on: arc-runner-set` should show a pod appear and
  disappear in `kubectl get pods -n arc-runners -w` while it runs.

## Going back

`.meta/arc/teardown` uninstalls both Helm releases; add `--cluster` to
also delete the `kind` cluster `arc-cluster` created. No `justfile` recipe
on purpose — going back down is rare and deliberate enough not to need
one.
