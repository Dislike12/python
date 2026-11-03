"""Profile local CSV structure, missing values, inferred types, and sample values."""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, TextIO

SCHEMA_VERSION = 1
MAX_EXAMPLES = 3
_INTEGER_RE = re.compile(r"^[+-]?\d+$")


@dataclass
class ColumnProfile:
    name: str
    non_empty: int = 0
    missing: int = 0
    value_types: set[str] = field(default_factory=set)
    examples: list[str] = field(default_factory=list)

    @property
    def inferred_type(self) -> str:
        """Return a simple type label based on all non-empty values seen."""
        if not self.value_types:
            return "empty"
        if len(self.value_types) == 1:
            return next(iter(self.value_types))
        if self.value_types <= {"integer", "number"}:
            return "number"
        return "mixed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "non_empty": self.non_empty,
            "missing": self.missing,
            "inferred_type": self.inferred_type,
            "examples": self.examples,
        }


@dataclass
class CSVProfile:
    delimiter: str
    rows: int
    rows_with_missing: int
    malformed_rows: int
    extra_cells: int
    columns: list[ColumnProfile]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "delimiter": self.delimiter,
            "rows": self.rows,
            "columns_count": len(self.columns),
            "rows_with_missing": self.rows_with_missing,
            "malformed_rows": self.malformed_rows,
            "extra_cells": self.extra_cells,
            "columns": [column.as_dict() for column in self.columns],
        }


def _infer_value_type(value: str) -> str:
    normalized = value.strip()
    if normalized.casefold() in {"true", "false"}:
        return "boolean"
    if _INTEGER_RE.fullmatch(normalized):
        return "integer"
    try:
        number = Decimal(normalized)
    except InvalidOperation:
        pass
    else:
        if number.is_finite():
            return "number"
    try:
        date.fromisoformat(normalized)
    except ValueError:
        try:
            datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            return "text"
    return "date"


def _make_reader(stream: TextIO, delimiter: str | None) -> tuple[csv.reader, str]:
    if delimiter is not None:
        if len(delimiter) != 1:
            raise ValueError("delimiter must be exactly one character")
        return csv.reader(stream, delimiter=delimiter, strict=True), delimiter

    sample = stream.read(4096)
    stream.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return csv.reader(stream, dialect=dialect, strict=True), dialect.delimiter


def profile_csv(path: Path, delimiter: str | None = None) -> CSVProfile:
    """Return a streaming profile of a CSV file whose first record is a header."""
    path = path.expanduser()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader, actual_delimiter = _make_reader(stream, delimiter)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("CSV file is empty; expected a header row") from exc
        if not header:
            raise ValueError("CSV header row is empty")

        names = [name.strip() for name in header]
        if any(not name for name in names):
            raise ValueError("CSV header names must not be blank")
        if len(set(names)) != len(names):
            raise ValueError("CSV header names must be unique after trimming whitespace")
        columns = [ColumnProfile(name=name) for name in names]
        rows = 0
        rows_with_missing = 0
        malformed_rows = 0
        extra_cells = 0

        try:
            for record in reader:
                rows += 1
                if len(record) != len(columns):
                    malformed_rows += 1
                if len(record) > len(columns):
                    extra_cells += len(record) - len(columns)
                record_has_missing = False
                for index, column in enumerate(columns):
                    if index >= len(record) or not record[index].strip():
                        column.missing += 1
                        record_has_missing = True
                        continue
                    value = record[index]
                    column.non_empty += 1
                    column.value_types.add(_infer_value_type(value))
                    if value not in column.examples and len(column.examples) < MAX_EXAMPLES:
                        column.examples.append(value)
                if record_has_missing:
                    rows_with_missing += 1
        except csv.Error as exc:
            raise ValueError(f"invalid CSV near line {reader.line_num}: {exc}") from exc

    return CSVProfile(
        delimiter=actual_delimiter,
        rows=rows,
        rows_with_missing=rows_with_missing,
        malformed_rows=malformed_rows,
        extra_cells=extra_cells,
        columns=columns,
    )


def _format_text(profile: CSVProfile) -> str:
    lines = [
        f"Delimiter: {profile.delimiter!r}",
        f"Rows: {profile.rows}",
        f"Columns: {len(profile.columns)}",
        f"Rows with missing values: {profile.rows_with_missing}",
        f"Rows with a field-count mismatch: {profile.malformed_rows}",
        f"Extra cells: {profile.extra_cells}",
        "Column profiles:",
    ]
    for column in profile.columns:
        examples = ", ".join(repr(value) for value in column.examples) or "(none)"
        lines.append(
            f"- {column.name}: {column.inferred_type}; "
            f"non-empty={column.non_empty}; missing={column.missing}; "
            f"examples={examples}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="CSV file to inspect (read only)")
    parser.add_argument(
        "--delimiter",
        metavar="CHAR",
        help=(
            "one-character separator; auto-detected from comma, semicolon, "
            "tab, or pipe by default"
        ),
    )
    parser.add_argument("--json", action="store_true", help="print a machine-readable JSON report")
    args = parser.parse_args(argv)
    try:
        profile = profile_csv(args.source, delimiter=args.delimiter)
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(profile.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_format_text(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
