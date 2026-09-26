#!/usr/bin/env python3
"""Generate ignored Gatling feeders from the accounts that the isolated ParaBank really exposes.

Every account and customer used by a simulation is read back from the ParaBank API first, so a
campaign cannot fail because the stock dataset does not contain the customer or account a feeder
invented. Row counts are sized for the acceptance campaigns and can be overridden with environment
variables. Amounts are fixed and small: ParaBank does not validate balances, so a long campaign
cannot run out of funds, and a fixed amount keeps the post-run ledger reconciliation comparable.
"""
import csv
import json
import os
from pathlib import Path

import parabank_api as api

OUT = Path(__file__).resolve().parents[1] / "src/test/resources/data"
EVIDENCE = Path(os.getenv("EVIDENCE_DIR", "evidence/runs"))

TRANSFER_ROWS = api.env_int("TRANSFER_ROWS", 60000)
TRANSFER_AMOUNT = os.getenv("TRANSFER_AMOUNT", "1.00")
PAYMENT_ROWS = api.env_int("PAYMENT_ROWS", 24000)
PAYMENT_AMOUNT = os.getenv("PAYMENT_AMOUNT", "0.01")
LOAN_ROWS = api.env_int("LOAN_ROWS", 12000)
LOAN_AMOUNT = os.getenv("LOAN_AMOUNT", "10.00")
LOAN_DOWN_PAYMENT = os.getenv("LOAN_DOWN_PAYMENT", "0.01")
STATEMENT_ROWS = api.env_int("STATEMENT_ROWS", 0)
CUSTOMER_SCAN = api.env_int("CUSTOMER_SCAN", 40)
CANDIDATE_LOGINS = os.getenv("PARABANK_LOGINS", "john:demo")


def discover_customers():
    explicit = os.getenv("PARABANK_CUSTOMER_IDS")
    if explicit:
        candidates = [value.strip() for value in explicit.split(",") if value.strip()]
    else:
        candidates = [str(12212 + offset) for offset in range(CUSTOMER_SCAN)]
    return api.existing_customers(candidates)


def discover_logins():
    logins = []
    for pair in CANDIDATE_LOGINS.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        username, password = pair.split(":", 1)
        if isinstance(api.login(username.strip(), password.strip()), dict):
            logins.append((username.strip(), password.strip()))
    return logins


def write(name, headers, rows):
    with (OUT / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    customers = discover_customers()
    if not customers:
        raise SystemExit("ParaBank exposes no customer; cannot prepare feeders")
    logins = discover_logins()
    if not logins:
        raise SystemExit("No valid ParaBank login was found; cannot prepare users.csv")

    owned = []
    for customer_id in customers:
        owned.extend((customer_id, account) for account in api.accounts_of(customer_id))
    if len(owned) < 2:
        raise SystemExit("ParaBank exposes fewer than two CHECKING/SAVINGS accounts; cannot prepare feeders")

    write("users", ["username", "password"], [{"username": name, "password": secret} for name, secret in logins])

    accounts = [account["id"] for _, account in owned]
    # A statement check requires an account that really has movements, otherwise the request is
    # counted as a functional error that the bank never produced.
    with_activity = [(owner, account) for owner, account in owned if api.entries_of(account["id"])]
    if not with_activity:
        raise SystemExit("No exposed account has transactions; cannot prepare the statement feeder")
    statement_targets = with_activity[:STATEMENT_ROWS] if STATEMENT_ROWS else with_activity
    write("statements", ["caseId", "accountId"],
          [{"caseId": f"statement-{index + 1:06d}", "accountId": account["id"]}
           for index, (_, account) in enumerate(statement_targets)])

    transfers = []
    for index in range(TRANSFER_ROWS):
        source = accounts[index % len(accounts)]
        destination = accounts[(index + 1 + (index // len(accounts)) % (len(accounts) - 1)) % len(accounts)]
        if destination == source:
            destination = accounts[(index + 1) % len(accounts)]
        transfers.append({"caseId": f"transfer-{index + 1:06d}", "customerId": owned[index % len(owned)][0],
                          "fromAccountId": source, "toAccountId": destination, "amount": TRANSFER_AMOUNT})
    write("transfers", ["caseId", "customerId", "fromAccountId", "toAccountId", "amount"], transfers)

    payments = []
    for index in range(PAYMENT_ROWS):
        owner, account = owned[index % len(owned)]
        payments.append({"caseId": f"payment-{index + 1:06d}", "accountId": account["id"], "amount": PAYMENT_AMOUNT,
                         "payeeName": f"Perf Payee {index % 500:03d}", "street": "1 Test Street", "city": "Test City",
                         "state": "CA", "zipCode": "90001", "phone": "5550100", "payeeAccount": str(24680 + index % 500)})
    write("payments", ["caseId", "accountId", "amount", "payeeName", "street", "city", "state", "zipCode", "phone",
                       "payeeAccount"], payments)

    loans = []
    for index in range(LOAN_ROWS):
        owner, account = owned[index % len(owned)]
        loans.append({"caseId": f"loan-{index + 1:06d}", "customerId": owner, "amount": LOAN_AMOUNT,
                      "downPayment": LOAN_DOWN_PAYMENT, "fromAccountId": account["id"]})
    write("loans", ["caseId", "customerId", "amount", "downPayment", "fromAccountId"], loans)

    summary = {"baseUrl": api.base_url(), "customers": customers, "logins": [name for name, _ in logins],
               "accounts": [{"id": account["id"], "type": account["type"], "balance": account["balance"],
                             "customerId": owner} for owner, account in owned],
               "rows": {"users": len(logins), "statements": len(statement_targets), "transfers": TRANSFER_ROWS,
                        "payments": PAYMENT_ROWS, "loans": LOAN_ROWS}}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "prepared-data.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared feeders for {len(customers)} customer(s), {len(owned)} account(s): " + json.dumps(summary["rows"]))


if __name__ == "__main__":
    main()
