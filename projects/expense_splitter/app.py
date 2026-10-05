"""Split shared expenses exactly to cents and suggest simple settlements."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def _to_cents(value: Any) -> int:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {value}") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("expense amounts must be positive finite numbers")
    rounded = amount.quantize(Decimal("0.01"))
    if rounded != amount:
        raise ValueError("expense amounts may have at most two decimal places")
    return int(rounded * 100)


def _money(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def calculate_settlements(
    participants: list[str],
    expenses: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Return transfers that settle the net balance for equal expense shares."""
    names = [name.strip() for name in participants]
    if (
        not names
        or any(not name for name in names)
        or len({name.casefold() for name in names}) != len(names)
    ):
        raise ValueError("participants must be non-empty, unique names")
    balances = {name: 0 for name in names}
    for expense in expenses:
        payer = expense.get("paid_by")
        if payer not in balances:
            raise ValueError(f"unknown payer: {payer}")
        split = expense.get("split_among", names)
        if not isinstance(split, list) or not split or len(set(split)) != len(split):
            raise ValueError("split_among must be a non-empty list of unique participants")
        if any(person not in balances for person in split):
            raise ValueError("split_among contains an unknown participant")
        cents = _to_cents(expense.get("amount"))
        share, remainder = divmod(cents, len(split))
        balances[payer] += cents
        for index, person in enumerate(split):
            balances[person] -= share + (1 if index < remainder else 0)
    debtors = [[name, -amount] for name, amount in sorted(balances.items()) if amount < 0]
    creditors = [[name, amount] for name, amount in sorted(balances.items()) if amount > 0]
    transfers: list[dict[str, str]] = []
    debtor_index = creditor_index = 0
    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor, owed = debtors[debtor_index]
        creditor, due = creditors[creditor_index]
        amount = min(owed, due)
        transfers.append({"from": debtor, "to": creditor, "amount": _money(amount)})
        debtors[debtor_index][1] -= amount
        creditors[creditor_index][1] -= amount
        if debtors[debtor_index][1] == 0:
            debtor_index += 1
        if creditors[creditor_index][1] == 0:
            creditor_index += 1
    return transfers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expense_file", type=Path, help="JSON file with participants and expenses")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.expense_file.read_text(encoding="utf-8"))
        transfers = calculate_settlements(document["participants"], document["expenses"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    if not transfers:
        print("Everyone is settled.")
    for transfer in transfers:
        print(f"{transfer['from']} pays {transfer['to']} {transfer['amount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
