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
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
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
CONTAINER_OPENCODE_AUTH_DIR = f"{CONTAINER_HOME}/.local/share/opencode"
CONTAINER_CODEX_HOME = f"{CONTAINER_HOME}/.adore-codex"
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
