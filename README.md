# Python

A growing collection of practical, self-contained Python projects and learning tools. This repository now has six command-line applications under [`projects/`](projects/README.md).

## Projects

| Project | What it does |
| --- | --- |
| [Habit Tracker](projects/habit_tracker/README.md) | Track daily habits and streaks in a local JSON file. |
| [Safe File Organizer](projects/file_organizer/README.md) | Preview file moves by extension; moving requires an explicit `--apply`. |
| [Flashcard Coach](projects/flashcard_coach/README.md) | Review local flashcards with a simple spaced-repetition schedule. |
| [Expense Splitter](projects/expense_splitter/README.md) | Split shared expenses to the cent and calculate settlements. |
| [URL Health Checker](projects/url_health/README.md) | Check HTTP(S) endpoints with a timeout and readable status. |
| [Backup Manifest](projects/backup_manifest/README.md) | Create and verify local backup inventories using SHA-256 hashes. |

See the [project catalog](projects/README.md) for the full index. The machine-readable [`projects/catalog.json`](projects/catalog.json) is the source of truth for existing project slugs and helps future additions avoid duplicates.

## Run a project

Run commands from the repository root. For example:

```bash
python -m projects.habit_tracker.app --help
python -m projects.file_organizer.app --help
python -m projects.flashcard_coach.app --help
python -m projects.expense_splitter.app --help
python -m projects.url_health.app --help
python -m projects.backup_manifest.app --help
```

Projects use only the Python standard library. Personal data stays in local files; the tools do not upload files or records.

## Tests and lint

```bash
python -m unittest discover -s tests -v
python -m pip install ruff
ruff check projects tests
```

GitHub Actions runs tests, Ruff, and compilation on Python 3.10, 3.11, and 3.12. Each project is documented and tested independently.
