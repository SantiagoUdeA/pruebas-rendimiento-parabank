#!/usr/bin/env python3
"""Write ignored smoke feeders matching a freshly initialized local ParaBank demo DB."""
import csv
from pathlib import Path

out = Path(__file__).resolve().parents[1] / "src/test/resources/data"
out.mkdir(parents=True, exist_ok=True)

def write(name, headers, rows):
    with (out / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

write("users", ["username", "password"], [{"username": "john", "password": "demo"}])
accounts = ["12456", "12567", "12678", "12789", "12900", "13011", "13122", "13233", "13344", "54321"]
transfers = []
for i in range(200):
    source_index = i % len(accounts)
    destination_index = (source_index + 1 + (i // len(accounts)) % (len(accounts) - 1)) % len(accounts)
    amount = f"{(i // len(accounts) + 1) / 100:.2f}"
    transfers.append({"caseId": f"local-transfer-{i + 1:04d}", "customerId": "12212",
                      "fromAccountId": accounts[source_index], "toAccountId": accounts[destination_index], "amount": amount})
write("transfers", ["caseId", "customerId", "fromAccountId", "toAccountId", "amount"], transfers)
write("statements", ["caseId", "accountId"], [{"caseId": "local-statement-001", "accountId": "54321"}])
loan_accounts = ["54321", "13122", "13344", "12567", "12789", "13011"]
loans = [{"caseId": f"local-loan-{i + 1:04d}", "customerId": "12212", "amount": "10.00",
          "downPayment": "5.00", "fromAccountId": loan_accounts[i % len(loan_accounts)]} for i in range(200)]
write("loans", ["caseId", "customerId", "amount", "downPayment", "fromAccountId"], loans)
payments = [{"caseId": f"local-payment-{i + 1:04d}", "accountId": loan_accounts[i % len(loan_accounts)], "amount": f"{(i + 1) / 100:.2f}",
             "payeeName": f"Smoke Test Payee {i + 1}", "street": "1 Test Street", "city": "Test City",
             "state": "CA", "zipCode": "90001", "phone": "5550100", "payeeAccount": str(24680 + i)}
            for i in range(200)]
write("payments", ["caseId", "accountId", "amount", "payeeName", "street", "city", "state", "zipCode", "phone", "payeeAccount"], payments)
print(f"Prepared local demo feeders in {out}; CSV files are git-ignored.")
