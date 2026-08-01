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
@file test_branding.py
@brief Contract tests for canonical ADORE product and runtime names.
@details Proves the clear-path identity values used across the hard-cut rename.
"""

from __future__ import annotations

# IMPORTS
from adore import branding

# PUBLIC API / TESTS


def test_canonical_adore_branding_contract() -> None:
    """
    @brief   Every fixed product-controlled name uses the ADORE namespace.
    """
    assert branding.PRODUCT_NAME == "Agentic Delivery Orchestrator & Runtime Engine"
    assert branding.PRODUCT_ACRONYM == "ADORE"
    assert branding.PRODUCT_SLUG == "adore"
    assert branding.PACKAGE_NAME == "adore"
    assert branding.PROFILE_HOME_ENV == "ADORE_HOME"
    assert branding.DEFAULT_STATE_ROOT == ".adore"
    assert branding.DEFAULT_QUESTIONS_FILE == "ADORE_QUESTIONS.md"
    assert branding.DEFAULT_BOT_EMAIL == "adore-bot@local"
    assert branding.PROCESS_LOG_FILE == "adore.log"
    assert branding.CONTAINER_USER == "adore"
    assert branding.CONTAINER_HOME == "/home/adore"
    assert branding.CONTAINER_REPO_MOUNT == "/adore/repo"
    assert branding.CONTAINER_WORKTREE_MOUNT == "/adore/work"
    assert branding.CONTAINER_IO_MOUNT == "/adore/io"
    assert branding.CONTAINER_UV_CACHE_MOUNT == "/home/adore/.cache/uv"
    assert branding.CONTAINER_NPM_CACHE_MOUNT == "/home/adore/.npm"
    assert branding.CONTAINER_OPENCODE_AUTH_DIR == "/home/adore/.local/share/opencode"
    assert branding.CONTAINER_CODEX_HOME == "/home/adore/.adore-codex"
    assert branding.EGRESS_PROXY_ALIAS == "adore-egress-proxy"
    assert branding.EXECUTOR_BASE_IMAGE == "adore-executor-base:1.0.0"
    assert branding.EGRESS_PROXY_IMAGE == "adore-egress-proxy:1.0.0"
    assert branding.EGRESS_NETWORK_PREFIX == "adore-egress"
    assert branding.UV_CACHE_VOLUME == "adore-uv-cache"
    assert branding.NPM_CACHE_VOLUME == "adore-npm-cache"
    assert branding.SYSTEMD_SERVICE_NAME == "adore.service"
    assert branding.WINDOWS_TASK_NAME == "ADORE Orchestrator & Runtime Engine"
    assert branding.RUNTIME_PACKAGE_PREFIX == "adore-runtime"


# END OF FILE
