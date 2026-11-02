#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
# @file    verify-runtime.sh
# @brief   Live verification pass for a container runtime (docker or podman).
# @details Mirrors, flag for flag, every runtime CLI call ADORE's
#          ContainerManager makes (adore/isolation.py) against a scratch git
#          repo + worktree: image inspect, volume create, run --detach with
#          the exact mount/env shape (bare `--env KEY` for secrets - values
#          only in the process environment, HOME inline), exec (identity,
#          tool USABILITY not just presence, git via GIT_DIR/GIT_WORK_TREE
#          with the commit visible host-side), inspect --format status,
#          stop/start (park/resume), ps --all --filter, rm --force, and
#          absent detection. A green pass means config.toml can point at
#          this runtime.
#          Run it ON the Linux side (an Ubuntu host, or inside the WSL
#          distro); the WSL command wrapping / path translation is
#          runtime-independent and already live-proven with docker.
#          Rootless podman note: on SELinux hosts (Fedora/RHEL) bind mounts
#          may additionally need :z/:Z labels - not needed on Ubuntu; a
#          finding here would be an ADORE config addition, record it.
# @usage   RUNTIME=podman ./verify-runtime.sh     (default: RUNTIME=docker)
#          RUN_ARGS="..." extra `run` option tokens, mirroring ADORE's
#          [container] run_args (rootless podman needs
#          RUN_ARGS="--userns=keep-id" - live finding 2026-07-04: without it
#          container uid 1000 maps to a subuid that cannot write the
#          bind-mounted worktree).
#          IMAGE=<tag> overrides the image (default
#          adore-executor-base:1.0.0); the default base image is built from
#          Dockerfile.executor-base in this directory if absent.
#          REQUIRED_TOOL_CHECKS="make --version;terraform --version" adds
#          runtime-project image checks. EGRESS_MODE=open|none|allowlist-proxy
#          verifies the new network posture; in proxy mode, ALLOWLIST is a
#          comma-separated hostname list and ALLOWED_URL / DENIED_URL prove the
#          proxy permits only the configured hosts.
#          SELINUX_RELABEL=off|shared mirrors [container] selinux_relabel; use
#          "shared" on an SELinux-enforcing host (Fedora/RHEL/CentOS Stream/
#          Rocky/Alma) so the bind mounts carry `z` exactly as ADORE sends
#          them. Verifying with "off" there fails on permission denied, which
#          is the real host behaviour, not a script defect.
# @author  Eng. Dan Dumitru Pasare
# @date    2026-09-18
# @version 0.6.0
# -----------------------------------------------------------------------------
# shellcheck disable=SC2015  # `check && ok || bad` is safe: ok is a bare echo
set -euo pipefail

# CONSTANTS (mount targets mirror adore/isolation.py CONTAINER_* constants)
RUNTIME="${RUNTIME:-docker}"
IMAGE="${IMAGE:-adore-executor-base:1.0.0}"
EGRESS_MODE="${EGRESS_MODE:-open}"
ALLOWLIST="${ALLOWLIST:-example.com}"
ALLOWED_URL="${ALLOWED_URL:-https://example.com}"
DENIED_URL="${DENIED_URL:-https://github.com}"
PROXY_IMAGE="${PROXY_IMAGE:-adore-egress-proxy:1.0.0}"
# Pinned in Dockerfile.executor-base; a different version fails the check.
EXPECTED_NODE_VERSION="v22.23.4"
EXPECTED_PI_VERSION="1.4.0"
EXPECTED_PI_WEB_ACCESS_VERSION="0.46.0"
PI_PREFIX="/opt/pi/lib/node_modules"
PI_CLI="${PI_PREFIX}/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
PI_GUARD="/opt/adore/pi/adore-guard.ts"
PI_AGENT_DIR="/home/adore/.adore-pi-agent"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="adore-verify-$$"
PROXY_NAME="${NAME}-egress-proxy"
EGRESS_NETWORK="adore-verify-egress-$$"
VOL_UV="adore-verify-uv-$$"
VOL_NPM="adore-verify-npm-$$"
SCRATCH="$(mktemp -d)"
read -r -a RT <<< "${RUNTIME}"
read -r -a EXTRA_RUN_ARGS <<< "${RUN_ARGS:-}"
# Mirrors [container] selinux_relabel: "shared" appends `z` to the HOST bind
# mounts (never the named cache volumes), which an SELinux-enforcing host needs
# before the container may read them. Without this the script would report a
# false failure on exactly the hosts that setting exists for.
SELINUX_RELABEL="${SELINUX_RELABEL:-off}"
case "${SELINUX_RELABEL}" in
    off)    BIND_SUFFIX="" ;;
    shared) BIND_SUFFIX=":z" ;;
    *) echo "error: SELINUX_RELABEL must be off or shared"; exit 1 ;;
