"""Create and verify SHA-256 manifests for local backup directories."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
CHUNK_SIZE = 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


@dataclass(frozen=True)
class VerificationResult:
    missing: tuple[str, ...]
    changed: tuple[str, ...]
    unexpected: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not (self.missing or self.changed or self.unexpected)


def _digest_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def build_manifest(root: Path, exclude: Path | None = None) -> list[FileRecord]:
    """Return sorted hashes for regular files, excluding symlinks and an optional path."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"source directory does not exist or is not a directory: {root}")

    excluded = exclude.expanduser().resolve() if exclude is not None else None
    records: list[FileRecord] = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name
            for name in directories
            if not (current_path / name).is_symlink()
        )
        for name in sorted(filenames):
            path = current_path / name
            if excluded is not None and path.resolve() == excluded:
                continue
            try:
                mode = path.lstat().st_mode
            except OSError:
                raise
            if not stat.S_ISREG(mode):
                continue
            size, digest = _digest_file(path)
            relative = path.relative_to(root).as_posix()
            records.append(FileRecord(relative, size, digest))
    return sorted(records, key=lambda item: item.path)


def write_manifest(records: list[FileRecord], destination: Path, force: bool = False) -> None:
    """Write a JSON manifest atomically; refuse to replace an existing file by default."""
    destination = destination.expanduser()
    if destination.is_symlink():
        raise ValueError("manifest destination must not be a symbolic link")
    if destination.exists() and not force:
        raise FileExistsError(f"manifest already exists (use --force to replace): {destination}")
    document = {
        "schema_version": SCHEMA_VERSION,
        "files": [record.as_dict() for record in records],
    }
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=destination.parent, delete=False
        ) as temporary:
            temporary.write(payload)
            temporary_name = temporary.name
        os.replace(temporary_name, destination)
    finally:
        if temporary_name is not None and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _parse_manifest(document: Any) -> list[FileRecord]:
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"manifest must be an object with schema_version {SCHEMA_VERSION}")
    entries = document.get("files")
    if not isinstance(entries, list):
        raise ValueError("manifest 'files' must be a list")

    records: list[FileRecord] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"manifest file entry {index} must be an object")
        path = entry.get("path")
        size = entry.get("size")
        digest = entry.get("sha256")
        if not isinstance(path, str) or not path or "\\" in path:
            raise ValueError(f"manifest file entry {index} has an invalid path")
        parsed_path = PurePosixPath(path)
        if parsed_path.is_absolute() or any(part in {"", ".", ".."} for part in path.split("/")):
            raise ValueError(f"manifest file entry {index} path must stay relative to the source")
        if path in seen:
            raise ValueError(f"manifest contains duplicate path: {path}")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError(f"manifest file entry {index} has an invalid size")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ValueError(f"manifest file entry {index} has an invalid SHA-256 digest")
        seen.add(path)
        records.append(FileRecord(path, size, digest))
    return records


def read_manifest(path: Path) -> list[FileRecord]:
    """Load and validate a manifest from JSON."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON manifest: {exc}") from exc
    return _parse_manifest(document)


def verify_manifest(root: Path, manifest_path: Path) -> VerificationResult:
    """Compare a saved manifest with the current regular files beneath ``root``."""
    expected_records = read_manifest(manifest_path)
    expected = {record.path: record for record in expected_records}
    actual = {
        record.path: record
        for record in build_manifest(root, exclude=manifest_path)
    }
    missing = tuple(sorted(expected.keys() - actual.keys()))
    unexpected = tuple(sorted(actual.keys() - expected.keys()))
    changed = tuple(
        sorted(
            path
            for path in expected.keys() & actual.keys()
            if expected[path].size != actual[path].size
            or expected[path].sha256 != actual[path].sha256
        )
    )
    return VerificationResult(missing, changed, unexpected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create_parser = commands.add_parser("create", help="write a SHA-256 manifest")
    create_parser.add_argument("source", type=Path, help="directory to inventory")
    create_parser.add_argument("manifest", type=Path, help="JSON output file")
    create_parser.add_argument(
        "--force", action="store_true", help="replace an existing manifest file"
    )
    verify_parser = commands.add_parser("verify", help="compare a directory with a manifest")
    verify_parser.add_argument("source", type=Path, help="directory to check")
    verify_parser.add_argument("manifest", type=Path, help="JSON manifest to verify")
    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            records = build_manifest(args.source, exclude=args.manifest)
            write_manifest(records, args.manifest, force=args.force)
            print(f"Created {args.manifest} with {len(records)} file(s).")
            return 0
        result = verify_manifest(args.source, args.manifest)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    if result.ok:
        print("OK: all listed files match; no unexpected regular files found.")
        return 0
    for label, paths in (
        ("Missing", result.missing),
        ("Changed", result.changed),
        ("Unexpected", result.unexpected),
    ):
        for path in paths:
            print(f"{label}: {path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
