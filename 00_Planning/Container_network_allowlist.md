# ADORE Container Egress Allowlist Plan

## Summary
Implement a generic, runtime-project-agnostic egress control for ADORE executor containers. Keep today’s behavior as `open` for supervised pilots, add `none` for offline/pre-provisioned runs, and add `allowlist-proxy` for unattended operation. The feature must work through the existing container runtime abstraction: Docker, Podman, and WSL-wrapped Docker/Podman.

## Key Changes

### Config Contract
Add a nested `[container.egress]` config section:

```toml
[container.egress]
mode = "open" # open | allowlist-proxy | none
allowlist = []
no_proxy = ["localhost", "127.0.0.1", "::1"]
proxy_image = "adore-egress-proxy:1.0.0"
proxy_port = 3128
network_prefix = "adore-egress"
```

Rules:

- `open`: current behavior, no network restrictions.
- `none`: executor container starts with `--network none`.
- `allowlist-proxy`: executor has no direct internet; it reaches HTTP/HTTPS through an ADORE-managed proxy container.
- `allowlist` entries are generic hostnames, exact or wildcard, for example `gitlab.example.com`, `api.openai.com`, `*.pythonhosted.org`.
- No runtime-project-specific hosts are hardcoded in code or examples except generic placeholders.
- `allowlist-proxy` requires a non-empty allowlist.
- Reject schemes, paths, shell metacharacters, empty entries, and invalid hostnames.
- Keep the current default: missing `[container.egress]` means `mode = "open"`.

### Isolation Behavior
Extend the container layer generically:

- Add an ADORE proxy image under `docker/`, based on Squid or another small HTTP CONNECT-capable proxy.
- Generate the proxy allowlist config from the runtime-project profile at provision time.
- For each run in `allowlist-proxy` mode:
  - create an internal per-run network, for example `<network_prefix>-<safe-run-id>`;
  - start a per-run proxy container with normal outbound access;
  - connect the proxy container to the internal network with alias `adore-egress-proxy`;
  - start the executor container only on the internal network;
  - inject `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, and lowercase equivalents into the executor container/exec environment.
- For `none` mode:
  - add `--network none`;
  - do not inject proxy env.
- For `open` mode:
  - preserve current argv and behavior.
- Cleanup must remove executor container, proxy container, and per-run network; `adore cleanup` must also sweep orphan proxy containers/networks.

### Deployment Guardrails
Update deployment scripts so unattended installs fail closed by default:

- If installing Task Scheduler/systemd and `egress.mode = "open"`, fail unless an explicit override is passed:
  - Windows: `-AllowOpenEgress`
  - Ubuntu: `--allow-open-egress`
- For `allowlist-proxy`, verify the proxy image exists; Ubuntu may build it, Windows should print the exact build command if absent.
- Supervised manual `adore run --once` remains allowed with open egress.

### Documentation
Update operator and component docs:

- Configuration reference: explain `[container.egress]`, modes, allowlist syntax, examples.
- Setup guide: add when to use `open`, `allowlist-proxy`, and `none`.
- Docker README: document proxy image build and runtime verification.
- Deployment docs: document unattended egress guardrails.
- Isolation component doc: document proxy/network lifecycle.
- Changelog: add under `Unreleased`.

## Test Plan

Add offline unit tests:

- Config accepts default/missing egress section as `open`.
- Config accepts valid `none` and `allowlist-proxy`.
- Config rejects empty allowlist for `allowlist-proxy`.
- Config rejects invalid allowlist values: URL with scheme, path, whitespace, shell characters, empty strings.
- `open` mode preserves existing `docker run` argv.
- `none` mode adds `--network none`.
- `allowlist-proxy` creates network, starts proxy, connects proxy, starts executor on internal network, injects proxy env.
- Proxy/network failures raise `IsolationError`.
- Cleanup removes orphan executor containers, proxy containers, and egress networks.
- WSL-wrapped runtime prefixes all network/proxy commands correctly.
- Podman `run_args` such as `--userns=keep-id` still land correctly.

Add live verification script support:

```bash
EGRESS_MODE=allowlist-proxy \
ALLOWLIST="example.com" \
ALLOWED_URL="https://example.com" \
DENIED_URL="https://github.com" \
./verify-runtime.sh
```

Expected:

- allowed URL succeeds;
- denied URL fails;
- `open` still succeeds broadly;
- `none` cannot reach internet.

## Assumptions

- Implement `allowlist-proxy` with HTTP/HTTPS proxy semantics; non-proxy-aware protocols such as SSH are out of scope for v1.
- Exact and wildcard domain allowlists are enough for v1; no CIDR/IP allowlists unless later requested.
- Proxy is ADORE-managed and generic; runtime projects only provide allowlist entries in their profile.
- Docker path must be live-verified first. Podman must share the same code path and tests; if live Podman verification exposes runtime-specific gaps, document them instead of hardcoding project behavior.
- Follow repository rules: update tests, docs, changelog, component docs, and Python/file `@version` markers for touched implementation files.
