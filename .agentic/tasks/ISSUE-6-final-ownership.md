<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Issue 6 scoped candidate ownership

Original base: 705e248ad24787e8f573aca477f36fdd4c6fd09f. Integrated comparison
base: b6903f5 (issue 5 owner commits 9da9747 and b6903f5 excluded from this
delivery). No issue 6 commit/publication has been performed.

The initial manifest remains historical. Its owner-updated issue 5 journal is
excluded. Four shared documents preserve issue 5 content with explicit issue 6
hunks: project context, web knowledge, operator guide and changelog. Every other
initial issue 5 entry has identical SHA-256/absence, including all frontend source,
static output, tests and requirements, after production build.

## Authored candidate files

14 product/documentation files (limit 20). Workflow records below count separately.

| Path | Working-copy SHA-256 | Delta evidence |
| --- | --- | --- |
| `.agentic/context/project.md` | `2a2128172bfbf2e8fa18fb66a9d607ba4f73b4a83a30e9cfa2953719c75293d1` | `1227d2a5e015c91a25a6284cc33cd92aae133720fef821d00fd5b725388b1fb4` |
| `.agentic/knowledge/profiles.md` | `7b79fbaa00d938a9d25126e3617337ffb8f149d6771a872d759080f3d8a0cadc` | `2de8cd9c7c5863a22d93b256dbb57a0c64c2c86d00cb5d89f035b0191f0d2117` |
| `.agentic/knowledge/web-interface.md` | `e2f8d70735e0614947faac5d9895f1dd091f31f9d5cfa1bf2083aec1315ae955` | `34426077c5192a86a713fd79cdd68633aa744162978f2f198f98587ede9960cf` |
| `.agentic/knowledge/wizard.md` | `da22862bb8d555720e64cf4c85c8e05ce6a24707af77d04c823e6091333c6a26` | `71e4665dc52ca59a9c1dbefa437d5d3462b05e118c69459f1c5637a2e1dfb17e` |
| `01_Documentation/Web_Interface.md` | `db35c85662e364d6d1faaba8cda88b57820e524e9cd268254f2dcf6c0d880726` | `ec14721546265f3b733683fac5855bcd9fd5f7f3bd9f7027e96bc6f8c048d517` |
| `04_Software/adore/profiles.py` | `fb42582b75e9055506d0fbd930970553658c375b80e181a69fece10e3c7659b1` | `4f59f79914278bfdb338ad23c14249f19ce0cc156e1766cf970b8cfbfbb93e71` |
| `04_Software/adore/web/app.py` | `fc47af2bd912745542ba2844cc084fb7faa097696188faf47c984d563ecc2525` | `5c7480480958184371df4be37e729e8f7b7feb6279047682e75a3be9d3f152b9` |
| `04_Software/adore/wizard.py` | `45a204fd24f8e661fa9aa52809ee3e19bceaee3fd8c2aae2390c138beff147ad` | `d78d1ea263c56b8f2d744f31cc312b030195b41512778e0df74635a199e225a2` |
| `04_Software/tests/test_web_enrollment.py` | `5bf3a0c8fa2255be10c993b6d7cb6138d3125d8ead186cb3d82e0b7de76cc686` | `5bf3a0c8fa2255be10c993b6d7cb6138d3125d8ead186cb3d82e0b7de76cc686` |
| `04_Software/tests/test_web_errors.py` | `9e02036c7a784dffcb005ecf55e0baebdb4a3a93bf36da39e03721067f371c39` | `2dfd89667cd5d181ff7e39a5b147212a69dcc9f3db4d15be02ffed065a858db4` |
| `05_SoftwareDocu/Component_Profiles.md` | `e8b22f56caca2cb86e9e6db7a4be75eb9a2933143a14775786b7c5571d746b12` | `70259abc658dd84cc3421e91fc69874c3dbbea477ad4b9965d7274b80818fb23` |
| `05_SoftwareDocu/Component_Web_API.md` | `4da056d455dbc7e71c3f142e38d1923b9206ffed9cd50ab4a4c63b85917e196b` | `ae3ca9aed28e960cc7447fc052445a5d0cc19373c1ec6cd8946cba4f9f9a703d` |
| `05_SoftwareDocu/Component_Wizard.md` | `cda3715dfdb158c558f353fae90cd27b308de32e001f04ff16b8cecaab5023f0` | `7684aa48d1ec149280e887b87731c538b36752abbde268203ede892cdd1df0cc` |
| `CHANGELOG.md` | `08900480278601b8552fc67e75f465815bf7cac1509cac45d5d41f9a9e0a61af` | `d59c69d6eebba8e78cb43f54222f666c45dba5c4ae8737e3392ab73cd383b9f3` |

