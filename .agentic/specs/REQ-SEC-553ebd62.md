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

## Old cut names (clean break)

Before this contract a long `S` was simply cut to 50 (proxy) or 48 (network)
characters. Such **old cut names** are never created or reused by
provisioning and never removed by reaping. A run whose executor container was
created under an old cut network must be finished or re-provisioned before the
upgrade; otherwise its restarted executor stays on the old network without a
reachable proxy.

`adore cleanup` treats both forms as derived names of a run: for each target
executor it may remove the new and the old cut proxy/network names, except any
name that a retained executor or any other existing executor container (listed
under `<slug>-run-`, proxies excluded) also derives in either form. If that
listing fails, cleanup removes no proxy or network in that pass.

## Data / interface

- `ContainerManager.cleanup_orphan_containers(prefix, targets, retained)`,
  `cleanup_egress_proxies(targets, retained)` and
  `cleanup_egress_networks(targets, retained)` derive both name forms. Proxy
  candidates are listed by the `-egress-proxy` suffix, because a bounded
  per-run proxy name of a long slug no longer starts with `<slug>-run-`;
  networks are listed by their prefixes.
- `ContainerManager.list_executors(prefix)` lists executor containers without
  proxy containers (an old cut proxy name derives itself and would otherwise
  keep itself).
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
- Cleanup of project A's done run keeps the old cut proxy that project B's
  existing executor also derives.

## Acceptance

- Automated tests cover the examples, provisioning of a second long-named run,
  reaping, and the cleanup rules for old cut names, including a failed listing.

## Assumptions and open decisions

- Ten hexadecimal characters (40 bits) make an accidental clash between two
  executor names on one host negligible.
- 63 characters keep the proxy name a valid DNS label.
