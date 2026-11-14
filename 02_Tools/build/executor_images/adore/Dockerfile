# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# =============================================================================
# Synthetic ADORE project executor (DCP toolchain reconstruction)
#
# ADORE-owned tooling only: Python 3.11 + uv, Node/npm, git, glab/gh, and Pi
# (ADORE's only coding agent) with pi-web-access pinned under /opt/pi plus
# ADORE's Pi guard extension. Runtime-project images must extend this image and
# add project-specific build/test dependencies.
#
# Build from repository root; see the adjacent README.md for verification.
# Secrets: never baked in; ADORE injects the executor's env subset at run time.
# =============================================================================

FROM --platform=linux/amd64 ubuntu:22.04

# Tool versions observed in the DCP image; distribution and transitive npm
# packages still resolve at build time. See README.md for reconstruction limits.
# Node 22 LTS: Pi 1.x needs >= 22.19.0; the official tarball is checked against
# its published SHA-256.
ARG NODE_VERSION=22.23.4
ARG NODE_SHA256=1805bcd35e6815559bd2eb97db438d3fdb0eb3a5e6a977b7c1badca76337e9ce
ARG GLAB_VERSION=1.55.0
ARG UV_VERSION=0.13.7
ARG PYTHON_VERSION=3.11.18
ARG PLAYWRIGHT_VERSION=1.63.0
# Browser versions from this Playwright release's `install --dry-run chromium`.
ARG CHROMIUM_VERSION=153.0.8010.12
ARG CHROMIUM_REVISION=1243
ARG FFMPEG_REVISION=1011
# Pi, ADORE's only coding agent, runs as `pi --mode rpc`; pi-web-access is its
# web search and page reading extension, installed in the same prefix.
ARG PI_PACKAGE=@earendil-works/pi-coding-agent@1.4.0
ARG PI_WEB_ACCESS_PACKAGE=pi-web-access@0.46.0

ENV DEBIAN_FRONTEND=noninteractive

# --- Base OS tooling: git, curl, Python 3.11 (Ubuntu 22.04 universe) ---------
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        sudo \
        gnupg \
        python3.11 \
        python3.11-venv \
        xz-utils \
    && ln -s /usr/bin/python3.11 /usr/local/bin/python \
    && rm -rf /var/lib/apt/lists/*

# --- Node (exact version, official linux-x64 build) ---------------------------
RUN curl -fsSL -o /tmp/node.tar.xz \
        "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    && echo "${NODE_SHA256}  /tmp/node.tar.xz" | sha256sum -c - \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
        --exclude='*/CHANGELOG.md' --exclude='*/LICENSE' --exclude='*/README.md' \
    && rm -f /tmp/node.tar.xz \
    && node --version

# --- uv (Python project tool; installs into /usr/local/bin) ------------------
RUN curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" \
        | env UV_INSTALL_DIR=/usr/local/bin INSTALLER_NO_MODIFY_PATH=1 sh

# --- glab (GitLab CLI; optional inside the container, baked per setup doc) ---
RUN curl -fsSL -o /tmp/glab.deb \
        "https://gitlab.com/gitlab-org/cli/-/releases/v${GLAB_VERSION}/downloads/glab_${GLAB_VERSION}_linux_amd64.deb" \
    && apt-get update \
    && apt-get install -y /tmp/glab.deb \
    && rm -f /tmp/glab.deb \
    && rm -rf /var/lib/apt/lists/*

# --- gh (GitHub CLI; official apt repository) --------------------------------
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# --- Coding agent (via npm) --------------------------------------------------
# Pi and pi-web-access at exact versions in their own prefix (pi-web-access
# resolves Pi's packages from it). Install scripts are skipped: neither needs
# them. ADORE starts Pi as `node <prefix>/lib/node_modules/.../cli.js`;
# /opt/pi/bin on PATH is for operators.
RUN npm install -g --prefix /opt/pi --ignore-scripts --no-fund --no-audit \
        "${PI_PACKAGE}" "${PI_WEB_ACCESS_PACKAGE}"
ENV PATH=/opt/pi/bin:$PATH
# ADORE's guard extension, loaded with `-e` by every Pi run; root-owned, so the
# agent cannot change it.
COPY 04_Software/docker/pi/adore-guard.ts /opt/adore/pi/adore-guard.ts
COPY 04_Software/docker/pi/adore-chatgpt.mjs /opt/adore/pi/adore-chatgpt.mjs
RUN chmod 0644 /opt/adore/pi/adore-guard.ts /opt/adore/pi/adore-chatgpt.mjs

# --- Non-root user; mount points; git trust for bind-mounted repos ------------
# Bind mounts on Docker Desktop (Windows) show foreign ownership; without
# safe.directory git refuses to operate on the mounted repo/worktree.
# USER_UID/USER_GID must match the host user that runs ADORE so that files
# written by the container to bind-mounted volumes (worktree, IO, caches) are
# owned by that host user/group. Docker has no runtime UID remapping like
# Podman's --userns=keep-id, so they are baked at image-build time via
# --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g). Podman
# deployments can ignore this and use --userns=keep-id instead.
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} adore \
    && useradd --create-home --uid ${USER_UID} --gid ${USER_GID} adore \
    && mkdir -p /adore/repo /adore/work /adore/io \
    && chown -R ${USER_UID}:${USER_GID} /adore \
    && git config --system --add safe.directory '*'

USER adore
WORKDIR /adore/work

# Pin HOME to the adore user's home: some daemons (Docker Engine in WSL2)
# otherwise inject the host user's HOME into the container, breaking every
# HOME-based cache - uv, npm, Pi, and project tools.
ENV HOME=/home/adore

# Cache volume mount points (created so ownership is right before mounting):
# uv cache at /home/adore/.cache/uv, npm cache at /home/adore/.npm. The
# ADORE-owned Pi agent directory replaces the personal ~/.pi/agent.
RUN mkdir -p /home/adore/.cache/uv /home/adore/.npm \
    && mkdir -m 0700 /home/adore/.adore-pi-agent
ENV UV_CACHE_DIR=/home/adore/.cache/uv

# Proper CPython 3.11: Ubuntu 22.04's python3.11 apt package is stuck at
# 3.11.0rc1, so bake a uv-managed release build (into ~/.local/share/uv,
# not the runtime-mounted cache) and make uv prefer it project-wide.
RUN uv python install "${PYTHON_VERSION}"
ENV UV_PYTHON=3.11

# Make `python3`/`python` on PATH resolve to the uv-managed 3.11 release:
# the target repo's AEGIS CLI (`python .agentic/aegis.py`) is stdlib-only but
# requires Python 3.11+ (system /usr/bin/python3 stays 3.10 for apt). git
# enables its diff-based checks; node serves the npm-installed executors above.
USER root
RUN target="$(ls -d /home/adore/.local/share/uv/python/cpython-3.11*/bin/python3.11 2>/dev/null | head -n1)" \
    && test -x "$target" \
    && ln -sf "$target" /usr/local/bin/python3 \
    && ln -sf "$target" /usr/local/bin/python
