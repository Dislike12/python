"""A small local-first habit tracker with a JSON-backed command line."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

DEFAULT_DATA = Path.home() / ".habit_tracker.json"


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD format") from exc


class HabitStore:
    """Persist habits and completion dates in one local JSON document."""

    def __init__(self, path: str | Path = DEFAULT_DATA) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"habits": []}
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read habit data: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(document.get("habits"), list):
            raise ValueError("habit data must contain a 'habits' list")
        if any(not isinstance(item, dict) for item in document["habits"]):
            raise ValueError("each habit record must be an object")
        return document

    def _save(self, document: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f"{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(document, handle, indent=2, sort_keys=True)
                handle.write("\n")
                temporary = Path(handle.name)
            os.replace(temporary, self.path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def add(self, name: str, created_on: str | date | None = None) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("habit name cannot be empty")
        document = self._load()
        if any(
            item.get("name", "").casefold() == clean_name.casefold() for item in document["habits"]
        ):
            raise ValueError(f"habit already exists: {clean_name}")
        start = _as_date(created_on) if created_on is not None else date.today()
        document["habits"].append(
            {"name": clean_name, "created_on": start.isoformat(), "completed": []}
        )
        self._save(document)

    def mark_done(self, name: str, on: str | date | None = None) -> bool:
        target = _as_date(on) if on is not None else date.today()
        document = self._load()
        habit = next(
            (
                item
                for item in document["habits"]
                if item.get("name", "").casefold() == name.strip().casefold()
            ),
            None,
        )
        if habit is None:
            raise ValueError(f"unknown habit: {name}")
        completions = habit.setdefault("completed", [])
        if target.isoformat() in completions:
            return False
        completions.append(target.isoformat())
        completions.sort()
        self._save(document)
        return True

    def report(self, as_of: str | date | None = None) -> list[dict[str, Any]]:
        target = _as_date(as_of) if as_of is not None else date.today()
        result = []
        for habit in self._load()["habits"]:
            completed = set(habit.get("completed", []))
            cursor = target if target.isoformat() in completed else target - timedelta(days=1)
            streak = 0
            while cursor.isoformat() in completed:
                streak += 1
                cursor -= timedelta(days=1)
            result.append({"name": habit["name"], "total": len(completed), "streak": streak})
        return sorted(result, key=lambda row: row["name"].casefold())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="local JSON data file")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="create a habit")
    add.add_argument("name")
    done = commands.add_parser("done", help="record today's completion (or a supplied date)")
    done.add_argument("name")
    done.add_argument("--date", help="completion date in YYYY-MM-DD format")
    report = commands.add_parser("report", help="show totals and current streaks")
    report.add_argument("--date", help="date at which to calculate streaks")
    args = parser.parse_args(argv)
    store = HabitStore(args.data)
    try:
        if args.command == "add":
            store.add(args.name)
            print(f"Added habit: {args.name.strip()}")
        elif args.command == "done":
            changed = store.mark_done(args.name, args.date)
            print("Recorded completion." if changed else "Already recorded for that day.")
        else:
            rows = store.report(args.date)
            if not rows:
                print("No habits yet. Add one with the 'add' command.")
            for row in rows:
                print(f"{row['name']}: {row['total']} completion(s), {row['streak']}-day streak")
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
