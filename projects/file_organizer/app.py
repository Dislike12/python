"""Preview or apply a collision-safe file organization by extension."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def plan_moves(directory: str | Path) -> list[tuple[Path, Path]]:
    """Plan moves for direct child files; do not follow symlinks or move anything."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    reserved: set[Path] = set()
    planned: list[tuple[Path, Path]] = []
    for source in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
        if source.is_symlink() or not source.is_file():
            continue
        extension = source.suffix.lower().lstrip(".") or "no_extension"
        bucket = root / extension
        candidate = bucket / source.name
        index = 2
        while candidate.exists() or candidate in reserved:
            candidate = bucket / f"{source.stem}_{index}{source.suffix}"
            index += 1
        reserved.add(candidate)
        planned.append((source, candidate))
    return planned


def apply_moves(plan: list[tuple[Path, Path]]) -> list[Path]:
    """Apply a plan without replacing an existing destination."""
    moved = []
    for source, destination in plan:
        if not source.exists() or source.is_symlink():
            raise FileNotFoundError(f"source changed since preview: {source}")
        if destination.exists():
            raise FileExistsError(f"destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        moved.append(destination)
    return moved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory", type=Path, help="directory whose direct child files to organize"
    )
    parser.add_argument(
        "--apply", action="store_true", help="perform the displayed moves (default is preview only)"
    )
    args = parser.parse_args(argv)
    try:
        plan = plan_moves(args.directory)
        root = Path(args.directory).expanduser().resolve()
        for source, destination in plan:
            print(f"{source.name} -> {destination.relative_to(root)}")
        if args.apply:
            apply_moves(plan)
            print(f"Moved {len(plan)} file(s).")
        else:
            print(f"Preview only: {len(plan)} move(s). Add --apply to move files.")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
