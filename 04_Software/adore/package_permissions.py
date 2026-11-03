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

# END OF FILE
