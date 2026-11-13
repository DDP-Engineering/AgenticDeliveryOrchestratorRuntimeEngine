<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
System package installation is enabled. You may directly run `sudo -n` with the image's supported package manager (for example apt-get). Inspect command output and exits, diagnose missing dependencies and adapt within this stage and the existing job limits. Install project libraries as the normal user; avoid root-owned repository/cache files. Respect lockfiles and justify any product dependency changes within ticket scope. Package scripts have container-root authority; never modify the host. A fresh container requires rechecking and reinstalling dependencies.