<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-6e8cc2e7 diagrams

Illustrates `## Design` in `TASK-6e8cc2e7.md`. The Design text is authoritative.

## Structure

Node classes, from the Design edits:

| Node | Class | Design basis |
|---|---|---|
| `Orchestrator._conduct_task_impl` | changed | validate -> done trigger, revalidation route moves to done |
| `AegisClient.probe` | changed | `MINIMUM_SERIES = (0, 15)` |
| `aegis.STATUS_STAGES` | changed | names deliver itself for older journals; the pinned task decode refuses it |
| `aegis.FULL_STAGES`, `QUICK_STAGES`, `STAGE_STEP_FILES` | changed | 0.15.0 path tables, no deliver |
| `aegis.allowed_transition` | changed | done -> validate replaces deliver -> validate |
| `Orchestrator._strict_verification` | changed | expects done |
| `Orchestrator._validation_failure` | changed | done-stage task view |
| `Orchestrator._launch_stage`, `_stage_prompt` | changed | no close-out parameter; advance, log, pause wording |
| `Orchestrator._handoff_notice` | changed | names `brief` and the full task journal |
| `Orchestrator._publish`, `_publish_impl` | changed | push and MR/PR only, from done or publishing |
| `Orchestrator.retry`, `Orchestrator._enter_review` | changed | review, publication or conduct from done; review records the published candidate |
| `Orchestrator._published`, `RunState.published_fingerprint` | added | published candidate marker |
| `RunState.from_dict` | changed | checks the published fingerprint as a digest |
| `Orchestrator._invalidate_approval`, `_reconcile_review` | changed | no longer write `approved_product` |
| `Orchestrator.reset` | changed | refuses every target for a run recorded at deliver |
| `Orchestrator._conduct`, `_present_for_approval`, `_approval_ready`, `_reconcile_approval`, `_reconcile_runs`, `_push_branch`, `handoff`, `AegisClient._status_list`, `Forge.open_merge_request` | none | reused unchanged |
| `AegisClient.report`, `AegisClient.evolution` | removed | no caller remains |
| `Orchestrator._recover_done_publication` | removed | done is the approval state |
| `Orchestrator._approved_product`, `WorktreeManager.product_diff_fingerprint` | removed | no executor session after approval |
| `config.AEGIS_STAGES`, `implementation_settings.STAGES`, `implementationSettings.executionStages`, `settingHelp` stage timeout copy | changed | five stages |
| `RESETTABLE_STAGES`, `config.validate_config`, `implementation_settings.valid_collection`, `SettingsList`, `state._STAGES`, `jobs._journal`, `jobModel.stages`, `JobWorkspace.stageKeys` | none | unchanged; the last four keep deliver for history |

Conducting a task:

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    entry["Orchestrator._conduct, _conduct_task"] --> probe["AegisClient.probe"]:::changed
    probe --> status_list["AegisClient._status_list"]
    status_list --> status_stages["aegis.STATUS_STAGES"]:::changed
    entry --> conduct["Orchestrator._conduct_task_impl"]:::changed
    conduct -- "_transition_accepted" --> allowed["aegis.allowed_transition"]:::changed
    allowed --> tables["aegis.FULL_STAGES, QUICK_STAGES, STAGE_STEP_FILES"]:::changed
    conduct --> launch["Orchestrator._launch_stage"]:::changed
    launch --> prompt["Orchestrator._stage_prompt"]:::changed
    conduct --> strict["Orchestrator._strict_verification"]:::changed
    strict --> remediation["Orchestrator._validation_failure"]:::changed
    remediation --> launch
    conduct --> present["Orchestrator._present_for_approval"]
    conduct -.-> recover["Orchestrator._recover_done_publication"]:::removed
    handoff["Orchestrator.handoff"] --> notice["Orchestrator._handoff_notice"]:::changed
```

Approval, publication and retry:

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    poll["Orchestrator._reconcile_runs"] --> approval["Orchestrator._reconcile_approval"]
    poll --> review["Orchestrator._reconcile_review"]:::changed
    approval --> ready["Orchestrator._approval_ready"]
    ready --> invalidate["Orchestrator._invalidate_approval"]:::changed
    approval --> publish["Orchestrator._publish, _publish_impl"]:::changed
    publish --> push["Orchestrator._push_branch"]
    publish --> forge["Forge.open_merge_request"]
    publish --> enter["Orchestrator._enter_review"]:::changed
    enter ==> marker["RunState.published_fingerprint"]:::added
    publish -. "close-out sessions" .-> launch["Orchestrator._launch_stage"]:::changed
    publish -.-> report_evolution["AegisClient.report, AegisClient.evolution"]:::removed
    publish -.-> guard["Orchestrator._approved_product, WorktreeManager.product_diff_fingerprint"]:::removed
    publish -.-> invalidate
    publish -.-> recover["Orchestrator._recover_done_publication"]:::removed
    retry["Orchestrator.retry"]:::changed ==> published["Orchestrator._published"]:::added
    published ==> marker
    retry == "published candidate at done or publishing" ==> enter
    retry --> ready
    retry -- "approved, unpublished" --> publish
    retry -- "any other run" --> conduct_entry["Orchestrator._conduct"]
```

Stage vocabularies:

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    reset["Orchestrator.reset"]:::changed --> resettable["RESETTABLE_STAGES"]
    resettable --> full["aegis.FULL_STAGES"]:::changed
    validate_cfg["config.validate_config"] --> cfg_stages["config.AEGIS_STAGES"]:::changed
    valid_coll["implementation_settings.valid_collection"] --> impl_stages["implementation_settings.STAGES"]:::changed
    editor["SettingsList stage-timeouts editor"] --> exec_stages["implementationSettings.executionStages"]:::changed
    editor --> help_copy["settingHelp workflow.stage_timeout_overrides"]:::changed
    from_dict["RunState.from_dict"]:::changed --> state_stages["state._STAGES, keeps deliver"]
    journal_reader["jobs._journal"] --> event_stages["run-journal stage set, keeps deliver"]
    job_view["JobWorkspace.stageKeys"] --> job_model["jobModel.stages, keeps deliver"]
```

## Sequence

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant E as Executor session
    participant A as AEGIS CLI
    participant F as Forge
    participant H as Human
    O->>E: validate prompt (_launch_stage)
    E->>A: check --task TASK --strict --run, report
    E->>A: advance TASK (validate -> done)
    E-->>O: session exits
    O->>A: status TASK --json (stage done)
    O->>A: check --task TASK --strict --run
    O->>O: checkpoint, candidate fingerprint
    O->>F: remove approval label, post approval comment
    H->>F: add agent-approved
    O->>F: read ticket labels
    O->>O: fetch, compare target and fingerprint (_approval_ready)
    alt candidate and target unchanged
        O->>F: push branch, open or adopt MR/PR
        O->>O: enter review at stage done
    else candidate or target changed
        O->>F: remove label, post approval-invalidated comment
        O->>E: route prompt for the done task
        E->>A: advance TASK --to validate
        O->>E: validate prompt after target integration
    end
```

## State

```mermaid
stateDiagram-v2
    [*] --> frame
    frame --> specify: full path
    frame --> build: quick path
    specify --> design
    design --> build
    build --> validate
    validate --> build: return
    validate --> design: return, full path
    validate --> specify: return, full path
    validate --> done: advance, then ADORE strict check
    done --> validate: route without ADORE verification evidence, or remediation
    done --> build: remediation after a failed ADORE check
    done --> design: remediation, full path
    done --> specify: remediation, full path
    done --> [*]: approval, push, MR/PR, review
```
