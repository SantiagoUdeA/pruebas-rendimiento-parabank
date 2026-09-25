#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

out = Path("evidence/runs")
out.mkdir(parents=True, exist_ok=True)
metadata = {
    "startedOrRecordedAtUtc": datetime.now(timezone.utc).isoformat(),
    "commit": os.getenv("GITHUB_SHA", "local"),
    "actionsRunId": os.getenv("GITHUB_RUN_ID", "local"),
    "scenario": os.getenv("SCENARIO", "unspecified"),
    "profile": os.getenv("PROFILE", "unspecified"),
    "baseUrlHost": __import__("urllib.parse", fromlist=["urlparse"]).urlparse(os.getenv("BASE_URL", "")).hostname,
    "sutVersion": os.getenv("SUT_VERSION", "not-recorded"),
    "runner": os.getenv("RUNNER_NAME", "local"),
    "verdict": "PENDING_RECONCILIATION",
    "note": "Gatling assertion results do not replace transaction reconciliation or environment stability review.",
}
name = f"{metadata['actionsRunId']}-{metadata['scenario']}.json"
(out / name).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
