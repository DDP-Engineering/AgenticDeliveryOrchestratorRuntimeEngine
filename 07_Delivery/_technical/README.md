<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Delivery technical material

End users need only the two complete archives in the parent directory.

| Directory | Contents |
| --- | --- |
| `checksums/` | SHA-256 files for the complete Windows/Linux archives |
| `reports/` | Test summaries, validation logs and diagnostic traces |
| `verification/` | Native acceptance receipts, logs and isolated extracted test applications |
| `work/` | Older intermediate builds and temporary tooling fixtures |
| `runtime/` | Advanced source/deployment archives requiring host Python/uv |
| `offline/` | Optional host-specific offline installation bundles, when generated |

The advanced archives are `runtime/adore-runtime-0.13.0.zip` and
`runtime/adore-runtime-0.13.0.tar.gz`; they are not separate portable CLI editions.
All source packaging, launch and setup scripts remain under `02_Tools/`.
The workspaces and existing verification evidence were moved here without
changing either end-user archive. No installed ADORE instance or user data was
modified.

On Linux, check the two final archives from `checksums/` with:

```bash
sha256sum -c *.sha256
```

Each entry resolves the archive through a relative `../../<archive>` path.
The current integrated acceptance report is
[reports/simple-setup-test-report.json](reports/simple-setup-test-report.json).
Native receipts are `verification/portable-check-windows/result.json` and
`verification/portable-check-linux/result.json`.
The historical test commands in logs retain their original invocation paths.
Current report and receipt references point to this organized layout.
