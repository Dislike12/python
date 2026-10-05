# Flashcard Coach

A dependency-free, local flashcard CLI. Cards are stored in `~/.flashcard_coach.json` by default; pass `--data PATH` before the command to use another file.

```bash
python -m projects.flashcard_coach.app --data /tmp/cards.json add "HTTP stands for?" "Hypertext Transfer Protocol"
python -m projects.flashcard_coach.app --data /tmp/cards.json due
python -m projects.flashcard_coach.app --data /tmp/cards.json review CARD_ID good
```

A `good` review schedules intervals of 1, 3, 7, and 14 days, then grows the interval up to a 60-day cap. `again` resets the sequence and schedules the card for tomorrow. The tool prints questions, not answers, in the due list. It is a simple learning aid, not a full adaptive learning system; all data stays in the local JSON file.
