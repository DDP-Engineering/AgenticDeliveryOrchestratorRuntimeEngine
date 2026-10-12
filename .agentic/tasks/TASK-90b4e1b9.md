<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-90b4e1b9 - Turn How ADORE works into a localized in-app help center

stage: done
type: change
path: full
interaction: autopilot
requirements: REQ-UX-d4ab6f8d, REQ-UX-77d9307c, REQ-REL-6e6f465b, REQ-UX-8031b8eb
parent:
branch: task/adore-web-interface
base: b2ccb847867a095a564e2ddd3182a09a35c0ba95
opened: 2026-10-12

## Done checklist (current stage)

- [x] red records, anchor, implementation, focused green, links, docs, check clean
- [x] `stage: validate`

## Frame

Problem: How ADORE works is a six-term dropdown glossary; users have no in-app guide to the interface or to the ADORE workflow (registering a repository, project settings, choosing/defining an executor, preparing tickets for automatic pickup, job lifecycle). STATED: "Trebuie sa fie ca un fel de help file - care sa prezinte atat interfata - dar si workflow-ul adore: cum se inregistreaza un repo, setari pe repo, cum se alege / defineste un executor, cum trebuiesc setate tichetele pentru a fi preluate automat, etc." Choices: full /help page; all 10 topics now; all 4 languages.
Desired outcome: a localized help center at /help with ten topics, search and an outline, contextual help links on key pages, glossary folded in as a topic, content checked for locale parity and links, and an agent rule to keep it current.
Actors: administrators and developers.
Primary scenario: press How ADORE works -> /help (What ADORE does) -> table of contents -> "Tickets for automatic pickup" -> labels table; on a project's Tickets view the ? link opens that topic in a new tab.
Examples: 01_Documentation (Getting_Started labels/ticket preparation, Web_Interface, Project_Executor_Images, Local_Execution, Integrating_A_Runtime_Project).
Counterexamples: operator docs in 01_Documentation stay the canonical CLI/operator reference; no new runtime dependency; no backend change; About unchanged.
In scope: route /help[/<topic>], HelpCenter page, Markdown subset renderer, help content (10 topics x 4 locales), HelpLink on Tickets/Add project/Settings, removal of the dropdown glossary, node + e2e tests, AGENTS.md/CLAUDE.md rule, docs, requirements, release notes.
Out of scope: rewriting 01_Documentation; screenshots in help; full suite (STATED: at the end).
Constraints: content must match real behavior (sourced from 01_Documentation and code); no raw HTML rendering; offline bundle unchanged in dependencies.
Success signals: focused tests green; DCP shows the help center.
Evidence: OBSERVED Presentation.tsx DeliveryGlossary (6 terms), routes.ts parseRoute/formatRoute, App currentRoute/applyRoute, jobs.spec/shell.spec glossary tests, shell.test.mjs glossary keys.
Assumptions: none. Unknowns: none. Decision-blocking questions: answered (placement, scope, languages).
Proposed behaviors: B1 help center (REQ-UX-d4ab6f8d); B2 contextual links (REQ-UX-77d9307c); B3 content parity and maintenance (REQ-REL-6e6f465b); B4 glossary as a topic (REQ-UX-8031b8eb revised).
Path and reason: full - new user-visible feature, new content set and a new repository rule.

## Requirement coverage

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| Help center | B1 | REQ-UX-d4ab6f8d (new) | /help, topics, search, outline, locale | unknown topic falls back to /help; no match message | e2e help.spec, node help/routes | D1, D2, D3 |
| Contextual help | B2 | REQ-UX-77d9307c (new) | Tickets, Add project, Settings links | opens a new tab, page state kept | e2e help.spec, node help | D4 |
| Content parity and upkeep | B3 | REQ-REL-6e6f465b (new) | four locales, same outline/links | parity, subset or link breach fails | node help.test | D2, D5 |
| Glossary | B4 | REQ-UX-8031b8eb (revised) | six terms in the Glossary topic | approval on forge, human merge | node help.test, e2e | D3 |

## Design

