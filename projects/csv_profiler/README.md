# CSV Profiler

A standard-library command-line tool for quickly inspecting a local CSV before importing or sharing it. It reports record and column counts, missing cells, rows whose field count differs from the header, inferred value types, and a few sample values. It streams records and keeps only column summaries and up to three examples per column in memory.

## Setup and usage

Requires Python 3.10 or newer. No installation or third-party packages are needed. Run commands from the repository root:

```bash
python -m projects.csv_profiler.app /path/to/data.csv
python -m projects.csv_profiler.app /path/to/data.csv --json
```

The first record is treated as the header. Comma, semicolon, tab, and pipe delimiters are detected from a sample; specify another one-character separator explicitly when needed:

```bash
python -m projects.csv_profiler.app /path/to/data.csv --delimiter ';'
```

The report shows the number of data records, rows with at least one missing cell, field-count mismatches, extra cells, and for each column its non-empty and missing cell counts, inferred type, and up to three distinct examples. Whitespace-only values count as missing. Type inference recognizes booleans, integers, finite decimal numbers, ISO dates and date-times, text, mixed values, and empty columns. Use `--json` for a machine-readable report with schema version `1`.

Run its focused tests with:

```bash
python -m unittest tests.test_csv_profiler -v
```

## Limitations

- Type inference is heuristic, not a schema validator. For example, locale-specific dates and numeric formats are reported as text.
- Delimiter detection uses a short sample; specify `--delimiter` if the file is ambiguous.
- The first CSV record must contain non-empty, unique column names. Records with a different number of fields are counted and reported, not repaired.
- Examples may contain sensitive data. Review the report before sharing it, especially when using `--json`.

## Privacy and safety

The tool reads the selected file locally, uses only Python's standard library, makes no network requests, and does not modify the source file. The report includes sample field values, so handle it with the same care as the original CSV.
