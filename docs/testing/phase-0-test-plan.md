# Phase 0 — Test plan (modular monolith)

For the short copy-paste version, see [phase-0-how-to-test.md](phase-0-how-to-test.md).

How to check Phase 0 is working, automatically and by hand. Each case has an ID, the command to run, and the
expected result. Run every command from the repo root.

**Status:** Phase 0 is complete. Every case below is implemented and was run on 2026-09-24.

---

## 1. Phase 0 acceptance criteria and their evidence

| Criterion (docs/ROADMAP.md) | Evidence |
|---|---|
| `make clean && make up && make demo-0` works on a fresh clone | M-20; ends with `Phase 0 demo passed.` |
| The concurrency test proves exactly one winner | A-31 `test_atomic_reservation_has_exactly_one_winner` |
| A payment failure leaves stock unchanged (single-transaction rollback) | A-22 `test_payment_failure_leaves_stock_unchanged`, demo step 2 |
| The import-boundary test fails if one module imports another's internals | A-35…A-37, and M-21 (a forbidden import in real code fails the test) |
| ADR-0001 records the modular monolith and its boundaries | `docs/adr/0001-modular-monolith.md` |

What's left for you: commit, tag `phase-0-done`, and answer the self-check (the ADR lists the answers).

---

## 2. Prerequisites

```bash
uv sync                  # install Python deps into .venv
docker info >/dev/null   # Docker must be running (component tests and the stack need it)
cp .env.example .env     # optional; every value has a default
```

Seed IDs used below:

| What | ID |
|---|---|
| Last Unit Lamp (stock = 1) | `10000000-0000-4000-8000-00000000000a` |
| Mechanical Keyboard (stock 50, 8999 minor units) | `10000000-0000-4000-8000-000000000001` |
| Alice Rich (wallet 1,000,000 minor units) | `20000000-0000-4000-8000-000000000001` |
| Zero Zoe (wallet 0) | `20000000-0000-4000-8000-000000000005` |

Shortcut used in the manual tests:

```bash
C="docker compose -f infra/compose/docker-compose.yml"
```

---

## 3. Quality gates (run after every change)

| ID | Check | Command | Expected |
|---|---|---|---|
| G-01 | Lint, format, types | `make lint` | `All checks passed!`, `… files already formatted`, `Success: no issues found` |
| G-02 | All automated tests | `make test` | `65 passed` |
| G-03 | Stack starts healthy | `make up` | Both containers `Healthy`, then `{"status":"ok","checks":{"postgres":"up"}}` |

Useful test selections:

```bash
uv run pytest -m "not component"            # unit tests only: fast, no Docker (35 tests)
uv run pytest -m component                  # component tests only: starts a Postgres container (30 tests)
uv run pytest -v                            # every test, one per line
uv run pytest <file>::<test_name>           # one test
```

---

## 4. Automated test cases

### 4.1 Correlation ID — `libs/common/tests/test_correlation.py`

| ID | Test | What it proves | Type |
|---|---|---|---|
| A-01 | `test_generates_id_when_missing` | With no header, a UUIDv4 is created, returned in `X-Correlation-ID`, and bound to the log context | happy |
| A-02 | `test_propagates_incoming_id` | A valid incoming ID is kept end to end | happy |
| A-03 | `test_replaces_malformed_id` | A non-UUID header is **rejected** and replaced (client input is never logged as an ID) | failure |
| A-04 | `test_context_is_cleared_after_request` | The ID doesn't leak into the next request's context | failure |

```bash
uv run pytest libs/common/tests/test_correlation.py -v
```

### 4.2 Config — `monolith/tests/unit/test_config.py`

| ID | Test | What it proves | Type |
|---|---|---|---|
| A-05 | `test_currency_must_be_iso_4217_shaped` | `CURRENCY=usd` is rejected at startup | failure |
| A-06 | `test_database_url_is_required` | A missing `DATABASE_URL` fails fast instead of falling back to a default | failure |

```bash
uv run pytest monolith/tests/unit/test_config.py -v
```

### 4.3 Health endpoints, no DB — `monolith/tests/unit/test_health.py`

| ID | Test | What it proves | Type |
|---|---|---|---|
| A-07 | `test_live_is_ok_even_when_db_is_down` | `/health/live` = 200 with no database | failure |
| A-08 | `test_ready_returns_503_when_db_refuses_connections` | `/health/ready` = 503 `{"postgres":"down"}` on connection refused | failure |
| A-09 | `test_ready_returns_503_within_timeout_when_db_hangs` | A hanging DB gives 503 within the timeout; the probe never hangs | failure |
| A-10 | `test_responses_carry_a_correlation_id` | The middleware is wired into the monolith app | happy |

