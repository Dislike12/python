# Project Catalog

These projects are standalone Python tools under active development. Each has its own README and command-line entry point. The machine-readable [`catalog.json`](catalog.json) is the source of truth for project slugs and summaries; check it before adding another project so daily additions stay distinct.

| # | Project | Summary |
| --- | --- | --- |
| 1 | [Habit Tracker](habit_tracker/README.md) | Local habit log with daily check-ins and current streak summaries. |
| 2 | [Safe File Organizer](file_organizer/README.md) | Dry-run-first file sorting with collision-safe destinations. |
| 3 | [Flashcard Coach](flashcard_coach/README.md) | Local flashcards with deterministic spaced-repetition intervals. |
| 4 | [Expense Splitter](expense_splitter/README.md) | Exact-cent shared-expense splitting and settlement suggestions. |
| 5 | [URL Health Checker](url_health/README.md) | Bounded-time HTTP(S) checks with clear status reporting. |
| 6 | [Backup Manifest](backup_manifest/README.md) | Create and verify local backup inventories with SHA-256 hashes. |

Run all project tests from the repository root with `python -m unittest discover -s tests -v`. CI also runs Ruff for `projects/` and `tests/` on supported Python versions.