esac

STEP=0
FAILURES=0

# LOCAL HELPERS
step() {
    STEP=$((STEP + 1))
    printf '%2d. %s ... ' "${STEP}" "$1"
}
ok()  { echo "OK"; }
bad() { echo "FAIL: $*"; FAILURES=$((FAILURES + 1)); }

cleanup() {
    "${RT[@]}" rm --force "${NAME}" >/dev/null 2>&1 || true
    "${RT[@]}" rm --force "${PROXY_NAME}" >/dev/null 2>&1 || true
    "${RT[@]}" network rm "${EGRESS_NETWORK}" >/dev/null 2>&1 || true
    "${RT[@]}" volume rm "${VOL_UV}" "${VOL_NPM}" >/dev/null 2>&1 || true
    rm -rf "${SCRATCH}"
}
trap cleanup EXIT

command -v git >/dev/null 2>&1 || { echo "error: git is required on this host"; exit 1; }
command -v "${RT[0]}" >/dev/null 2>&1 || { echo "error: '${RT[0]}' not found"; exit 1; }

echo "ADORE runtime verification: RUNTIME='${RUNTIME}', IMAGE='${IMAGE}'," \
     "RUN_ARGS='${RUN_ARGS:-}', EGRESS_MODE='${EGRESS_MODE}'," \
     "SELINUX_RELABEL='${SELINUX_RELABEL}'"
echo

# 1-2. runtime + image
step "runtime responds (${RT[0]} --version)"
"${RT[@]}" --version >/dev/null && ok || bad "runtime not usable"

step "image ${IMAGE} present (image inspect; build if absent)"
if "${RT[@]}" image inspect "${IMAGE}" >/dev/null 2>&1; then
    ok
else
    echo "absent - building (this takes a few minutes)"
    "${RT[@]}" build -f "${SCRIPT_DIR}/Dockerfile.executor-base" -t "${IMAGE}" "${SCRIPT_DIR}"
fi

if [ "${EGRESS_MODE}" = "allowlist-proxy" ]; then
    step "egress proxy image ${PROXY_IMAGE} present (image inspect; build if absent)"
    if "${RT[@]}" image inspect "${PROXY_IMAGE}" >/dev/null 2>&1; then
        ok
    else
        echo "absent - building"
        "${RT[@]}" build -f "${SCRIPT_DIR}/Dockerfile.egress-proxy" \
            -t "${PROXY_IMAGE}" "${SCRIPT_DIR}" >/dev/null && ok || bad "proxy image build"
    fi
fi

# 3. volumes (ContainerManager.ensure_volumes)
step "volume create x2"
"${RT[@]}" volume create "${VOL_UV}" >/dev/null \
    && "${RT[@]}" volume create "${VOL_NPM}" >/dev/null && ok || bad "volume create"

# 4. scratch repo + worktree + io dir (what WorktreeManager provides)
step "scratch git repo + worktree on the host"
git -C "${SCRATCH}" init -q -b develop repo
git -C "${SCRATCH}/repo" -c user.name=host -c user.email=host@local \
    commit -q --allow-empty -m "root"
git -C "${SCRATCH}/repo" worktree add -q -b verify-branch "${SCRATCH}/work" develop
mkdir -p "${SCRATCH}/io"
ADMIN_DIR="$(basename "$(sed 's/^gitdir: //' "${SCRATCH}/work/.git")")"
[ -n "${ADMIN_DIR}" ] && ok || bad "worktree admin dir not readable"