```bash
uv run pytest monolith/tests/unit/test_health.py -v
```

### 4.4 Real Postgres (testcontainers) — `monolith/tests/component/`

Each session starts one throwaway `postgres:16` container. Before **every** test the schema is downgraded to base
and upgraded to head, so each test starts from the seed data and every migration's `downgrade()` is exercised.

| ID | Test | What it proves | Type |
|---|---|---|---|
| A-11 | `test_ready_is_ok_with_real_postgres` | `/health/ready` = 200 `{"postgres":"up"}` | happy |
| A-12 | `test_one_schema_per_module` | Schemas `customer, orders, inventory, payment, shipping, notification` exist | happy |
| A-13 | `test_seed_products` | 10 products; exactly one (Last Unit Lamp) has stock 1 | happy |
| A-14 | `test_seed_customers_have_wallets` | 5 customers with wallets; exactly one (Zero Zoe) has balance 0 | happy |
| A-15 | `test_customer_table_uses_legacy_column_names` | Customer table uses `cust_id, cust_nm, cust_eml` (the Phase 1 ACL relies on this) | happy |
| A-16 | `test_database_rejects_negative_stock` | The DB CHECK refuses `stock_qty < 0` (C1 backstop) | failure |
| A-17 | `test_database_rejects_negative_wallet_balance` | The DB CHECK refuses `balance_minor < 0` | failure |

```bash
uv run pytest monolith/tests/component -v
```

---

## 5. Manual test cases

Start with the stack running: `make up`.

### M-01 — Fresh start from a clean state
```bash
make clean && make up
```
**Expected:** images build, `orderflow-postgres-1 Healthy`, `orderflow-monolith-1 Healthy`, then
`{"status":"ok","checks":{"postgres":"up"}}`.

### M-02 — Liveness
```bash
curl -s -w ' HTTP %{http_code}\n' localhost:8000/health/live
```
**Expected:** `{"status":"ok"} HTTP 200`

### M-03 — Readiness
```bash
curl -s -w ' HTTP %{http_code}\n' localhost:8000/health/ready
```
**Expected:** `{"status":"ok","checks":{"postgres":"up"}} HTTP 200`

### M-04 — Migrations ran in the container on startup
```bash
$C logs monolith | grep "Running upgrade"
```
**Expected:** two lines: `-> 0001, One schema per module…` and `0001 -> 0002, Seed data…`

### M-05 — Migrations are idempotent
```bash
make migrate
```
**Expected:** only `Context impl PostgresqlImpl` / `Will assume transactional DDL`, with no "Running upgrade"
lines (already at head).

### M-06 — Seed data in the running stack
```bash
$C exec -T postgres psql -U orderflow -d orderflow -c "
select (select count(*) from inventory.products)                    as products,
       (select count(*) from inventory.products where stock_qty=1)  as last_unit,
       (select count(*) from customer.customers)                    as customers,
       (select count(*) from payment.wallets where balance_minor=0) as zero_wallets,
       (select version_num from alembic_version)                    as rev;"
```
**Expected:** `10 | 1 | 5 | 1 | 0002`

### M-07 — One schema per module
```bash
$C exec -T postgres psql -U orderflow -d orderflow -c '\dn'
```
**Expected:** `customer, inventory, notification, orders, payment, shipping` (plus `public`).

### M-08 — Correlation ID echoed back
```bash
curl -si localhost:8000/health/live -H 'X-Correlation-ID: 3f2b8c1e-0d4a-4e6b-9c7d-1a2b3c4d5e6f' | grep -i x-correlation
```
**Expected:** `x-correlation-id: 3f2b8c1e-0d4a-4e6b-9c7d-1a2b3c4d5e6f`

### M-09 — Correlation ID generated or replaced (failure path)
```bash
curl -si localhost:8000/health/live | grep -i x-correlation
curl -si localhost:8000/health/live -H 'X-Correlation-ID: garbage' | grep -i x-correlation
```
**Expected:** both return a **new** UUID; `garbage` is never echoed.

### M-10 — Database down: live stays up, ready reports it (failure path)
```bash
$C stop postgres
curl -s -w ' HTTP %{http_code}\n' localhost:8000/health/live
time curl -s -w ' HTTP %{http_code}\n' localhost:8000/health/ready
$C logs monolith | grep readiness_check_failed | tail -1
```
**Expected:**
- live: `{"status":"ok"} HTTP 200`
- ready: `{"status":"unavailable","checks":{"postgres":"down"}} HTTP 503` in about **2 s**. Inside Docker the
  lookup for the stopped `postgres` host hangs, so the `DB_READY_TIMEOUT_S` limit (default 2 s) ends it.
