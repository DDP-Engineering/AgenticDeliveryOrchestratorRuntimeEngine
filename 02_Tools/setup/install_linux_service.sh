#!/usr/bin/env bash
# @file    install_linux_service.sh
# @brief   Prepare a source checkout and optionally install its Linux CLI service.
# @details Fail-fast, idempotent, re-runnable. Steps: check host prerequisites,
#          sync the Python environment (uv), validate config.toml, build the
#          executor base image when absent, and optionally install + start the
#          systemd unit (adore.service template in this directory).
#          Secrets are never echoed and never appear in argv; they stay in
#          .env / an EnvironmentFile.
# @usage   bash 02_Tools/setup/install_linux_service.sh [--service] [--skip-image]
#            [--allow-open-egress] [--uninstall]
#            (no flag)   prepare only: env sync + config validate + image
#            --service   also install/enable/start the systemd unit (sudo)
#            --skip-image  do not check/build the executor image
#            --uninstall stop/disable/remove the systemd unit (sudo)
# @author  Eng. Dan Dumitru Pasare
# @date    2026-11-15
# -----------------------------------------------------------------------------
set -euo pipefail

# CONSTANTS
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Source checkout: <root>/02_Tools/setup beside <root>/04_Software.
DEPLOYMENT_PARENT="$(dirname "${SCRIPT_DIR}")"
SOFTWARE_DIR="$(dirname "${DEPLOYMENT_PARENT}")/04_Software"
UNIT_TEMPLATE="${SCRIPT_DIR}/adore.service"
UNIT_PATH="/etc/systemd/system/adore.service"
IMAGE_TAG="${IMAGE_TAG:-adore-executor-base:1.0.0}"
IMAGE_DOCKERFILE="${IMAGE_DOCKERFILE:-Dockerfile.executor-base}"
ADORE_USER_CHOSEN="${ADORE_USER:+yes}"
ADORE_USER="${ADORE_USER:-$(id -un)}"

# LOCAL HELPERS
fail() { echo "error: $*" >&2; exit 1; }
note() { echo "==> $*"; }
need_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "'$1' not found. $2"
}
as_root() {
    if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi
}

usage() {
    cat <<'EOF'
usage: bash <path-to-deploy>/install_linux_service.sh [--service] [--skip-image] [--allow-open-egress] [--uninstall]
  (no flag)             prepare only: env sync + config validate + executor image
  --service             also install/enable/start the systemd unit (uses sudo;
                        service user from ADORE_USER, default: the invoking user)
  --skip-image          do not check/build the executor image
  --allow-open-egress   allow unattended service install while [executor]
                        internet is true (supervised pilots only)
  --uninstall           stop/disable/remove the systemd unit (all state is kept)
EOF
}

# ARGUMENTS
WITH_SERVICE=0
SKIP_IMAGE=0
ALLOW_OPEN_EGRESS=0
MODE="install"
for arg in "$@"; do
    case "${arg}" in
        --service)           WITH_SERVICE=1 ;;
        --skip-image)        SKIP_IMAGE=1 ;;
        --allow-open-egress) ALLOW_OPEN_EGRESS=1 ;;
        --uninstall)         MODE="uninstall" ;;
        -h|--help)           usage; exit 0 ;;
        *)                   usage; fail "unknown option: ${arg}" ;;
    esac
done

# UNINSTALL
if [ "${MODE}" = "uninstall" ]; then
    note "removing the adore systemd unit (worktrees, containers, and .adore state are kept)"
    if [ -f "${UNIT_PATH}" ]; then
        as_root systemctl disable --now adore.service || true
        as_root rm -f "${UNIT_PATH}"
        as_root systemctl daemon-reload
        note "removed ${UNIT_PATH}"
    else
        note "no unit at ${UNIT_PATH}; nothing to do"
    fi
    exit 0
fi

# Started through sudo, the invoking user is root: the service would run as root
# and the Python environment would be root-owned. That is never the default.
if [ "$(id -u)" -eq 0 ] && [ -z "${ADORE_USER_CHOSEN}" ]; then
    fail "do not start this script as root or with sudo: it asks for sudo itself where needed. Run it as the account that will run ADORE, or set ADORE_USER explicitly (ADORE_USER=root to run as root on purpose)"
fi

# INSTALL - 1. host prerequisites (fail closed with a hint, never auto-install)
[ -f "${SOFTWARE_DIR}/pyproject.toml" ] && [ -d "${SOFTWARE_DIR}/adore" ] \
    || fail "runtime not found at '${SOFTWARE_DIR}'; keep 02_Tools/setup beside 04_Software in a source checkout"
note "checking host prerequisites"
need_cmd uv   "Install it as described at https://docs.astral.sh/uv/getting-started/installation/"
need_cmd git  "Install: sudo apt-get install -y git"
if ! command -v glab >/dev/null 2>&1 && ! command -v gh >/dev/null 2>&1 \
    && ! command -v tea >/dev/null 2>&1; then
    need_cmd az "Install Microsoft Azure CLI (Azure DevOps Services only)"
    az extension show --name azure-devops --output none --only-show-errors >/dev/null 2>&1 \
        || fail "Install the official extension: az extension add --name azure-devops"
fi

