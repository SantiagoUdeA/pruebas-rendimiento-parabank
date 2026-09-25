#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
port=$(docker compose -f compose.yaml config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["parabank"]["ports"][0]["published"])')
url="http://127.0.0.1:${port}/parabank/services/bank/initializeDB"
case "$url" in http://127.0.0.1:*) ;; *) echo "Refusing non-loopback reset target" >&2; exit 2 ;; esac
curl --silent --show-error --fail --request POST --output /dev/null "$url"
printf 'Reset the isolated local ParaBank database. Recreate local feeders if needed.\n'
