#!/bin/sh
set -eu
case "$0" in */*) script_dir=${0%/*} ;; *) script_dir=. ;; esac
bundle_dir=$(CDPATH= cd -- "$script_dir" && pwd)
unset PYTHONPATH PYTHONHOME
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
exec "$bundle_dir/python/bin/python3.12" -I -B -m adore "$@"
