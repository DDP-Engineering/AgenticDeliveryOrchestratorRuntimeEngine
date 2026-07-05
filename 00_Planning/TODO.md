## Two honest gaps worth fixing later (I'd fold them into the metrics phase)

io/output.jsonl is overwritten by each gate — right now you always see the current/last gate's stream, not an archive of all six. Per-gate archiving (output-intake.jsonl, …) is a small change.
The orchestrator's own stdout isn't persisted by ADOR itself — fine interactively and under systemd/journald, but a rotating .ador/ador.log would make --once-from-Task-Scheduler runs auditable too.

===================================

## Implement for podman
   VERIFIED 2026-07-04 (podman 4.9.3 rootless, Ubuntu-24.04/WSL2): 17/17 on
   04_Software/docker/verify-runtime.sh (which mirrors every runtime CLI
   call ADOR makes; docker baseline also 17/17). FINDING: rootless podman
   needs `--userns=keep-id` - container uid 1000 (ador) otherwise maps to a
   subuid that cannot write the bind-mounted worktree ("Permission denied"
   on the first file the executor creates). IMPLEMENTED as [container]
   run_args = ["--userns=keep-id"] (validated config option, inserted after
   `run --detach`; regression-tested). Benign note: `sleep infinity` ignores
   SIGTERM so podman warns before SIGKILL on stop (~10 s; docker behaves the
   same silently). PILOT COMPLETE 2026-07-05: ticket #47 conducted END TO END
   on rootless podman -> draft MR !30 (agent-ready -> 6 gates, incl. one
   invariant self-correction retry + one delivery merge-conflict fix -> merge
   origin/develop -> preflight -> push feature/ador-47 -> draft MR). Two
   podman/docker PARITY BUGS found live and fixed with regression tests:
   (a) ensure_volumes - `podman volume create` errors on an existing volume
   (docker idempotent); now tolerates "already exists" [isolation.py
   _EXISTS_MARKERS]. (b) force_rmtree - `uv sync` inside the Linux container
   makes `.venv/lib64 -> lib`, a reparse point Windows scandir refuses
   (WinError 1920); now drops the link entry directly [util.py]. Verdict:
   podman is runtime-equivalent to docker for ADOR (set runtime = podman +
   run_args = ["--userns=keep-id"]). NB the earlier #46 attempt was blocked
   only by the TARGET-REPO TMPDIR trap below - which #47's own change fixes.

## how the ADOR will be deployed? Scripts?
   DONE 2026-07-04: 04_Software/deploy/ - install-ubuntu.sh (+ ador.service
   systemd template) and install-windows.ps1 (Task Scheduler: loop at logon
   or repeating --once). See deploy/README.md and Component_Deployment.md.
   Note: deployment does NOT change the egress posture - the allowlist-proxy
   decision below still gates unattended running.

## Create interface for PI Agent and Qwen Code
   PI: CODE DONE 2026-07-05. Executors refactored to a shared
   FileProtocolExecutor base; `PiExecutor` added; `build_executor` selects
   opencode|pi from `[executor] default` (no engine change); wizard offers pi;
   config.example + Dockerfile (pi npm package) + docs updated; 4 pi unit
   tests (suite 217, ruff clean); a `default = "pi"` config validates and the
   factory returns PiExecutor (verified). PENDING LIVE SPIKE (cannot run pi
   here - not installed): (1) build the executor image with
   `@earendil-works/pi-coding-agent` and confirm it runs; (2) `pi -p --mode
   json` runs the `.agentic` CLI non-interactively + commits; (3) pin the
   session-header schema and find a token-usage field (usage is 0 until then);
   (4) PROJECT TRUST - Pi loads its `.pi` agentic-guard + skills only after the
   project is trusted (`ctx.isProjectTrusted()`); ADOR must pre-trust the
   worktree for headless runs, else the guard does not load (container
   isolation still blocks remote writes). Find/verify the non-interactive
   trust mechanism. Qwen: same pattern once PI is proven (trivial subclass).

## A fail-fast tool check — a small planned improvement: [container] required_tools = ["make", "tflint", ...] verified at provision (one which exec per tool), so a missing binary fails in 2 seconds with a clear message instead of surfacing mid-delivery through a model-driven fix loop. Tonight's make-shaped detour is exactly what that check prevents

## Put promts for LLM in external files

## Can we package the app as an executable for windows / app package for UBUNTU?

## For the docker container creation - can we have like a procedure where the user at repo setup, creates an reference image that then is used by the workflow?

===================================

## CONTAINER NETWORK EGRESS — SECURITY DECISION (before any unattended running)

Finding (verified live 2026-07-04): the run container has FULL outbound internet.
`curl https://github.com` from inside the container returns HTTP 200. This is what
lets `uv sync` / `npm ci` / `tflint --init` pull dependencies at runtime (the design
relies on runtime dependency resolution), but it is unrestricted.

