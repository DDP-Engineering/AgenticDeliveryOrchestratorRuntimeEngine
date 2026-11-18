# Settings scope, limits and uniformity review

Status: approved domains implemented locally; targeted verification recorded below. No AEGIS, commit, push or deployment.

Date: 2026-11-18. Baseline: ADORE 0.20.0, commit `6d24e72e2b0342f6536f2170a85bdb5d117f3aa6`.

## Purpose and boundaries

Use this inventory to agree which configuration rules should be shared, which bounds
should change and which accepted settings should disappear. It describes the inspected
code, not a proposed replacement configuration. Proposed decisions below are deliberately
separate from current behavior.

- The review itself changed no code or deployed data. The user subsequently authorized
  local implementation of the approved domains below; DCP changes remain out of scope.
- No migration, compatibility reader, automatic reset or schema-version increment is proposed.
- Keep bounded autonomous execution. Distinguish product limits, provider restrictions,
  browser precision, transport bounds and practical machine capacity.
- Scope does not imply editability: a per-project value can be operator-owned and read-only
  in the browser. A centrally stored record can still be associated with one project.
- A missing explicit maximum is not an unlimited-execution option. Parser, transport,
  storage, OS and provider constraints still exist.

## Sources of truth inspected

| Source | Relevant responsibility |
|---|---|
| [config.py](../04_Software/adore/config.py) | Dataclass defaults, `validate_config`, `validate_budgets`, provider rules and branch naming |
| [chatgpt.py](../04_Software/adore/chatgpt.py) | `MAX_STAGE_SECONDS = 3000` and ChatGPT authorization strategy |
| [pi_providers.py](../04_Software/adore/pi_providers.py) | Model IDs, thinking levels, custom endpoint and web-search choices |
| [web/app.py](../04_Software/adore/web/app.py) | Enrollment API bounds, `_setting_domain`, candidate edits, accounts and audit policy |
| [implementation_settings.py](../04_Software/adore/web/implementation_settings.py) | Browser/API collection domains and safe integer bounds |
| [executor_configuration.py](../04_Software/adore/web/executor_configuration.py) | Atomic provider/model/endpoint edits |
| [settings_batch.py](../04_Software/adore/web/settings_batch.py) | Reviewed settings batches, maximum 100 edits |
| [web/store.py](../04_Software/adore/web/store.py) | Account, preference, audit and price persistence validation |
| [settingKeys.json](../04_Software/web/src/settingKeys.json) | Frontend setting-key inventory; presence alone does not mean editable or effective |
| [implementationSettings.ts](../04_Software/web/src/implementationSettings.ts) | Frontend duration and collection validation |
| [Configuration Reference](../01_Documentation/Configuration_Reference.md) | Operator semantics, reserved settings and edit boundaries |
| [Component Orchestrator](../05_SoftwareDocu/Component_Orchestrator.md) | Runtime budgets, saved execution configuration and checkpoint behavior |

Recheck these sources against HEAD before implementation; this is a dated planning baseline.

## 1. Scope and application of changes

| Configuration area | Scope | Application / ownership |
|---|---|---|
| Forge, repository and labels | Project | Project config and repository connection |
| Executor provider, model, thinking and internet | Project | Existing jobs retain saved execution settings; new defaults apply to new jobs |
| Backend, container image, runtime, preparation and local environment | Project | Some values are operator-owned; environment changes use dedicated guarded flows |
| Polling, concurrency, readiness, clarification, recovery and review | Project | Concurrency is per project, not one installation-wide pool |
| Budgets | Project, measured per job | Current project budgets are reread before subsequent attempts; consumption is retained |
| AEGIS/Direct selection | Job override over project default | Manual start chooses the workflow; Retry retains the saved workflow and conversation |
| Worktree, state and metrics paths | Project configuration on the server | Paths are not global merely because the same disk is shared; several are read-only in web Settings |
| Audit retention | Installation | Shared web audit policy |
| Accounts and roles | Installation | Project grants associate a user with authorized projects |
| Language, theme, ticket body presentation | User | Account preferences, not project settings |
| Model price records | Centrally administered, keyed by project/executor/model/date | Not a single installation-wide price applied to every project |
| Service address, port, installation home, host policy and native execution delegation | Server/operator | Outside ordinary project Settings |

