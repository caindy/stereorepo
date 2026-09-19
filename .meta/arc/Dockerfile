# The single-source runner container image (solorepo's DR-156, solorepo's DR-160).
# Base image provides python3 (Python 3.12.3); pre-bakes core CLI toolchain.
FROM ghcr.io/actions/actions-runner:2.337.0

USER root

# Install C toolchain (build-essential), git, curl, jq, GitHub CLI (gh), libsqlite3-0, and xz-utils
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        jq \
        libsqlite3-0 \
        xz-utils && \
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

# Install pinned Node.js (22.14.0 LTS) and pinned Gemini CLI (0.59.0)
RUN ARCH=$(dpkg --print-architecture) && \
    case "$ARCH" in \
        amd64) NODE_ARCH="x64" ;; \
        arm64) NODE_ARCH="arm64" ;; \
        *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;; \
    esac && \
    curl -fsSL "https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-${NODE_ARCH}.tar.xz" | \
    tar -xJ -C /usr/local --strip-components=1 && \
    npm install -g @google/gemini-cli@0.59.0 && \
    chown -R runner:runner /usr/local/lib/node_modules /usr/local/bin

# Install pinned Antigravity CLI (1.2.7)
RUN ARCH=$(dpkg --print-architecture) && \
    case "$ARCH" in \
        amd64) AGY_ARCH="x64"; TAR_ARCH="x64" ;; \
        arm64) AGY_ARCH="arm"; TAR_ARCH="arm64" ;; \
        *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;; \
    esac && \
    curl -fsSL "https://storage.googleapis.com/antigravity-public/antigravity-cli/1.2.7-6731160148115456/linux-${AGY_ARCH}/cli_linux_${TAR_ARCH}.tar.gz" | \
    tar -xz -C /usr/local/bin antigravity && \
    ln -s /usr/local/bin/antigravity /usr/local/bin/agy && \
    chown runner:runner /usr/local/bin/antigravity /usr/local/bin/agy

# Install pinned APM CLI (0.30.0)
RUN ARCH=$(dpkg --print-architecture) && \
    case "$ARCH" in \
        amd64) APM_ARCH="x86_64" ;; \
        arm64) APM_ARCH="arm64" ;; \
        *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;; \
    esac && \
    mkdir -p /usr/local/lib/apm && \
    curl -fsSL "https://github.com/microsoft/apm/releases/download/v0.30.0/apm-linux-${APM_ARCH}.tar.gz" | \
    tar -xz -C /usr/local/lib/apm --strip-components=1 && \
    ln -s /usr/local/lib/apm/apm /usr/local/bin/apm && \
    chown -R runner:runner /usr/local/lib/apm /usr/local/bin/apm

# Install rustup for the runner user
USER runner
ENV RUSTUP_HOME="/home/runner/.rustup" \
    CARGO_HOME="/home/runner/.cargo" \
    PATH="/home/runner/.cargo/bin:${PATH}"

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --default-toolchain none --profile minimal
