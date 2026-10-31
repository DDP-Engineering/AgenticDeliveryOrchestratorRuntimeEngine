#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file       package_permissions.py
@brief      Container-only authorization for agent-owned package installation.
@details    This fixed script configures sudo permission; it never installs
            packages or selects dependencies. Package hooks have container-root
            authority. The host interpreter never executes this script.
"""

# IMPORTS
from pathlib import Path

from adore.isolation import IsolationError
from adore.util import strict_json_loads

# CONSTANTS
PACKAGE_AUTHORIZATION_ACK = "adore-system-packages-ready"

# Use the image's root-owned OS Python, not the user-owned uv interpreter.
# Neither script nor UID is read from the mounted worktree or IO directory.
PACKAGE_AUTHORIZATION_SCRIPT = r'''
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See LICENSE.txt. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile

os.environ.clear()
os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
uid = int(sys.argv[1])
if os.geteuid() != 0 or not 0 < uid < 4294967295:
    raise RuntimeError('non-root agent UID required')
sudo, visudo = shutil.which('sudo'), shutil.which('visudo')
if not sudo or not visudo:
    raise RuntimeError('image requires sudo and visudo; rebuild the executor image')
managers = [p for p in (
    '/usr/bin/apt-get', '/usr/bin/apt', '/usr/bin/dpkg', '/usr/bin/dnf',
    '/usr/bin/yum', '/sbin/apk', '/usr/bin/pacman', '/usr/bin/zypper',
) if os.path.isfile(p) and os.access(p, os.X_OK)]
if not managers:
    raise RuntimeError('image has no supported system package manager')
directory = pathlib.Path('/etc/sudoers.d')
info = directory.lstat()
if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
    raise RuntimeError('unsafe sudoers directory')
policy = (
    '# Copyright (c) 2026 DDP Engineering\n'
    '# This software is licensed under the PolyForm Noncommercial License 1.0.0.\n'
    '# Commercial use requires a separate commercial license.\n'
    '# See LICENSE.txt. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0\n'
    'Defaults env_keep += "HTTP_PROXY HTTPS_PROXY NO_PROXY '
    'http_proxy https_proxy no_proxy DEBIAN_FRONTEND"\n'
    '#' + str(uid) + ' ALL=(root) NOPASSWD: ' + ', '.join(managers) + '\n'
)
fd, temporary = tempfile.mkstemp(prefix='.adore-', dir=str(directory))
try:
    with os.fdopen(fd, 'w') as handle:
        handle.write(policy)
        os.fchmod(handle.fileno(), 0o440)
    subprocess.run([visudo, '-cf', temporary], check=True, capture_output=True, timeout=5)
    os.replace(temporary, str(directory / 'adore-system-packages'))
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
# Exercise the actual non-root -> root transition without installing anything.
subprocess.run([sudo, '-u', '#' + str(uid), '--', sudo, '-n', '--', managers[0],
                '--version'], check=True, capture_output=True, timeout=5)
print('adore-system-packages-ready')
'''

# PUBLIC API
def staged_auth_redactions(path: Path) -> dict[str, str]:
    """@brief Collect bounded values from the exact approved staged auth snapshot.
    @param[in] path Temporary executor-auth snapshot owned by the conductor.
    @return Redaction-only string values, kept in memory and never in evidence.
    @exception IsolationError Unreadable, oversized, ambiguous or malformed auth.
    """
    try:
        if path.is_symlink():
            raise ValueError("linked auth snapshot")
        with path.open("rb") as handle:
            raw = handle.read(131073)
        if len(raw) > 131072:
            raise ValueError("auth exceeds bound")
        auth = strict_json_loads(raw.decode("utf-8"))
        if not isinstance(auth, dict):
            raise ValueError("auth must be an object")
        pending = [(auth, 0)]
        values = set()
        while pending:
            value, depth = pending.pop()
            if depth > 16:
                raise ValueError("auth nesting exceeds bound")
            if isinstance(value, str) and value:
                value.encode("utf-8")
                values.add(value)
            elif isinstance(value, dict | list):
                pending.extend((item, depth + 1) for item in (
                    value.values() if isinstance(value, dict) else value))
        return {f"staged-auth-{index}": value for index, value in enumerate(sorted(values))}
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise IsolationError("staged executor auth cannot be safely redacted") from exc


# END OF FILE