Built-in defaults are code defaults, not an editable global profile inherited dynamically
by every project. Do not introduce global overrides as an incidental consequence of
uniform validation.

An in-flight executor retains its timeout. Budget edits do not reset consumed work or
restart a failed job. Stage-specific timeout overrides take precedence over the common
attempt timeout and are not part of the budget-only edit exception. Most non-budget
changes require the normal idle/edit boundary. Administrators can apply a reviewed
budget-only batch while jobs are settled in clarification, subject to existing guards.

## 2. Numeric limits: pre-change baseline

All rows in this section are project-scoped. Unless stated otherwise, numbers must be
whole numbers. “No explicit maximum” refers to the general configuration validator,
not to all entry points. Section 3 lists additional enrollment limits.

| Key | Minimum | Maximum in general validation | Built-in default / meaning |
|---|---:|---|---|
| `budgets.per_gate_timeout_seconds` | 1 s | 3000 s for `chatgpt`; otherwise no explicit maximum | 1800 s; one executor attempt |
| `workflow.stage_timeout_overrides.<stage>` | 1 s | 3000 s for `chatgpt`; otherwise no explicit functional maximum | Empty map; falls back to common attempt timeout |
| `budgets.max_wall_clock_seconds` | 1 s | No explicit maximum | 3600 s; cumulative active work, excluding human waits |
| `budgets.max_iterations` | 1 | No explicit maximum | 20 executor launches |
| `budgets.max_files_touched` | 1 | No explicit maximum | 120 changed files |
| `budgets.max_cost_usd` | 0 | No explicit maximum; must be finite | 5 USD; 0 disables the reported-cost cap |
| `polling.max_concurrent_runs` | 1 | No explicit maximum | 1 project execution place |
| `polling.poll_interval_seconds` | Greater than 0 | No explicit maximum | 60 s |
| `polling.poll_jitter_seconds` | 0 | No explicit maximum | 5 s |
| `clarification.max_rounds` | 1 | No explicit maximum | 3 human question/answer rounds |
| `clarification.answer_timeout` | Positive duration; 1 s in the whole-second editor | No explicit functional maximum | `72h`; accepts seconds or `s`, `m`, `h`, `d` duration notation |
| `recovery.max_stage_failures` | 1 | No explicit maximum | 3 |
| `recovery.max_transient_retries` | 1 | No explicit maximum | 3 |
| `recovery.retry_backoff_seconds` entries | 0 s | No explicit maximum in core; see collection bounds below | `[5, 30, 120]` |
| `review.max_review_rounds` | 1 | No explicit maximum | 5 additional rounds; initial implementation is excluded |
| `execution.preparation_step_timeout_seconds` | 1 s | 1800 s | 300 s |
| `execution.preparation_total_timeout_seconds` | 1 s | 3600 s | 900 s |
| `execution.preparation_max_attempts` | 1 | 3 | 2 |
| `container.egress.proxy_port` | 1 | 65535 | 3128 |

Important qualifications:

- Only the cost budget explicitly supports 0 as disabled. Zero is invalid for the other budgets.
- The wizard recommends 5400 active seconds, while the base dataclass default is 3600.
  `ProjectInput` also declares a launch default of 12; the documented CLI/web enrollment
  behavior uses 20. Resolve the effective route before changing any default.
- The ChatGPT 3000-second cap is an ADORE policy tied to a token acquired before an attempt
  and not refreshed during that attempt. It is not evidence of a universal model/provider
  execution limit. Do not remove it without reviewing the authorization lifecycle.
