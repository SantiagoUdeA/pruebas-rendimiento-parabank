#!/usr/bin/env python3
"""Export the ParaBank ledger of the accounts touched by a run, as a baseline and as a delta.

The stock database already owns ledger rows, and a campaign can produce tens of thousands of new
ones, so a reconciliation cannot compare the full history against the attempt log. This script takes
a baseline before the simulation and, afterwards, writes only the entries created by the run. ParaBank
gives every entry a unique id, which is what makes the delta exact.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parabank_api as api

ACCOUNT_COLUMNS = ("accountId", "fromAccountId", "toAccountId")
SNAPSHOT_COLUMNS = ("entryId", "entryType", "accountId", "amount")


def accounts_from(attempts_path):
    accounts = []
    with Path(attempts_path).open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            for column in ACCOUNT_COLUMNS:
                value = (row.get(column) or "").strip()
                if value and value not in accounts:
                    accounts.append(value)
    return accounts


def accounts_from_prepared(prepared_path):
    prepared = json.loads(Path(prepared_path).read_text(encoding="utf-8"))
    return [str(account["id"]) for account in prepared.get("accounts", [])]


def resolve_accounts(args):
    if args.attempts and Path(args.attempts).exists() and Path(args.attempts).stat().st_size > 0:
        accounts = accounts_from(args.attempts)
        if accounts:
            return accounts
    if args.prepared:
        return accounts_from_prepared(args.prepared)
    raise SystemExit("Provide --attempts (after the run) or --prepared (before the run)")


def rows_for(accounts):
    rows = []
    for account_id in accounts:
        for entry in api.entries_of(account_id):
            rows.append({"entryId": str(entry.get("id", "")), "entryType": str(entry.get("type", "")),
                         "accountId": str(entry.get("accountId", account_id)), "amount": str(entry.get("amount", ""))})
    return rows


def write_csv(path, columns, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def snapshot(args):
    accounts = resolve_accounts(args)
    if not accounts:
        raise SystemExit("No account id could be resolved for the ledger snapshot")
    rows = rows_for(accounts)
    write_csv(args.output, SNAPSHOT_COLUMNS, rows)
    print(f"Baseline: {len(rows)} ledger entries across {len(accounts)} account(s) -> {args.output}")


def delta(args):
    accounts = resolve_accounts(args)
    baseline_ids = set()
    if Path(args.baseline).exists():
        with Path(args.baseline).open(newline="", encoding="utf-8-sig") as stream:
            baseline_ids = {row["entryId"] for row in csv.DictReader(stream) if row.get("entryId")}
    rows = [row for row in rows_for(accounts) if row["entryId"] not in baseline_ids]
    write_csv(args.output, ("entryType", "accountId", "amount"), rows)
    print(f"Delta: {len(rows)} new ledger entries across {len(accounts)} account(s) -> {args.output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("snapshot", "delta"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--attempts", help="AttemptRecorder CSV of the run; used when it exists")
        sub.add_argument("--prepared", help="prepared-data.json written before the run")
        sub.add_argument("--output", required=True)
        if command == "delta":
            sub.add_argument("--baseline", required=True)
    args = parser.parse_args()
    if args.command == "snapshot":
        snapshot(args)
    else:
        delta(args)


if __name__ == "__main__":
    main()
