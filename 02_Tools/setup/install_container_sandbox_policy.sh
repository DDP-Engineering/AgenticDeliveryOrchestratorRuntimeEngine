#!/usr/bin/env bash
# Install the common executor policy on the Linux container runtime host.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
    echo "Run with sudo on the Linux Docker/Podman host." >&2
    exit 1
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
policy=${1:-"${script_dir}/executor-apparmor"}
if [[ $# -eq 0 && ! -f "$policy" ]]; then
    policy="${script_dir}/../../04_Software/adore/container_assets/executor-apparmor"
fi
target=/etc/apparmor.d/adore-executor
command -v apparmor_parser >/dev/null
[[ -f "$policy" ]] || { echo "Provide the executor-apparmor asset path." >&2; exit 1; }
# Validate without changing kernel policy. Older parsers must not drop userns rules.
apparmor_parser --skip-kernel-load "$policy"
if [[ -f "$target" ]]; then
    cmp -s "$policy" "$target" || {
        echo "A different policy exists; wait for idle jobs before replacing it manually." >&2
        exit 1
    }
fi
if grep -q '^adore-executor ' /sys/kernel/security/apparmor/profiles; then
    [[ -f "$target" ]] || {
        echo "A loaded policy has no verified source; refusing to replace it." >&2
        exit 1
    }
    echo "Policy already loaded; no active policy changed."
    exit 0
fi
[[ -f "$target" ]] || install -m 0644 "$policy" "$target"
apparmor_parser --add "$target"
echo "Installed adore-executor; existing container policies and host sysctls are unchanged."
