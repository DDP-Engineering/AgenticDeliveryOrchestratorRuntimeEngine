<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Web Endpoint Probe

## 1. Purpose

Test a configured local OpenCode model from the executor's container network,
so API-host connectivity cannot be mistaken for execution readiness.

## 2. Responsibilities

`probe_endpoint` verifies that the selected model, compatible provider override,
and URL agree. It uses the project's executor image and egress policy in a
disposable container, sends a bounded streamed chat-completions request with a
required tool call, and reports a redacted reason. It never runs AEGIS or
publishes repository changes.

## 3. Implementation Overview

The API supplies a bounded injectable command runner. The probe first inspects
the executor and optional egress-proxy images locally, preventing image pulls.
It creates a random temporary container with the configured egress policy,
executes a Python standard-library HTTP probe inside it, and force-removes the
container and proxy resources in a `finally` block. HTTP redirects are refused.
When `NODE_EXTRA_CA_CERTS` names a file in the executor image, the probe uses
that same file through `SSL_CERT_FILE` for HTTPS verification. It checks the
configured OpenCode request timeout is a bounded integer.

## 4. Dependencies

`adore.isolation.ContainerManager`, the project container runtime and image,
and Python inside that image. An allowlisted credential environment variable
is passed as a process environment value, never as a command argument.

## 5. Inputs And Outputs

Inputs are the validated project configuration and bounded runner. The result
contains `context=executor-container`, `model`, boolean `ready`, and a stable
redacted `reason`; endpoint responses, URL, and credentials are not returned.

## 6. Data Contracts

OpenCode's configured `provider/model` must identify an
`@ai-sdk/openai-compatible` provider whose model and `baseURL` match the ADORE
endpoint. Success requires an HTTP 200 event stream containing a tool-call
delta. Missing images, credentials, redirects, incompatible responses, timeouts,
and runtime failures yield an explicit false result.

## 7. Workflow Integration

The administrator's project readiness action invokes the probe only after
configuration validation. Existing host-tool checks remain host-context checks;
the model result is separately identified as executor-container evidence.

## 9. Validation And Tests

`tests/test_web_readiness.py` exercises success and incompatible stream output
through a fake container runtime. Live acceptance still requires a prepared
executor image and an internal OpenAI-compatible endpoint.

## Native execution contract

Native endpoint checks use non-secret local.environment and owned Python with approved provider values in memory. Context is executor-local. Local host readiness leaves model connectivity untested until explicit checking.

See [Local execution](../01_Documentation/Local_Execution.md) and
[Local execution component](Component_Local_Execution.md). Focused proof:
`04_Software/tests/test_local_execution.py`.
