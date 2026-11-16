#!/usr/bin/env python3
"""Repository check for the four-locale user-facing release notes."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04_Software"))

from adore.release_notes import (  # noqa: E402
    UNRELEASED,
    ReleaseNotesError,
    contract_issues,
    parse_release_notes,
)


NOTES = "04_Software/adore/release_notes.toml"
CHANGELOG = "CHANGELOG.md"
VERSION_FILE = "04_Software/adore/__init__.py"
_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})[ \t]*$", re.M)
_VERSION = re.compile(r'^__version__ = "([^"]+)"', re.M)


def _issues(root: Path) -> list[str]:
    """
    Collect every release notes issue for a repository root.
    root: Repository root.
    Returns: Issues; empty when the notes meet the contract.
    """
    try:
        releases = parse_release_notes((root / NOTES).read_text(encoding="utf-8"))
        changelog = (root / CHANGELOG).read_text(encoding="utf-8-sig")
        current = _VERSION.search((root / VERSION_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ReleaseNotesError) as exc:
        return [f"cannot read release notes inputs: {exc}"]
    issues = contract_issues(releases)
    dated = dict(_HEADING.findall(changelog))
    for release in releases:
        version, date = release["version"], release["date"]
        if version == UNRELEASED:
            continue
        if version not in dated:
            issues.append(f"release {version}: no matching '## [{version}] - <date>' section "
                          "in CHANGELOG.md")
        elif date != dated[version]:
            issues.append(f"release {version}: date {date} differs from CHANGELOG.md "
                          f"date {dated[version]}")
    if current is None:
        issues.append(f"cannot read __version__ from {VERSION_FILE}")
    elif all(release["version"] != current.group(1) for release in releases):
        issues.append(f"current version {current.group(1)} has no release section")
    return issues


def _warnings(root: Path, since: str) -> list[str]:
    """
    Warn when the changelog changed since a revision but the notes did not.
    root: Repository root.
    since: Git revision to compare the working tree with.
    Returns: Warning messages.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", "--end-of-options", since, "--"],
            check=False, capture_output=True, text=True)
        untracked = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
            check=False, capture_output=True, text=True)
    except OSError as exc:
        return [f"cannot compare with {since}: {exc}"]
    if result.returncode != 0:
        return [f"cannot compare with {since}: {result.stderr.strip()}"]
    changed = set(result.stdout.split())
    # A release notes file not yet added to git is a change too.
    changed |= set(untracked.stdout.split())
    if CHANGELOG in changed and NOTES not in changed:
        return [f"{CHANGELOG} changed since {since} but {NOTES} did not; add release notes "
                "for user-visible changes, or record 'release-notes: none (<reason>)' in the "
                "task journal"]
    return []


def main(argv: list[str] | None = None) -> int:
    """
    Run the check and print its findings.
    argv: Command-line arguments.
    Returns: 1 when the notes break the contract, else 0.
    """
    parser = argparse.ArgumentParser(description="Check the four-locale user-facing release notes.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--since",
                        help="git revision; warn when CHANGELOG.md changed but the notes did not")
    args = parser.parse_args(argv)
    issues = _issues(args.repo_root)
    for issue in issues:
        print(f"FAIL {issue}")
    for warning in _warnings(args.repo_root, args.since) if args.since else []:
        print(f"WARN {warning}")
    print(f"release notes: {len(issues)} issue(s)" if issues else "release notes: ok")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
