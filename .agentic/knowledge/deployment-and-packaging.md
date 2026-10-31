<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Deployment and packaging

The public repository tools are `02_Tools/setup_environment.py`,
`create_package.py` and `verify_package.py`.
Setup synchronizes frozen Python/web development dependencies, frontend packages
and Chromium without running tests, configuring credentials or installing services.
Create checks release metadata/notes, compiles and licenses the frontend, then
bundles managed CPython, frozen dependencies, ADORE, three curated user guides
and the `02_Tools/portable/` launch templates for the matching native OS.
Verify checks archive release identity and optional hash, relocates/exercises the
actual media with isolated data, then removes all temporary files on exit.

`07_Delivery/` retains only complete Windows ZIP/Linux TAR.GZ user archives and
optional adjacent hashes. No technical directory, README, report, build workspace
or extracted verification media is retained. Build and verification use managed
OS temporary storage and console output.

`02_Tools/internal/` contains release metadata/note checks and asset licensing.
`02_Tools/deploy/` remains specialized service administration. No automated tests
are added or run for environment setup or deployment scripts. The old advanced
source bundle and separate wheelhouse installer flow have been retired.

Component references: `05_SoftwareDocu/Component_Packaging.md`,
`Component_Portable_Distribution.md` and `Component_Deployment.md`.