- The core polling comparisons do not consistently enforce strict integer types in the same
  way as budget validation. GUI integer metadata is not proof of equivalent TOML validation.
- Web duration/collection editors use JavaScript-safe integer values, at most
  `9007199254740991`; this is a transport/precision bound, not a useful execution budget.
- Reported-cost limits depend on available reported cost. Estimated UI prices should not
  be confused with a guaranteed provider spending cap.

## 3. Pre-change differences at project creation and browser transport

### Enrollment-only numeric maxima

The `ProjectInput` API currently adds the following maxima. They are not the same
as the general Settings/TOML validator's domain.

| Key | Enrollment interval | General project validation |
|---|---|---|
| `budgets.max_iterations` | 1..10000 | Integer >= 1, no explicit maximum |
| `budgets.max_wall_clock_seconds` | 1..31536000 s | Integer >= 1, no explicit maximum |
| `budgets.max_files_touched` | 1..1000000 | Integer >= 1, no explicit maximum |
| `budgets.max_cost_usd` | 0..1000000 USD, finite | Finite number >= 0, no explicit maximum |
| Ready and approval labels | 1..120 characters | Different, less uniformly bounded label checks |
| Custom endpoint URL | At most 512 characters | URL syntax validation without the same explicit length bound |

The `_setting_domain` metadata supplies positive minima for the main numeric settings,
but its maximum map currently includes only preparation bounds and proxy port.
In particular, it does not advertise the conditional 3000-second ChatGPT timeout maximum.
The full backend validator can therefore reject a value that the input itself did not bound.

### Collection and request bounds

| Input | Current web/API bound | Core / other-channel difference |
|---|---|---|
| Azure `platform.work_item_types`, `platform.closed_states` | 1..32 unique entries; each 1..128 characters, trimmed, no controls | Do not assume every direct TOML path uses the identical collection helper |
| `executor.env_keys` | At most 32 unique names, `[A-Z][A-Z0-9_]{0,63}`; approved names at edit time | Core also forbids forge credentials; local execution has additional launch-variable exclusions |
| `recovery.retry_backoff_seconds` | Nonempty list, at most 1000 integers, each 0..9007199254740991 | Core requires a nonempty list of nonnegative integers without these same maxima |
| Complete stage timeout override map | Only `frame`, `specify`, `design`, `build`, `validate`; values 1..9007199254740991 | Provider-specific maximum still applies; inspect individual dotted-key edits too |
| Complete collection edit | Wire string at most 32768 characters in `set_collection` | A transport bound, not an independent runtime setting |
| Settings batch | 1..100 distinct, nonoverlapping edits | Guarded transaction shape, not a limit on total project configuration keys |
| Imported project TOML | 1..524288 characters in import input | Separate from the live setting value domain |
| Agent instruction | 1..4000 characters; no NUL or invalid Unicode; now/queued modes | Per-job action payload, not a project budget |

Do not copy an accidental wire limit into the product's semantic maximum without an
explicit decision. Conversely, alternate entry points must not bypass a chosen product rule.

## 4. Other project settings and constraints

These groups complete the inventory beyond the numeric fields. No claim is made that
every accepted key is editable in every screen.

