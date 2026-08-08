<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE - Agentic Delivery Orchestrator & Runtime Engine

Current release: **ADORE 3.0.0**.

ADORE 3.0 is the completed hard break to the AEGIS 3.x grouped CLI and schema-3
governance contract. It has no AEGIS 1.x/2.x compatibility or migration layer.

This is the standalone repository for **Agentic Delivery Orchestrator & Runtime Engine**:
a service that selects eligible tickets from GitLab, GitHub or Gitea, guides an
executor agent (OpenCode, Pi, Codex, or Qwen) through governed AEGIS stages and,
after the required evidence is accepted, opens a **draft** merge/pull request
for human review.
A human still reviews and merges.

The repository keeps planning, operator documentation, tooling, implementation,
implementation notes, delivery material, and support files in separate
top-level folders.

The runnable Python package lives in `04_Software/`.

## Start Here

- New operators: [Getting Started](01_Documentation/Getting_Started.md).
- Credentials and the human merge boundary:
  [Security and Credentials](01_Documentation/Security_And_Credentials.md).
- Add a repository and its executor image:
  [Integrating a Runtime Project](01_Documentation/Integrating_A_Runtime_Project.md).
- Daily operation and recovery:
  [Operations Guide](01_Documentation/Operations_Guide.md) and
  [Recovery and Maintenance](01_Documentation/Recovery_And_Maintenance.md).
- Complete settings and command reference:
  [Configuration Reference](01_Documentation/Configuration_Reference.md) and
  [CLI Reference](01_Documentation/CLI_Reference.md).

For a deployment-ready runtime bundle, use the scripts in
[02_Tools](02_Tools/README.md); delivery artifacts are written to
[07_Delivery](07_Delivery/README.md).

## How ADORE Works

```text
forge ticket (eligible labels and readiness rules)
        -> orchestrator selects by configured priority and readiness
        -> isolates work (git worktree + container)
        -> starts one AEGIS 3.x run (`aegis run start <kind> [--quick]`)
        -> guides the executor stage by stage (thick conductor)
             intake -> alignment -> requirement -> design -> check ->
             implementation -> validation -> delivery      (quick: 4 stages)
             every fresh executor session starts from validated `run context`;
             executor follows AEGIS-owned reads and stage instructions;
             ADORE verifies objectively and closes the stage
        -> parks and asks on ambiguity (posts a comment, resumes on reply)
        -> AEGIS run complete -> integrate target, `aegis verify run`, push
        -> opens a DRAFT MR/PR, assigns a human reviewer
human reviewer -> approves and merges
```

## Design At A Glance

- **Forge-agnostic.** GitLab (`glab`), GitHub (`gh`) and Gitea (`tea`) sit
  behind one adapter interface, so the orchestrator logic never calls a
  platform CLI directly.
- **Executor-agnostic.** OpenCode, Pi, Codex, and Qwen are selectable through
  a configurable launcher.
- **AEGIS-governed.** ADORE 3.0 speaks exactly one governance contract, the
  AEGIS 3.x grouped CLI. AEGIS owns the stage pointer and the verification;
  ADORE reads it from `run status`, checks it against the declared sequence,
  and never guesses. No AEGIS 1.x support and no migration layer.
- **Context-led and fail-closed.** Every fresh executor session receives the
  bounded schema-1 `run context` bootstrap. ADORE reads run artifacts only
  through a contained, regular-file, size-bounded, strict-UTF-8 boundary and
  rejects corrupt, cross-run, or contradictory evidence.
- **Thick conductor, delegated approver.** The orchestrator drives one AEGIS
  stage at a time. AEGIS context owns the procedure; ADORE
  verifies objectively - stage readiness, `aegis verify run`, committed work -
  and issues `aegis stage close` itself. It never waives a blocker and never
  repairs AEGIS state: both escalate to a human with the exact command.
- **Truthful outcomes.** A waived failing check is accepted but never reported
  as passed; not-enforced and not-applicable checks remain neutral. An AEGIS
  run completed as `abandoned` is terminal and can never enter publication.
- **Human-gated delivery.** The orchestrator opens a draft MR/PR only; it never
  merges. Merge stays a human decision.
- **Portable.** Targets Ubuntu 22+ and Windows 11; the orchestrator is written
  in portable Python and runs the executor in a container.

## Repository Layout

- `00_Planning/` - architecture notes, design decisions, and roadmap.
- `01_Documentation/` - canonical operator, configuration, and CLI
  documentation.
- `02_Tools/` - repository-level helper scripts, release checks, and runtime
  packaging.
- `04_Software/` - the runnable orchestrator Python package.
- `05_SoftwareDocu/` - implementation notes and deeper technical contracts.
- `07_Delivery/` - generated runtime bundles, packaging, and release material.
- `09_Others/` - miscellaneous support material and local reference files.

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license. See `LICENSE.txt` for
full license details.

SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
