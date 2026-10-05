<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Issue 6 initial ownership boundary

Captured on 2026-10-05 before product edits. The newly created issue 6 journal is excluded to reproduce the exact initial status observed before task creation. All entries below belong to the pre-existing issue 5 candidate and are excluded from issue 6 delivery. TASK-7546e6dc remains at deliver, awaiting publication approval. Local HEAD and freshly queried remote task/adore-web-interface both equal 705e248ad24787e8f573aca477f36fdd4c6fd09f. No staged changes existed.

## Exact initial porcelain status

```text
 M .agentic/context/project.md
 M .agentic/knowledge/web-interface.md
 M 01_Documentation/Web_Interface.md
 D 04_Software/adore/web/static/assets/index-CDZ3eQGu.css
 D 04_Software/adore/web/static/assets/index-eXaOMm5B.js
 M 04_Software/adore/web/static/index.html
 M 04_Software/web/e2e/dashboard.spec.ts
 M 04_Software/web/src/App.tsx
 M 04_Software/web/src/i18n.ts
 M 04_Software/web/src/styles.css
 M 05_SoftwareDocu/Component_Web_Frontend.md
 M CHANGELOG.md
?? .agentic/requirements/ux/REQ-UX-0713852d.toml
?? .agentic/requirements/ux/REQ-UX-257ab3f0.toml
?? .agentic/requirements/ux/REQ-UX-8031b8eb.toml
?? .agentic/requirements/ux/REQ-UX-955615bd.toml
?? .agentic/requirements/ux/REQ-UX-9a8b409d.toml
?? .agentic/requirements/ux/REQ-UX-aa5e358e.toml
?? .agentic/tasks/TASK-7546e6dc.md
?? 04_Software/adore/web/static/assets/DDP_Engineering_logo_dark-BgzND1ZS.png
?? 04_Software/adore/web/static/assets/index-BHRcXEB7.js
?? 04_Software/adore/web/static/assets/index-DxNytJps.css
?? 04_Software/web/e2e/shell.spec.ts
?? 04_Software/web/src/DashboardShell.tsx
?? 04_Software/web/src/Presentation.tsx
?? 04_Software/web/src/assets/
?? 04_Software/web/tests/shell.test.mjs
```

## Expanded file inventory

