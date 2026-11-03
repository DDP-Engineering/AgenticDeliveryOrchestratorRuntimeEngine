# TASK-c6b3c54f diagrams

Illustrates `## Design` in `TASK-c6b3c54f.md`. The Design text is authoritative.

Node map: added = `_native_tool_response`, `modelEvidence.ts`; changed =
`probe_model_connection` (local branch), `REASONS`, `ModelConnection.tsx`,
`ReadinessEvidence.tsx`; unchanged = `_native_response`, `local_probe`, `run_gate`,
`_RUNNER (container)`, `model-connection-test API`.

## Structure

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    api["model-connection-test API"] --> probe["probe_model_connection"]:::changed
    probe --> lp["local_probe"]
    probe --> gate["run_gate"]
    probe ==> tool["_native_tool_response"]:::added
    probe --> plain["_native_response (qwen)"]
    probe --> runner["_RUNNER (container)"]
    probe --> reasons["REASONS"]:::changed
    ui["ModelConnection.tsx"]:::changed ==> mc["modelEvidence.ts"]:::added
    ready["ReadinessEvidence.tsx"]:::changed --> api
    ui --> api
```

## Sequence

```mermaid
sequenceDiagram
    participant A as Administrator (UI)
    participant P as probe_model_connection
    participant G as run_gate (local_probe)
    participant X as Executor CLI (OpenCode/Pi/Codex)
    A->>P: Test AI connection
    P->>G: prompt "echo <tool nonce>, then reply <reply nonce>", timeout 90 s
    G->>X: configured command, job environment
    X-->>G: JSON events (shell call, final reply)
    G-->>P: exit code, bounded output
    P->>P: _native_tool_response -> ready / tool-call-failed / invalid-response
    P-->>A: closed evidence {executor, model, ready, reason}
```

## State

Not drawn: the design adds no lifecycle or state transition.