- log: a JSON line with `"event": "readiness_check_failed"`, `"dependency": "postgres"` and a `correlation_id`.

### M-11 — Database recovers without restarting the monolith
```bash
$C start postgres && sleep 4
curl -s -w ' HTTP %{http_code}\n' localhost:8000/health/ready
```
**Expected:** `{"status":"ok","checks":{"postgres":"up"}} HTTP 200` (`pool_pre_ping` discards the dead
connections).

### M-12 — The DB refuses negative stock (failure path)
```bash
$C exec -T postgres psql -U orderflow -d orderflow -c \
  "UPDATE inventory.products SET stock_qty = stock_qty - 2 WHERE id = '10000000-0000-4000-8000-00000000000a';"
```
**Expected:** `ERROR: … violates check constraint "ck_products_stock_non_negative"`

### M-13 — The DB refuses a negative wallet balance (failure path)
```bash
$C exec -T postgres psql -U orderflow -d orderflow -c \
  "UPDATE payment.wallets SET balance_minor = balance_minor - 1 WHERE customer_id = '20000000-0000-4000-8000-000000000005';"
```
**Expected:** `ERROR: … violates check constraint "ck_wallets_balance_non_negative"`

### M-14 — The image contains no dev tools
```bash
$C exec -T monolith sh -c 'ls /app/.venv/lib/python3.12/site-packages | grep -ciE "^(pytest|ruff|mypy|testcontainers)"'
```
**Expected:** `0`

### M-15 — REST Client
Open `http/health.http` in VS Code and click **Send Request** above each request.
**Expected:** the same results as M-02, M-03 and M-08.

### M-16 — e2e placeholder
```bash
make e2e
```
**Expected:** `No e2e tests yet (tests/e2e/test_*.py)` with a non-zero exit. Cross-service e2e tests start in
Phase 1.

---

## 6. Place Order, break-it and boundaries

### 6.1 Automated

| ID | Test (file) | What it proves | Type |
|---|---|---|---|
| A-18 | `test_successful_order_is_shipped_and_every_module_did_its_part` (`component/test_place_order.py`) | 201 SHIPPED; stock and wallet down; 1 payment, 1 shipment; APPROVED + SHIPPED notifications | happy |
| A-19 | `test_price_is_snapshotted_at_order_time` | A later price change doesn't alter the order | happy |
| A-20 | `test_unknown_order_is_404` | GET of an unknown order → 404 | failure |
| A-21 | `test_cancel_unknown_order_is_404` | Cancel of an unknown order → 404 | failure |
| A-22 | `test_payment_failure_leaves_stock_unchanged` | Zoe: REJECTED "insufficient funds"; **stock unchanged**; no payment or shipment | failure |
| A-23 | `test_partial_funds_charge_nothing` | Dan (3000) can't buy 8999; wallet untouched | failure |
| A-24 | `test_insufficient_stock_is_rejected_without_charging` | 2 lamps from stock 1 → REJECTED; no charge | failure |
| A-25 | `test_reservation_is_all_or_nothing` | Keyboard taken, then lamp fails → keyboard put back | failure |
| A-26 | `test_unknown_customer_is_refused_and_nothing_is_stored` | 422; no order row | failure |
| A-27 | `test_unknown_product_is_refused` | 422; nothing stored or reserved | failure |
| A-28 | `test_malformed_orders_are_refused` | No lines, qty 0 or −1, duplicate line, bad UUID → 422 | failure |
| A-29 | `test_cancel_of_terminal_order_is_409_and_changes_nothing` | SHIPPED and REJECTED can't be cancelled | failure |
| A-30 | `test_naive_reservation_oversells_the_last_unit` (`component/test_concurrency.py`) | **Break it:** naive mode ships more than 1 lamp from stock 1 | break-it |
| A-31 | `test_atomic_reservation_has_exactly_one_winner` | **Fix:** 1 SHIPPED, 9 REJECTED, stock 0, 1 payment, charged once | fix |
| A-32 | `component/test_catalogue_and_admin.py` (9 tests) | List/get products; stock ±; below zero → 422; top-up; amount ≤ 0 → 422; unknown → 404 | happy/failure |
| A-33 | `unit/test_order_aggregate.py` (15 tests) | Total in integer minor units; invalid orders refused; every legal and illegal transition | happy/failure |
| A-34 | `test_real_codebase_respects_module_boundaries` (`unit/test_architecture.py`) | The real modules only import each other's `service.py` | happy |
| A-35 | `test_reaching_into_another_modules_internals_fails` (5 cases) | Absolute, dotted, `from x import infra` and relative forms are all caught | failure |
| A-36 | `test_framework_import_in_domain_fails` (2 cases) | `sqlalchemy` / `fastapi` in `domain/` is caught | failure |
| A-37 | `test_allowed_imports_pass`, `test_violation_message_points_at_file_and_line` | No false positives; the message names file and line | happy |