| Path | Initial working-copy SHA-256 |
| --- | --- |
| `.agentic/context/project.md` | `a0a607779964ec53d761736693af2b0c228d49eb3f4be9999a29948fa371a280` |
| `.agentic/knowledge/web-interface.md` | `453b56ac61b61250f3e54364d557730788cbed517543ebb46ecf13a9f41da9b6` |
| `.agentic/requirements/ux/REQ-UX-0713852d.toml` | `8ea21711dc7ed3f5f9193684617dc4aad0e81adb11e4dd8ef54b0c184ac9c9f2` |
| `.agentic/requirements/ux/REQ-UX-257ab3f0.toml` | `ec09b4ba1ed4c25121ccdffa2d410be5c396df161323c64b712de699c5f257c6` |
| `.agentic/requirements/ux/REQ-UX-8031b8eb.toml` | `21ffa5e22094cced2b710d10e71b2c216f775c21e00b47a2f5872c16c425f29a` |
| `.agentic/requirements/ux/REQ-UX-955615bd.toml` | `ff7c057800c460e589ca7b81e370fe6f1dd212623e34dab9960a9b90857fe61c` |
| `.agentic/requirements/ux/REQ-UX-9a8b409d.toml` | `d510be97743670135b045fe3027b444fb3a8535817e5b72e07b74f1c80dd274d` |
| `.agentic/requirements/ux/REQ-UX-aa5e358e.toml` | `20a439e6fd15712bee56d4613fbfd66fecb0634fa09785aee603aea94d5a996b` |
| `.agentic/tasks/TASK-7546e6dc.md` | `fecf35986bdbcaa0c1137a1def7f84b9c36759fb9a7db85f22d28bfff5d81fd9` |
| `01_Documentation/Web_Interface.md` | `b29732025b9357ee0834f08a58e74afef8fdcd685937206309e366b9830969bb` |
| `04_Software/adore/web/static/assets/DDP_Engineering_logo_dark-BgzND1ZS.png` | `4957da4edf9aebf02dcb0e24823ff5f8d5ee524622773f4285c9e2261903c481` |
| `04_Software/adore/web/static/assets/index-BHRcXEB7.js` | `ed0237beb93e610f26b2c64971e6bee5ed8ee8b3e01d80dd71311bb8dca18c64` |
| `04_Software/adore/web/static/assets/index-CDZ3eQGu.css` | `ABSENT (tracked deletion)` |
| `04_Software/adore/web/static/assets/index-DxNytJps.css` | `cf835e33b3d68abae004d8dceefe4274b1c6886434730bd501c73788b21cb35c` |
| `04_Software/adore/web/static/assets/index-eXaOMm5B.js` | `ABSENT (tracked deletion)` |
| `04_Software/adore/web/static/index.html` | `793624b3dc1b4ab66dd2a4b904a847e9d98b0ad83caa52daa192ec18df88b0bf` |
| `04_Software/web/e2e/dashboard.spec.ts` | `b9194a1f4a42013df1aab037be9ce65490df0fc6fb917c8b32827f1767d7f997` |
| `04_Software/web/e2e/shell.spec.ts` | `94e5b73b448bb07b2ad43cffc75d8c5ace1a5aca008dbc21f3cb9c8064cf1674` |
| `04_Software/web/src/App.tsx` | `b2b31d29c7edf7d40c2efd4d534e21e16e58491128a21d4955b56876fded4a7a` |
| `04_Software/web/src/DashboardShell.tsx` | `feb236535caf6fc41d720058c6f4232d7828078b861c6d73da06732f754eb6b9` |
| `04_Software/web/src/Presentation.tsx` | `833baf9830c8a0221323cb808130062662122671fb272cb2ae1ded98fbe66ea7` |
| `04_Software/web/src/assets/DDP_Engineering_logo_dark.png` | `4957da4edf9aebf02dcb0e24823ff5f8d5ee524622773f4285c9e2261903c481` |
| `04_Software/web/src/i18n.ts` | `12f081eb37bd7c0ebaa2cae842bc13ce1471c117964414944994525fdc3ab795` |
| `04_Software/web/src/styles.css` | `9a637ca1f9d76451ff2ce4b6581e518cc650526b8ff96194f821c4bd6f3229db` |
| `04_Software/web/tests/shell.test.mjs` | `6e860e004a00d87e087ce41aa5a5becb528d901215fd273483a3953d77407eef` |
| `05_SoftwareDocu/Component_Web_Frontend.md` | `72ed0c1c92d3c433c3e17872ff54b5430c09fe5069582d79d21663480a47996c` |
| `CHANGELOG.md` | `e524d6a570c6cfb29a05ff97b2f9f92b0efe3d6d06b0ef260706614c0e01b166` |

Initial `git diff --binary HEAD` SHA-256: `a3b011c7925c0a15ae7bfbc476245c279940a056ba78c173462fcdf6e44dddd4`.

## Issue 6 ownership policy

Backend files and their tests are owned by issue 6. Frontend source, browser tests and bundled assets above remain issue 5-owned. Shared documents may gain separately inventoried issue 6 hunks while preserving initial content; retain an anchor-relative patch and exact scoped manifest before delivery. Never stage the whole working tree. Compare initial hashes before shared-document edits and excluded files at every stage boundary. Report concrete overlap before any change that would overwrite issue 5 work. Workflow records for issue 6 are separate files. Production frontend output remains issue 5-owned; isolated frontend validation output is ignored.

Provisional issue 6 authored inventory (19): adore/profiles.py, adore/wizard.py, adore/web/app.py, adore/web/store.py; tests/test_profiles.py, tests/test_wizard.py, tests/test_web_projects.py, tests/test_web_readiness.py, tests/test_web_import.py, tests/test_web_commands.py, tests/test_web_rbac.py (all under 04_Software); 05_SoftwareDocu/Component_Profiles.md, Component_Wizard.md, Component_Web_API.md; 01_Documentation/Web_Interface.md; .agentic/knowledge/profiles.md, wizard.md, web-interface.md; CHANGELOG.md. Knowledge pages count conservatively as authored files; requirements/specs/journals/ownership evidence count separately. Worker implementation/documentation or additional components require design-time scope/file-budget reconciliation before editing. Twenty-file limit is binding, not a target.
