#!/usr/bin/env bash
# Phase 0 demo: one process, one database, one transaction.
#   1. A successful order.
#   2. An insufficient-funds order: REJECTED, and the stock it reserved is rolled back.
#   3. Break it: 10 parallel orders for the last lamp with ATOMIC_STOCK_RESERVATION=false.
#   4. Fix it:   the same race with ATOMIC_STOCK_RESERVATION=true.
# Needs: a running stack (make up), curl, python3. Exits non-zero if an expectation fails.
set -euo pipefail
cd "$(dirname "$0")/../.."

set -a; [ -f .env ] && . ./.env; set +a
BASE="http://localhost:${MONOLITH_HOST_PORT:-8000}"
COMPOSE=(docker compose -f infra/compose/docker-compose.yml)
[ -f .env ] && COMPOSE+=(--env-file .env)
PGUSER_="${POSTGRES_USER:-orderflow}"; PGDB_="${POSTGRES_DB:-orderflow}"

KEYBOARD=10000000-0000-4000-8000-000000000001
LAMP=10000000-0000-4000-8000-00000000000a
ALICE=20000000-0000-4000-8000-000000000001
ZOE=20000000-0000-4000-8000-000000000005
N=10

bold() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✔ %s\033[0m\n' "$*"; }
fail() { printf '  \033[31m✘ %s\033[0m\n' "$*"; exit 1; }
field() { python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }
sql()  { "${COMPOSE[@]}" exec -T postgres psql -U "$PGUSER_" -d "$PGDB_" -tAc "$1"; }
stock()   { curl -fsS "$BASE/products/$1" | field stock_qty; }
balance() { sql "SELECT balance_minor FROM payment.wallets WHERE customer_id = '$1'"; }
order_json() { printf '{"customer_id":"%s","lines":[{"product_id":"%s","quantity":%d}]}' "$1" "$2" "$3"; }
place() { curl -fsS -X POST "$BASE/orders" -H 'content-type: application/json' -d "$(order_json "$@")"; }

restart_monolith() {  # $1 = true|false
  ATOMIC_STOCK_RESERVATION="$1" "${COMPOSE[@]}" up -d --wait monolith >/dev/null 2>&1
  echo "  monolith restarted with ATOMIC_STOCK_RESERVATION=$1"
}

set_stock() {  # $1 = product, $2 = wanted quantity
  local delta=$(( $2 - $(stock "$1") ))
  curl -fsS -X POST "$BASE/admin/products/$1/stock" -H 'content-type: application/json' \
    -d "{\"delta\": $delta}" >/dev/null
}

race() {  # prints "shipped rejected"
  local body dir; body=$(order_json "$ALICE" "$LAMP" 1); dir=$(mktemp -d)
  # One file per request: parallel curls writing to one shared pipe can interleave their output.
  seq "$N" | xargs -P "$N" -I{} curl -sS -o "$dir/{}.json" -X POST "$BASE/orders" \
      -H 'content-type: application/json' -d "$body"
  python3 - "$dir" <<'PY'
import json, pathlib, sys
statuses = [json.loads(p.read_text()).get("status") for p in pathlib.Path(sys.argv[1]).glob("*.json")]
print(statuses.count("SHIPPED"), statuses.count("REJECTED"))
PY
  rm -rf "$dir"
}

bold "0. Stack is ready"
curl -fsS "$BASE/health/ready"; echo

bold "1. Alice orders 1 keyboard (happy path)"
s0=$(stock $KEYBOARD); b0=$(balance $ALICE)
r=$(place $ALICE $KEYBOARD 1); st=$(field status <<<"$r")
s1=$(stock $KEYBOARD); b1=$(balance $ALICE)
echo "  status=$st  stock $s0 -> $s1  wallet $b0 -> $b1"
[ "$st" = SHIPPED ] && [ "$s1" -eq $((s0 - 1)) ] && [ "$b1" -eq $((b0 - 8999)) ] \
  && ok "shipped, stock and wallet both decremented" || fail "unexpected happy-path result"

bold "2. Zoe (wallet 0) orders 1 keyboard: payment fails AFTER stock was reserved"
s0=$(stock $KEYBOARD)
r=$(place $ZOE $KEYBOARD 1); st=$(field status <<<"$r"); why=$(field rejection_reason <<<"$r")
s1=$(stock $KEYBOARD)
echo "  status=$st  reason=\"$why\"  stock $s0 -> $s1"
[ "$st" = REJECTED ] && [ "$s1" -eq "$s0" ] \
  && ok "rejected, and the reservation was rolled back with the failed charge (one transaction)" \
  || fail "stock changed on a failed payment"

bold "3. BREAK IT: $N parallel orders for the last lamp, naive reservation"
restart_monolith false
set_stock $LAMP 1
read -r shipped rejected < <(race)
left=$(stock $LAMP)
echo "  lamps in stock: 1   shipped: $shipped   rejected: $rejected   stock now: $left"
[ "$shipped" -gt 1 ] \
  && ok "OVERSOLD: $shipped customers paid for 1 lamp; stock still reads $left (lost update)" \
  || fail "expected the naive version to oversell"

bold "4. FIX IT: the same race, atomic conditional UPDATE"
restart_monolith true
set_stock $LAMP 1
read -r shipped rejected < <(race)
left=$(stock $LAMP)
echo "  lamps in stock: 1   shipped: $shipped   rejected: $rejected   stock now: $left"
[ "$shipped" -eq 1 ] && [ "$rejected" -eq $((N - 1)) ] && [ "$left" -eq 0 ] \
  && ok "exactly one winner" || fail "expected exactly one winner"

bold "Phase 0 demo passed."
