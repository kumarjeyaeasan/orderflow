# Phase 0 — Test plan (modular monolith)

How to check Phase 0 is working, automatically and by hand. Each case has an ID, the command to run, and the
expected result. Run every command from the repo root.

**Status legend:** ✅ implemented and passing · ⏳ planned for a later Phase 0 step (not runnable yet)

---

## 1. What is left to finish Phase 0

Phase 0 is done only when every acceptance criterion in `docs/ROADMAP.md` is met with evidence
(see "Definition of Done: a phase" in `CLAUDE.md`).

| # | Work item | Roadmap task | Status |
|---|---|---|---|
| 1 | uv workspace, Makefile, ruff/mypy/pytest, `.env.example`, testcontainers fixture | T1 | ✅ Step 1 |
| 2 | `monolith/` with six modules (`api/ domain/ infra/`), legacy customer fields, health endpoints | T2 | ✅ skeleton (Step 1) |
| 3 | One Postgres DB, one schema per module | T3 | ✅ Step 1 |
| 4 | Compose (postgres + monolith), Alembic, seed data | T6 | ✅ Step 1 |
| 5 | Domain models + ORM per module; public `service.py` interface per module | T2, T4 | ⏳ Step 2 |
| 6 | Import-boundary test (a module may import only another module's `service.py`) | T4 | ⏳ Step 2 |
| 7 | API: `POST /orders`, `GET /orders/{id}`, `POST /orders/{id}/cancel`, `GET /products[/{id}]`, admin stock and wallet top-up | Brief §4 | ⏳ Step 2–3 |
| 8 | Place Order in **one DB transaction** (reserve → charge → approve → ship → notify) | T5 | ⏳ Step 3 |
| 9 | **Break it:** naive stock check (read → check in Python → write), with a test showing more than one winner | Break it | ⏳ Step 4 |
| 10 | **Fix:** atomic conditional `UPDATE … WHERE qty >= :n` (or `SELECT … FOR UPDATE`), with a test showing exactly one winner | Break it | ⏳ Step 4 |
| 11 | `.http` files for every endpoint | T6 | ⏳ (health only so far) |
| 12 | `scripts/demo/phase-0.sh` + `make demo-0` | Demo | ⏳ Step 5 |
| 13 | ADR-0001: modular monolith and module boundaries | Acceptance | ⏳ Step 5 |
| 14 | Update `docs/PROGRESS.md`, suggest tag `phase-0-done` | DoD | ⏳ Step 5 |

**Acceptance criteria (from ROADMAP), with the test that will prove each one:**

| Criterion | Proved by | Status |
|---|---|---|
| `make clean && make up && make demo-0` works on a fresh clone | M-01 + M-20 | ⏳ (demo missing) |
| The concurrency test proves exactly one winner | P-09 | ⏳ |
| A payment failure leaves stock unchanged (single-transaction rollback) | P-05 | ⏳ |
| The import-boundary test fails if one module imports another's internals | P-01, P-02 | ⏳ |
| ADR-0001 exists | `ls docs/adr/0001-*` | ⏳ |

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
| G-02 | All automated tests | `make test` | `17 passed` (the count grows with later steps) |
| G-03 | Stack starts healthy | `make up` | Both containers `Healthy`, then `{"status":"ok","checks":{"postgres":"up"}}` |

Useful test selections:

```bash
uv run pytest -m "not component"            # unit tests only: fast, no Docker (10 tests)
uv run pytest -m component                  # component tests only: starts a Postgres container (7 tests)
uv run pytest -v                            # every test, one per line
uv run pytest <file>::<test_name>           # one test
```

---

## 4. Automated test cases (implemented in Step 1) ✅

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

Each session starts a throwaway `postgres:16` container and runs `alembic upgrade head` against it.

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

## 5. Manual test cases (implemented in Step 1) ✅

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

### M-16 — Placeholder targets fail clearly
```bash
make demo-0 ; make e2e
```
**Expected (until Step 5):** `scripts/demo/phase-0.sh does not exist yet` and
`No e2e tests yet (tests/e2e/test_*.py)`, each with a non-zero exit.

---

## 6. Test cases still to build in Phase 0 ⏳

Written down now so the target is clear. IDs are stable; the test names may change when they're written.

### Automated

| ID | Planned test | What it will prove | Type |
|---|---|---|---|
| P-01 | Import boundary: clean codebase | No module imports another module's `api/`, `domain/` or `infra/` | happy |
| P-02 | Import boundary: violation detected | A deliberate cross-module internal import makes the checker fail | failure |
| P-03 | Domain imports no framework code | `*/domain/` imports no fastapi, sqlalchemy or pydantic-settings | failure-guard |
| P-04 | Place order, happy path | Order `SHIPPED`; stock ↓ by quantity; wallet ↓ by total; shipment + notification rows exist | happy |
| P-05 | Insufficient funds (Zero Zoe) | Order `REJECTED`; **stock unchanged**; wallet unchanged (single-transaction rollback) | failure |
| P-06 | Insufficient stock | Order `REJECTED`; no charge; stock unchanged | failure |
| P-07 | Multi-line order, one line short | **No** line reserved (all or nothing) | failure |
| P-08 | Naive reserve, 10 parallel orders for the last unit | **Break it:** more than one order succeeds (kept behind a toggle so it stays reproducible) | break-it |
| P-09 | Atomic reserve, 10 parallel orders for the last unit | Exactly **1** `SHIPPED`, 9 `REJECTED`, stock = 0 | fix |
| P-10 | Price snapshot | Changing a product price after ordering doesn't change the order total | happy |
| P-11 | Validation errors | Unknown product or customer → 404/422; quantity ≤ 0 → 422 | failure |
| P-12 | Order state machine | Allowed transitions pass; e.g. `SHIPPED → CANCELLED` raises | failure |
| P-13 | Cancel in `PENDING`/`APPROVED` | `CANCELLED`, with stock and wallet restored | happy |
| P-14 | Cancel in `SHIPPED`/`REJECTED` | 409; nothing changes | failure |
| P-15 | Admin stock adjust and wallet top-up | Values change; a negative result → 422 | happy/failure |
| P-16 | Money | Totals are integer minor units in `CURRENCY`; no floats | happy |

### Manual (once the endpoints exist)

| ID | Planned check | Command (indicative) |
|---|---|---|
| M-17 | Place an order as Alice | `curl -s -XPOST localhost:8000/orders -H 'content-type: application/json' -d '{"customer_id":"20000000-0000-4000-8000-000000000001","lines":[{"product_id":"10000000-0000-4000-8000-000000000001","quantity":1}]}'` → `SHIPPED` |
| M-18 | Order as Zero Zoe | Same request with Zoe's ID → `REJECTED`, stock unchanged |
| M-19 | 10 parallel orders for the last unit | `seq 10 \| xargs -P10 -I{} curl -s -XPOST localhost:8000/orders …` → one success, stock 0 |
| M-20 | Full demo from a clean state | `make clean && make up && make demo-0` |
| M-21 | Every endpoint via REST Client | `http/*.http` |

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: monolith` in tests | `uv sync --reinstall-package monolith --reinstall-package orderflow-common` |
| Component tests hang or fail at startup | Docker isn't running, or it can't pull `postgres:16` offline (pull it once while online) |
| `make up` fails on a port | Something else uses 5432 or 8000; set `POSTGRES_HOST_PORT` or `MONOLITH_HOST_PORT` in `.env` |
| Seed data looks wrong after edits | `make clean && make up` (seed migrations run once per fresh volume) |
