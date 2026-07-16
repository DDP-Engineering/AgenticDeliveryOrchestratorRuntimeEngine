#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
# @file    package_runtime.sh
# @brief   Build a trimmed ADORE runtime bundle on POSIX hosts.
# @details Creates a deployable bundle from 04_Software without development
#          state, tests, worktrees, caches, or virtual environments. The bundle
#          includes the existing deploy scripts for Ubuntu systemd and Windows
#          Task Scheduler setup.
# @usage   ./02_Tools/package_runtime.sh [--output-dir 07_Delivery]
#             [--format tar.gz|zip|directory] [--include-config] [--name NAME]
# @author  Eng. Dan Dumitru Pasare
# @date    2026-07-06
# @version 0.3.0
# -----------------------------------------------------------------------------
set -euo pipefail

# CONSTANTS
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${SCRIPT_DIR}")"
SOFTWARE_DIR="${REPO_ROOT}/04_Software"
DOCUMENTATION_DIR="${REPO_ROOT}/01_Documentation"
OUTPUT_DIR="${REPO_ROOT}/07_Delivery"
FORMAT="tar.gz"
INCLUDE_CONFIG=0
PACKAGE_NAME=""
PYTHON_CMD=()

# LOCAL HELPERS
fail() { echo "error: $*" >&2; exit 1; }
note() { echo "==> $*"; }

detect_python() {
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD=(python3)
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD=(python)
    elif command -v py >/dev/null 2>&1; then
        PYTHON_CMD=(py -3)
    else
        fail "python3/python not found; install Python 3.11+ or run the PowerShell packager on Windows"
    fi
}

usage() {
    cat <<'EOF'
usage: ./02_Tools/package_runtime.sh [options]
  --output-dir DIR       Destination directory (default: 07_Delivery)
  --format FORMAT        tar.gz, zip, or directory (default: tar.gz)
  --include-config       Include 04_Software/config.toml; .env is never copied
  --name NAME            Override package directory/archive base name
  -h, --help             Show this help
EOF
}

full_path() {
    local resolved
    resolved="$("${PYTHON_CMD[@]}" - "$1" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
    )"
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -u "${resolved}"
    else
        printf '%s\n' "${resolved}"
    fi
}

remove_tree_inside() {
    local target="$1"
    local allowed_root="$2"
    local target_full
    local root_full
    target_full="$(full_path "${target}")"
    root_full="$(full_path "${allowed_root}")"
    case "${target_full}" in
        "${root_full}"/*) rm -rf "${target_full}" ;;
        *) fail "refusing to remove path outside output directory: ${target_full}" ;;
    esac
}

copy_required() {
    local relative="$1"
    local destination_root="$2"
    local source="${SOFTWARE_DIR}/${relative}"
    local destination="${destination_root}/${relative}"
    [ -e "${source}" ] || fail "required runtime path missing: 04_Software/${relative}"
    mkdir -p "$(dirname "${destination}")"
    cp -R "${source}" "${destination}"
}

copy_documentation() {
    local destination_root="$1"
    [ -d "${DOCUMENTATION_DIR}" ] || fail "required documentation directory missing: 01_Documentation"
    cp -R "${DOCUMENTATION_DIR}" "${destination_root}/Documentation"
}

update_bundle_readme_links() {
    "${PYTHON_CMD[@]}" - "${1}/README.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8-sig")
path.write_text(
    text.replace("../01_Documentation/", "Documentation/"),
    encoding="utf-8",
)
PY
}

read_package_version() {
    "${PYTHON_CMD[@]}" - "${SOFTWARE_DIR}/pyproject.toml" <<'PY'
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
if not match:
    raise SystemExit("could not read project version from 04_Software/pyproject.toml")
print(match.group(1))
PY
}

write_bundle_readme() {
    local destination_root="$1"
    local version="$2"
    cat > "${destination_root}/README_PACKAGED.md" <<EOF
# ADORE Runtime Bundle

Version: ${version}

This bundle contains only the files needed to run ADORE as a Python package.
It intentionally excludes tests, worktrees, .adore state, caches, and .venv.

Read [Documentation](Documentation/README.md) before deployment. It contains
the prerequisite, credential, configuration, operation, and recovery guides.

Prepare:

\`\`\`bash
uv sync --frozen
cp config.example.toml config.toml
\${EDITOR:-vi} config.toml
\`\`\`

Ubuntu service-style setup:

\`\`\`bash
bash deploy/install-ubuntu.sh
bash deploy/install-ubuntu.sh --service
\`\`\`

Windows service-style setup:

\`\`\`powershell
.\deploy\install-windows.ps1 -NoTask
.\deploy\install-windows.ps1
\`\`\`

Authenticate \`glab\` or \`gh\` on the host for forge access. Put only executor
provider keys named by \`[executor].env_keys\` in \`.env\` beside this file.
The package never includes \`.env\`.
EOF
}

make_zip() {
    local bundle_dir="$1"
    local archive="$2"
    "${PYTHON_CMD[@]}" - "${bundle_dir}" "${archive}" <<'PY'
from pathlib import Path
import sys
import zipfile
bundle = Path(sys.argv[1]).resolve()
archive = Path(sys.argv[2]).resolve()
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(bundle.rglob("*")):
        zf.write(path, path.relative_to(bundle.parent))
PY
}

# ARGUMENTS

# Stage 1: parse command-line options and fail closed on unknown input.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --output-dir)
            [ "$#" -ge 2 ] || fail "--output-dir needs a value"
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --format)
            [ "$#" -ge 2 ] || fail "--format needs a value"
            FORMAT="$2"
            shift 2
            ;;
        --include-config)
            INCLUDE_CONFIG=1
            shift
            ;;
        --name)
            [ "$#" -ge 2 ] || fail "--name needs a value"
            PACKAGE_NAME="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

# Stage 2: validate the requested output format.
case "${FORMAT}" in
    tar.gz|zip|directory) ;;
    *) fail "--format must be tar.gz, zip, or directory" ;;
esac

# PUBLIC SCRIPT FLOW

# Stage 3: verify the expected repository layout and Python runtime exist.
[ -d "${SOFTWARE_DIR}" ] || fail "04_Software not found next to 02_Tools"
[ -d "${DOCUMENTATION_DIR}" ] || fail "01_Documentation not found next to 02_Tools"
detect_python

# Stage 4: read the project release version and derive a safe package name.
VERSION="$(read_package_version)"
if [ -z "${PACKAGE_NAME}" ]; then
    PACKAGE_NAME="adore-runtime-${VERSION}"
fi
case "${PACKAGE_NAME}" in
    */*|*\\*|.|..) fail "package name must be a single directory name, not a path: ${PACKAGE_NAME}" ;;