The delta hash is the Git patch relative to b6903f5 for tracked files, or full
new-file bytes. Shared documents stage only these issue 6 deltas. Whole-tree staging
is forbidden. Recheck HEAD, protected files and candidate hashes before publication.

## Separate workflow records

- `.agentic/requirements/data/REQ-DATA-70e5e3bb.toml`
- `.agentic/requirements/data/REQ-DATA-d893df33.toml`
- `.agentic/requirements/functional/REQ-FUNC-3d8f6f5e.toml`
- `.agentic/requirements/functional/REQ-FUNC-e8e0e304.toml`
- `.agentic/requirements/reliability/REQ-REL-c598b075.toml`
- `.agentic/requirements/security/REQ-SEC-61fb8552.toml`
- `.agentic/specs/REQ-REL-c598b075.md`
- `.agentic/tasks/ISSUE-6-initial-ownership.md`
- `.agentic/tasks/TASK-8265e125.md`

## Protected initial entries

- `.agentic/requirements/ux/REQ-UX-0713852d.toml` — identical initial hash/absence
- `.agentic/requirements/ux/REQ-UX-257ab3f0.toml` — identical initial hash/absence
- `.agentic/requirements/ux/REQ-UX-8031b8eb.toml` — identical initial hash/absence
- `.agentic/requirements/ux/REQ-UX-955615bd.toml` — identical initial hash/absence
- `.agentic/requirements/ux/REQ-UX-9a8b409d.toml` — identical initial hash/absence
- `.agentic/requirements/ux/REQ-UX-aa5e358e.toml` — identical initial hash/absence
- `04_Software/adore/web/static/assets/DDP_Engineering_logo_dark-BgzND1ZS.png` — identical initial hash/absence
- `04_Software/adore/web/static/assets/index-BHRcXEB7.js` — identical initial hash/absence
- `04_Software/adore/web/static/assets/index-CDZ3eQGu.css` — identical initial hash/absence
- `04_Software/adore/web/static/assets/index-DxNytJps.css` — identical initial hash/absence
- `04_Software/adore/web/static/assets/index-eXaOMm5B.js` — identical initial hash/absence
- `04_Software/adore/web/static/index.html` — identical initial hash/absence
- `04_Software/web/e2e/dashboard.spec.ts` — identical initial hash/absence
- `04_Software/web/e2e/shell.spec.ts` — identical initial hash/absence
- `04_Software/web/src/App.tsx` — identical initial hash/absence
- `04_Software/web/src/DashboardShell.tsx` — identical initial hash/absence
- `04_Software/web/src/Presentation.tsx` — identical initial hash/absence
- `04_Software/web/src/assets/DDP_Engineering_logo_dark.png` — identical initial hash/absence
- `04_Software/web/src/i18n.ts` — identical initial hash/absence
- `04_Software/web/src/styles.css` — identical initial hash/absence
- `04_Software/web/tests/shell.test.mjs` — identical initial hash/absence
- `05_SoftwareDocu/Component_Web_Frontend.md` — identical initial hash/absence
