#!/usr/bin/env python3
"""Check confirmed transfer completions in the five-minute steady window.

The test profile ramps for 60 seconds; that interval is treated as warm-up. The
first observed completion anchors the window, so keep Gatling's system clock and
this verifier on the same host. This check is a load acceptance aid; transaction
ledger reconciliation is still required before declaring H2 passed.
"""
import argparse
import csv
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempts", help="AttemptRecorder CSV output")
    parser.add_argument("--warmup-seconds", type=int, default=60)
    parser.add_argument("--window-seconds", type=int, default=300)
    parser.add_argument("--minimum-per-second", type=float, default=150)
    args = parser.parse_args()
    with Path(args.attempts).open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        sys.exit("No attempt rows; result is inconclusive")
    required = {"caseId", "status", "timestampMillis"}
    if not required <= set(rows[0]):
        sys.exit(f"Missing required columns: {sorted(required)}")
    try:
        times = [int(row["timestampMillis"]) for row in rows]
    except (ValueError, KeyError):
        sys.exit("Invalid attempt timestamps; result is inconclusive")
    start = min(times) + args.warmup_seconds * 1000
    end = start + args.window_seconds * 1000
    buckets = [0] * (args.window_seconds // 10)
    confirmed = 0
    for row, timestamp in zip(rows, times):
        if start <= timestamp < end and row["status"].strip().upper() == "CONFIRMED":
            confirmed += 1
            buckets[(timestamp - start) // 10000] += 1
    expected = len(buckets)
    if expected != 30:
        sys.exit("The stable window must contain 30 consecutive 10-second blocks")
    per_second = [count / 10 for count in buckets]
    summary = {"windowStartMillis": start, "windowEndMillis": end, "attemptedInWindow": sum(
        1 for timestamp in times if start <= timestamp < end), "confirmedInWindow": confirmed,
        "averageConfirmedPerSecond": confirmed / args.window_seconds,
        "minimumBlockConfirmedPerSecond": min(per_second), "blockRatesPerSecond": per_second,
        "minimumRequiredPerSecond": args.minimum_per_second,
        "verdict": "PASS" if min(per_second) >= args.minimum_per_second else "FAIL"}
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
