#!/usr/bin/env sh
set -eu
set +x
install_secret() {
  name="$1"
  variable="$2"
  value=$(printenv "$variable" || true)
  if [ -z "$value" ]; then
    echo "Required Actions secret $variable is missing" >&2
    exit 1
  fi
  printf '%s\n' "$value" > "src/test/resources/data/$name.csv"
  chmod 600 "src/test/resources/data/$name.csv"
}
install_secret users USERS_CSV
install_secret transfers TRANSFERS_CSV
install_secret statements STATEMENTS_CSV
install_secret loans LOANS_CSV
install_secret payments PAYMENTS_CSV
