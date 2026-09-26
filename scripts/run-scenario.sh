#!/usr/bin/env bash
# Run one Gatling scenario against the isolated ParaBank instance and verify it end to end.
# GitHub Actions and local runs share this script so a measured result is reproducible the same way.
set -euo pipefail
cd "$(dirname "$0")/.."

CLASS="${1:?usage: run-scenario.sh <SimulationClass> [profile]}"
PROFILE="${2:-${PROFILE:-smoke}}"
RUN_DIR="${EVIDENCE_DIR:-evidence/runs}"
SIMULATION="com.parabank.perf.simulations.${CLASS}"
ATTEMPTS="${RUN_DIR}/attempts-${CLASS}.csv"
BASELINE="${RUN_DIR}/baseline-${CLASS}.csv"
LEDGER="${RUN_DIR}/ledger-${CLASS}.csv"
CONSOLE="${RUN_DIR}/console-${CLASS}.txt"

# The simulations read the campaign from the environment, so the profile chosen here must be exported.
# RAMP_SECONDS, DURATION_SECONDS, USERS and RATE_PER_SECOND are taken from the caller's environment and
# otherwise keep the defaults declared in Environment.java.
export PROFILE
export USERS="${USERS:-2}"
export RATE_PER_SECOND="${RATE_PER_SECOND:-5}"
export DATA_DIR="${DATA_DIR:-data}"
ramp_seconds="${RAMP_SECONDS:-60}"
window_seconds="${DURATION_SECONDS:-300}"
if [ "${PROFILE}" = "smoke" ]; then
  ramp_seconds="${RAMP_SECONDS:-10}"
  window_seconds="${DURATION_SECONDS:-10}"
fi

mkdir -p "${RUN_DIR}"
export EVIDENCE_DIR="${RUN_DIR}"

echo "== Preparing isolated data for ${CLASS} (profile=${PROFILE})"
scripts/reset-local-parabank-db.sh
python3 scripts/prepare-parabank-local-data.py
python3 scripts/parabank-ledger.py snapshot --prepared "${RUN_DIR}/prepared-data.json" --output "${BASELINE}"

echo "== Running ${SIMULATION}"
status=0
ATTEMPTS_FILE="${ATTEMPTS}" ./mvnw -B -ntp gatling:test "-Dgatling.simulationClass=${SIMULATION}" >"${CONSOLE}" 2>&1 || status=$?
cat "${CONSOLE}"
echo "== Gatling exit status: ${status}"

operation=""
case "${CLASS}" in
  TransferSimulation) operation=transfer ;;
  BillPaySimulation) operation=payment ;;
esac

if [ -n "${operation}" ] && [ -s "${ATTEMPTS}" ]; then
  echo "== Reconciling ${operation} operations against the ParaBank ledger"
  reconciliation=0
  python3 scripts/parabank-ledger.py delta --baseline "${BASELINE}" --attempts "${ATTEMPTS}" --output "${LEDGER}" || reconciliation=$?
  python3 scripts/reconcile-transactions.py --attempts "${ATTEMPTS}" --ledger "${LEDGER}" \
    --operation "${operation}" --output "${RUN_DIR}/reconcile-${CLASS}.json" || reconciliation=$?
  if [ "${reconciliation}" -ne 0 ]; then
    echo "Reconciliation did not pass; the run is not conclusive." >&2
    status=1
  fi
fi

if [ "${CLASS}" = "TransferSimulation" ] && [ "${PROFILE}" != "smoke" ] && [ -s "${ATTEMPTS}" ]; then
  echo "== Checking confirmed transfers per second in the stable window"
  minimum="${MINIMUM_CONFIRMED_PER_SECOND:-150}"
  throughput=0
  python3 scripts/evaluate-transfer-throughput.py "${ATTEMPTS}" --warmup-seconds "${ramp_seconds}" \
    --window-seconds "${window_seconds}" --minimum-per-second "${minimum}" \
    --output "${RUN_DIR}/transfer-throughput.json" || throughput=$?
  if [ "${throughput}" -ne 0 ]; then
    echo "Throughput target was not met; the run is not conclusive." >&2
    status=1
  fi
fi

echo "== ${CLASS} finished with status ${status}"
exit "${status}"
