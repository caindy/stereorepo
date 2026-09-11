# The single-source runner container image (solorepo's DR-156, solorepo's DR-160).
# Base image provides python3 (Python 3.12.3); pre-bakes core CLI toolchain.
FROM ghcr.io/actions/actions-runner:2.337.0

USER root

# Install C toolchain (build-essential), git, curl, jq, and GitHub CLI (gh)
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        jq && \
    mkdir -p -m 755 /etc/apt/keyrings && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends gh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install pinned just (1.58.0)
RUN curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | \
    bash -s -- --tag 1.58.0 --to /usr/local/bin

# Install pinned uv / uvx (0.6.14)
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /usr/local/bin/

# Install rustup for the runner user
USER runner
ENV RUSTUP_HOME="/home/runner/.rustup" \
    CARGO_HOME="/home/runner/.cargo" \
    PATH="/home/runner/.cargo/bin:${PATH}"

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --default-toolchain none --profile minimal