| Keys | Current domain / restriction |
|---|---|
| `agent.name`, `agent.slug`, `agent.email` | Nonblank name; slug matches `[a-z][a-z0-9-]*`; email can be derived when omitted. Do not infer comprehensive email-address validation from the label |
| `platform.kind`, `platform.repo`, `platform.login` | GitLab/GitHub/Gitea/Azure DevOps; repository required; Gitea uses OWNER/REPO and optional tea login; login rejected for other adapters |
| `platform.organization`, `platform.project`, `platform.area_path` | Azure-specific scope validation; organization/project/area rejected on other adapters |
| `platform.work_item_types`, `platform.closed_states` | Azure lists; collection bounds in section 3 |
| `state.store_root` | Project state location; server-owned rather than an ordinary editable Settings section |
| `polling.mode`, `polling.poll_backoff`, `polling.quiet_hours` | `loop`/`once`, boolean backoff, valid HH:MM-HH:MM windows; CLI can override startup mode; web owns its scheduler |
| `readiness.require_acceptance_criteria`, `readiness.require_priority_label` | Booleans |
| `labels.lifecycle.*` | `ready`, `working`, `clarify`, `answered`, `review`, `failed`, `done`; nonblank and distinct from lifecycle/control peers |
| `labels.control.*` | `hold`, `exclude`; nonblank and distinct from lifecycle/control peers |
| `labels.selection.*` | `priority_high`, `priority_medium`, `priority_low`, `type_feature`, `type_bug`, `type_epic`; audit inconsistent nonblank/length checks rather than assuming one rule already exists |
| `executor.provider`, `executor.model`, `executor.thinking` | Catalog provider, `chatgpt` or `custom`; model ID 1..200 characters using allowed syntax; optional thinking must be supported for the exact provider/model; custom explicit thinking only `off` |
| `executor.internet`, `executor.web.search` | Boolean internet switch; search `exa`, `brave`, `tavily`, `none`; network restrictions apply to containers, not as a local-execution firewall |
| `executor.endpoint.base_url`, `executor.endpoint.api` | Custom provider only; HTTP(S) host URL without credentials/query/fragment; API is openai-completions, openai-responses, anthropic-messages or google-generative-ai |
| `executor.questions_file`, `executor.env_keys` | Questions exchange path is subject to safe-file operations; injected variables are names, not secret values; see section 3 |
| `execution.backend`, `execution.preparation` | `container`/`local`; reviewed preparation selection `path#job@full-commit`; preparation unsupported for local backend |
| `local.account`, `local.path` | Account is `current`; PATH override is plain text without controls; host delegation is operator-owned |
| `container.runtime`, `container.image`, `container.build_definition` | Docker/Podman, including accepted wrapped runtimes; web image reference is 1..255 allowed characters; build definition is safe manifest path pinned to a full commit |
| `container.system_packages` | Boolean; container backend only; managed mode restricts runtime options to preserve isolation |
| `container.run_args`, `container.runtime_env`, `container.required_tool_checks` | Single option tokens; string environment values with managed-name exclusions; nonempty simple tool commands without shell control operators |
| `container.selinux_relabel` | Accepted relabel modes only; private SELinux `Z` is not offered for shared clone mounts |
| `container.uv_cache_volume`, `container.npm_cache_volume` | Runtime cache-volume names; not an application-managed disk quota |
| `container.egress.allowlist`, `container.egress.no_proxy` | Safe hostname/wildcard/loopback entries as appropriate; not URLs or shell text |
| `container.egress.proxy_image`, `container.egress.network_prefix` | Nonblank proxy image; prefix begins alphanumeric and uses letters/digits/dot/underscore/dash |
| `worktree.repo_path`, `worktree.root` | Required clone/root paths; operator-owned environment |
| `worktree.branch_template`, `worktree.branch_rule` | At most 512 characters each; valid Git name; template supports slug/run_id/iid and requires job identity; regex evaluation is bounded to one second |
| `workflow.mode`, `workflow.default_kind`, `workflow.kind_labels` | Project mode auto/direct; valid AEGIS task kinds and nonblank label mapping; manual job selection takes precedence |
| `workflow.aegis_python` | Executable command with backend-specific validation; operator-owned/read-only in web Settings |
| `clarification.timeout_state` | `failed`/`stale` |
| `delivery.target_branch`, `delivery.reviewers`, `delivery.approval_label` | Nonblank target; reviewers 1..255 characters per entry without whitespace/controls/leading dash, Azure uses GUIDs; approval label distinct from lifecycle/control labels |
| `delivery.draft`, `delivery.remove_source_branch`, `delivery.require_human_approval`, `delivery.publish_checkpoints` | Booleans; publication never authorizes merging |
| `review.trigger`, `review.revise_label`, `review.on_pipeline_failure` | Trigger `label`; revision label; failed-pipeline action revise/notify/ignore |
| `metrics.enabled`, `metrics.capture_tokens` | Booleans |
| `metrics.db_path`, `metrics.export_jsonl`, `metrics.html_out` | Server-owned project paths; browser writes rejected; export/HTML paths omitted from normal Settings controls |