NETWORK_ARGS=()
PROXY_ENV_ARGS=()
if [ "${EGRESS_MODE}" = "none" ]; then
    NETWORK_ARGS=(--network none)
elif [ "${EGRESS_MODE}" = "allowlist-proxy" ]; then
    step "egress proxy network + proxy container"
    PROXY_CONF="${SCRATCH}/squid.conf"
    DOMAINS=""
    IFS=',' read -r -a ALLOWLIST_ITEMS <<< "${ALLOWLIST}"
    for host in "${ALLOWLIST_ITEMS[@]}"; do
        host="${host#"${host%%[![:space:]]*}"}"
        host="${host%"${host##*[![:space:]]}"}"
        [ -n "${host}" ] || continue
        if [[ "${host}" == \*.* ]]; then
            host=".${host:2}"
        fi
        DOMAINS="${DOMAINS} ${host}"
    done
    cat > "${PROXY_CONF}" <<EOF
http_port 3128
acl allowed_domains dstdomain${DOMAINS}
http_access allow allowed_domains
http_access deny all
access_log stdio:/var/log/squid/access.log
cache_log /var/log/squid/cache.log
coredump_dir /var/spool/squid
EOF
    "${RT[@]}" network create --internal "${EGRESS_NETWORK}" >/dev/null \
        && "${RT[@]}" run --detach --name "${PROXY_NAME}" \
            --volume "${PROXY_CONF}:/etc/squid/squid.conf:ro${BIND_SUFFIX/:/,}" \
            "${PROXY_IMAGE}" >/dev/null \
        && "${RT[@]}" network connect --alias adore-egress-proxy \
            "${EGRESS_NETWORK}" "${PROXY_NAME}" \
        && ok || bad "proxy setup"
    NETWORK_ARGS=(--network "${EGRESS_NETWORK}")
    export HTTP_PROXY="http://adore-egress-proxy:3128"
    export HTTPS_PROXY="${HTTP_PROXY}"
    export ALL_PROXY="${HTTP_PROXY}"
    export NO_PROXY="localhost,127.0.0.1,::1"
    export http_proxy="${HTTP_PROXY}"
    export https_proxy="${HTTP_PROXY}"
    export all_proxy="${HTTP_PROXY}"
    export no_proxy="${NO_PROXY}"
    PROXY_ENV_ARGS=(
        --env "HTTP_PROXY=${HTTP_PROXY}" --env "HTTPS_PROXY=${HTTPS_PROXY}"
        --env "ALL_PROXY=${ALL_PROXY}" --env "NO_PROXY=${NO_PROXY}"
        --env "http_proxy=${http_proxy}" --env "https_proxy=${https_proxy}"
        --env "all_proxy=${all_proxy}" --env "no_proxy=${no_proxy}"
    )
elif [ "${EGRESS_MODE}" != "open" ]; then
    bad "unknown EGRESS_MODE: ${EGRESS_MODE}"
fi

# 5. provision - the EXACT argv shape from ContainerManager.provision:
#    HOME inline (not a secret; must beat any daemon-injected value), all
#    other env as bare --env KEY with values ONLY in the process environment.
step "run --detach (mounts, workdir, bare --env secrets, HOME inline)"
export ADORE_VERIFY_SECRET="s3cret-$$"
export GIT_DIR="/adore/repo/.git/worktrees/${ADMIN_DIR}"
export GIT_WORK_TREE="/adore/work"
export GIT_AUTHOR_NAME="ADORE" GIT_AUTHOR_EMAIL="adore-bot@local"
export GIT_COMMITTER_NAME="ADORE" GIT_COMMITTER_EMAIL="adore-bot@local"
"${RT[@]}" run --detach ${EXTRA_RUN_ARGS[@]+"${EXTRA_RUN_ARGS[@]}"} \
    --name "${NAME}" \
    --volume "${SCRATCH}/repo:/adore/repo${BIND_SUFFIX}" \
    --volume "${SCRATCH}/work:/adore/work${BIND_SUFFIX}" \
    --volume "${SCRATCH}/io:/adore/io${BIND_SUFFIX}" \
    --volume "${VOL_UV}:/home/adore/.cache/uv" \
    --volume "${VOL_NPM}:/home/adore/.npm" \
    --workdir /adore/work \
    ${NETWORK_ARGS[@]+"${NETWORK_ARGS[@]}"} \
    --env "HOME=/home/adore" \
    ${PROXY_ENV_ARGS[@]+"${PROXY_ENV_ARGS[@]}"} \
    --env ADORE_VERIFY_SECRET \
    --env GIT_DIR --env GIT_WORK_TREE \
    --env GIT_AUTHOR_NAME --env GIT_AUTHOR_EMAIL \
    --env GIT_COMMITTER_NAME --env GIT_COMMITTER_EMAIL \
    "${IMAGE}" sleep infinity >/dev/null && ok || bad "run failed"
# The container snapshotted the env values at creation; unset them NOW so the
# host-side git checks below do not inherit GIT_DIR=/adore/... themselves.
unset GIT_DIR GIT_WORK_TREE GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL \
      GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

# 6-8. identity + env contract (verify with printenv, never $VAR expansion -
#      the HOME/tflint live lesson)
step "secret crossed via process env, not argv (printenv inside)"
[ "$("${RT[@]}" exec "${NAME}" printenv ADORE_VERIFY_SECRET)" = "${ADORE_VERIFY_SECRET}" ] \
    && ok || bad "secret not visible inside"

step "container user is 'adore'"
[ "$("${RT[@]}" exec "${NAME}" whoami)" = "adore" ] && ok || bad "wrong user"

step "HOME is /home/adore inside"
[ "$("${RT[@]}" exec "${NAME}" printenv HOME)" = "/home/adore" ] && ok || bad "wrong HOME"

if [ "${EGRESS_MODE}" = "allowlist-proxy" ]; then
    step "allowlist-proxy permits ALLOWED_URL"
    "${RT[@]}" exec "${NAME}" python -c \
        'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=20).read(1)' \
        "${ALLOWED_URL}" >/dev/null 2>&1 && ok || bad "allowed URL failed"

    step "allowlist-proxy denies DENIED_URL"
    if "${RT[@]}" exec "${NAME}" python -c \
        'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=20).read(1)' \
        "${DENIED_URL}" >/dev/null 2>&1; then
        bad "denied URL succeeded"
    else
        ok
    fi
elif [ "${EGRESS_MODE}" = "none" ]; then
    step "network none cannot reach ALLOWED_URL"
    if "${RT[@]}" exec "${NAME}" python -c \
        'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=10).read(1)' \
        "${ALLOWED_URL}" >/dev/null 2>&1; then
        bad "network none reached the internet"
    else
        ok
    fi
fi

# 9. tool usability (exit 0, not mere presence)
step "executor-base toolchain usable (python/uv/node/git/pi)"
TOOLS_OK=1
for tool_cmd in "python --version" "uv --version" "node --version" \
                "git --version" "pi --help"; do
    # shellcheck disable=SC2086
    if ! "${RT[@]}" exec "${NAME}" ${tool_cmd} >/dev/null 2>&1; then
        TOOLS_OK=0
        echo
        echo "    NOT USABLE: ${tool_cmd}"
    fi
done
[ "${TOOLS_OK}" -eq 1 ] && ok || bad "one or more tools unusable"

step "pinned Node ${EXPECTED_NODE_VERSION}"
FOUND="$("${RT[@]}" exec "${NAME}" node --version 2>&1 || true)"
[ "${FOUND}" = "${EXPECTED_NODE_VERSION}" ] && ok || bad "node is '${FOUND}'"

step "pinned Pi ${EXPECTED_PI_VERSION} (node <cli.js> --version)"
FOUND="$("${RT[@]}" exec "${NAME}" node "${PI_CLI}" --version 2>&1 || true)"
[ "${FOUND}" = "${EXPECTED_PI_VERSION}" ] && ok || bad "pi is '${FOUND}'"

step "pinned pi-web-access ${EXPECTED_PI_WEB_ACCESS_VERSION} next to Pi"
FOUND="$("${RT[@]}" exec "${NAME}" node -p \
    "require('${PI_PREFIX}/pi-web-access/package.json').version" 2>&1 || true)"
[ "${FOUND}" = "${EXPECTED_PI_WEB_ACCESS_VERSION}" ] && ok || bad "pi-web-access is '${FOUND}'"

step "Pi guard extension present and agent directory writable"
"${RT[@]}" exec "${NAME}" sh -c \
    "test -r '${PI_GUARD}' && test ! -w '${PI_GUARD}' && test -w '${PI_AGENT_DIR}'" \
    && ok || bad "guard missing/writable or agent dir not writable"

if [ -n "${REQUIRED_TOOL_CHECKS:-}" ]; then
    step "runtime-project required tool checks"
    PROJECT_TOOLS_OK=1
    IFS=';' read -r -a PROJECT_CHECKS <<< "${REQUIRED_TOOL_CHECKS}"
    for tool_cmd in "${PROJECT_CHECKS[@]}"; do
        [ -n "${tool_cmd// }" ] || continue
        # shellcheck disable=SC2086
        if ! "${RT[@]}" exec "${NAME}" ${tool_cmd} >/dev/null 2>&1; then
            PROJECT_TOOLS_OK=0
            echo
            echo "    NOT USABLE: ${tool_cmd}"
        fi
    done
    [ "${PROJECT_TOOLS_OK}" -eq 1 ] && ok || bad "one or more project tools unusable"
fi

# 10-11. git inside via GIT_DIR/GIT_WORK_TREE, commit visible host-side
step "git status works inside (GIT_DIR/GIT_WORK_TREE model)"
"${RT[@]}" exec "${NAME}" git status --porcelain >/dev/null && ok || bad "git status"

step "commit inside is visible on the host under bot authorship"
"${RT[@]}" exec "${NAME}" sh -c 'echo hello > verify.txt && git add verify.txt && git commit -q -m "verify commit"' \
    || bad "commit inside failed"
if git -C "${SCRATCH}/work" log -1 --format='%an %s' | grep -q "ADORE verify commit"; then
    ok
else
    bad "commit not visible host-side"
fi

# 12-14. status / park / resume (inspect --format, stop, start)
step "inspect --format .State.Status == running"
[ "$("${RT[@]}" inspect --format '{{.State.Status}}' "${NAME}")" = "running" ] \
    && ok || bad "unexpected status"

step "stop -> exited (park)"
"${RT[@]}" stop "${NAME}" >/dev/null
[ "$("${RT[@]}" inspect --format '{{.State.Status}}' "${NAME}")" = "exited" ] \
    && ok || bad "not exited after stop"

step "start -> running (resume)"
"${RT[@]}" start "${NAME}" >/dev/null
[ "$("${RT[@]}" inspect --format '{{.State.Status}}' "${NAME}")" = "running" ] \
    && ok || bad "not running after start"

# 15. listing (adore cleanup's orphan sweep)
step "ps --all --filter name= --format .Names lists the container"
"${RT[@]}" ps --all --filter "name=adore-verify-" --format '{{.Names}}' \
    | grep -qx "${NAME}" && ok || bad "not listed"

# 16-17. teardown + absent detection
step "rm --force (reap)"
"${RT[@]}" rm --force "${NAME}" >/dev/null && ok || bad "rm failed"

step "absent detection (inspect error contains a known marker)"
ERR="$("${RT[@]}" inspect --format '{{.State.Status}}' "${NAME}" 2>&1 || true)"
echo "${ERR}" | tr '[:upper:]' '[:lower:]' \
    | grep -qE "no such container|no such object|not found" \
    && ok || bad "unrecognized absence error: ${ERR}"

echo
if [ "${FAILURES}" -eq 0 ]; then
    echo "RESULT: all ${STEP} steps passed - '${RUNTIME}' is compatible with ADORE."
    echo "Next: set [container] runtime in config.toml and run a disposable-ticket pilot."
else
    echo "RESULT: ${FAILURES} of ${STEP} steps FAILED - record findings before using '${RUNTIME}'."
    exit 1
fi

# END OF FILE