Risk: with open network an autonomous/unattended executor could exfiltrate the
repo or secrets, pull a compromised dependency (supply chain), or be steered by a
prompt-injection in a ticket/comment (which feeds back into the prompt on resume)
to fetch and run something. `env_keys` limits WHICH secrets are in the container;
network is the egress path for whatever is there.

Three postures:

- Open (today): install anything. Highest risk. Crawl-phase supervised pilots only.
- Allowlist proxy (RECOMMENDED for walk/production): docker egress locked to
    approved registries only (pypi, npm, the GitLab host, tflint/terraform plugin
    sources). `uv sync`/`npm ci` still work; "reach anything" is removed. Even a
    compromised prompt can't egress to an unapproved host. Implement as a
    [container] config addition (network_mode / egress_allowlist), not a redesign.
- No network + pre-provisioned: deps resolved at image build / container warm,
    cache volumes mounted read-only at run. Lowest risk, highest assurance.

Decision: open is acceptable for the current supervised pilot; MOVE TO ALLOWLIST
PROXY before unattended running. Add to the security sign-off list. (Recorded in
Setup_And_Credentials / prereq report as well when written up.)

-----------------------------------

tflint failure ROOT CAUSE (fixed 2026-07-04): NOT a plugin-init problem. The WSL2
Docker daemon injects the host WSL user's HOME/identity into every container -
inside the run container HOME=/home/dpasare and whoami=dpasare, even though the
image user is `ador` (/home/ador). tflint's bundled ruleset runs as a go-plugin
subprocess keyed on HOME; a non-existent home failed its cold handshake. This
silently threatened ALL HOME-based caches (uv, npm, opencode staged auth). Fix:
force HOME=/home/ador — image ENV plus ADOR's injected container env (which wins
over the daemon leak via the existing --env/WSLENV path). Lesson: a binary being
present is not the same as being usable; the required_tools check should verify
usability (e.g. `tflint --version` exit 0 in the container env), not just presence.

Per-project executor images: the current Dockerfile is monolithic (one target
repo). When a second project arrives, split into Dockerfile.base (python/uv, node,
git, opencode, glab/gh, user) + Dockerfile.<project> (that repo's gate toolchain,
ideally FROM the project's own CI image so "passes in container" == "passes in
CI"). Each project gets its own config.toml + .ador store; per-store lock lets
multiple ADOR instances coexist on one host.

Teardown race on WSL (observed at the done-leg, 2026-07-04): removing the
worktree immediately after `docker rm -f` can fail with ENOSYS ("Function not
implemented") because the container's 9P bind-mount on the directory has not
fully released yet; seconds later everything succeeds. The run still ends
correctly (`done`; failure only logged), but a husk directory can remain.
RESOLVED 2026-07-05: `_teardown` now retries worktree removal with backoff
(delays 1/2/4s, ~7s ceiling) ONLY on the transient mount-race signatures
(_TEARDOWN_RACE_MARKERS: ENOSYS "function not implemented", EBUSY, ENOTEMPTY)
via the injectable `self.sleep` seam - a real error is never retried, and if
the mount is genuinely stuck the husk is still left for `ador cleanup` (no
regression). Native docker/Linux succeeds on the first try (no sleeps).
Backstop unchanged: `ador cleanup` + reparse-point-safe force_rmtree sweeps
any husk that does survive. Regression-tested (transient->retry->success;
real-error->no-retry).

-----------------------------------

TMPDIR-in-worktree breaks go-plugin tools in containers on Windows hosts
(found by podman pilot #46, 2026-07-05; affects docker IDENTICALLY - probed
both): the target repo's Makefile exports TMPDIR := $(CURDIR)/.tmp, i.e.
into the bind-mounted worktree; on a Windows host that mount is 9P/drvfs,
which does not support unix sockets (Errno 95); tflint's ruleset runs as a
go-plugin child that creates its socket in TMPDIR -> instant death ->
"failed to negotiate handshake" -> make lint-infra red -> INV-4 blocks
validation. Latent since 2026-06-25 (commit 407a1ec in cockpit-gcp);
pilot #45's gate runs never exercised this leg. Fix belongs in the TARGET
repo: make the TMPDIR relocation Windows-host-only (ifeq ($(OS),Windows_NT))
or point it at a socket-capable path when inside a container. ADOR-side
lesson recorded in docker/README.md: repos must not force TMPDIR into the
worktree; a bind-mounted worktree cannot host unix sockets on Windows hosts.
FIXED 2026-07-05: ADOR itself conducted the fix as ticket #47 -> draft MR
!30 (Makefile: wrap the TMPDIR/TMP/TEMP relocation in
ifeq ($(OS),Windows_NT), and drop a now-redundant inline TMPDIR=/tmp
override on the tflint call). Pending human review/merge of !30.

-----------------------------------

Prompt quality — gate output not surfaced: the .agentic CLI writes failure detail
to evidence files, not stdout, so the delivery-fix prompt's "Output tail" is often
empty and the executor gets a vague "check failed (exit N)". Feed the relevant
evidence/report content into the fix prompt so the executor knows WHAT failed.
