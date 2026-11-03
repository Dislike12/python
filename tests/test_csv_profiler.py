from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from projects.csv_profiler.app import main, profile_csv


class CSVProfilerTests(unittest.TestCase):
    def test_auto_detects_comma_and_profiles_quoted_values_and_bom(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "contacts.csv"
            source.write_text(
                '\ufeffname,age,note\n"Ada, Lovelace",36,"first line\nsecond line"\n',
                encoding="utf-8",
            )

            profile = profile_csv(source)

            self.assertEqual(profile.delimiter, ",")
            self.assertEqual(profile.rows, 1)
            self.assertEqual(profile.malformed_rows, 0)
            self.assertEqual(profile.columns[0].examples, ["Ada, Lovelace"])
            self.assertEqual(profile.columns[0].inferred_type, "text")
            self.assertEqual(profile.columns[1].inferred_type, "integer")
            self.assertEqual(profile.columns[2].examples, ["first line\nsecond line"])

    def test_explicit_delimiter_reports_missing_values_and_ragged_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "measurements.csv"
            source.write_text(
                "id;value;note\n1;2.5;ok\n2;;\n3;4\n4;5;ok;unexpected\n",
                encoding="utf-8",
            )

            profile = profile_csv(source, delimiter=";")

            self.assertEqual(profile.rows, 4)
            self.assertEqual(profile.rows_with_missing, 2)
            self.assertEqual(profile.malformed_rows, 2)
            self.assertEqual(profile.extra_cells, 1)
            self.assertEqual(profile.columns[1].missing, 1)
            self.assertEqual(profile.columns[2].missing, 2)
            self.assertEqual(profile.columns[1].inferred_type, "number")

    def test_infers_boolean_date_mixed_and_empty_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "types.csv"
            source.write_text(
                "enabled,created,mixed,unused\ntrue,2026-11-03,1,\nfalse,2026-11-04,unknown,\n",
                encoding="utf-8",
            )

            columns = profile_csv(source).columns

            self.assertEqual(
                [column.inferred_type for column in columns],
                ["boolean", "date", "mixed", "empty"],
            )
            self.assertEqual(columns[3].missing, 2)

    def test_rejects_empty_duplicate_and_blank_headers(self) -> None:
        invalid_contents = ("", "a,a\n1,2\n", "a, \n1,2\n")
        for content in invalid_contents:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / "invalid.csv"
                source.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    profile_csv(source)

    def test_rejects_multi_character_delimiter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "data.csv"
            source.write_text("a,b\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly one character"):
                profile_csv(source, delimiter="||")

    def test_json_cli_smoke_test(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "data.csv"
            source.write_text("score\n7\n", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                result = main([str(source), "--json"])

            report = json.loads(output.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(report["rows"], 1)
            self.assertEqual(report["columns"][0]["inferred_type"], "integer")


if __name__ == "__main__":
    unittest.main()