esac

# Stage 5: prepare the output and temporary staging directories.
mkdir -p "${OUTPUT_DIR}"
OUTPUT_FULL="$(full_path "${OUTPUT_DIR}")"
STAGE_ROOT="${OUTPUT_FULL}/.packaging_tmp"
BUNDLE_DIR="${STAGE_ROOT}/${PACKAGE_NAME}"

note "staging ADORE runtime bundle ${PACKAGE_NAME}"
remove_tree_inside "${STAGE_ROOT}" "${OUTPUT_FULL}"
mkdir -p "${BUNDLE_DIR}"

# Stage 6: copy only the runtime files needed by the deployment host.
for path in \
    "adore" \
    "deploy" \
    "docker" \
    "pyproject.toml" \
    "uv.lock" \
    "README.md" \
    "config.example.toml" \
    ".env.example"
do
    copy_required "${path}" "${BUNDLE_DIR}"
done

# Stage 7: copy the canonical operator documentation and repair bundled links.
copy_documentation "${BUNDLE_DIR}"
update_bundle_readme_links "${BUNDLE_DIR}"

# Stage 8: remove generated Python caches from copied runtime directories.
find "${BUNDLE_DIR}" \( -type d -name "__pycache__" -o -type f \( -name "*.pyc" -o -name "*.pyo" \) \) -prune -exec rm -rf {} +

# Stage 9: include root release notes when present.
if [ -f "${REPO_ROOT}/CHANGELOG.md" ]; then
    cp "${REPO_ROOT}/CHANGELOG.md" "${BUNDLE_DIR}/CHANGELOG.md"
fi

# Stage 10: optionally include the target config, but never include secrets.
if [ "${INCLUDE_CONFIG}" -eq 1 ]; then
    copy_required "config.toml" "${BUNDLE_DIR}"
    note "included config.toml by explicit request; .env is still excluded"
fi

# Stage 11: write short unpack-and-deploy instructions into the bundle.
write_bundle_readme "${BUNDLE_DIR}" "${VERSION}"

# Stage 12: either keep the staged directory as the artifact or create archive.
if [ "${FORMAT}" = "directory" ]; then
    FINAL_DIR="${OUTPUT_FULL}/${PACKAGE_NAME}"
    remove_tree_inside "${FINAL_DIR}" "${OUTPUT_FULL}"
    mv "${BUNDLE_DIR}" "${FINAL_DIR}"
    remove_tree_inside "${STAGE_ROOT}" "${OUTPUT_FULL}"
    note "wrote ${FINAL_DIR}"
    exit 0
fi

# Stage 13: create the selected archive artifact.
if [ "${FORMAT}" = "zip" ]; then
    ARCHIVE="${OUTPUT_FULL}/${PACKAGE_NAME}.zip"
    rm -f "${ARCHIVE}"
    make_zip "${BUNDLE_DIR}" "${ARCHIVE}"
else
    ARCHIVE="${OUTPUT_FULL}/${PACKAGE_NAME}.tar.gz"
    rm -f "${ARCHIVE}"
    tar -C "${STAGE_ROOT}" -czf "${ARCHIVE}" "${PACKAGE_NAME}"
fi

# Stage 14: clean temporary staging files.
remove_tree_inside "${STAGE_ROOT}" "${OUTPUT_FULL}"
note "wrote ${ARCHIVE}"

# END OF FILE
