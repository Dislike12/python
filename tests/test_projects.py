from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from projects.expense_splitter.app import calculate_settlements
from projects.file_organizer.app import apply_moves, plan_moves
from projects.flashcard_coach.app import due_cards, new_card, review_card
from projects.habit_tracker.app import HabitStore
from projects.url_health.app import check_url, validate_url


class HabitTrackerTests(unittest.TestCase):
    def test_add_check_in_and_current_streak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = HabitStore(Path(tmp) / "data.json")
            store.add("Read", date(2026, 10, 3))
            self.assertTrue(store.mark_done("Read", date(2026, 10, 4)))
            self.assertTrue(store.mark_done("Read", date(2026, 10, 5)))
            self.assertFalse(store.mark_done("Read", date(2026, 10, 5)))
            self.assertEqual(
                store.report(date(2026, 10, 5)), [{"name": "Read", "total": 2, "streak": 2}]
            )

    def test_duplicate_names_are_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = HabitStore(Path(tmp) / "data.json")
            store.add("Read")
            with self.assertRaisesRegex(ValueError, "already exists"):
                store.add(" read ")

    def test_streak_breaks_after_a_missed_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = HabitStore(Path(tmp) / "data.json")
            store.add("Walk")
            store.mark_done("Walk", date(2026, 10, 3))
            self.assertEqual(store.report(date(2026, 10, 5))[0]["streak"], 0)


class FileOrganizerTests(unittest.TestCase):
    def test_preview_does_not_move_and_apply_moves_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.TXT").write_text("hello", encoding="utf-8")
            plan = plan_moves(root)
            self.assertEqual(len(plan), 1)
            self.assertTrue((root / "notes.TXT").exists())
            moved = apply_moves(plan)
            self.assertEqual(moved, [root / "txt" / "notes.TXT"])
            self.assertEqual(moved[0].read_text(encoding="utf-8"), "hello")

    def test_destination_collision_gets_numbered_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "txt").mkdir()
            (root / "txt" / "report.txt").write_text("old", encoding="utf-8")
            (root / "report.txt").write_text("new", encoding="utf-8")
            _, destination = plan_moves(root)[0]
            self.assertEqual(destination.name, "report_2.txt")
            self.assertEqual((root / "txt" / "report.txt").read_text(encoding="utf-8"), "old")


class FlashcardTests(unittest.TestCase):
    def test_good_reviews_progress_and_due_filter(self) -> None:
        card = new_card("Q", "A", date(2026, 10, 1))
        self.assertEqual(len(due_cards([card], date(2026, 10, 1))), 1)
        card = review_card(card, "good", date(2026, 10, 1))
        self.assertEqual((card["interval_days"], card["due_date"]), (1, "2026-10-02"))
        self.assertEqual(due_cards([card], date(2026, 10, 1)), [])
        card = review_card(card, "good", date(2026, 10, 2))
        self.assertEqual(card["interval_days"], 3)

    def test_again_resets_schedule(self) -> None:
        card = new_card("Q", "A", date(2026, 10, 1))
        card = review_card(card, "good", date(2026, 10, 1))
        card = review_card(card, "again", date(2026, 10, 2))
        self.assertEqual(
            (card["repetitions"], card["interval_days"], card["due_date"]), (0, 1, "2026-10-03")
        )


class ExpenseSplitterTests(unittest.TestCase):
    def test_shared_expense_produces_balanced_transfers(self) -> None:
        result = calculate_settlements(
            ["Alice", "Bob", "Cara"],
            [{"paid_by": "Alice", "amount": "30.00", "split_among": ["Alice", "Bob", "Cara"]}],
        )
        self.assertEqual(
            result,
            [
                {"from": "Bob", "to": "Alice", "amount": "10.00"},
                {"from": "Cara", "to": "Alice", "amount": "10.00"},
            ],
        )

    def test_remainder_cents_are_assigned_deterministically(self) -> None:
        result = calculate_settlements(
            ["Alice", "Bob", "Cara"],
            [{"paid_by": "Alice", "amount": "10.00", "split_among": ["Alice", "Bob", "Cara"]}],
        )
        self.assertEqual([item["amount"] for item in result], ["3.33", "3.33"])

    def test_rejects_fractional_cents(self) -> None:
        with self.assertRaisesRegex(ValueError, "two decimal"):
            calculate_settlements(["A", "B"], [{"paid_by": "A", "amount": "1.001"}])


class URLHealthTests(unittest.TestCase):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def getcode(self):
            return self.status

    def test_rejects_non_http_urls_and_credentials(self) -> None:
        for url in ("example.com", "ftp://example.com", "https://user:pass@example.com"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    @patch("projects.url_health.app.urlopen")
    def test_success_uses_head_request(self, mocked_open) -> None:
        mocked_open.return_value = self.Response()
        result = check_url("https://example.com")
        self.assertTrue(result.healthy)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(mocked_open.call_args.args[0].get_method(), "HEAD")

    @patch("projects.url_health.app.urlopen")
    def test_falls_back_to_get_when_head_is_unsupported(self, mocked_open) -> None:
        mocked_open.side_effect = [
            HTTPError("https://example.com", 405, "unsupported", {}, None),
            self.Response(),
        ]
        result = check_url("https://example.com")
        self.assertTrue(result.healthy)
        self.assertEqual(mocked_open.call_count, 2)
        self.assertEqual(mocked_open.call_args.args[0].get_method(), "GET")

    @patch("projects.url_health.app.urlopen", side_effect=URLError("offline"))
    def test_network_failure_is_reported_without_raising(self, _mocked_open) -> None:
        result = check_url("https://example.com")
        self.assertFalse(result.healthy)
        self.assertIn("offline", result.error or "")


if __name__ == "__main__":
    unittest.main()
