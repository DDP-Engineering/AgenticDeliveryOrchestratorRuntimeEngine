<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-SEC-553ebd62 — Give each run its own egress proxy and network

## Behavior

In `allowlist-proxy` egress mode every run has an executor container
`<slug>-run-<run ID>`, one egress proxy container and one internal egress
network. Their names are derived from the executor container name `E`:

1. `S` is the runtime-safe form of `E`: every run of characters outside
   `A-Za-z0-9_.-` becomes `-`, then leading and trailing `-`, `.` and `_` are
   removed (`run` when nothing is left).
2. **Bounded part** for a limit `L`: when `len(S) <= L` it is `S` unchanged.
   Otherwise it is the first `L - 11` characters of `S` with trailing `-`,
   `.` and `_` removed, then `-`, then the first 10 lowercase hexadecimal
   characters of the SHA-256 digest of `E` encoded as UTF-8.
3. **Proxy name** = bounded part with `L = 50`, then `-egress-proxy`
   (at most 63 characters).
4. **Network name** = `<network prefix>-` + bounded part with `L = 48`.
5. Provisioning (network create, executor `--network`, proxy run/start and
   connect) and reaping (`remove_egress`) use only these names.
6. Names that fit their limit are the same as before; only cut names change.

## Names of earlier builds

Earlier ADORE builds simply cut a long `S` to 50 (proxy) or 48 (network)
characters. ADORE does not recognise such old cut names: provisioning never
creates or reuses them, and neither reaping nor `adore cleanup` removes them.
An operator removes leftovers of an earlier build by hand with the container
runtime CLI (01_Documentation/Recovery_And_Maintenance.md).

For each target executor `adore cleanup` may remove its per-run proxy and
network names, except any name that a retained executor or any other existing
executor container (listed under `<slug>-run-`, proxies excluded) also
derives. If that listing fails, cleanup removes no proxy or network in that
pass.

## Data / interface

- `ContainerManager.cleanup_orphan_containers(prefix, targets, retained)`,
  `cleanup_egress_proxies(targets, retained)` and
  `cleanup_egress_networks(targets, retained)` derive the per-run names. Proxy
  candidates are listed by the `-egress-proxy` suffix, because a bounded
  per-run proxy name of a long slug no longer starts with `<slug>-run-`;
  networks are listed by their prefixes.
- `ContainerManager.list_executors(prefix)` lists executor containers without
  proxy containers (a proxy name often starts with the executor prefix but is
  not an executor).
- No configuration, command or report change.

## Examples

- `E = adore-run-x`: proxy `adore-run-x-egress-proxy`, network
  `adore-egress-adore-run-x` (unchanged).
- `E = adore-run-gitea-dpasare-2026_Networked_Intelligent_Lab_Orchestrator-26`:
  proxy `adore-run-gitea-dpasare-2026_Networked-bdeedb3462-egress-proxy`
  (62 characters: the 39-character cut ends in `_`, which is removed) and
  network `adore-egress-adore-run-gitea-dpasare-2026_Networke-bdeedb3462`. Run
  27 gets `...-6ce0f44c60` in both names.
- A 36-character slug: `E = examplex-digital-delivery-agent-prod-run-gitea-dpasare-alpha-9`
  gives proxy `examplex-digital-delivery-agent-prod-ru-1cb1a4a1e2-egress-proxy`
  (63 characters), which cleanup still finds.
- Two projects `dpasare/2026_Networked_Intelligent_Lab_Orchestrator` and
  `dpasare/2026_Networked_Intelligent_Lab_Other` get different proxy and
  network names.
- Cleanup of project A's done run leaves an old cut proxy or network of an
  earlier build in place.

## Acceptance

- Automated tests cover the examples, provisioning of a second long-named run,
  reaping, and the cleanup rules for per-run names, including a failed listing.

## Assumptions and open decisions

- Ten hexadecimal characters (40 bits) make an accidental clash between two
  executor names on one host negligible.
- 63 characters keep the proxy name a valid DNS label.
