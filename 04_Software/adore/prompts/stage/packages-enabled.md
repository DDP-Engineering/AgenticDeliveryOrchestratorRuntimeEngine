<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->
Container environment administration is enabled. Use `sudo -n` to install missing system packages and configure the build/test environment as needed; package choice and diagnosis are your responsibility. Do not ask for clarification just because a dependency is missing. Install project libraries and write repository/cache files as the normal user. Respect lockfiles and keep product dependency changes within ticket scope. Administrative authority is inside this container, including its mounted project files; never modify the host, ADORE resources or injected tooling. Keep application sandboxes enabled: do not use --no-sandbox or disable security checks to make tests pass. Network access remains separately configured. If a host restriction blocks a required operation, report the exact error instead of weakening isolation. Dependencies remain only in this container; reassess them in a fresh container.