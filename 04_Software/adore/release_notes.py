"""Four-locale user-facing release notes shown in the web What's new window."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

RELEASE_NOTES_PATH = Path(__file__).with_name("release_notes.toml")
SCHEMA = 1
UNRELEASED = "Unreleased"
CATEGORIES = ("new", "improved", "fixed")
LOCALES = ("en", "fr", "de", "ro")
MAX_TEXT = 100
MAX_TOPIC = 40
MAX_PER_CATEGORY = 10
# Product names written in CamelCase are plain language, not code identifiers; add new ones here.
PRODUCT_NAMES = frozenset({"GitHub", "GitLab", "PolyForm", "JavaScript", "PowerShell", "macOS"})
_VERSION = re.compile(r"\d+\.\d+\.\d+")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TECHNICAL = (
    re.compile(r"`"),
    re.compile(r"\bhttps?://"),
    re.compile(r"\b[\w-]+\.(?:py|tsx?|mjs|js|toml|md|json|css|html|sh|ps1|cmd|txt|ya?ml|lock|csv"
               r"|log|ini|cfg|env)\b"),
    re.compile(r"(?:^|[\s(])/[\w.-]"),
    re.compile(r"\b[\w.-]+/[\w.-]+/[\w.-]+"),
    re.compile(r"\b(?:REQ|TASK|RULING)-[0-9A-Za-z-]+"),
    re.compile(r"\b[a-z0-9]+_[a-z0-9_]+\b"),
    re.compile(r"\b[A-Z][A-Z0-9]+_[A-Z0-9_]+\b"),
)
_CAMEL = re.compile(r"\b(?:[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+|[a-z]+[A-Z][A-Za-z0-9]*)\b")


class ReleaseNotesError(ValueError):
    """The release notes document does not have the served shape."""


def _texts(value: object, where: str) -> dict[str, str]:
    """
    Validate a locale-to-text table.
    value: Parsed TOML value.
    where: Location used in error messages.
    Returns: The table as a plain dict.
    Raises ReleaseNotesError: Value is not a table of strings.
    """
    if not isinstance(value, dict) or \
            not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise ReleaseNotesError(f"{where} must be a table of locale texts")
    return dict(value)


def _technical(text: str) -> bool:
    """
    Detect file names, paths, endpoints, ids and code identifiers.
    text: One locale text.
    Returns: True when the text names something only developers know.
    """
    if any(pattern.search(text) for pattern in _TECHNICAL):
        return True
    return any(match.group(0) not in PRODUCT_NAMES for match in _CAMEL.finditer(text))


def _version_key(version: str) -> tuple[int, ...]:
    """Numeric sort key of a released version."""
    return tuple(int(part) for part in version.split("."))


def parse_release_notes(text: str) -> list[dict]:
    """
    Parse release notes into the shape the web API serves.
    text: TOML document text.
    Returns: Releases as dicts with version, date (or None) and entries.
    Raises ReleaseNotesError: The document is not valid TOML of the expected shape.
    """
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ReleaseNotesError(f"invalid TOML: {exc}") from exc
    if type(data.get("schema")) is not int or data["schema"] != SCHEMA or \
            set(data) - {"schema", "release"}:
        raise ReleaseNotesError(f"expected schema = {SCHEMA} and only [[release]] tables")
    releases = data.get("release", [])
    if not isinstance(releases, list):
        raise ReleaseNotesError("release must be an array of tables")
    parsed = []
    for index, release in enumerate(releases, start=1):
        where = f"release {index}"
        if not isinstance(release, dict) or set(release) - {"version", "date", "entry"}:
            raise ReleaseNotesError(f"{where} may hold only version, date and entry")
        version, date = release.get("version"), release.get("date")
        if not isinstance(version, str) or date is not None and not isinstance(date, str):
            raise ReleaseNotesError(f"{where} needs a version string and an optional date string")
        entries = release.get("entry", [])
        if not isinstance(entries, list):
            raise ReleaseNotesError(f"{where} entry must be an array of tables")
        items = []
        for number, entry in enumerate(entries, start=1):
            spot = f"release {version} entry {number}"
            if not isinstance(entry, dict) or set(entry) != {"category", "topic", "text"} or \
                    not isinstance(entry["category"], str):
                raise ReleaseNotesError(f"{spot} needs exactly category, topic and text")
            items.append({"category": entry["category"],
                          "topic": _texts(entry["topic"], f"{spot} topic"),
                          "text": _texts(entry["text"], f"{spot} text")})
        parsed.append({"version": version, "date": date, "entries": items})
    return parsed


def load_release_notes(path: Path = RELEASE_NOTES_PATH) -> list[dict]:
    """
    Read and parse the packaged release notes.
    path: Release notes file; defaults to the packaged one.
    Returns: Parsed releases.
    Raises OSError: The file cannot be read.
    Raises ReleaseNotesError: The document has the wrong shape.
    """
    return parse_release_notes(path.read_text(encoding="utf-8"))


def contract_issues(releases: list[dict]) -> list[str]:
    """
    Check parsed releases against the release notes authoring contract.
    releases: Output of parse_release_notes.
    Returns: Human-readable issues; empty when the notes meet the contract.
    """
    issues: list[str] = []
    released: list[str] = []
    for index, release in enumerate(releases):
        version, date = release["version"], release["date"]
        if version == UNRELEASED:
            if index != 0:
                issues.append(f"release {version}: order - {UNRELEASED} must be the first release")
            if date is not None:
                issues.append(f"release {version}: an unreleased release has no date")
        elif not _VERSION.fullmatch(version):
            issues.append(f"release {version}: version must be {UNRELEASED} or x.y.z")
        else:
            if date is None or not _DATE.fullmatch(date):
                issues.append(f"release {version}: date must be YYYY-MM-DD")
            if released and _version_key(version) >= _version_key(released[-1]):
                issues.append(f"release {version}: order - released versions must be newest "
                              "first without repeats")
            released.append(version)
        counts = dict.fromkeys(CATEGORIES, 0)
        for number, entry in enumerate(release["entries"], start=1):
            spot = f"release {version} entry {number}"
            category = entry["category"]
            if category not in CATEGORIES:
                issues.append(f"{spot}: category {category!r} must be one of "
                              f"{', '.join(CATEGORIES)}")
            else:
                counts[category] += 1
            for field, limit in (("topic", MAX_TOPIC), ("text", MAX_TEXT)):
                values = entry[field]
                for locale in LOCALES:
                    value = values.get(locale, "").strip()
                    if not value:
                        issues.append(f"{spot}: {field} missing locale {locale}")
                    elif len(value) > limit:
                        issues.append(f"{spot}: {field} {locale} longer than {limit} characters")
                    elif _technical(value):
                        issues.append(f"{spot}: {field} {locale} has a technical reference "
                                      "(file, path, endpoint, id or identifier)")
                for locale in sorted(set(values) - set(LOCALES)):
                    issues.append(f"{spot}: {field} unknown locale {locale}")
        for category, count in counts.items():
            if count > MAX_PER_CATEGORY:
                issues.append(f"release {version}: more than {MAX_PER_CATEGORY} {category} "
                              f"entries ({count}); merge related notes")
    return issues
