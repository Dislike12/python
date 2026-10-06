# Backup Manifest

A small, standard-library command-line tool for checking whether files in a local backup still match a saved SHA-256 inventory. It is useful for detecting accidental edits, omissions, or additions between backup copies. It reads files and writes a JSON manifest; it does not copy, repair, or delete data.

## Setup and usage

Requires Python 3.10 or newer. No installation or third-party packages are needed. Run commands from the repository root.

Create a manifest (the destination must not already exist unless `--force` is supplied):

```bash
python -m projects.backup_manifest.app create /path/to/backup /path/to/backup-manifest.json
```

Verify the directory later:

```bash
python -m projects.backup_manifest.app verify /path/to/backup /path/to/backup-manifest.json
```

A successful verification exits with status `0`. Any missing, changed, or unexpected regular file is listed and causes exit status `1`. Invalid input and file-system errors are reported as command-line errors. The manifest can also be stored inside the source directory; that exact manifest path is excluded from the inventory.

Run its focused tests with:

```bash
python -m unittest tests.test_backup_manifest -v
```

## Limitations

- SHA-256 detects content changes but does not prove who created a manifest or protect it from tampering. Keep a trusted copy of the manifest separately when that distinction matters.
- The tool hashes regular files only and skips symbolic links and non-regular files. It does not preserve permissions, timestamps, ownership, or empty directories.
- Files can change while a scan is running; run verification against a stable backup for dependable results.
- File names appear in the manifest. The JSON file is not encrypted, and the tool does not compare files across machines or perform backup/restore operations.

## Privacy and safety

All processing is local and uses Python's standard library; no network requests or telemetry are made. The tool only reads source files. It writes a new manifest atomically and refuses to overwrite an existing destination unless `--force` is given. Review where you store the manifest because its paths and hashes may reveal information about the backup contents. Never treat an unsigned manifest as an authenticity guarantee.
