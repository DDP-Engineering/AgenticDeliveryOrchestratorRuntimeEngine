<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Container timeout correction — delivery candidate

Validated; awaiting explicit local commit approval. No push, PR or merge.

Reported container timeouts now stop the verified immutable resource before output
retention. A later command resumes that same container with installed dependencies
and files intact. Network/package authority stays separate. Unconfirmed recovery
blocks active admission and becomes a terminal infrastructure failure; operator
cancellation wins. Failed active admission requires inspection and a fresh controller.
Native targets and preparation replay keep their existing contracts.

Source binding: `c6f5f0b5308283c92d2df57b9781d3c51241485fadde2b0053147b4874a5b5af`,27 paths, unchanged after both round1
approvals and final proof. Comparison tree: `2ff029eddeea063ed1e23b872c7b45b6402ead2b`.
Immutable record snapshot: `refs/adore/validated/TASK-f6de6c0b`.
The source map uses raw verified working bytes; manifest records reversible Git
line-ending normalization for the stored tree. Journal/manifest/report are mutable
records outside the source binding.

Final `python .agentic/aegis.py check --task TASK-f6de6c0b --strict --run --json`:
exit0,1349.85s;2239 Python passed,8 existing skips,1 upstream Starlette/httpx
warning;Ruff passed;226 Chromium passed;strict0 errors,182 nonpromoted advisories,
22 notes. No new skipped test or unresolved review finding. Existing unrelated
coverage/layout/journal debt and bounded derived-asset scan advisories remain.

Real disposable Docker acceptance reproduced then eliminated the leftover writer
and IO-open failure. Same ID/image, deferred restart and normal user were retained.
An additional network-none fixture installed a local system package through apt,
kept its root-owned payload after timeout/restart and denied unrelated sudo id.
All disposable resources were removed. Separate actual issue25 evidence proves
that the agent itself installed Chromium libraries/fonts and retained them on retry.
No live Podman or Azure-tenant acceptance is claimed here.

DEVIATION build: scoped file bound28→30 covers two pre-existing runtime doubles
updated to provide truthful identity/lifecycle receipts. Product checks were not
relaxed. The final design keeps failed active admission quarantined rather than
adding a new same-backend absence-confirmation protocol.

The proposed local change includes exactly the30 paths below, including records.
It excludes the independent Azure implementation, unrelated baseline work, host
credentials and the earlier Git delivery records. Preserve the real index/branch;
private baseline ancestry must not be pushed automatically.

- `.agentic/context/environment.md`
- `.agentic/context/project.md`
- `.agentic/knowledge/execution.md`
- `.agentic/knowledge/orchestrator.md`
- `.agentic/requirements/data/REQ-DATA-62052e16.toml`
- `.agentic/requirements/functional/REQ-FUNC-bff135e2.toml`
- `.agentic/requirements/reliability/REQ-REL-d8e08cca.toml`
- `.agentic/requirements/reliability/REQ-REL-ea593cbb.toml`
- `.agentic/specs/REQ-FUNC-bff135e2.md`
- `.agentic/tasks/TASK-f6de6c0b.candidate.json`
- `.agentic/tasks/TASK-f6de6c0b.md`
- `.agentic/tasks/delivery_TASK-f6de6c0b.md`
- `.agentic/tasks/diagram_TASK-f6de6c0b.md`
- `01_Documentation/Operations_Guide.md`
- `04_Software/adore/execution.py`
- `04_Software/adore/orchestrator.py`
- `04_Software/adore/release_notes.toml`
- `04_Software/adore/web/static/assets/index-BjR5GEqz.js`
- `04_Software/adore/web/static/assets/index-C6PbXIfO.js`
- `04_Software/adore/web/static/index.html`
- `04_Software/tests/test_container_timeout.py`
- `04_Software/tests/test_orchestrator.py`
- `04_Software/tests/test_preparation_lifecycle.py`
- `04_Software/web/src/help/content/de/jobs.md`
- `04_Software/web/src/help/content/en/jobs.md`
- `04_Software/web/src/help/content/fr/jobs.md`
- `04_Software/web/src/help/content/ro/jobs.md`
- `05_SoftwareDocu/Component_Execution.md`
- `05_SoftwareDocu/Component_Orchestrator.md`
- `CHANGELOG.md`