# 2. Python environment (locked, reproducible)
note "syncing the Python environment (uv sync --frozen)"
( cd "${SOFTWARE_DIR}" && uv sync --frozen )
[ -x "${SOFTWARE_DIR}/.venv/bin/adore" ] || fail ".venv/bin/adore missing after uv sync"

# 3. configuration (the unit refuses to start on an invalid config anyway;
#    catch it here where the operator is watching)
[ -f "${SOFTWARE_DIR}/config.toml" ] \
    || fail "config.toml not found; copy config.example.toml and adjust it first"
note "validating config.toml"
( cd "${SOFTWARE_DIR}" && ./.venv/bin/adore -c config.toml config validate )
CONFIG_JSON="$(cd "${SOFTWARE_DIR}" && ./.venv/bin/adore -c config.toml config show)"
json_field() {
    printf '%s' "${CONFIG_JSON}" | "${SOFTWARE_DIR}/.venv/bin/python" -c \
        'import json, sys; data=json.load(sys.stdin); cur=data
for part in sys.argv[1].split("."):
    cur = cur[part]
print(cur)' "$1"
}
# [executor] internet decides the agent's network: true is open egress,
# false the per-run allowlist proxy that admits only the model provider.
INTERNET="$(json_field executor.internet)"
BACKEND="$(json_field execution.backend)"
PROXY_IMAGE="$(json_field container.egress.proxy_image)"
if [ "${WITH_SERVICE}" -eq 1 ] && [ "${INTERNET}" = "True" ] \
    && [ "${BACKEND}" = "container" ] && [ "${ALLOW_OPEN_EGRESS}" -eq 0 ]; then
    fail "refusing unattended service install with [executor] internet = true; switch it off or pass --allow-open-egress for a supervised pilot"
fi

if [ ! -f "${SOFTWARE_DIR}/.env" ]; then
    note "note: no .env file (fine when glab/gh/tea host auth covers everything;"
    note "      see .env.example for the canonical secret list)"
elif [ -n "$(find "${SOFTWARE_DIR}/.env" -maxdepth 0 -perm /077 2>/dev/null)" ]; then
    # Advisory only: the file holds secrets and other accounts can open it.
    note "warning: .env can be read or changed by other accounts;"
    note "         restrict it with: chmod 600 ${SOFTWARE_DIR}/.env"
fi

# 4. executor base image (build only when absent; rebuilds are an explicit choice)
if [ "${SKIP_IMAGE}" -eq 0 ]; then
    need_cmd docker "Install Docker Engine, or re-run with --skip-image for a wrapped runtime"
    if docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1; then
        note "executor image ${IMAGE_TAG} already present"
    else
        note "building executor image ${IMAGE_TAG} (USER_UID=$(id -u) USER_GID=$(id -g))"
        docker build --build-arg USER_UID="$(id -u)" --build-arg USER_GID="$(id -g)" \
            -f "${SOFTWARE_DIR}/docker/${IMAGE_DOCKERFILE}" \
            -t "${IMAGE_TAG}" "${SOFTWARE_DIR}/docker"
    fi
else
    note "skipping executor image check (--skip-image)"
fi

# Only an internet-off container project runs behind the proxy.
if [ "${INTERNET}" != "True" ] && [ "${BACKEND}" = "container" ]; then
    need_cmd docker "Install Docker Engine, or build/verify ${PROXY_IMAGE} before service install"
    if docker image inspect "${PROXY_IMAGE}" >/dev/null 2>&1; then
        note "egress proxy image ${PROXY_IMAGE} already present"
    else
        note "building egress proxy image ${PROXY_IMAGE}"
        docker build -f "${SOFTWARE_DIR}/docker/Dockerfile.egress-proxy" \
            -t "${PROXY_IMAGE}" "${SOFTWARE_DIR}/docker"
    fi
fi

# 5. systemd unit (optional; the design's Ubuntu service mode, 12a)
if [ "${WITH_SERVICE}" -eq 1 ]; then
    note "installing systemd unit for user '${ADORE_USER}' (override with ADORE_USER=...)"
    id -u "${ADORE_USER}" >/dev/null 2>&1 || fail "user '${ADORE_USER}' does not exist"
    # The path is written into the unit as it is. These characters would change
    # the substitution or the meaning of the unit, so the unit would not start.
    case "${SOFTWARE_DIR}" in
        *[[:space:]\|\&%\\\"\']*)
            fail "the checkout path '${SOFTWARE_DIR}' has a space or one of | & % \\ \" ' and cannot be written into a systemd unit; move the checkout to a plain path" ;;
    esac
    rendered="$(mktemp)"
    sed -e "s|__ADORE_DIR__|${SOFTWARE_DIR}|g" \
        -e "s|__ADORE_USER__|${ADORE_USER}|g" \
        "${UNIT_TEMPLATE}" > "${rendered}"
    as_root cp "${rendered}" "${UNIT_PATH}"
    rm -f "${rendered}"
    as_root systemctl daemon-reload
    as_root systemctl enable --now adore.service
    note "unit installed and started; follow logs with: journalctl -u adore -f"
else
    note "prepared (no service installed). Run the poller manually with:"
    note "    cd ${SOFTWARE_DIR} && ./.venv/bin/adore run --loop"
    note "or re-run this script with --service to install the systemd unit."
fi

# END OF FILE
