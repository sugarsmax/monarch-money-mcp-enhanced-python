#!/usr/bin/env python3
"""
Find duplicate charges on ...2971 from a single export file.

  python analyze.py data/transactions_2971.json
  python analyze.py data/transactions_2971.json -o data/report.json

Duplicate = same date + amount + merchant_id (or merchant name if id missing),
excluding split children (original_transaction_id set).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def is_split_child(t: dict) -> bool:
    return bool(t.get("original_transaction_id"))


def signature(t: dict) -> tuple:
    mid = str(t.get("merchant_id") or t.get("merchant") or "").strip().lower()
    return (t.get("date"), round(float(t.get("amount", 0)), 2), mid)


def build_report(txs: list[dict]) -> dict:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for t in txs:
        if is_split_child(t):
            continue
        groups[signature(t)].append(t)

    dup_groups = {k: v for k, v in groups.items() if len(v) >= 2}
    pair_groups = {k: v for k, v in dup_groups.items() if len(v) == 2}
    trip_groups = {k: v for k, v in dup_groups.items() if len(v) == 3}
    quad_plus = {k: v for k, v in dup_groups.items() if len(v) >= 4}

    extra_txns = sum(len(v) - 1 for v in dup_groups.values())
    max_amt = 0.0
    max_example = None
    for sig, items in dup_groups.items():
        amt = abs(float(sig[1]))
        if amt > max_amt:
            max_amt = amt
            max_example = (sig, items)

    cross_connection = sum(
        1
        for items in dup_groups.values()
        if len({i.get("account_id") for i in items}) >= 2
    )

    report: dict = {
        "methodology": (
            "Single export file; same date + amount + merchant_id; "
            "split children excluded."
        ),
        "transaction_count": len(txs),
        "duplicate_groups_total": len(dup_groups),
        "duplicate_pairs": len(pair_groups),
        "triplicate_groups": len(trip_groups),
        "quad_or_more_groups": len(quad_plus),
        "groups_with_multiple_account_ids": cross_connection,
        "extra_duplicate_transactions": extra_txns,
        "biggest_duplicate_amount": max_amt,
        "biggest_duplicate_example": None,
    }
    if max_example:
        sig, items = max_example
        report["biggest_duplicate_example"] = {
            "date": sig[0],
            "amount": sig[1],
            "merchant": items[0].get("merchant"),
            "count": len(items),
            "account_ids": sorted({str(i.get("account_id")) for i in items}),
            "transaction_ids": [i["id"] for i in items],
        }

    ranked = sorted(
        dup_groups.items(),
        key=lambda kv: abs(float(kv[0][1])),
        reverse=True,
    )[:25]
    report["top_duplicates_by_amount"] = [
        {
            "date": sig[0],
            "amount": sig[1],
            "merchant": items[0].get("merchant"),
            "count": len(items),
            "distinct_account_ids": len({i.get("account_id") for i in items}),
            "transaction_ids": [i["id"] for i in items],
        }
        for sig, items in ranked
    ]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "export_json",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parent / "data" / "transactions_2971.json",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "report.json",
    )
    args = parser.parse_args()

    txs = json.loads(args.export_json.read_text())
    if not isinstance(txs, list):
        raise SystemExit(f"Expected JSON array in {args.export_json}")

    report = build_report(txs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
