"""Runtime-project profiles: the cross-platform store that lets one ADORE"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
import errno
import json
import os
from pathlib import Path
import re
from tempfile import mkstemp
from time import sleep
import unicodedata
from uuid import uuid4

from adore import __version__
from adore.branding import PRODUCT_SLUG, PROFILE_HOME_ENV
from adore.util import force_rmtree, utc_now_iso

CONFIG_FILE = "config.toml"
METADATA_FILE = "profile.json"
PROFILES_DIR = "profiles"
ACTIVE_POINTER = "active_profile"
DEFAULT_CONFIG_NAME = "config.toml"

_ENV_HOME = PROFILE_HOME_ENV
_ENV_APPDATA = "APPDATA"
_ENV_LOCALAPPDATA = "LOCALAPPDATA"
_ENV_XDG = "XDG_CONFIG_HOME"



class ProfileError(RuntimeError):
    """
    Raised when a profile is missing or its metadata is corrupt.
    Fail-closed signal (same shape as StateError / ForgeError /
             IsolationError): the caller reports it, never guesses or silently
             recreates a profile.
    """

    def __init__(self, message: str, *, code: str = "profile_error", field: str = "name"):
        """Carry a stable non-secret contract code alongside CLI diagnostics."""
        super().__init__(message)
        self.code = code
        self.field = field


@dataclass
class Profile:
    """
    Metadata sidecar for one runtime-project profile (profile.json).
    Describes the project the config.toml targets plus lightweight
             usage counters. Secret values NEVER live here (design decision
             D5): only env-key names belong in the config, tokens stay in .env.
             Rich run statistics (merged/failed/success-rate) are computed on
             demand from the project's metrics DB, not duplicated here.
    """

    name: str
    project_id: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str = ""
    use_count: int = 0
    platform: str = ""
    host: str = ""
    repo: str = ""
    runtime: str = ""
    host_os: str = ""
    adore_version: str = ""
    config_path: str = ""
    store_root: str = ""
    archived: bool = False
    display_name: str = ""




_PROFILE_FIELDS = frozenset(f.name for f in fields(Profile))


def validate_display_name(value: object) -> str:
    """
    Validate a bounded human label without silently normalizing it.
    value: Explicit display name.
    Returns: The unchanged validated name.
    Raises ProfileError: On empty, untrimmed, unsafe or malformed input.
    """
    if (not isinstance(value, str) or not 1 <= len(value) <= 120
            or value != value.strip()
            or any(unicodedata.category(char).startswith("C") for char in value)):
        raise ProfileError("invalid display name", code="invalid_display_name",
                           field="display_name")
    return value


def validate_profile_id(name: object) -> str:
    """
    Validate portable web profile IDs and immutable-ID ambiguity.
    name: Requested directory identity.
    Returns: The unchanged validated ID.
    Raises ProfileError: On malformed or reserved input.
    """
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", name):
        raise ProfileError("invalid profile ID", code="invalid_project_name")
    stem = name.split(".")[0]
    if (name.endswith(".") or stem in {"con", "prn", "aux", "nul"}
            or re.fullmatch(r"(?:com|lpt)[1-9]", stem)
            or re.fullmatch(r"[0-9a-f]{32}", name)
            or name in {"import", "import-preview", "setup-preview", "setup-check",
                        "setup-create", "id-availability", "transfer-source",
                        "transfer-preview", "transfer-check", "transfer-create",
                        # Page and API routes beside /projects/<id>.
                        "new", "clone", "repository-source"}):
        raise ProfileError("reserved profile ID", code="reserved_project_name")
    return name


def _profile_from_dict(data: dict, name: str) -> Profile:
    """
    Build a Profile from the parsed JSON this build writes.
    There are no migrations while ADORE is in development: unknown
                or missing keys mean another build wrote the file, which is
                refused. The directory name is the authoritative identity, so
                it always overrides any stored name.
    data: Parsed profile.json mapping.
    name: The profile's directory name (source of truth).
    Returns: The reconstructed Profile.
    Raises ProfileError: For a file of another build or invalid values.
    """
    unknown = sorted(set(data) - _PROFILE_FIELDS)
    missing = sorted(_PROFILE_FIELDS - set(data))
    if unknown or missing:
        raise ProfileError(
            f"profile.json of project {name!r} was written by another ADORE build "
            f"(unknown keys {unknown}, missing keys {missing}); delete or fix that file"
        )
    known = dict(data)
    if (not isinstance(known["project_id"], str)
            or not re.fullmatch(r"[0-9a-f]{32}", known["project_id"])):
        raise ProfileError(f"corrupt profile.json for {name!r}: invalid project ID")
    known["name"] = name
    known["display_name"] = validate_display_name(known["display_name"])
    if type(known["archived"]) is not bool:
        raise ProfileError(f"corrupt profile.json for {name!r}: invalid archived flag")
    return Profile(**known)


def _home_for(os_name: str, environ: Mapping[str, str]) -> Path:
    """
    Pure OS/env -> ADORE home decision (testable without globals).
    Precedence: ADORE_HOME override, then the OS-native config dir
                (Windows %APPDATA%/%LOCALAPPDATA%, POSIX $XDG_CONFIG_HOME or
                ~/.config), each suffixed with "adore". Kept pure so tests can
                pass "nt"/"posix" and a fake environ instead of monkeypatching
                os.name (which would break pathlib process-wide).
    os_name: Value of os.name ("nt" | "posix").
    environ: Environment mapping to read overrides from.
    Returns: The ADORE home directory (not created here).
    """
    override = environ.get(_ENV_HOME)
    if override:
        return Path(override)
    if os_name == "nt":
        base = environ.get(_ENV_APPDATA) or environ.get(_ENV_LOCALAPPDATA)
        if base:
            return Path(base) / PRODUCT_SLUG
        return Path.home() / "AppData" / "Roaming" / PRODUCT_SLUG
    xdg = environ.get(_ENV_XDG)
    if xdg:
        return Path(xdg) / PRODUCT_SLUG
    return Path.home() / ".config" / PRODUCT_SLUG


def adore_home() -> Path:
    """
    Resolve the global ADORE config home for the current host.
    Read at call time so tests can point ADORE_HOME at a tmp dir;
                the branching logic lives in _home_for.
    Returns: The ADORE home directory (not created here).
    """
    return _home_for(os.name, os.environ)


def resolve_config_path(
    explicit: str | None,
    profile: str | None,
    *,
    store: ProfileStore | None = None,
    cwd_default: str = DEFAULT_CONFIG_NAME,
) -> tuple[Path, str | None]:
    """
    Decide which config.toml a command should use (decision D3).
    Precedence: an explicit `-c FILE` wins; then a named
                `--profile`; then the active-profile pointer; then the local
                ./config.toml. A named
                profile that does not exist fails closed; a stale active
                pointer (profile since deleted) falls through to the default
                rather than erroring.
    explicit: The `-c/--config` value, or None.
    profile: The `--profile` name, or None.
    store: Profile store (defaults to the resolved adore_home()).
    cwd_default: Fallback config filename in the working directory.
    Returns: (config_path, resolved_profile_name_or_None).
    Raises ProfileError: When `profile` is named but does not exist.
    """
    if explicit:
        return Path(explicit), None
    store = store or ProfileStore()
    if profile:
        if not store.exists(profile):
            raise ProfileError(f"no such profile: {profile!r}")
        return store.config_path(profile), profile
    active = store.get_active()
    if active and store.exists(active):
        return store.config_path(active), active
    return Path(cwd_default), None




class ProfileStore:
    """
    CRUD over runtime-project profiles under the ADORE config home.
    Persistence only: create/load/save/list/rename/delete a profile's
             metadata, manage the active-profile pointer, and expose the paths
             (config.toml, state dir) the wizard and CLI build on. Missing is
             not corrupt: load() raises ProfileError only when metadata exists
             but is unreadable; list_profiles() skips corrupt entries and
             invalid_profiles() reports them (mirrors StateStore).
    """

    def __init__(
        self,
        home: str | Path | None = None,
        *,
        now: Callable[[], str] = utc_now_iso,
    ) -> None:
        """
        Build the store rooted at an ADORE home.
        home: Config home (defaults to adore_home()).
        now: Timestamp function (injectable for deterministic tests).
        """
        self.home = Path(home) if home is not None else adore_home()
        self.profiles_dir = self.home / PROFILES_DIR
        self.active_pointer = self.home / ACTIVE_POINTER
        self._now = now

    # -- paths --------------------------------------------------------------------

    def profile_dir(self, name: str) -> Path:
        """
        The directory holding a profile's files.
        name: Profile name.
        Returns: `<home>/profiles/<name>`.
        """
        return self.profiles_dir / name

    def config_path(self, name: str) -> Path:
        """
        A profile's config.toml path (written by the wizard later).
        name: Profile name.
        Returns: `<home>/profiles/<name>/config.toml`.
        """
        return self.profile_dir(name) / CONFIG_FILE

    def default_store_root(self, name: str) -> Path:
        """
        The profile-owned state root (decision D2).
        Keeps a project's runs/metrics/lock isolated under its
                    profile so statistics are trivially findable.
        name: Profile name.
        Returns: `<home>/profiles/<name>/state`.
        """
        return self.profile_dir(name) / "state"

    def _metadata_path(self, name: str) -> Path:
        """
        A profile's profile.json path.
        name: Profile name.
        Returns: `<home>/profiles/<name>/profile.json`.
        """
        return self.profile_dir(name) / METADATA_FILE

    # -- CRUD ---------------------------------------------------------------------

    def exists(self, name: str) -> bool:
        """
        Whether a profile's metadata is present.
        name: Profile name.
        Returns: True when profile.json exists.
        """
        return self._metadata_path(name).is_file()

    def id_availability(self, name: str) -> bool:
        """
        Check an advisory web ID against complete and incomplete ownership.
        name: Portable profile ID.
        Returns: True only when no case-folded directory or immutable ID collides.
        Raises ProfileError: On malformed IDs or corrupt metadata.
        Note: Creation must recheck while holding an enrollment lock.
        """
        validate_profile_id(name)
        if self.invalid_profiles():
            raise ProfileError("project metadata is corrupt", code="project_corrupt")
        projects = self.list_profiles()
        if len({item.project_id for item in projects}) != len(projects):
            raise ProfileError("duplicate project identity", code="project_corrupt")
        if self.profiles_dir.exists() and any(
            entry.name.casefold() == name.casefold() for entry in self.profiles_dir.iterdir()
        ):
            return False
        return not any(item.project_id == name for item in projects)

    def create(self, name: str, *, overwrite: bool = False, **fields_: object) -> Profile:
        """
        Create and persist a new profile's metadata.
        name: Profile name (directory identity).
        overwrite: Allow replacing an existing profile.
        fields_: Optional Profile fields (repo, platform, runtime...).
        Returns: The saved Profile (created_at/updated_at stamped).
        Raises ProfileError: When the profile exists and overwrite is False.
        """
        if self.exists(name) and not overwrite:
            raise ProfileError(f"profile already exists: {name!r}")
        if "display_name" in fields_:
            validate_display_name(fields_["display_name"])
        allowed = {key: value for key, value in fields_.items()
                   if key in _PROFILE_FIELDS and key != "project_id"}
        now = self._now()
        profile = Profile(name=name, project_id=uuid4().hex,
                          adore_version=__version__, created_at=now, **allowed)
        if "display_name" not in fields_:
            profile.display_name = name
        self.save(profile)
        return profile

    def save(self, profile: Profile) -> None:
        """
        Persist a profile's metadata atomically, stamping updated_at.
        profile: The Profile to write.
        """
        validate_display_name(profile.display_name or profile.name)
        # Without a display name the profile ID is shown.
        profile.display_name = profile.display_name or profile.name
        if not profile.created_at:
            profile.created_at = self._now()
        if not re.fullmatch(r"[0-9a-f]{32}", profile.project_id):
            raise ProfileError(f"invalid project ID for {profile.name!r}")
        profile.updated_at = self._now()
        self._write_json(self._metadata_path(profile.name), asdict(profile))

    def load(self, name: str) -> Profile:
        """
        Load a profile's metadata.
        name: Profile name.
        Returns: The reconstructed Profile.
        Raises ProfileError: When the profile is missing or corrupt (fail
                    closed: reported, never reinitialized).
        """
        path = self._metadata_path(name)
        try:
            if not path.is_file():
                raise ProfileError(f"no such profile: {name!r}")
            for attempt, delay in enumerate((0.0, 0.01, 0.025, 0.05, 0.1)):
                if delay:
                    sleep(delay)
                try:
                    with path.open(encoding="utf-8") as handle:
                        data = json.load(handle)
                    break
                except PermissionError as exc:
                    # Windows CRT reads can report EACCES without winerror during
                    # replacement. Bound that denial like explicit sharing errors.
                    winerror = getattr(exc, "winerror", None)
                    sharing = winerror in (5, 32, 33) or (
                        winerror is None and exc.errno == errno.EACCES)
                    if not sharing or attempt == 4:
                        raise
        except (json.JSONDecodeError, OSError) as exc:
            raise ProfileError(f"corrupt profile.json for {name!r}: {exc}") from exc
        if not isinstance(data, dict):
            raise ProfileError(f"corrupt profile.json for {name!r}: not a JSON object")
        return _profile_from_dict(data, name)

    def list_profiles(self) -> list[Profile]:
        """
        All readable profiles, sorted by name.
        Corrupt entries are skipped here (see invalid_profiles).
        Returns: Loaded Profiles.
        """
        profiles: list[Profile] = []
        for name in self._profile_names():
            try:
                profiles.append(self.load(name))
            except ProfileError:
                continue
        return sorted(profiles, key=lambda profile: profile.name)

    def find_by_id(self, project_id: str) -> Profile | None:
        """
        Resolve an immutable ID from one strict metadata scan.
        project_id: Valid 32-hex project identity.
        Returns: Matching profile, or None when no stored profile has that ID.
        Raises ProfileError: Invalid identity, unreadable metadata or duplicate ID.
        Note: Unlike display listings, identity lookup never skips a failed read.
        """
        if not isinstance(project_id, str) or not re.fullmatch(r"[0-9a-f]{32}", project_id):
            raise ProfileError("invalid project ID")
        try:
            profiles = [self.load(name) for name in self._profile_names()]
        except (ProfileError, OSError) as exc:
            raise ProfileError("project metadata is corrupt") from exc
        matches = [item for item in profiles if item.project_id == project_id]
        if len(matches) > 1:
            raise ProfileError("duplicate project ID")
        return matches[0] if matches else None

    def invalid_profiles(self) -> list[str]:
        """
        Names whose profile.json exists but fails to load.
        The fail-closed counterpart of list_profiles(): these need
                    a human, not a silent recreate.
        Returns: Sorted corrupt profile names.
        """
        broken: list[str] = []
        for name in self._profile_names():
            try:
                self.load(name)
            except ProfileError:
                broken.append(name)
        return sorted(broken)

    def touch(self, name: str) -> Profile:
        """
        Record a use: bump use_count and last_used_at.
        name: Profile name.
        Returns: The updated Profile.
        Raises ProfileError: When the profile is missing or corrupt.
        """
        profile = self.load(name)
        profile.use_count += 1
        profile.last_used_at = self._now()
        self.save(profile)
        return profile

    def rename(self, old: str, new: str) -> None:
        """
        Rename a profile (moves its whole directory).
        The active pointer is repointed when it named the profile.
        old: Existing profile name.
        new: New profile name.
        Raises ProfileError: When old is missing or new already exists.
        """
        if not self.exists(old):
            raise ProfileError(f"no such profile: {old!r}")
        if self.exists(new):
            raise ProfileError(f"profile already exists: {new!r}")
        self.profile_dir(old).replace(self.profile_dir(new))
        profile = self.load(new)  # rewrite metadata name to match the new dir
        self.save(profile)
        if self.get_active() == old:
            self.set_active(new)

    def delete(self, name: str) -> None:
        """
        Remove a profile and everything under it (config + state).
        Idempotent; clears the active pointer when it named the
                    profile. Uses the read-only/reparse-point-tolerant rmtree.
        name: Profile name.
        """
        force_rmtree(self.profile_dir(name))
        if self.get_active() == name:
            self.clear_active()

    # -- active pointer -----------------------------------------------------------

    def get_active(self) -> str | None:
        """
        The active profile name, if one is set and still exists.
        Returns: The active name, or None.
        """
        if not self.active_pointer.is_file():
            return None
        name = self.active_pointer.read_text(encoding="utf-8").strip()
        return name or None

    def set_active(self, name: str) -> None:
        """
        Set the active profile.
        name: Profile name (must exist).
        Raises ProfileError: When the profile does not exist.
        """
        if not self.exists(name):
            raise ProfileError(f"no such profile: {name!r}")
        self.home.mkdir(parents=True, exist_ok=True)
        self.active_pointer.write_text(name + "\n", encoding="utf-8")

    def clear_active(self) -> None:
        """Unset the active profile (idempotent)."""
        self.active_pointer.unlink(missing_ok=True)

    # -- internals ----------------------------------------------------------------

    def _profile_names(self) -> list[str]:
        """
        Directory names under `profiles/` that hold metadata.
        Returns: Candidate profile names (unsorted).
        """
        if not self.profiles_dir.is_dir():
            return []
        return [
            entry.name
            for entry in self.profiles_dir.iterdir()
            if entry.is_dir() and (entry / METADATA_FILE).is_file()
        ]

    def _write_json(self, path: Path, data: dict) -> None:
        """
        Write JSON atomically (tmp file + replace).
        Bound retries for Windows file sharing and keep the previous
                    file until the complete replacement succeeds.
        path: Destination file.
        data: JSON-serializable mapping.
        Raises OSError: When the destination remains unwritable.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
        tmp = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            for delay in (0.02, 0.05, 0.1, 0.2, 0.4):
                try:
                    tmp.replace(path)
                    return
                except PermissionError as exc:
                    # An open reader on Windows can deny replacement of its target.
                    if getattr(exc, "winerror", None) not in (5, 32, 33):
                        raise
                    sleep(delay)
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
