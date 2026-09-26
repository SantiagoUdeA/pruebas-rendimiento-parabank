#!/usr/bin/env python3
"""Build the acceptance table of a campaign: target criterion, measured value, verdict.

Gatling prints the measured statistics and the assertion outcome of every acceptance criterion to
its console output, and the post-run verifiers write JSON. This script only reads those artefacts,
so the table can never claim a value that was not measured.
"""
import json
import re
import sys
from pathlib import Path

RUN_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "evidence/runs")
STORIES = {
    "LoginSimulation": "H1 Login",
    "TransferSimulation": "H2 Transferencias",
    "StatementSimulation": "H3 Estado de cuenta",
    "LoanSimulation": "H4 Prestamo",
    "BillPaySimulation": "H5 Pago de servicios",
}
STAT_LABELS = (("request count", "Peticiones"), ("percentage of failed requests", "% fallos"),
               ("min response time", "Min ms"), ("mean response time", "Media ms"),
               ("response time 50th percentile", "p50 ms"), ("response time 95th percentile", "p95 ms"),
               ("response time 99th percentile", "p99 ms"), ("max response time", "Max ms"),
               ("mean throughput", "Peticiones/s"))


def columns(line):
    values = []
    for cell in line.split("|")[1:]:
        value = cell.strip().replace(",", "")
        values.append(value if value else "-")
    return values


def console_stats(path):
    stats = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith("> "):
            continue
        label = line[2:].split("|")[0].strip()
        values = columns(line)
        if not values:
            continue
        for key, name in STAT_LABELS:
            if label.startswith(key):
                stats[name] = values[0]
        if label.startswith("request count") and len(values) > 2:
            stats["KO"] = values[2]
    return stats


def assertions(path):
    found = []
    pattern = re.compile(r"^(?P<name>[A-Za-z ]+): (?P<criterion>.+?) : (?P<result>true|false) \(actual : (?P<actual>[^)]+)\)")
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.match(line.strip())
        if match:
            found.append({"criterion": match.group("criterion").strip(), "actual": match.group("actual").strip(),
                          "passed": match.group("result") == "true"})
    return found


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main():
    rows = []
    for simulation, story in STORIES.items():
        console = RUN_DIR / f"console-{simulation}.txt"
        if not console.exists():
            continue
        stats = console_stats(console)
        for assertion in assertions(console):
            rows.append((story, assertion["criterion"], assertion["actual"], "CUMPLE" if assertion["passed"] else "NO CUMPLE"))
        if simulation == "TransferSimulation":
            throughput = read_json(RUN_DIR / "transfer-throughput.json")
            if throughput:
                rows.append((story, "Transferencias confirmadas por segundo (minimo de cada bloque de 10 s)",
                             f"{throughput['minimumBlockConfirmedPerSecond']}", "CUMPLE" if throughput["verdict"] == "PASS" else "NO CUMPLE"))
        reconciliation = read_json(RUN_DIR / f"reconcile-{simulation}.json")
        if reconciliation:
            label = ("Ninguna transferenda perdida o duplicada" if reconciliation["operation"] == "transfer"
                     else "Cada pago registrado una sola vez en el historial")
            rows.append((story, label, f"{reconciliation['confirmed']} confirmadas / {reconciliation['ledgerEntries']} asientos",
                         "CUMPLE" if reconciliation["verdict"] == "PASS" else "NO CUMPLE"))
        if stats:
            rows.append((story, "Metricas de la corrida (total / fallos / media / p95 / max)",
                         " / ".join(stats.get(key, "-") for key in ("Peticiones", "KO", "Media ms", "p95 ms", "Max ms")), "Informativo"))

    if not rows:
        raise SystemExit(f"No console output found in {RUN_DIR}; run at least one scenario first")

    lines = ["# Tabla de cumplimiento de la campana", "",
             "| Historia | Criterio | Valor medido | Resultado |", "|---|---|---|---|"]
    lines += [f"| {story} | {criterion} | {measured} | {verdict} |" for story, criterion, measured, verdict in rows]
    failed = sum(1 for row in rows if row[3] == "NO CUMPLE")
    lines += ["", f"Criterios evaluados: {len(rows)}. Incumplidos: {failed}.",
              "", "Los valores provienen de la salida de consola de Gatling y de los verificadores "
              "`transfer-throughput.json` y `reconcile-*.json` de la misma ejecucion."]
    report = "\n".join(lines) + "\n"
    (RUN_DIR / "summary.md").write_text(report, encoding="utf-8")
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
