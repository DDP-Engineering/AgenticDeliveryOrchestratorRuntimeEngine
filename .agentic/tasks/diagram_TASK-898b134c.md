# TASK-898b134c diagrams

Illustrates `## Design` in `TASK-898b134c.md`. The Design text is authoritative.

Node map: added = egress_policy, provider_hosts; changed = ExecutorConfig,
ContainerEgressConfig, pi_catalog, ContainerManager, PiExecutor, orchestrator,
probe_model_connection, probe_setup, Settings; unchanged = pi_rpc.

## Structure

```mermaid
flowchart LR
    classDef added fill:#e1f5ee,stroke:#0f6e56
    classDef changed fill:#faeeda,stroke:#854f0b
    exec_cfg["config.ExecutorConfig (internet, web.search)"]:::changed
    egress_cfg["config.ContainerEgressConfig (no mode)"]:::changed
    catalog["pi_catalog.json hosts"]:::changed
    hosts["pi_providers.provider_hosts"]:::added
    policy["config.egress_policy"]:::added
    manager["isolation.ContainerManager"]:::changed
    executor["launcher.PiExecutor"]:::changed
    orch["orchestrator"]:::changed
    probe["model_connection.probe_model_connection"]:::changed
    ready["web.app._probe_setup"]:::changed
    ui["web Settings Agent and model"]:::changed
    rpc["pi_rpc.run_pi_rpc"]
    catalog --> hosts
    exec_cfg --> policy
    egress_cfg --> policy
    hosts --> policy
    policy --> manager
    orch --> policy
    probe --> policy
    ready --> policy
    orch --> executor
    exec_cfg --> executor
    executor --> rpc
    ui --> exec_cfg
```

## Sequence

```mermaid
sequenceDiagram
    participant O as orchestrator
    participant C as config.egress_policy
    participant M as ContainerManager
    participant E as PiExecutor
    participant P as Pi (container)
    O->>C: egress_policy(config)
    C-->>O: allowlist-proxy + provider hosts (Off) / open (On)
    O->>M: provision(run, egress)
    M-->>O: container (proxy network when Off)
    O->>E: run_gate(prompt)
    alt internet On and search != none
        E->>M: cp web-search.json into agent dir
        E->>P: pi --mode rpc -e pi-web-access
    else internet Off
        E->>P: pi --mode rpc --append-system-prompt notice
    end
    P-->>E: RPC events
```

## State

Not drawn: the change adds no lifecycle or status transitions.