Azure tag names additionally reject semicolons. Provider connection fields are edited
atomically through the connection flow, not as independent scalar changes.

### Accepted but ineffective configuration

| Keys | Current status |
|---|---|
| `container.keep_parked`, `container.parked_ttl_mode`, `container.parked_ttl_seconds`, `container.parked_ttl_polls` | Reserved. A parked container is stopped and retained; these values do not implement automatic expiry or reclaim space |
| `reconcile.on_ticket_deleted`, `reconcile.on_ticket_closed`, `reconcile.on_trigger_removed` | Reserved. Current schema-1 behavior is fixed rather than selected by these values |

Recommendation to discuss: remove ineffective settings and their UI/help exposure instead
of making their validation look more consistent. Do not add compatibility aliases or
activate new cleanup behavior as an incidental cleanup of the settings catalog.

## 5. Installation and user domains

| Setting / action | Scope | Current limits / values |
|---|---|---|
| Audit retention days | Installation | GUI 0..36500; 0 is converted to no limit. API/store uses null or integer 1..36500 |
| Audit data limit | Installation | GUI 0..1024 MiB; 0 is converted to no limit. API/store uses null or integer 1..1073741824 bytes |
| Cost rates | Central records keyed by project/executor/model/effective date | 0..1000000 USD per configured token-rate unit; fixed-point text, at most 6 fractional digits |
| Language | User | en/fr/de/ro |
| Theme | User | light/dark/system |
| Ticket body mode | User | rendered/source |
| Username | Installation account | 1..64 characters; current name rule accepts alphanumeric characters and underscore |
| New/reset password | Installation account | Web paths bound new passwords to 8..1024 characters; sign-in accepts 1..1024 so validation differs intentionally by operation |
| Role | Installation account | admin/developer; last active administrator is protected |
| Project grants | User/project relationship | Explicit grants; account creation input allows at most 1000 project IDs |
| Repository credential input | Connection / project association | Browser server URL at most 512 characters; token 1..4096 characters; actual forge/key validity checked separately |
| Executor credential input | Project/model connection | Variable name 1..64; token at most 4096 characters; supported variable and operation semantics apply |
| Service bind / port / home | Server operator | CLI default loopback:8765; supported service entry point requires loopback binding and a TLS reverse proxy for remote access. DCP uses its separately managed TLS launcher |

The GUI's audit zero-to-null conversion is an intentional representation difference,
not evidence that zero should disable every project budget. Session lifetime, login
throttling and Pi startup timeouts are internal operational policies, not ordinary
user-editable project settings in this inventory.

## 6. Confirmed pre-change inconsistencies

