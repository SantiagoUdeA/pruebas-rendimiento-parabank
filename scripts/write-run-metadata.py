#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

out = Path("evidence/runs")
out.mkdir(parents=True, exist_ok=True)


def collect_reconciliations():
    found = {}
    for path in sorted(out.glob("reconcile-*.json")):
        try:
            found[path.stem.removeprefix("reconcile-")] = json.loads(path.read_text(encoding="utf-8"))["verdict"]
        except (OSError, ValueError, KeyError):
            found[path.stem.removeprefix("reconcile-")] = "UNREADABLE"
    return found


def failed_checks():
    found = []
    for path in sorted(out.glob("console-*.txt")):
        scenario = path.stem.removeprefix("console-")
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if " : false (actual :" in line:
                found.append({"scenario": scenario, "check": line.strip()})
    return found


reconciliations = collect_reconciliations()
failed = failed_checks()
if failed:
    verdict = "CRITERIA_NOT_MET"
elif reconciliations and any(result != "PASS" for result in reconciliations.values()):
    verdict = "RECONCILIATION_NOT_PASSED"
elif reconciliations:
    verdict = "PASS"
else:
    verdict = "NO_FINANCIAL_RECONCILIATION_REQUIRED"

metadata = {
    "startedOrRecordedAtUtc": datetime.now(timezone.utc).isoformat(),
    "commit": os.getenv("GITHUB_SHA", "local"),
    "actionsRunId": os.getenv("GITHUB_RUN_ID", "local"),
    "scenario": os.getenv("SCENARIO", "unspecified"),
    "profile": os.getenv("PROFILE", "unspecified"),
    "baseUrlHost": __import__("urllib.parse", fromlist=["urlparse"]).urlparse(os.getenv("BASE_URL", "")).hostname,
    "sutVersion": os.getenv("SUT_VERSION", "not-recorded"),
    "runner": os.getenv("RUNNER_NAME", "local"),
    "verdict": verdict,
    "failedChecks": failed,
    "reconciliations": reconciliations,
    "note": "Gatling assertion results do not replace transaction reconciliation or environment stability review.",
}
name = f"{metadata['actionsRunId']}-{metadata['scenario']}.json"
(out / name).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
