#!/bin/sh
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
set -eu
case "$0" in */*) script_dir=${0%/*} ;; *) script_dir=. ;; esac
bundle_dir=$(CDPATH= cd -- "$script_dir" && pwd)
unset PYTHONPATH PYTHONHOME
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
exec "$bundle_dir/python/bin/python3.12" -I -B -m adore "$@"