- D1 Routing: Route `{ view: "help"; topic?: HelpTopic }`, `/help` and `/help/<topic>` (unknown topic -> null -> overview normalisation as today); Page "help" with helpTopic state in App; both roles; section anchors use `#<slug>`.
- D2 Content: `src/help/content/<locale>/<topic>.md` for topics overview, interface, projects, settings, executors, tickets, jobs, statistics, administration, glossary; loaded with `import.meta.glob(..., { query: "?raw", eager: true })` in `src/help/content.ts`. `src/help/markdown.ts` (pure) parses the subset: first-line `# Title`, `##`/`###` with slug ids, paragraphs, `-` and `1.` lists, pipe tables, fenced code, `>` notes; inline `**bold**`, `` `code` ``, `[text](/internal)`; anything else is an error in tests and plain text at runtime. Rendered to React elements, never HTML strings.
- D3 HelpCenter page: table of contents (topic titles from each file), search (accent/case-insensitive over title and text, lists matching topics), article with an On this page outline from `##` headings, internal links navigate in-app; the header How ADORE works button navigates to /help; the dropdown DeliveryGlossary and its six definition keys are removed and its content becomes the Glossary topic.
- D4 HelpLink: small "?" link with an accessible name ("Help: <topic title>") opening `/help/<topic>` in a new tab (`target=_blank`, `rel=noopener`), placed in the Tickets toolbar, the Add project wizard step heading and the project Settings heading.
- D5 Checks and rule: tests/help.test.mjs (parity of outline/tables/link targets across locales, subset, link/anchor and route validity via parseRoute, contextual targets, glossary terms); AGENTS.md "Help content rules" + CLAUDE.md line + journal line `help: updated | none (<reason>)`; docs (Web_Interface.md, Component_Web_Frontend.md, knowledge), CHANGELOG, release notes.

## Log

