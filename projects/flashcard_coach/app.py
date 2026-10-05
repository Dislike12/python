"""A local flashcard coach with a small, deterministic review schedule."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

DEFAULT_DATA = Path.home() / ".flashcard_coach.json"


def new_card(question: str, answer: str, today: date | None = None) -> dict[str, Any]:
    question, answer = question.strip(), answer.strip()
    if not question or not answer:
        raise ValueError("question and answer must not be empty")
    start = today or date.today()
    return {
        "id": uuid.uuid4().hex[:10],
        "question": question,
        "answer": answer,
        "due_date": start.isoformat(),
        "interval_days": 0,
        "repetitions": 0,
    }


def due_cards(cards: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    target = today or date.today()
    return sorted(
        (card for card in cards if date.fromisoformat(card["due_date"]) <= target),
        key=lambda card: (card["due_date"], card["id"]),
    )


def review_card(card: dict[str, Any], grade: str, today: date | None = None) -> dict[str, Any]:
    if grade not in {"again", "good"}:
        raise ValueError("grade must be 'again' or 'good'")
    target = today or date.today()
    updated = dict(card)
    if grade == "again":
        updated["interval_days"] = 1
        updated["repetitions"] = 0
    else:
        repetitions = int(card.get("repetitions", 0)) + 1
        interval = {1: 1, 2: 3, 3: 7, 4: 14}.get(repetitions)
        if interval is None:
            interval = min(max(int(card.get("interval_days", 14)) * 2, 14), 60)
        updated["repetitions"] = repetitions
        updated["interval_days"] = interval
    updated["due_date"] = (target + timedelta(days=updated["interval_days"])).isoformat()
    return updated


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        cards = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read flashcards: {exc}") from exc
    if not isinstance(cards, list) or any(not isinstance(card, dict) for card in cards):
        raise ValueError("flashcard data must be a list of objects")
    return cards


def _save(path: Path, cards: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(cards, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="local JSON data file")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="add a flashcard")
    add.add_argument("question")
    add.add_argument("answer")
    commands.add_parser("due", help="list cards due today")
    review = commands.add_parser("review", help="review a card by id")
    review.add_argument("card_id")
    review.add_argument("grade", choices=("again", "good"))
    args = parser.parse_args(argv)
    try:
        cards = _load(args.data)
        if args.command == "add":
            card = new_card(args.question, args.answer)
            cards.append(card)
            _save(args.data, cards)
            print(f"Added {card['id']}: {card['question']}")
        elif args.command == "due":
            due = due_cards(cards)
            if not due:
                print("No cards due today.")
            for card in due:
                print(f"{card['id']}  {card['question']}  (answer hidden; due {card['due_date']})")
        else:
            index = next(
                (i for i, card in enumerate(cards) if card.get("id") == args.card_id), None
            )
            if index is None:
                raise ValueError(f"unknown card id: {args.card_id}")
            cards[index] = review_card(cards[index], args.grade)
            _save(args.data, cards)
            print(f"Reviewed {args.card_id}: next due {cards[index]['due_date']}")
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
