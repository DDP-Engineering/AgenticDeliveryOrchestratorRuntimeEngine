#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file       test_portable.py
@brief      Offline contract checks for portable delivery trust boundaries.
@details    Exercises the public verifier and command argument validation using
            temporary isolated media; never downloads or starts services.
"""

# IMPORTS
import hashlib
import importlib.util
import io
import json
import socket
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

# CONSTANTS
REPO = Path(__file__).resolve().parents[2]
WORK = Path(tempfile.gettempdir())
SPEC = importlib.util.spec_from_file_location("portable_launcher",
                                             REPO / "02_Tools/portable/launch.py")
LAUNCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAUNCHER)
PACKAGE_SPEC = importlib.util.spec_from_file_location("portable_packager", REPO / "02_Tools/create_package.py")
PACKAGER = importlib.util.module_from_spec(PACKAGE_SPEC)
PACKAGE_SPEC.loader.exec_module(PACKAGER)


# PUBLIC API / TESTS
class PortableDocumentation(unittest.TestCase):
    """@brief User distributions contain a fixed practical guide set."""

    def test_only_curated_user_guides_are_copied(self) -> None:
        """@brief Extra engineering and handoff files never enter the user documentation."""
        with tempfile.TemporaryDirectory(prefix="portable-doc-unit-", dir=WORK) as temp:
            source = Path(temp) / "source"
            source.mkdir()
            body = (REPO / "02_Tools/portable/README.md").read_text(encoding="utf-8")
            for name in (*PACKAGER.USER_DOC_FILES, "Code_Style.md", "Web_UX_Acceptance_Handoff.md"):
                (source / name).write_text(body, encoding="utf-8")
            (source / "Operator_Cheat_Sheets").mkdir()
            destination = Path(temp) / "Documentation"
            PACKAGER.copy_user_documentation(destination, source=source)
            self.assertEqual({p.name for p in destination.iterdir()}, set(PACKAGER.USER_DOC_FILES))
            self.assertEqual((destination / "README.md").read_text(encoding="utf-8"), body)

    def test_missing_guide_fails_before_copying(self) -> None:
        """@brief Incomplete source documentation fails before staging a partial guide set."""
        with tempfile.TemporaryDirectory(prefix="portable-doc-unit-", dir=WORK) as temp:
            source = Path(temp) / "source"
            source.mkdir()
            (source / "README.md").write_text(
                (REPO / "02_Tools/portable/README.md").read_text(encoding="utf-8"), encoding="utf-8")
            destination = Path(temp) / "Documentation"
            with self.assertRaisesRegex(RuntimeError, "guide missing"):
                PACKAGER.copy_user_documentation(destination, source=source)
            self.assertFalse(destination.exists())

    @unittest.skipIf(sys.platform == "win32", "POSIX document-link boundary")
    def test_linked_guide_fails_before_copying(self) -> None:
        """@brief A linked guide cannot escape the curated source boundary."""
        with tempfile.TemporaryDirectory(prefix="portable-doc-unit-", dir=WORK) as temp:
            source = Path(temp) / "source"
            source.mkdir()
            for name in PACKAGER.USER_DOC_FILES:
                (source / name).symlink_to(REPO / "02_Tools/portable/README.md")
            destination = Path(temp) / "Documentation"
            with self.assertRaisesRegex(RuntimeError, "guide missing or linked"):
                PACKAGER.copy_user_documentation(destination, source=source)
            self.assertFalse(destination.exists())


class PortableDelivery(unittest.TestCase):
    """@brief Verify media contracts without depending on packaging libraries."""

    def setUp(self) -> None:
        """@brief Create tiny delivery media inside the delivery output tree."""
        self.temporary = tempfile.TemporaryDirectory(prefix="portable-unit-",
                                                      dir=WORK)
        self.addCleanup(self.temporary.cleanup)
        self.bundle = Path(self.temporary.name)
        self.payload = self.bundle / "payload.txt"
        self.payload.write_bytes(b"content")
        self.manifest = {
            "schema": 1, "version": "0.13.0", "architecture": "x64",
            "system": platform.system().lower(), "python_version": platform.python_version(),
            "files": {"payload.txt": hashlib.sha256(b"content").hexdigest()},
        }
        self.write_manifest()

    def write_manifest(self) -> None:
        """@brief Materialize the supplied external manifest, including bad values."""
        (self.bundle / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_complete_inventory_verifies(self) -> None:
        """@brief A complete, host-matched manifest returns the recorded release."""
        self.assertEqual(LAUNCHER.verify(self.bundle)["version"], "0.13.0")

    def test_corrupt_missing_and_unlisted_files_fail_closed(self) -> None:
        """@brief Media corruption, absence and unlisted files are explicit errors."""
        self.payload.write_bytes(b"changed")
        with self.assertRaises(LAUNCHER.DeliveryError):
            LAUNCHER.verify(self.bundle)
        self.payload.unlink()
        with self.assertRaises(LAUNCHER.DeliveryError):
            LAUNCHER.verify(self.bundle)
        self.payload.write_bytes(b"content")
        (self.bundle / "unlisted.txt").write_bytes(b"extra")
        with self.assertRaises(LAUNCHER.DeliveryError):
            LAUNCHER.verify(self.bundle)

    def test_invalid_manifest_and_host_fail_closed(self) -> None:
        """@brief Corrupt schema, inventory and host metadata never start a service."""
        for field, value in (("schema", True), ("schema", 99), ("system", "other"),
                             ("architecture", "arm64"), ("python_version", "0.0.0"),
                             ("files", []), ("files", {})):
            with self.subTest(field=field, value=value):
                original = self.manifest[field]
                self.manifest[field] = value
                self.write_manifest()
                with self.assertRaises(LAUNCHER.DeliveryError):
                    LAUNCHER.verify(self.bundle)
                self.manifest[field] = original
        (self.bundle / "manifest.json").write_bytes(b"{truncated")
        with self.assertRaises(LAUNCHER.DeliveryError):
            LAUNCHER.verify(self.bundle)

    def test_manifest_paths_cannot_escape_bundle(self) -> None:
        """@brief External paths, traversal and malformed digests are refused."""
        for name in ("../outside", "/absolute", "C:/absolute", "a\\b", "a/./b", "a//b"):
            with self.subTest(path=name):
                self.manifest["files"] = {name: "0" * 64}
                self.write_manifest()
                with self.assertRaises(LAUNCHER.DeliveryError):
                    LAUNCHER.verify(self.bundle)
        self.manifest["files"] = {"payload.txt": "invalid"}
        self.write_manifest()
        with self.assertRaises(LAUNCHER.DeliveryError):
            LAUNCHER.verify(self.bundle)

    def test_invalid_launcher_arguments_fail_before_media_access(self) -> None:
        """@brief Invalid external limits fail before package or user-state access."""
        for arguments in (("--port", "0"), ("--startup-timeout", "999"),
                          ("--restart-limit", "-1"), ("--service", "worker")):
            result = subprocess.run([sys.executable, str(REPO / "02_Tools/portable/launch.py"),
                                     *arguments], capture_output=True, timeout=10, check=False)
            self.assertEqual(result.returncode, 2)

    def test_packager_rejects_output_outside_delivery(self) -> None:
        """@brief An output escape is rejected before network or build operations."""
        result = subprocess.run([sys.executable, str(REPO / "02_Tools/create_package.py"),
                                 "--output", "02_Tools/invalid-output"],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_failed_service_pairs_exhaust_the_explicit_restart_limit(self) -> None:
        """@brief Public startup stops after two failed pairs with restart limit one."""
        root_module = ModuleType("adore")
        profile_module = ModuleType("adore.profiles")
        profile_module.adore_home = lambda: self.bundle
        created = []
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            test_port = probe.getsockname()[1]

        def spawn(*_args, **_kwargs):
            """@brief Simulate failed external processes without starting any CLI."""
            child = SimpleNamespace(stdout=io.StringIO(), poll=lambda: 1,
                                    wait=lambda **_kwargs: 1)
            created.append(child)
            return child

        with tempfile.TemporaryDirectory(prefix="portable-unit-",
                                          dir=WORK) as home, \
                mock.patch.dict(sys.modules, {"adore": root_module,
                                               "adore.profiles": profile_module}), \
                mock.patch.object(LAUNCHER, "verify", return_value=self.manifest), \
                mock.patch.object(LAUNCHER.signal, "signal"), \
                mock.patch.object(LAUNCHER.subprocess, "Popen", side_effect=spawn):
            original_handlers = set(LAUNCHER.LOG.handlers)
            try:
                with self.assertRaisesRegex(LAUNCHER.DeliveryError, "could not stay running"):
                    LAUNCHER.main(["--home", home, "--no-browser", "--restart-limit", "1",
                                   "--port", str(test_port)])
                self.assertEqual(len(created), 4)
                self.assertFalse((Path(home) / ".launcher.json").exists())
            finally:
                # The CLI process normally owns these handlers until exit. This
                # in-process test must release its file before Windows cleanup.
                for handler in set(LAUNCHER.LOG.handlers) - original_handlers:
                    LAUNCHER.LOG.removeHandler(handler)
                    handler.close()

    @unittest.skipIf(sys.platform == "win32", "POSIX symlink trust-boundary case")
    def test_media_links_are_refused(self) -> None:
        """@brief A linked payload is rejected even when its bytes match the manifest."""
        target = self.bundle / "target.txt"
        self.payload.rename(target)
        self.payload.symlink_to(target)
        with self.assertRaises(LAUNCHER.DeliveryError):
            LAUNCHER.verify(self.bundle)


if __name__ == "__main__":
    unittest.main()

# END OF FILE
