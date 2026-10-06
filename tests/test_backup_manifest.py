from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from projects.backup_manifest.app import (
    FileRecord,
    build_manifest,
    read_manifest,
    verify_manifest,
    write_manifest,
)


class BackupManifestTests(unittest.TestCase):
    def test_builds_sorted_hashes_and_skips_manifest_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "backup"
            root.mkdir()
            (root / "z.txt").write_text("last", encoding="utf-8")
            (root / "a.txt").write_text("first", encoding="utf-8")
            manifest = root / "manifest.json"

            records = build_manifest(root, exclude=manifest)

            self.assertEqual([record.path for record in records], ["a.txt", "z.txt"])
            self.assertEqual(records[0].size, 5)
            self.assertEqual(records[0].sha256, hashlib.sha256(b"first").hexdigest())

    def test_verification_reports_missing_changed_and_unexpected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "backup"
            root.mkdir()
            (root / "changed.txt").write_text("before", encoding="utf-8")
            (root / "missing.txt").write_text("gone", encoding="utf-8")
            manifest = Path(temporary) / "manifest.json"
            write_manifest(build_manifest(root), manifest)

            (root / "changed.txt").write_text("after", encoding="utf-8")
            (root / "missing.txt").unlink()
            (root / "new.txt").write_text("new", encoding="utf-8")

            result = verify_manifest(root, manifest)

            self.assertFalse(result.ok)
            self.assertEqual(result.missing, ("missing.txt",))
            self.assertEqual(result.changed, ("changed.txt",))
            self.assertEqual(result.unexpected, ("new.txt",))

    def test_manifest_in_source_directory_is_not_counted_as_unexpected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "backup"
            root.mkdir()
            (root / "note.txt").write_text("saved", encoding="utf-8")
            manifest = root / "manifest.json"
            write_manifest(build_manifest(root, exclude=manifest), manifest)

            self.assertTrue(verify_manifest(root, manifest).ok)

    def test_refuses_overwrite_without_force_and_round_trips_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "manifest.json"
            original = [FileRecord("note.txt", 1, hashlib.sha256(b"x").hexdigest())]
            write_manifest(original, destination)
            self.assertEqual(read_manifest(destination), original)
            with self.assertRaises(FileExistsError):
                write_manifest([], destination)
            write_manifest([], destination, force=True)
            self.assertEqual(read_manifest(destination), [])

    def test_rejects_path_traversal_and_invalid_digest(self) -> None:
        invalid_documents = (
            {"path": "../outside", "size": 0, "sha256": "0" * 64},
            {"path": "safe.txt", "size": 0, "sha256": "not-a-digest"},
        )
        for entry in invalid_documents:
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "manifest.json"
                path.write_text(
                    json.dumps({"schema_version": 1, "files": [entry]}),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    read_manifest(path)


if __name__ == "__main__":
    unittest.main()
