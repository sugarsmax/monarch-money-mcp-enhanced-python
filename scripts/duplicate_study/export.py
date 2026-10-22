#!/usr/bin/env python3
"""
Build one canonical transaction file for ...2971 duplicate analysis.

Sources (pick one workflow):
  1) Merge MCP GetTransactions JSON exports (recommended):
       python export.py merge chunk_a.json chunk_b.json -o data/transactions_2971.json
       cat mcp_response.json | python export.py merge - -o data/transactions_2971.json

  2) Monarch CSV export (Transactions export from the app):
       python export.py from-csv ~/Downloads/transactions.csv -o data/transactions_2971.json

Output: JSON array of normalized rows + optional CSV alongside.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from config import (
    ALLOWED_ACCOUNT_IDS,
    CANONICAL_FIELDS,
    CARD_MARKER,
    EXCLUDED_ACCOUNT_ID,
)


def is_target_card(row: dict) -> bool:
    acct = str(row.get("account") or row.get("Account") or "")
    return CARD_MARKER in acct


def allowed_account(row: dict) -> bool:
    aid = str(row.get("account_id") or row.get("Account ID") or "")
    if not aid or aid == EXCLUDED_ACCOUNT_ID:
        return False
    return aid in ALLOWED_ACCOUNT_IDS


def normalize_mcp_tx(t: dict) -> dict:
    return {
        "id": str(t["id"]),
        "date": t.get("date"),
        "amount": round(float(t.get("amount", 0)), 2),
        "merchant": t.get("merchant"),
        "merchant_id": str(t.get("merchant_id") or ""),
        "account": t.get("account"),
        "account_id": str(t.get("account_id") or ""),
        "category": t.get("category"),
        "original_transaction_id": t.get("original_transaction_id") or None,
    }


def load_mcp_payload(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    return list(data.get("transactions") or [])


def merge_mcp_paths(paths: list[Path], existing: list[dict] | None = None) -> list[dict]:
    by_id: dict[str, dict] = {str(t["id"]): t for t in (existing or [])}
    for path in paths:
        if str(path) == "-":
            data = json.load(sys.stdin)
            batch = data if isinstance(data, list) else data.get("transactions", [])
        elif not path.exists():
            raise FileNotFoundError(path)
        else:
            batch = load_mcp_payload(path)
        for raw in batch:
            if not is_target_card(raw) or not allowed_account(raw):
                continue
            norm = normalize_mcp_tx(raw)
            by_id[norm["id"]] = norm
    return sorted(by_id.values(), key=lambda x: (x.get("date") or "", x["id"]))


def from_monarch_csv(path: Path) -> list[dict]:
    """Best-effort parse of Monarch / generic transaction CSV exports."""
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not is_target_card(r):
                continue
            amount_raw = r.get("Amount") or r.get("amount") or "0"
            amount = round(float(str(amount_raw).replace("$", "").replace(",", "")), 2)
            row = {
                "id": str(r.get("ID") or r.get("id") or r.get("Transaction ID") or ""),
                "date": r.get("Date") or r.get("date"),
                "amount": amount,
                "merchant": r.get("Merchant") or r.get("merchant"),
                "merchant_id": str(r.get("Merchant ID") or r.get("merchant_id") or ""),
                "account": r.get("Account") or r.get("account"),
                "account_id": str(r.get("Account ID") or r.get("account_id") or ""),
                "category": r.get("Category") or r.get("category"),
                "original_transaction_id": r.get("Original Transaction ID")
                or r.get("original_transaction_id")
                or None,
            }
            if not row["id"]:
                continue
            if not allowed_account(row):
                continue
            rows.append(row)
    by_id = {r["id"]: r for r in rows}
    return sorted(by_id.values(), key=lambda x: (x.get("date") or "", x["id"]))


def write_outputs(txs: list[dict], out_json: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(txs, indent=2))
    out_csv = out_json.with_suffix(".csv")
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(CANONICAL_FIELDS))
        w.writeheader()
        for t in txs:
            w.writerow({k: t.get(k) for k in CANONICAL_FIELDS})
    aids = sorted({t["account_id"] for t in txs if t.get("account_id")})
    print(f"Wrote {out_json} ({len(txs)} transactions, account_ids={aids})")
    print(f"Wrote {out_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    merge_p = sub.add_parser("merge", help="Merge MCP GetTransactions JSON file(s)")
    merge_p.add_argument(
        "sources",
        nargs="+",
        help="Paths to MCP JSON, or '-' for stdin (one file only)",
    )
    merge_p.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "transactions_2971.json",
    )
    merge_p.add_argument(
        "--append",
        action="store_true",
        help="Merge into existing --out file if present",
    )

    csv_p = sub.add_parser("from-csv", help="Import Monarch CSV export")
    csv_p.add_argument("csv_path", type=Path)
    csv_p.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "transactions_2971.json",
    )

    args = parser.parse_args()
    if args.cmd == "merge":
        existing = None
        if args.append and args.out.exists():
            existing = json.loads(args.out.read_text())
        paths = [Path(p) for p in args.sources]
        txs = merge_mcp_paths(paths, existing)
        write_outputs(txs, args.out)
    elif args.cmd == "from-csv":
        txs = from_monarch_csv(args.csv_path)
        write_outputs(txs, args.out)


if __name__ == "__main__":
    main()
