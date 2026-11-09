<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Issue 8 final candidate ownership

Branch: `task/adore-web-interface`. Base/HEAD before publication: `2c8dd9d49d7758de59892f171789bf6360ba7255`.
Task: `TASK-74eebc5c`. No child tasks, subagents or executor launches; additional executor budget USD 0.

This table inventories the stable candidate in working-tree bytes, including absent generated assets. Journal, review, ownership and final-validation output are lifecycle/evidence-only workflow records excluded from the candidate digest to avoid recursive hashes and allow factual delivery updates. They remain separately scoped files for coordinator inspection.
Fingerprint is SHA-256 of UTF-8 JSON of the sorted table entries, sorted keys, separators comma/colon; each entry has path/group/sha256.

Candidate fingerprint: `8f4edfd8cfa479840664b8d1674f914044c5a4698dbff76d9d71e22aca18f1ad`. Counts: 12 authored product/documentation paths, 5 generated paths, 8 stable workflow paths, plus four lifecycle/evidence records.

| Group | Repository path | Working-tree SHA-256 |
| --- | --- | --- |
| workflow | `.agentic/context/project.md` | `9f135ce248bf92144a84fb81af3f367cca67b1141be3784cfa3a4bc781932d58` |
| workflow | `.agentic/knowledge/web-interface.md` | `0a514ae65cad769b15b30f86ddab15fada11fee7e9070dd6d4701947b597a92b` |
| workflow | `.agentic/requirements/data/REQ-DATA-71853fbc.toml` | `da2ab9b2add12701bfaccfb2cea7a7a7d9ff0d2bf00175adad8ff9acb164ae4e` |
| workflow | `.agentic/requirements/functional/REQ-FUNC-c987bc4a.toml` | `c3d2a98297b6000fa73b68e1c3a7b2249de781865d50cfaaefa9d105a6380e88` |
| workflow | `.agentic/requirements/reliability/REQ-REL-39c1b197.toml` | `9191fe13a65bbc9bb7f07e526bb2d3c79d82d8140622b44e9fb4bd243daf14a7` |
| workflow | `.agentic/requirements/ux/REQ-UX-072cf049.toml` | `6d6ffd5c0a5c660f73b7359e020d910b497a2d74cd847f9db11c0e36faeca700` |
| workflow | `.agentic/requirements/ux/REQ-UX-3b5b2257.toml` | `0a2f0575dbf17164ac77e010519950a22e6f647679df57aadf35be5a6245098e` |
| workflow | `.agentic/specs/REQ-REL-39c1b197.md` | `e06c0a0cd4c207eb7a4ff7dbd63b2f467aa178035a86e20ba0e107bc0aebacf6` |
| authored | `01_Documentation/Web_Interface.md` | `00b3faf8bb1fe89bb19b1f9f20a9278ed2a672b9d0cab7548e8644d0370c34f3` |
| authored | `04_Software/adore/web/app.py` | `5c61b6a762ac99b0020836a0ef6887cf115e5eba6db2f9eaac48c332025ba294` |
| generated | `04_Software/adore/web/static/assets/index-BbLcvP-E.css` | `9d6057ccffdb9d4c52c58a344f08e301d6075cf8ca42b07ec2551c238c1127e9` |
| generated | `04_Software/adore/web/static/assets/index-CQD1LwPw.css` | `DELETED` |
| generated | `04_Software/adore/web/static/assets/index-GGhT67iS.js` | `DELETED` |
| generated | `04_Software/adore/web/static/assets/index-MBzzLshT.js` | `7d131e45a19bc8eb256536c98364eeadfacd156dde79e31b6236dbb8b2bf5e1d` |
| generated | `04_Software/adore/web/static/index.html` | `4c4d7649ee089948877e8ced665a567f4ca0546141ff9169650f4fca06975124` |
| authored | `04_Software/tests/test_web_import.py` | `6c2520ccb408cab1b271d3f98197c7ee179dd08163b5f6d0c566121a6bc53582` |
| authored | `04_Software/web/e2e/import.spec.ts` | `fb5a30dfb340a88b70d52c331930583a9a36b8d0c58a8ab01b3db354c9410943` |
| authored | `04_Software/web/src/App.tsx` | `7bd2ef5758b6f6122b409a71a22ee9751d052c9726ad810a7fd7ef52aad8e653` |
| authored | `04_Software/web/src/ImportWizard.tsx` | `0c0e493d6acd635e04f107542af341442160f3ca35fb12e95d610b0f279db980` |
| authored | `04_Software/web/src/i18n.ts` | `cadc8e2513ae5b07b152159b55d779ecb28451e8c231f10280a62b5eb59278f5` |
| authored | `04_Software/web/src/importCopy.ts` | `b599fe75bfdd863419533dd86349527311b61f390aff18d63738d73298aee038` |
| authored | `04_Software/web/src/styles.css` | `14ff40c1d21977a8cbbb66616e6bea2d1d488fa1af3f91584aa18a8345580fe3` |
| authored | `05_SoftwareDocu/Component_Web_API.md` | `6bed2377fe1ad189715491db02086aaabf389b961195294f0fd2eaf65436acc3` |
| authored | `05_SoftwareDocu/Component_Web_Frontend.md` | `a8443f3dc5d5131a9d9e7bc620a19831c1dd92092a1f8e4673a0af4e06c64dd0` |
| authored | `CHANGELOG.md` | `2508ac647238c93caf401a461b54e6dd45fda2670d2ae0e586fa9ba93fe51bab` |

Scope: issue #8 only, same-change operator/component documentation and generated production assets. No planning, release versions, lockfiles, dependency expansion, PR, merge, tag, deployment or live acceptance work. Delivery remains pending coordinator verification/instructions; no commit/push/closure has occurred.
