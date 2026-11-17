ARG BASE_IMAGE=adore-executor-base:1.0.0
FROM ${BASE_IMAGE}
ARG PLAYWRIGHT_VERSION=1.63.0
ARG CHROMIUM_VERSION=153.0.8010.12
ARG CHROMIUM_REVISION=1243
ARG FFMPEG_REVISION=1011

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
