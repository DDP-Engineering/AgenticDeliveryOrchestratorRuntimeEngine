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
  before the live pilot and 3.0.0 release; all corrections and the live pilot
  completed on 2026-08-08.

Basis re-verified 2026-08-08:

- Authoritative source pin, resolved from checkout:
  `D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System`, commit
  `676b754f438fd82f0f48692c874bd9c8340a96b0` on branch `master`.
- AEGIS release 3.0.0, WAEGIS 3.0.0, WAEGIS compatibility range
  `>=3.0.0,<4.0.0`, run-graph schema 3, context schema 1.
- ADORE repository commit `80b0f06559e668c165060313d3d58f4e2230a351`
  on branch `master`. The adaptation continues directly on local `master`;
  it does not create, rename, or switch branches.
- The original ADORE work packages WP1-WP7 are implemented. Their assumptions
  were the baseline corrected by CR1-CR5. Live-pilot WP8 is complete; see
  `../Prerequisites_Check_Report.md` section 19 for exact acceptance evidence.

This plan targets exactly that AEGIS 3 contract. It deliberately contains no
AEGIS 1.x/2.x compatibility, fallback, or migration path. ADORE's schema-3
doctor probe is a capability/readiness check, not a product-version negotiation
layer; the provisioned payload pin supplies the AEGIS 3 identity.
