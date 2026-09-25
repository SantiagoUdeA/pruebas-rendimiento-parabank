#!/usr/bin/env python3
"""Reconcile recorded financial attempts with an exported ParaBank ledger.

Attempts CSV is written by AttemptRecorder. Ledger CSV columns are
entryType,accountId,amount and optional caseId. Without caseId, matching is by
account, entry type, and absolute amount; repeated case keys are inconclusive
because they cannot be distinguished reliably.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--operation", choices=("transfer", "payment"), required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    attempt_headers, attempts = read_csv(args.attempts)
    ledger_headers, ledger = read_csv(args.ledger)
    required_attempt = {"caseId", "status", "amount", "fromAccountId", "toAccountId", "accountId"}
    required_ledger = {"entryType", "accountId", "amount"}
    if not required_attempt <= set(attempt_headers):
        sys.exit(f"attempts CSV requires columns: {sorted(required_attempt)}")
    if not required_ledger <= set(ledger_headers):
        sys.exit(f"ledger CSV requires columns: {sorted(required_ledger)}")
    if not attempts:
        sys.exit("No financial attempts found; result is inconclusive")

    case_ids = [row["caseId"].strip() for row in attempts]
    if any(not value for value in case_ids) or len(set(case_ids)) != len(case_ids):
        sys.exit("Attempt caseId values must be present and unique")

    expected = Counter()
    failed_ids = set()
    confirmed = 0
    attempt_keys = Counter()
    for row in attempts:
        case_id = row["caseId"].strip()
        status = row["status"].strip().upper()
        if status not in {"CONFIRMED", "FAILED"}:
            sys.exit(f"{case_id}: status must be CONFIRMED or FAILED")
        if status == "FAILED":
            failed_ids.add(case_id)
            continue
        confirmed += 1
        try:
            amount = abs(Decimal(row["amount"]))
        except InvalidOperation:
            sys.exit(f"{case_id}: invalid attempt amount")
        if args.operation == "transfer":
            source, destination = row["fromAccountId"].strip(), row["toAccountId"].strip()
            if not source or not destination or source == destination:
                sys.exit(f"{case_id}: transfer source and destination are required and must differ")
            keys = [("DEBIT", source, amount), ("CREDIT", destination, amount)]
        else:
            account = row["accountId"].strip()
            if not account:
                sys.exit(f"{case_id}: payment accountId is required")
            keys = [("DEBIT", account, amount)]
        for key in keys:
            expected[key] += 1
            attempt_keys[key] += 1

    actual = Counter()
    case_aware = "caseId" in ledger_headers and all(row.get("caseId", "").strip() for row in ledger)
    issues = []
    if case_aware:
        by_case = {row["caseId"].strip(): row for row in attempts}
        observed_case_counts = Counter()
        for entry in ledger:
            case_id = entry["caseId"].strip()
            attempt = by_case.get(case_id)
            if not attempt:
                issues.append({"caseId": case_id, "reason": "ledger entry without matching attempt"})
                continue
            if case_id in failed_ids:
                issues.append({"caseId": case_id, "reason": "ledger entry for failed attempt"})
                continue
            try:
                amount = abs(Decimal(entry["amount"]))
            except InvalidOperation:
                issues.append({"caseId": case_id, "reason": "invalid ledger amount"})
                continue
            kind = entry["entryType"].strip().upper()
            account = entry["accountId"].strip()
            valid = ((args.operation == "transfer" and ((kind == "DEBIT" and account == attempt["fromAccountId"].strip()) or (kind == "CREDIT" and account == attempt["toAccountId"].strip())))
                     or (args.operation == "payment" and kind == "DEBIT" and account == attempt["accountId"].strip()))
            if not valid or amount != abs(Decimal(attempt["amount"])):
                issues.append({"caseId": case_id, "reason": "account, entry type, or amount mismatch"})
            observed_case_counts[(case_id, kind)] += 1
        expected_per_case = 2 if args.operation == "transfer" else 1
        for row in attempts:
            case_id = row["caseId"].strip()
            count = sum(v for (cid, _), v in observed_case_counts.items() if cid == case_id)
            target = expected_per_case if row["status"].strip().upper() == "CONFIRMED" else 0
            if count != target:
                issues.append({"caseId": case_id, "reason": f"expected {target} ledger entries, found {count}"})
    else:
        for key, count in attempt_keys.items():
            if count > 1:
                issues.append({"reason": "inconclusive: repeated account/type/amount cannot be uniquely correlated", "key": [key[0], key[1], str(key[2])], "attempts": count})
        for entry in ledger:
            try:
                amount = abs(Decimal(entry["amount"]))
            except InvalidOperation:
                issues.append({"reason": "invalid ledger amount"})
                continue
            actual[(entry["entryType"].strip().upper(), entry["accountId"].strip(), amount)] += 1
        for key in sorted(set(expected) | set(actual), key=str):
            if expected[key] != actual[key]:
                issues.append({"key": [key[0], key[1], str(key[2])], "expected": expected[key], "actual": actual[key]})

    summary = {"operation": args.operation, "attempted": len(attempts), "confirmed": confirmed,
               "ledgerEntries": len(ledger), "issueCount": len(issues), "issues": issues,
               "verdict": "PASS" if not issues else "FAIL"}
    result = json.dumps(summary, indent=2)
    print(result)
    if args.output:
        Path(args.output).write_text(result + "\n", encoding="utf-8")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