| ID | Observation | Approved direction |
|---|---|---|
| S1 | Enrollment adds budget maxima absent from general validation | Choose one semantic domain per budget and reuse it for create/edit/import/CLI/runtime validation |
| S2 | ChatGPT timeout cap is enforced by backend but absent from numeric GUI maximum metadata | Expose the effective provider-dependent bound and show the reason before Save |
| S3 | Dataclass, API model and wizard defaults are not identical | Choose an intentional default or explicitly named recommendation; prevent silent route-dependent defaults |
| S4 | Collection size/precision bounds differ from TOML and individual edits | Separate product constraints from wire limits; make equivalent semantic edits validate identically |
| S5 | Some scalar comparisons accept types differently from strict budget checks | Adopt explicit types; reject booleans/fractions where a whole-second integer is required |
| S6 | Label and endpoint bounds differ between enrollment and later edits | Agree meaningful lengths and adapter exceptions, then reuse the same rules |
| S7 | Some accepted settings have no runtime effect | Decide removal; no compatibility or migration implementation |
| S8 | Browser metadata and backend validation are maintained separately | Derive field type, unit, domain and conditional bounds from a small shared core definition |
| S9 | Scope, editability and when a change takes effect are easy to confuse | Expose project/user/installation scope and current/new-job/next-attempt behavior consistently |
| S10 | Current-job and cumulative time limits cause different failures | Keep separate controls and evidence; make zero/disabled semantics explicit per field |
| S11 | Resource capacity is not the same as a config range | Do not advertise a large concurrency maximum as a machine capacity guarantee; decide whether an operator cap is needed |

## 7. Time and budget case study: VERA #317

On 2026-11-18 at approximately 01:21 Europe/Bucharest, the current attempt reached
its 1800-second timeout. The job then failed with `BUDGET_EXHAUSTED` because its
cumulative active work had reached the project's 7200-second budget. These were
configured job/project values, not the global maxima of ADORE.

Two Linux/PowerShell Electron acceptance repetitions had passed before that stop.
Ten modified files and the Pi conversation remained in place. The last published
checkpoint was `ee92d1a9`; passing checks did not themselves advance the conductor.

Policy questions to settle before changing limits:

- Are 30-minute attempts and the recommended total budget suitable for implementation,
  environment preparation, platform debugging and verification in one conversation?
- Should timeout end the attempt while preserving a checkpoint opportunity, and how should
  an interrupted/partial result be distinguished from completed implementation?
- Should exhaustion require an explicit budget increase and Retry, as it does now?
- How should users see cumulative consumption, remaining allowance and effective stage override?
- If longer ChatGPT attempts are desired, can authorization be refreshed safely within the
  existing conversation, or must the current 3000-second ceiling remain?

Changing checkpoint-on-timeout behavior or token refresh is separate product work,
not merely changing a validation constant. No automatic retry, budget increase or
job recovery is authorized by this document.

## 8. Approved decisions

Fill this table with agreed values before implementation. The following domains were approved by the user on 2026-11-18; implementation uses
`04_Software/adore/setting_limits.json` as the shared source.

| Topic | Proposed decision to evaluate | Agreed decision |
|---|---|---|
| Common attempt timeout | Select default/minimum/maximum and retain positive whole seconds | Approved; see exact domains below |
| ChatGPT conditional ceiling | Keep 3000 until authorization lifecycle supports a justified alternative | Approved; see exact domains below |
| Stage overrides | Same domain as common timeout; clearly visible precedence | Approved; see exact domains below |
| Cumulative active time | Choose default/max and decide whether an explicit disabled option is appropriate | Approved; see exact domains below |
| Launch/file/cost budgets | Agree maxima across all channels; retain or explicitly revise zero semantics | Approved; see exact domains below |
| Clarification/review/failure counts | Choose useful defaults and justified maxima rather than copying transport sizes | Approved; see exact domains below |
| Preparation limits | Confirm 1800/3600 seconds and 3 attempts meet intended installations | Approved; see exact domains below |
| Polling/concurrency | Confirm integer types, cadence minima and any operator capacity ceiling | Approved; see exact domains below |
| Audit retention | Keep zero in GUI/null in API or change deliberately; document units | Approved; see exact domains below |
| Ineffective settings | Remove, keep visibly reserved, or implement separately; prefer removal if unnecessary | Approved; see exact domains below |
| Existing project values outside newly agreed bounds | Operator edits identified data explicitly; no automatic conversion/reset | Approved; see exact domains below |

## 9. Suggested implementation sequence after approval

