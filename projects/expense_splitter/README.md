# Expense Splitter

A small standard-library tool for calculating who reimburses whom after shared costs. It works with integer cents internally and uses a deterministic greedy settlement; it does not process payments.

Create a JSON file, for example:

```json
{
  "participants": ["Alice", "Bob", "Cara"],
  "expenses": [
    {"paid_by": "Alice", "amount": "30.00", "split_among": ["Alice", "Bob", "Cara"]}
  ]
}
```

Then run:

```bash
python -m projects.expense_splitter.app trip.json
```

`split_among` is optional; if omitted, the expense is shared by everyone. Any leftover cents are assigned in the listed participant order, so the result is reproducible. Amounts must be positive and use no more than two decimal places. The suggested transfers are just arithmetic; settle them outside this program.
