#!/bin/sh
set -eu
case "$0" in */*) script_dir=${0%/*} ;; *) script_dir=. ;; esac
bundle_dir=$(CDPATH= cd -- "$script_dir" && pwd)
exec "$bundle_dir/python/bin/python3.12" -I -B "$bundle_dir/launch.py" --stop "$@"
