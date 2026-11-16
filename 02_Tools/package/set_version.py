#!/usr/bin/env python3
"""Synchronize release sources without tests, Git publication or package builds."""

from __future__ import annotations

import argparse
from datetime import date
import io
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOFTWARE = ROOT / "04_Software"
sys.path.insert(0, str(SOFTWARE))

from adore.release_notes import contract_issues, parse_release_notes  # noqa: E402

VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
TEXT_VERSIONS = (
    "README.md",
    "01_Documentation/README.md",
    "01_Documentation/User_Guide.md",
    "01_Documentation/Operator_Quick_Reference.md",
    "02_Tools/package/launcher_templates/README.md",
    "05_SoftwareDocu/README.md",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def current_version() -> str:
    """Read the authoritative release version; reject unsupported version syntax."""
    value = tomllib.loads(read("04_Software/pyproject.toml"))["project"]["version"]
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError("project version must be numeric x.y.z")
    return value


def check_current(version: str) -> None:
    """Check current release sources only; never inspect delivery archives."""
    if f'__version__ = "{version}"' not in read("04_Software/adore/__init__.py"):
        raise ValueError("adore.__version__ differs from pyproject.toml")
    packages = tomllib.loads(read("04_Software/uv.lock"))["package"]
    editable = [p for p in packages if p.get("source", {}).get("editable") == "."]
    if (
        len(editable) != 1
        or editable[0].get("name") != "adore"
        or editable[0].get("version") != version
    ):
        raise ValueError("editable adore package in uv.lock differs from pyproject.toml")
    headings = dict(
        re.findall(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", read("CHANGELOG.md"), re.M)
    )
    if version not in headings:
        raise ValueError("current version has no dated changelog heading")
    notes = parse_release_notes(read("04_Software/adore/release_notes.toml"))
    issues = contract_issues(notes)
    for release in notes:
        if (
            release["version"] != "Unreleased"
            and headings.get(release["version"]) != release["date"]
        ):
            issues.append(f"release notes date differs from changelog: {release['version']}")
    if not any(r["version"] == version for r in notes):
        issues.append("current version has no release notes section")
    released = [r for r in notes if r["version"] != "Unreleased"]
    if not released or released[0]["version"] != version:
        issues.append("latest released notes differ from pyproject.toml")
    if issues:
        raise ValueError("; ".join(issues))
    for relative in TEXT_VERSIONS:
        if version not in read(relative):
            raise ValueError(f"current version missing in {relative}")
    for path in presentations():
        with zipfile.ZipFile(path) as archive:
            slides = [n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
            if not slides or any(version not in archive.read(n).decode("utf-8") for n in slides):
                raise ValueError(f"current version missing from a slide in {path.name}")


def presentations() -> list[Path]:
    return sorted((ROOT / "01_Documentation/Operator_Cheat_Sheets/Presentations").glob("*.pptx"))


def build_plan(old: str, new: str, day: str) -> dict[Path, bytes]:
    """Validate all replacements before publishing any source file."""
    if not VERSION.fullmatch(new) or tuple(map(int, new.split("."))) <= tuple(
        map(int, old.split("."))
    ):
        raise ValueError("new version must be numeric x.y.z and higher than the current version")
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("release date must be YYYY-MM-DD")
    changes: dict[Path, bytes] = {}

    def text(relative: str, value: str) -> None:
        changes[ROOT / relative] = value.encode("utf-8")

    text(
        "04_Software/pyproject.toml",
        read("04_Software/pyproject.toml").replace(f'version = "{old}"', f'version = "{new}"', 1),
    )
    text(
        "04_Software/adore/__init__.py",
        read("04_Software/adore/__init__.py").replace(
            f'__version__ = "{old}"', f'__version__ = "{new}"', 1
        ),
    )
    lock = read("04_Software/uv.lock")
    lock, count = re.subn(
        r'(\[\[package\]\]\nname = "adore"\nversion = ")' + re.escape(old) + r'"',
        lambda m: m.group(1) + new + '"',
        lock,
    )
    if count != 1:
        raise ValueError("cannot uniquely locate the adore version in uv.lock")
    text("04_Software/uv.lock", lock)

    changelog = read("CHANGELOG.md")
    match = re.search(r"^## \[Unreleased\]\s*\n(.*?)(?=^## \[|\Z)", changelog, re.M | re.S)
    if match is None or not re.search(r"^- \S", match.group(1), re.M):
        raise ValueError("Unreleased changelog needs at least one change")
    changelog = (
        changelog[: match.start()]
        + "## [Unreleased]\n\n"
        + f"## [{new}] - {day}\n\n"
        + match.group(1).strip()
        + "\n\n"
        + changelog[match.end() :]
    )
    text("CHANGELOG.md", changelog)

    notes = read("04_Software/adore/release_notes.toml")
    unreleased = re.search(
        r'^\[\[release\]\]\nversion = "Unreleased".*?(?=^\[\[release\]\]|\Z)', notes, re.M | re.S
    )
    if unreleased:
        block = unreleased.group().replace('version = "Unreleased"', f'version = "{new}"', 1)
        block = re.sub(r'^date = "[^"\n]*"\n', "", block, flags=re.M)
        block = block.replace(f'version = "{new}"', f'version = "{new}"\ndate = "{day}"', 1)
        notes = (
            notes[: unreleased.start()]
            + '[[release]]\nversion = "Unreleased"\n\n'
            + block
            + notes[unreleased.end() :]
        )
    else:
        first_release = re.search(r"^\[\[release\]\]$", notes, re.M)
        if first_release is None:
            raise ValueError("release notes contain no release table")
        first = first_release.start()
        notes = (
            notes[:first]
            + '[[release]]\nversion = "Unreleased"\n\n'
            + f'[[release]]\nversion = "{new}"\ndate = "{day}"\n\n'
            + notes[first:]
        )
    issues = contract_issues(parse_release_notes(notes))
    if issues:
        raise ValueError("; ".join(issues))
    text("04_Software/adore/release_notes.toml", notes)

    for relative in TEXT_VERSIONS:
        value = read(relative).replace(old, new)
        if relative.endswith("README.md") and relative.startswith(("01_", "05_")):
            value = re.sub(
                r"(\*\*ADORE " + re.escape(new) + r"\*\* \()\d{4}-\d{2}-\d{2}(\))",
                lambda m: m.group(1) + day + m.group(2),
                value,
            )
        text(relative, value)
    for path in presentations():
        output = io.BytesIO()
        with zipfile.ZipFile(path) as source, zipfile.ZipFile(output, "w") as target:
            for member in source.infolist():
                data = source.read(member)
                if member.filename.endswith((".xml", ".rels")):
                    data = data.decode("utf-8").replace(old, new).encode("utf-8")
                target.writestr(member, data)
        changes[path] = output.getvalue()
    return changes


def write_plan(changes: dict[Path, bytes]) -> None:
    """Replace each prevalidated file atomically; report any write error to the operator."""
    for path, content in changes.items():
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".adore-version-")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="new numeric x.y.z release")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD release date")
    parser.add_argument(
        "--check", action="store_true", help="check current sources without changing them"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and list the release edits without writing"
    )
    args = parser.parse_args()
    if args.check and (args.version or args.dry_run) or not args.check and not args.version:
        parser.error("use --check alone, or VERSION with optional --dry-run")
    try:
        old = current_version()
        check_current(old)
        if args.check:
            print(f"ADORE {old}: release sources are consistent; archives were not inspected")
            return 0
        changes = build_plan(old, args.version, args.date)
        print(f"ADORE {old} -> {args.version} ({args.date})")
        for path in changes:
            print(path.relative_to(ROOT).as_posix())
        if args.dry_run:
            print("Dry run: no files changed")
        else:
            write_plan(changes)
            print("Release sources updated; no tests, builds, commits, tags or pushes were run")
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Cannot prepare release: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
