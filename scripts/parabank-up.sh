#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
docker compose -f compose.yaml up -d
port=$(docker compose -f compose.yaml config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["parabank"]["ports"][0]["published"])')
url="http://127.0.0.1:${port}/parabank/services/bank"
tries=60
while [ "$tries" -gt 0 ]; do
  if curl --silent --show-error --fail --output /dev/null "http://127.0.0.1:${port}/parabank/"; then
    printf 'ParaBank is ready at %s\n' "$url"
    exit 0
  fi
  tries=$((tries - 1))
  sleep 2
done
docker compose -f compose.yaml logs --tail=100 parabank >&2
echo "ParaBank did not become ready at $url" >&2
exit 1
