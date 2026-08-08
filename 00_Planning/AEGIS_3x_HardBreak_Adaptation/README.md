<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 3.x Hard-Break Adaptation

Planning material for **ADORE 3.0.0**: the no-compatibility adaptation of the
orchestrator to the released AEGIS 3.x grouped CLI and form-driven workflow.

- `AEGIS_3.0_Contract_Notes.md` pins the AEGIS contract ADORE must implement,
  including the versioned fresh-session context response, quick-run check
  evidence, verification outcomes, advisories, and abandoned runs.
- `ADORE_3.0_Adaptation_Plan.md` records the implementation baseline already
  present on the ADORE branch and the correction work packages still required
  before the live pilot and 3.0.0 release.

Basis re-verified 2026-08-08:

- Authoritative source pin, resolved from checkout:
  `D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System_WAEGIS_V3`,
  commit `a4a53081269facb3e79ece57bee6d627ec6bf51d` on branch
  `ddp/waegis-v3-implementation`.
- AEGIS release 3.0.0, WAEGIS 3.0.0, WAEGIS compatibility range
  `>=3.0.0,<4.0.0`, run-graph schema 3, context schema 1.
- ADORE repository commit `bbd204bed5b5d31dea3625ccd09b1f665f6e1dd7`
  on branch `feature/adore-2.0-aegis-2x`. The historical branch name is
  retained because this adaptation continues on the existing branch.
- The original ADORE work packages WP1-WP7 are implemented. Their assumptions
  are now the baseline to correct; the live-pilot WP8 has not been completed.

This plan targets exactly that AEGIS 3 contract. It deliberately contains no
AEGIS 1.x/2.x compatibility, fallback, or migration path. ADORE's schema-3
doctor probe is a capability/readiness check, not a product-version negotiation
layer; the provisioned payload pin supplies the AEGIS 3 identity.