1. Agree the worksheet, especially disabled values, timeouts and project-versus-job semantics.
2. Introduce a small core description for the agreed numeric/enum domains and defaults.
   Reuse existing code; avoid a new generic configuration framework or a second schema engine.
3. Make core configuration, enrollment and web candidate validation consume those rules.
   Project field domains can depend on provider; transport limits stay named separately.
4. Generate GUI guidance from the same effective domain, including units and conditional maxima.
   Preserve human approval, edit boundaries and safe credential/environment handling.
5. Remove explicitly approved ineffective keys and update current documentation, four-locale
   help and release notes. Name operator deletions if current stored definitions change.
6. Run focused public-behavior checks for accepted/rejected boundaries, provider changes,
   create/edit/import parity and budget continuation. Prefer extending existing parameterized
   cases rather than creating duplicate suites for the same rules.
7. Inspect any affected DCP configuration explicitly before deployment. Preserve active jobs,
   worktrees, conversations and consumption; no silent data repair or broad reset.
8. Full suites, packaging, commits, pushes and deployment follow the user's separate gates.

Review is complete when each exposed setting has an identified scope, type, unit,
effective/default value, supported domain, zero/disabled meaning, edit owner and application
boundary, and intentional entry-point differences are documented instead of accidental.

## 10. Approved domains and implementation handoff

All intervals are inclusive; integer fields reject booleans and fractions. The total
budget is independent of the attempt timeout. Changing limits preserves consumed work;
an active attempt keeps its timeout. The source baseline tables above are historical,
not the new accepted domains.

| Setting | Approved default | Approved domain |
|---|---|---|
| Attempt timeout / stage overrides | 3000 s / inherit | 60..3000 s ChatGPT; 60..14400 s otherwise |
| Cumulative active work | 28800 s (8 h) | 60..604800 s (7 d) |
| Executor launches | 40 | 1..1000 |
| Changed files | 500 | 1..100000 |
| Reported-cost cap | 0 (disabled) | 0..1000000 USD, finite |
| Stage failures / transient attempts | 3 / 3 | 1..10 each |
| Retry schedule | 5, 30, 120 s | 1..10 entries, 0..3600 s each |
| Clarification rounds / wait | 10 / 7 d | 1..100 / 60 s..90 d |
| Additional review rounds | 5 | 1..20 |
| Preparation step / total / attempts | 900 s / 3600 s / 2 | 1..3600 s / 1..14400 s / 1..3 |
| Poll interval / jitter | 60 s / 5 s | 10..86400 s / 0..300 s |
| Concurrent jobs | 1 | 1..32, project-scoped |
| Labels | Existing role defaults | Trimmed, 1..120 characters, no controls |
| Custom endpoint URL | Unset | At most 2048 characters plus current URL rules |
| Reviewers | Empty | At most 100 names; current forge-specific name/GUID rules |
| Other text, audit, account, preference bounds | Unchanged | Current supported domains |

Remove all parked TTL options, `[reconcile]`, `review.trigger` and `local.account`.
Further inspection confirmed `clarification.timeout_state` is also ineffective: it is
removed under the authorized cleanup; expiry remains failed. Keep actual native account
identity checks. No new cleanup policy or automatic migration is introduced.

Implementation decisions: one shared numeric/string-cap resource; no new global
configuration layer, generic schema framework, token-refresh feature, timeout checkpoint
policy or automatic DCP recovery. Update four-locale help/release notes and current manuals.
Targeted public-boundary verification only; no full suite, commit, push or deployment.

Implementation verification: the provider-aware attempt/stage boundary cases, file-config
budget maxima, create/edit/import paths, retained-budget continuation and typed collection
editors were checked with focused Python and frontend selections. Four browser settings
journeys passed for clarification duration/rounds, retry delays and stage overrides. The
full suite was not run. Help and release notes were updated in all four locales. Before
future deployment, inspect retired keys in operator data and renew all affected native
plan copies/integrity evidence explicitly; removing a field alone is insufficient.
