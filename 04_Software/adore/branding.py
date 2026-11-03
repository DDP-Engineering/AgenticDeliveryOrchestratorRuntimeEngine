#!/usr/bin/env python3
# -*- coding: utf-8 -*-  # noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file branding.py
@brief Canonical product identity and runtime naming constants for ADORE.
@details Centralizes the fixed product, package, filesystem, container, image,
         deployment, and delivery names used by the Python runtime. Shell and
         packaging surfaces mirror these constants and are checked by the
         release-consistency tool.
"""

from __future__ import annotations

# CONSTANTS

PRODUCT_NAME = "Agentic Delivery Orchestrator & Runtime Engine"
PRODUCT_ACRONYM = "ADORE"
PRODUCT_SLUG = "adore"
PACKAGE_NAME = "adore"
PROFILE_HOME_ENV = "ADORE_HOME"

DEFAULT_STATE_ROOT = ".adore"
DEFAULT_QUESTIONS_FILE = "ADORE_QUESTIONS.md"
DEFAULT_BOT_EMAIL = "adore-bot@local"
PROCESS_LOG_FILE = "adore.log"

CONTAINER_USER = "adore"
CONTAINER_HOME = "/home/adore"
CONTAINER_REPO_MOUNT = "/adore/repo"
CONTAINER_WORKTREE_MOUNT = "/adore/work"
CONTAINER_IO_MOUNT = "/adore/io"
CONTAINER_UV_CACHE_MOUNT = f"{CONTAINER_HOME}/.cache/uv"
CONTAINER_NPM_CACHE_MOUNT = f"{CONTAINER_HOME}/.npm"
# Pi is ADORE's only coding agent; usage events and project views name it so.
EXECUTOR_NAME = "pi"
# Native (installed) Pi launch template until PI-07 drives it over RPC.
PI_NATIVE_COMMAND = "pi -p --mode json --model {model} {prompt}"
# Pi in the executor image: the pinned prefix, ADORE's guard extension, and the
# ADORE-owned agent directory that replaces the personal ~/.pi/agent.
CONTAINER_PI_PREFIX = "/opt/pi"
CONTAINER_PI_CLI = (
    f"{CONTAINER_PI_PREFIX}/lib/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
)
CONTAINER_PI_GUARD = "/opt/adore/pi/adore-guard.ts"
#: The pinned pi-web-access extension next to Pi, loaded with `-e` only while
#: internet access is on.
CONTAINER_PI_WEB_ACCESS = f"{CONTAINER_PI_PREFIX}/lib/node_modules/pi-web-access"
CONTAINER_PI_AGENT_DIR = f"{CONTAINER_HOME}/.adore-pi-agent"
# The server's ChatGPT sign-in: ADORE's helper script in the image and the
# mount point of the credential directory in its helper container (never in a
# run container), and that directory's name under the ADORE home.
CONTAINER_PI_CHATGPT_SCRIPT = "/opt/adore/pi/adore-chatgpt.mjs"
CONTAINER_CHATGPT_MOUNT = "/adore/chatgpt"
CHATGPT_CREDENTIAL_DIR = "chatgpt"
EGRESS_PROXY_ALIAS = "adore-egress-proxy"

EXECUTOR_BASE_IMAGE = "adore-executor-base:1.0.0"
EGRESS_PROXY_IMAGE = "adore-egress-proxy:1.0.0"
EGRESS_NETWORK_PREFIX = "adore-egress"
UV_CACHE_VOLUME = "adore-uv-cache"
NPM_CACHE_VOLUME = "adore-npm-cache"

SYSTEMD_SERVICE_NAME = "adore.service"
WINDOWS_TASK_NAME = "ADORE Orchestrator & Runtime Engine"
RUNTIME_PACKAGE_PREFIX = "adore-runtime"

# END OF FILE