```bash
uv run pytest monolith/tests/component/test_place_order.py -v
uv run pytest monolith/tests/component/test_concurrency.py -v -s     # -s prints the outcome counts
uv run pytest monolith/tests/unit/test_architecture.py -v
```

### 6.2 Manual

Seed IDs are in section 2. Start with `make up`.

#### M-17 — Place an order
```bash
curl -s -XPOST localhost:8000/orders -H 'content-type: application/json' \
  -d '{"customer_id":"20000000-0000-4000-8000-000000000001","lines":[{"product_id":"10000000-0000-4000-8000-000000000001","quantity":1}]}'
```
**Expected:** HTTP 201 with `"status":"SHIPPED"` and `"total_minor":8999`.

#### M-18 — Insufficient funds leaves stock unchanged
```bash
curl -s localhost:8000/products/10000000-0000-4000-8000-000000000001    # note stock_qty
curl -s -XPOST localhost:8000/orders -H 'content-type: application/json' \
  -d '{"customer_id":"20000000-0000-4000-8000-000000000005","lines":[{"product_id":"10000000-0000-4000-8000-000000000001","quantity":1}]}'
curl -s localhost:8000/products/10000000-0000-4000-8000-000000000001    # same stock_qty
```
**Expected:** `"status":"REJECTED"`, `"rejection_reason":"insufficient funds"`; stock is the same before and after.

#### M-19 — The break-it race by hand
```bash
ATOMIC_STOCK_RESERVATION=false docker compose -f infra/compose/docker-compose.yml up -d --wait monolith
curl -s -XPOST localhost:8000/admin/products/10000000-0000-4000-8000-00000000000a/stock \
  -H 'content-type: application/json' -d '{"delta": 1}'                 # stock back to 1 (adjust delta if needed)
seq 10 | xargs -P10 -I{} curl -s -w '\n' -XPOST localhost:8000/orders -H 'content-type: application/json' \
  -d '{"customer_id":"20000000-0000-4000-8000-000000000001","lines":[{"product_id":"10000000-0000-4000-8000-00000000000a","quantity":1}]}' \
  | grep -o '"status":"[A-Z]*"' | sort | uniq -c
```
**Expected:** more than one `SHIPPED`. Repeat with `ATOMIC_STOCK_RESERVATION=true` (and stock reset to 1):
exactly `1 "status":"SHIPPED"` and `9 "status":"REJECTED"`. Finish with `ATOMIC_STOCK_RESERVATION=true`.

#### M-20 — The full demo from a clean state
```bash
make clean && make up && make demo-0
```
**Expected:** four green ✔ lines and `Phase 0 demo passed.` It is safe to re-run; it resets the lamp's stock itself.

#### M-21 — The boundary test catches a real violation
Add this line under `import structlog` in `monolith/src/monolith/modules/order/service.py`:
```python
from monolith.modules.inventory.infra.models import ProductRow  # noqa: F401
```
```bash
uv run pytest monolith/tests/unit/test_architecture.py::test_real_codebase_respects_module_boundaries -q
```
**Expected:** `1 failed`, with `service.py:12: cross-module internals: imports monolith.modules.inventory.infra.models.ProductRow`.
Remove the line afterwards.

#### M-22 — Every endpoint via REST Client
Open `http/products.http`, `http/orders.http` and `http/admin.http` and click **Send Request** on each.
**Expected:** the status codes written in each request's comment.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: monolith` in tests | `uv sync --reinstall-package monolith --reinstall-package orderflow-common` |
| Component tests hang or fail at startup | Docker isn't running, or it can't pull `postgres:16` offline (pull it once while online) |
| `make up` fails on a port | Something else uses 5432 or 8000; set `POSTGRES_HOST_PORT` or `MONOLITH_HOST_PORT` in `.env` |
| Seed data looks wrong after edits | `make clean && make up` (seed migrations run once per fresh volume) |