- 2026-10-12 frame: scope accepted (localized in-app help center; user chose full page, all 10 topics, 4 languages); autopilot; full path; full suite deferred by the user.
- 2026-10-12 specify: 3 created (REQ-UX-d4ab6f8d, REQ-UX-77d9307c, REQ-REL-6e6f465b), 1 revised (REQ-UX-8031b8eb glossary placement); 0 retired.
- 2026-10-12 design: see ## Design D1-D5.
- 2026-10-12 build red: REQ-UX-d4ab6f8d, REQ-REL-6e6f465b, REQ-UX-8031b8eb command=`node --test tests/help.test.mjs` exit=1 (ERR_MODULE_NOT_FOUND src/help/markdown.ts); REQ-UX-d4ab6f8d, REQ-UX-8031b8eb command=`node --test tests/routes.test.mjs tests/shell.test.mjs` exit=1 (2 failed: /help routes, help i18n keys); REQ-UX-d4ab6f8d, REQ-UX-77d9307c command=`npx playwright test e2e/help.spec.ts` exit=1 (no How ADORE works link, no contextual help links); expected missing behavior=help center absent.
- 2026-10-12 build green: node 93/93 (help.test 9 incl. parity of all four locales, routes, shell); tsc + e2e typecheck clean; e2e help+shell+jobs+tickets+enrollment+settings+dashboard+portable+import+transfer 139/139 after two fixes (the ? link's aria-label matched getByLabel("Repository") in the wizard -> named by visually hidden text; the Settings heading wrapper overflowed at 390px in de -> min-width 0). Content: 10 English topics drafted from 01_Documentation and the code by three agents and reviewed, then translated to fr/de/ro by three agents with a structural parity check; glossary intro corrected in all locales. Built route /help[/<topic>], src/help (topics, markdown, content, README), HelpCenter + HelpLink, contextual links (Tickets toolbar, Add project step heading, project Settings heading), header How ADORE works link; dropdown DeliveryGlossary, its CSS and the seven definition keys removed (REQ-UX-d4ab6f8d, REQ-UX-77d9307c, REQ-REL-6e6f465b, REQ-UX-8031b8eb).
- 2026-10-12 help: updated (new help center, 10 topics x 4 locales).
- 2026-10-12 release-notes: added (New / Help entry); `python 02_Tools/check_release_notes.py --since b2ccb84` ok.
- 2026-10-12 noted unrelated pre-existing catalog corruption (handoff status labels with literal '?' in de/fr/ro i18n.ts, since 0669199); offered as a separate task, not changed here.
- 2026-10-12 deployed to DCP as 90ba (backend + static; /help, /help/tickets, /help/glossary 200).
- 2026-10-12 validate review round 1: implementation-quality PASS with findings -> HTML/image checks now scan every line outside code fences; links are links only for in-app targets (SAFE_LINK; `//host` and schemes become plain text with an issue; test rejects `//`); bold may not contain code or links and headings are plain text; unsupported headings and nested items render as text; article title is h2 (one h1 per page) with sections h3/h4 and focus moves to the title after a topic change; wide tables and code blocks are focusable regions. Spec-compliance FAIL -> (1) the quick-path sentence claimed returns to Specify/Design: corrected in all four jobs.md (full path: Specify, Design or Build; quick path: Build only, per aegis.py); (2) fr/de/ro help named seven settings the localized UI showed only as a help sentence -> added fr/de/ro labels (settingsCopy localizedSettingLabel, used in the Settings label chain) and a help test that the help uses them; also corrected the earlier Unreleased release note that claimed images are built from Settings. node 94/94; tsc clean; e2e help+settings+portable+shell 52/52 (help+shell+jobs+enrollment+tickets+portable 76/76 after the quality fixes); DCP 90bb.
- 2026-10-12 DEVIATION validate: added fr/de/ro labels for seven settings in the Settings UI (unrequested UI change) - needed so the localized help names settings exactly as the screen shows them; the alternative was help text naming help-sentence fallbacks.
- 2026-10-12 validate review round 2: implementation-quality PASS (lows applied: hash and focus read in the next frame after the address updates; scrollable tables/code are regions named after their section; doc comment moved back); spec-compliance FAIL - the change review chain lacked the new fr/de/ro setting names -> localizedSettingLabel added to the candidate review label chain too. node 94/94; tsc clean; e2e help+settings+shell+jobs 79/79; DCP 90bc (frontend).
- 2026-10-12 validate review round 3: spec-compliance PASS (review and list share the fr/de/ro names); implementation-quality PASS (round-2 notes applied, no new findings).
- 2026-10-12 validate final: `python .agentic/aegis.py check --task TASK-90b4e1b9 --strict` errors=0. DEVIATION validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by node 94/94, tsc (src + e2e), e2e help+shell+jobs+tickets+enrollment+settings+dashboard+portable+import+transfer 139/139 and, after review fixes, help+settings+shell+jobs 79/79, release-notes check ok. DCP 90bc.
- 2026-10-12 deliver: user tested on DCP ("e ok, commite local") and approved a local commit on task/adore-web-interface (no push, no PR).
- 2026-10-12 close-out: outcome is a repository-local commit (no push/PR); close-out rides in the delivery commit; stage done.

## Rulings


## Handoff

current: done
status: ready
next: none
must_read: .agentic/tasks/TASK-90b4e1b9.md
blockers: none

## Stage report


stage: deliver
result: completed
current: done
changed: How ADORE works opens a localized help center (/help, ten topics x four locales, search, outline, per-topic addresses), contextual ? links on Tickets, Add project and Settings, glossary as a topic; Markdown subset parser and checks; fr/de/ro labels for seven settings; AGENTS.md Help content rules, CLAUDE.md line; requirements, docs, CHANGELOG, release notes
evidence: node 94/94, tsc clean, e2e 139/139 (10 specs) and 79/79 after review fixes, release-notes check ok; DCP 90bc
issues: DEVIATION full suite deferred by user; DEVIATION fr/de/ro labels for seven settings added to the Settings UI; pre-existing '?' corruption in de/fr/ro handoff status labels offered as a separate task
next: none
needs_user: no
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-12)

- stage: deliver; type: change; path: full; branch: task/adore-web-interface
- requirements:
  - REQ-UX-d4ab6f8d - Open a localized help center from How ADORE works
  - REQ-UX-77d9307c - Link key pages to their help topic
  - REQ-REL-6e6f465b - Keep help content complete in every locale and current with the interface
  - REQ-UX-8031b8eb - Explain delivery vocabulary in every supported locale
- deviations: 2 recorded
  - validate: added fr/de/ro labels for seven settings in the Settings UI (unrequested UI change) - needed so the localized help names settings exactly as the screen shows them; the alternative was help text naming help-sentence fallbacks.
  - validate: full suite (`check --strict --run`) not run - user instruction to run it at the end of all refinements; covered by node 94/94, tsc (src + e2e), e2e help+shell+jobs+tickets+enrollment+settings+dashboard+portable+import+transfer 139/139 and, after review fixes, help+settings+shell+jobs 79/79, release-notes check ok. DCP 90bc.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base b2ccb84: 71 file(s) changed, 3233 line(s) added
- checks: errors=0 warnings=15 notes=22
- checklist: 2/2 done
