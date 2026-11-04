#!/usr/bin/env bash
# Curl walkthrough against a deployed API. Prints HTTP statuses only, never tokens or PHI.
# Usage: scripts/smoke-deployed.sh [API_URL]
set -euo pipefail

API="${1:-${API_URL:-https://api-production-b3c6.up.railway.app}}"
PDF="$(cd "$(dirname "$0")/.." && pwd)/evals/cases/genhealth-cpap-fax.pdf"
EMAIL="smoke-$(date +%s)-$RANDOM@example.com"
PASSWORD="correct-horse-9"
fail=0

status() { # label expected actual
  if [ "$2" = "$3" ]; then echo "ok   $1 -> $3"; else echo "FAIL $1 -> $3 (expected $2)"; fail=1; fi
}

code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$API/auth/register" \
  -H 'content-type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
status "POST /auth/register" 201 "$code"

login=$(curl -sS -w '\n%{http_code}' -X POST "$API/auth/login" -d "username=$EMAIL&password=$PASSWORD")
status "POST /auth/login" 200 "${login##*$'\n'}"
TOKEN=$(printf '%s' "${login%$'\n'*}" | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

extract=$(curl -sS -w '\n%{http_code}' -X POST "$API/orders/extract" -H "$AUTH" \
  -F "file=@$PDF;type=application/pdf" --max-time 120)
status "POST /orders/extract" 201 "${extract##*$'\n'}"
body="${extract%$'\n'*}"
ORDER=$(printf '%s' "$body" | jq -r .id)
echo "     extracted status: $(printf '%s' "$body" | jq -r .status)"

patch=$(curl -sS -w '\n%{http_code}' -X PATCH "$API/orders/$ORDER" -H "$AUTH" \
  -H 'content-type: application/json' -d '{"provider_npi":"1234567893"}')
status "PATCH /orders/{id}" 200 "${patch##*$'\n'}"
echo "     patched status: $(printf '%s' "${patch%$'\n'*}" | jq -r .status)"

status "GET /orders" 200 "$(curl -sS -o /dev/null -w '%{http_code}' "$API/orders" -H "$AUTH")"
status "DELETE /orders/{id}" 204 "$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE "$API/orders/$ORDER" -H "$AUTH")"
status "GET /orders/{id} after delete" 404 "$(curl -sS -o /dev/null -w '%{http_code}' "$API/orders/$ORDER" -H "$AUTH")"

exit "$fail"
