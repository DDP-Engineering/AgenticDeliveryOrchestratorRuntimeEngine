# TASK-c9a9e72d diagrams

Illustrates `## Design` in `TASK-c9a9e72d.md`. The Design text is authoritative.

Node map: added = `OPENCODE_PERMISSION_POLICY`, `managed_opencode_config`;
changed = `local_environment`, `LocalBackend.__init__`; unchanged = `local_policy`,
`preparation (config plan)`, `Orchestrator`, `local_probe`, `[local].environment`,
`OpenCode native command`, `executor-config directory` (filesystem, created at run time).

## Structure

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    classDef removed stroke-dasharray:4 3
    plan["preparation (config plan)"] --> policy["local_policy"]
    orch["Orchestrator"] --> backend["LocalBackend.__init__"]:::changed
    probe["local_probe"] --> backend
    backend --> policy
    policy --> env["local_environment"]:::changed
    backend --> env
    env ==> helper["managed_opencode_config"]:::added
    env ==> perm["OPENCODE_PERMISSION_POLICY"]:::added
    explicit[("[local].environment")] --> env
    backend ==> dir[("executor-config directory")]
    backend --> cmd["OpenCode native command"]
```

## Sequence

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant B as LocalBackend.__init__
    participant E as local_environment
    participant F as executor-config directory
    participant C as OpenCode native command
    O->>B: construct for local profile
    B->>E: build environment (default executor opencode)
    E-->>B: XDG_CONFIG_HOME, OPENCODE_DISABLE_CLAUDE_CODE, OPENCODE_PERMISSION
    alt XDG_CONFIG_HOME is the managed path
        B->>F: mkdir(parents, exist_ok)
        F-->>B: directory or OSError / not a directory
        B-->>O: LocalExecutionError on failure (no launch)
    end
    O->>C: launch gate with the environment
```

## State

Not drawn: the design adds no lifecycle, status field or state transition.