USER adore

# The container idles; ADORE execs the executor into it one AEGIS stage at a
# time, and runs the AEGIS CLI itself through the same seam.
CMD ["sleep", "infinity"]


# --- ADORE frontend validation: Chromium in the same executor container -------
# Global Playwright seeds shared browsers; npm ci in the project worktree still
# installs the project's own @playwright/test and its other dependencies.
USER root
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
RUN HOME=/root npm install -g --ignore-scripts --no-fund --no-audit \
        "playwright@${PLAYWRIGHT_VERSION}" \
    && HOME=/root playwright install-deps chromium \
    && apt-get update && apt-get install -y --no-install-recommends unzip \
    && mkdir -p \
        "${PLAYWRIGHT_BROWSERS_PATH}/chromium-${CHROMIUM_REVISION}" \
        "${PLAYWRIGHT_BROWSERS_PATH}/chromium_headless_shell-${CHROMIUM_REVISION}" \
        "${PLAYWRIGHT_BROWSERS_PATH}/ffmpeg-${FFMPEG_REVISION}" \
    && curl -fL --retry 3 --connect-timeout 20 --max-time 600 -o /tmp/chromium.zip \
        "https://storage.googleapis.com/chrome-for-testing-public/${CHROMIUM_VERSION}/linux64/chrome-linux64.zip" \
    && unzip -q /tmp/chromium.zip -d "${PLAYWRIGHT_BROWSERS_PATH}/chromium-${CHROMIUM_REVISION}" \
    && curl -fL --retry 3 --connect-timeout 20 --max-time 600 -o /tmp/headless.zip \
        "https://storage.googleapis.com/chrome-for-testing-public/${CHROMIUM_VERSION}/linux64/chrome-headless-shell-linux64.zip" \
    && unzip -q /tmp/headless.zip -d "${PLAYWRIGHT_BROWSERS_PATH}/chromium_headless_shell-${CHROMIUM_REVISION}" \
    && curl -fL --retry 3 --connect-timeout 20 --max-time 300 -o /tmp/ffmpeg.zip \
        "https://cdn.playwright.dev/dbazure/download/playwright/builds/ffmpeg/${FFMPEG_REVISION}/ffmpeg-linux.zip" \
    && unzip -q /tmp/ffmpeg.zip -d "${PLAYWRIGHT_BROWSERS_PATH}/ffmpeg-${FFMPEG_REVISION}" \
    && test -x "${PLAYWRIGHT_BROWSERS_PATH}/chromium-${CHROMIUM_REVISION}/chrome-linux64/chrome" \
    && test -x "${PLAYWRIGHT_BROWSERS_PATH}/chromium_headless_shell-${CHROMIUM_REVISION}/chrome-headless-shell-linux64/chrome-headless-shell" \
    && test -x "${PLAYWRIGHT_BROWSERS_PATH}/ffmpeg-${FFMPEG_REVISION}/ffmpeg-linux" \
    && touch \
        "${PLAYWRIGHT_BROWSERS_PATH}/chromium-${CHROMIUM_REVISION}/INSTALLATION_COMPLETE" \
        "${PLAYWRIGHT_BROWSERS_PATH}/chromium_headless_shell-${CHROMIUM_REVISION}/INSTALLATION_COMPLETE" \
        "${PLAYWRIGHT_BROWSERS_PATH}/ffmpeg-${FFMPEG_REVISION}/INSTALLATION_COMPLETE" \
    && chmod -R a+rX "${PLAYWRIGHT_BROWSERS_PATH}" \
    && rm -f /tmp/chromium.zip /tmp/headless.zip /tmp/ffmpeg.zip \
    && rm -rf /var/lib/apt/lists/*
COPY LICENSE.txt /opt/adore/LICENSE.txt
LABEL org.opencontainers.image.title="ADORE synthetic project executor" \
      org.opencontainers.image.description="Reconstructed DCP executor tooling; see the source README for limits."
USER adore
