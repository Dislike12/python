# Habit Tracker

A local-first habit log for daily check-ins and simple streak summaries. It uses only the standard library and stores data in a JSON file on your machine.

## Quick start

```bash
python -m projects.habit_tracker.app --data /tmp/habits.json add "Read for 20 minutes"
python -m projects.habit_tracker.app --data /tmp/habits.json done "Read for 20 minutes" --date 2026-10-05
python -m projects.habit_tracker.app --data /tmp/habits.json report --date 2026-10-05
```

Omit `--data` to use `~/.habit_tracker.json`. Repeating `done` for the same habit and day is safe and does not double-count. A current streak includes today if completed; otherwise it counts consecutive days through yesterday.

## Data and limits

The JSON file is written atomically to reduce the chance of a partial save. The tool does not sync or upload data. Streaks are calendar-day based and use the date supplied to the command (or the machine's local date by default); this is not a reminder service.
