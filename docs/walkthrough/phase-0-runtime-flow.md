# Phase 0 — How it runs, end to end

This follows one full lifecycle of the Phase 0 system: from typing `make up`, through a single
`POST /orders` request, to shutting everything down. Each stage names the file and line that drives it,
plus a command you can run to watch it happen.

Line numbers are as of tag `phase-0-done` (+ docs). Versions checked in this repo: uv 0.12.18,
Docker Compose 5.5, FastAPI 0.141, Starlette 1.7, uvicorn 0.53, SQLAlchemy 2.0, Alembic 1.20.

---

## The big picture

```mermaid
flowchart LR
    make[make up] --> compose[docker compose]
    compose --> pg[(postgres 16)]
    compose --> alembic[alembic upgrade head]
    alembic --> uvicorn[uvicorn PID 1]
    uvicorn --> app[FastAPI app from create_app]
    curl[curl or REST Client] -->|localhost 8000| uvicorn
    alembic -->|postgres 5432| pg
    app -->|postgres 5432| pg
```
(Text version: `make up` → docker compose → starts postgres, then the monolith container. That container
first runs alembic migrations against postgres, then starts uvicorn, which serves the FastAPI app. Your curl
reaches uvicorn through `localhost:8000`. The app reaches the database at `postgres:5432`.)

| Stage | What happens | Driven by |
|---|---|---|
| 1 | `make up` becomes a `docker compose` command | `Makefile:5-6, 14-16` |
| 2 | Compose builds the monolith image | `infra/compose/docker-compose.yml:22-25`, `monolith/Dockerfile` |
| 3 | Compose starts Postgres and waits until it's healthy | `docker-compose.yml:6-20, 34-36` |
| 4 | The monolith container starts and runs migrations | `Dockerfile:36`, `migrations/env.py` |
| 5 | **Entry point:** uvicorn imports and calls `create_app()` | `Dockerfile:36`, `monolith/main.py:16` |
| 6 | App startup (lifespan), then listening on port 8000 | `main.py:20-31` |
| 7 | The healthcheck passes, and `make up` returns | `docker-compose.yml:37-43`, `Makefile:16` |
| 8 | A request travels through the app to the DB and back | `order/api/routes.py:61`, `order/service.py:55` |
| 9 | Shutdown (`make down` / `make clean`) | `Makefile:18-22`, `main.py:30-31` |

---

## Stage 1 — `make up`: from Make to Docker Compose

```bash
make up
```

`make` reads `Makefile` and finds the `up` target:

```make
5  ENV_FILE := $(if $(wildcard .env),--env-file .env,)
6  COMPOSE  := docker compose -f infra/compose/docker-compose.yml $(ENV_FILE)
...
14 up: ## Build and start core services; wait until healthy
15 	$(COMPOSE) up -d --build --wait
16 	@echo "--- $(MONOLITH_URL)/health/ready"; curl -fsS $(MONOLITH_URL)/health/ready; echo
```

So line 15 becomes:

```bash
docker compose -f infra/compose/docker-compose.yml [--env-file .env] up -d --build --wait
```

| Flag | Meaning |
|---|---|
| `-f infra/compose/…yml` | Which Compose file to use (it isn't in the repo root) |
| `--env-file .env` | Only added if `.env` exists (line 5); values like `${POSTGRES_USER:-orderflow}` read from it |
| `up` | Create and start the services |
| `-d` | Detached: run in the background and give the terminal back |
| `--build` | Rebuild the monolith image if the code changed |
| `--wait` | Don't return until every service is **healthy** (see Stage 7) |

**See it:** `make -n up` prints the commands without running them.

---

## Stage 2 — Building the monolith image

`docker-compose.yml:22-25`:

```yaml
monolith:
  build:
    context: ../..               # the repo root (relative to the compose file)
    dockerfile: monolith/Dockerfile
```

The **build context** is the whole repo, minus what `.dockerignore` excludes (`.venv`, `.git`, `tests`,
`.env`…), because the image must include both `monolith/` and `libs/common/`.

`monolith/Dockerfile` has **two stages**:

**Stage "builder"** (lines 4–22): installs the packages into a virtual environment.
```dockerfile
5  COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /bin/uv            # get the uv binary
12 COPY pyproject.toml uv.lock .python-version ./                    # dependency definitions only…
13 COPY libs/common/pyproject.toml libs/common/pyproject.toml
14 COPY monolith/pyproject.toml monolith/pyproject.toml
16 uv sync --locked --no-dev --package monolith --no-install-workspace   # …so this slow layer is cached
19 COPY libs/common libs/common                                      # now the real code
20 COPY monolith monolith
22 uv sync --locked --no-dev --package monolith --no-editable        # install our 2 packages into .venv
```
- `--locked`: fail if `uv.lock` is out of date, so versions are exactly what the tests used.
- `--no-dev`: no pytest, ruff or mypy in the image.
- `--package monolith`: install `monolith` and its dependencies (which include `orderflow-common`).
- `--no-editable`: copy the code *into* `.venv/lib/python3.12/site-packages/`, so the final image doesn't
  need the source tree.

**Final stage** (lines 25–36): a clean, small runtime image.
```dockerfile
28 COPY --from=builder /app/.venv /app/.venv                         # only the venv from the builder
29 COPY monolith/alembic.ini monolith/alembic.ini                    # migrations aren't a Python package,
30 COPY monolith/migrations monolith/migrations                      # so they're copied as files
31 ENV PATH="/app/.venv/bin:$PATH"                                   # `python`, `uvicorn`, `alembic` = venv's
33 USER app                                                          # don't run as root
36 CMD ["sh", "-c", "alembic … upgrade head && exec uvicorn monolith.main:create_app --factory …"]
```

**See it:**
```bash
docker image ls orderflow-monolith
docker image inspect orderflow-monolith --format '{{json .Config.Cmd}}'   # the CMD from line 36
```

---

## Stage 3 — Postgres starts first

Compose creates a private network `orderflow_default`. On it, each service is reachable **by its
service name**: the monolith reaches the database at host `postgres`, port `5432`.

`docker-compose.yml:6-20`:
- `image: postgres:16`: the official image. On the **first** start with an empty volume, it runs `initdb`
  and creates user, password and database from `POSTGRES_USER/PASSWORD/DB`.
- `volumes: pgdata:/var/lib/postgresql/data`: the data survives `make down`; only `make clean` deletes it.
- `ports: 5432:5432`: also exposed on your machine (for `psql` or a DB tool).
- `healthcheck: pg_isready …` every 2 s: the container is "healthy" once Postgres accepts connections.

`docker-compose.yml:34-36`:
```yaml
depends_on:
  postgres:
    condition: service_healthy     # the monolith isn't started until postgres is healthy
```
Without this, the monolith would start while Postgres is still initialising, and migrations would fail.

**See it:**
```bash
docker compose -f infra/compose/docker-compose.yml ps           # STATUS shows (healthy)
docker compose -f infra/compose/docker-compose.yml logs postgres | tail
```

---

## Stage 4 — The container starts: migrations first

Docker runs the image's `CMD` (there's no `ENTRYPOINT`), which is `Dockerfile:36`:

```bash
sh -c "alembic -c monolith/alembic.ini upgrade head && exec uvicorn monolith.main:create_app --factory --host 0.0.0.0 --port 8000"
```

`sh` is briefly PID 1 and runs two commands joined by `&&`: **the second runs only if the first
succeeds**. A failed migration stops the container before it serves any traffic.

### 4a. `alembic -c monolith/alembic.ini upgrade head`
1. `alembic` is `/app/.venv/bin/alembic` (found via `PATH`).
2. It reads `monolith/alembic.ini`: `script_location = %(here)s/migrations`, where `%(here)s` is the folder
   containing the ini file, so `/app/monolith/migrations`.
3. It runs `migrations/env.py`:
   - lines 21-25: no URL in the ini, so it reads `DATABASE_URL` from the environment. Compose set it at
     `docker-compose.yml:27` to
     `postgresql+asyncpg://orderflow:orderflow@postgres:5432/orderflow`.
   - line 61: `asyncio.run(run_async_migrations())` connects with the async `asyncpg` driver.
4. Alembic reads the `alembic_version` table (empty on a fresh DB), sees which revisions are missing, and
   applies them in order, each in a transaction:

| Revision | File | Does |
|---|---|---|
| 0001 | `versions/0001_module_schemas.py` | 6 schemas + `customers`, `products`, `wallets` tables |
| 0002 | `versions/0002_seed_data.py` | 10 products, 5 customers and wallets (fixed UUIDs) |
| 0003 | `versions/0003_order_flow_tables.py` | `orders`, `order_lines`, `payments`, `shipments`, `notification_log` |

5. It writes `0003` into `alembic_version`. On the next start, `upgrade head` finds nothing to do, so
   restarts are safe.

**See it:**
```bash
docker compose -f infra/compose/docker-compose.yml logs monolith | grep "Running upgrade"
docker compose -f infra/compose/docker-compose.yml exec -T postgres \
  psql -U orderflow -d orderflow -c 'select * from alembic_version'
```

---

## Stage 5 — THE ENTRY POINT: `exec uvicorn monolith.main:create_app --factory`

This is where our Python application actually begins. How each part of the line is determined:

| Part | What it does | Where it's defined |
|---|---|---|
| `exec` | Replaces `sh` with uvicorn, so **uvicorn becomes PID 1** and receives Docker's stop signal directly (Stage 9) | `Dockerfile:36` |
| `uvicorn` | The ASGI web server; the `/app/.venv/bin/uvicorn` script, found via `PATH` | installed by `uv sync` (`Dockerfile:22`); declared in `monolith/pyproject.toml` |
| `monolith.main` | A **Python import path**, not a file path. uvicorn runs `import monolith.main`, which Python finds in `.venv/lib/python3.12/site-packages/monolith/main.py` | package built from `monolith/src/monolith` (see `[tool.hatch.build.targets.wheel]` in `monolith/pyproject.toml`) |
| `:create_app` | After the colon: the attribute to take from that module | `monolith/src/monolith/main.py:16` |
| `--factory` | `create_app` is a **function that builds** the app, so uvicorn calls `create_app()` (no arguments) | uvicorn option: "Treat APP as an application factory" |
| `--host 0.0.0.0` | Listen on all interfaces *inside the container*. `127.0.0.1` would be unreachable from outside | `Dockerfile:36` |
| `--port 8000` | Container port; Compose maps host `8000` to it (`docker-compose.yml:33`) | `Dockerfile:36` |

**Why a factory instead of a module-level `app = FastAPI()`?** The tests call
`create_app(Settings(database_url=<test container>))` with their own settings, and every test gets a fresh
app. A module-level app would read the environment once at import time and be shared everywhere.

### What `import monolith.main` triggers
Importing `main.py` runs its imports (`main.py:4-13`), which pull in each module's API routes, which import
their `service.py`, which import their `domain/` and `infra/` code (ORM models). **No database connection
happens at import time.** The code is only defined, not run.

### What `create_app()` does (`main.py:16-39`)
```python
17  settings = settings or get_settings()      # no argument → read env vars (config.py:25-27)
18  configure_logging(...)                     # structlog → JSON lines on stdout
20  @asynccontextmanager async def lifespan…   # defined now, run later by uvicorn (Stage 6)
33  app = FastAPI(..., lifespan=lifespan)
34  app.add_middleware(CorrelationIdMiddleware)
35  app.include_router(health.router)          # /health/live, /health/ready
36  app.include_router(inventory_router)       # /products, /admin/products/{id}/stock
37  app.include_router(order_router)           # /orders, /orders/{id}, /orders/{id}/cancel
38  app.include_router(payment_router)         # /admin/customers/{id}/wallet
39  return app
```

`get_settings()` → `Settings()` (`config.py:7-22`) is **pydantic-settings**: each field is filled from the env
var of the same name (case-insensitive). `database_url` comes from `DATABASE_URL`, and
`atomic_stock_reservation` from `ATOMIC_STOCK_RESERVATION`. It's validated too: `CURRENCY=usd` would stop
the app right here. `database_url` has no default, so a missing value fails fast.

**See the routes:**
```bash
curl -s localhost:8000/openapi.json | python3 -c 'import json,sys; [print(m.upper(), p) for p,v in json.load(sys.stdin)["paths"].items() for m in v]'
```
Or open http://localhost:8000/docs in a browser. FastAPI generates this interactive page for free.

---

## Stage 6 — App startup (lifespan), then serving

uvicorn now runs the **lifespan startup**, the code before `yield` in `main.py:20-29`:

```python
24  engine = make_engine(settings.database_url)   # db.py:17 → create_async_engine(..., pool_pre_ping=True)
25  app.state.settings = settings
26  app.state.engine = engine
27  app.state.sessionmaker = make_sessionmaker(engine)
29  yield                                           # ← the app is now "running"; uvicorn serves requests
```

The engine is a **connection pool**, and creating it does **not** connect. Connections open lazily on the
first query. So the app starts even if the DB is down: `/health/live` returns 200 and `/health/ready`
returns 503 (tests A-07 and A-08).

uvicorn logs:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Stage 7 — Healthy, so `make up` returns

`docker-compose.yml:37-43`: every 5 s, Docker runs *inside the container*:
```python
urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)   # healthy if 200
```
`/health/ready` (`health.py:25-39`) runs `SELECT 1` with a 2-second limit. The first success marks the
container **healthy**, and `docker compose up --wait` returns. Make then runs `Makefile:16`:

```
--- http://localhost:8000/health/ready
{"status":"ok","checks":{"postgres":"up"}}
```

The system is up: **two containers, one network, one volume, and uvicorn as PID 1 in the monolith.**

**See it:**
```bash
docker compose -f infra/compose/docker-compose.yml ps
docker inspect --format '{{json .State.Health.Log}}' orderflow-monolith-1 | python3 -m json.tool | tail -8
docker compose -f infra/compose/docker-compose.yml exec monolith cat /proc/1/cmdline | tr '\0' ' '; echo   # PID 1 = uvicorn
```

---

## Stage 8 — One request, end to end: `POST /orders`

```bash
curl -s -X POST localhost:8000/orders -H 'content-type: application/json' \
  -d '{"customer_id":"20000000-0000-4000-8000-000000000001","lines":[{"product_id":"10000000-0000-4000-8000-000000000001","quantity":1}]}'
```

```mermaid
sequenceDiagram
  participant C as curl
  participant U as uvicorn
  participant M as Middleware stack
  participant R as order/api/routes.py
  participant S as order/service.py
  participant X as other modules' service.py
  participant DB as Postgres
  C->>U: HTTP POST /orders (host :8000 → container :8000)
  U->>M: ASGI call(scope, receive, send)
  M->>M: CorrelationIdMiddleware: read or create X-Correlation-ID
  M->>R: router matches POST /orders
  R->>R: validate JSON → OrderIn (422 if invalid)
  R->>DB: BEGIN
  R->>S: place_order(session, …)
  S->>X: customer.get_customer, inventory.get_products
  X->>DB: SELECT customer, SELECT products
  S->>DB: INSERT order (PENDING) + lines
  S->>DB: SAVEPOINT
  S->>X: inventory.reserve → UPDATE stock … WHERE stock_qty >= n
  S->>X: payment.charge → UPDATE wallet … WHERE balance >= total, then INSERT payment
  S->>DB: RELEASE SAVEPOINT
  S->>X: notification (APPROVED), shipping.create_shipment, notification (SHIPPED)
  S->>DB: UPDATE order status = SHIPPED
  S-->>R: Order (domain object)
  R->>DB: COMMIT
  R-->>M: 201 + OrderOut JSON
  M-->>U: add X-Correlation-ID header
  U-->>C: HTTP 201 response
```

### 8a. Network → uvicorn
`localhost:8000` on your machine is forwarded by Docker (`ports: 8000:8000`) to the container's port 8000,
where uvicorn listens. uvicorn parses the HTTP bytes into an **ASGI** call: `app(scope, receive, send)`.
`scope` holds the method, path and headers; `receive` yields the body; `send` sends the response.

### 8b. The middleware stack
FastAPI builds the stack like an onion, from outside to inside (checked in the installed
`fastapi/applications.py`, `build_middleware_stack`):

```
ServerErrorMiddleware        ← turns unexpected crashes into a plain 500
  CorrelationIdMiddleware    ← ours: libs/common/src/orderflow_common/correlation.py
    ExceptionMiddleware      ← turns HTTPException(422/404/409) into JSON error responses
      Router                 ← finds the route for "POST /orders"
```

`CorrelationIdMiddleware.__call__`:
- reads `X-Correlation-ID`, or creates a new UUID if it's missing or malformed;
- binds it to the log context, so **every log line of this request** carries `correlation_id`;
- wraps `send` so the response gets the same header.

### 8c. Routing, validation and dependencies (`order/api/routes.py:61-80`)
```python
61 @router.post("/orders", status_code=201)
62 async def place_order(body: OrderIn, sm: SessionMaker, settings: AppSettings) -> OrderOut:
```
Before our function body runs, FastAPI:
1. **Validates the body** against `OrderIn` (pydantic): the UUIDs must parse, `quantity > 0`, and there must
   be at least 1 line. If not, it returns **422 immediately** and our code never runs.
2. **Resolves dependencies**: `SessionMaker` and `AppSettings` (`db.py:36-37`) read the objects that
   lifespan stored on `app.state` in Stage 6.

### 8d. Open the transaction (`routes.py:66`)
```python
66 async with sm() as session, session.begin():
```
This takes a connection from the pool and sends `BEGIN`. **Everything until the end of this `with` block
is ONE database transaction.** That's the core idea of Phase 0.

### 8e. The business flow (`order/service.py:55-115`)

| Lines | Step | Module called (through its `service.py` only) | SQL, roughly |
|---|---|---|---|
| 69-70 | Customer exists? | `customer.get_customer` | `SELECT … FROM customer.customers WHERE cust_id=…` |
| 72-75 | Load products, check currency | `inventory.get_products` | `SELECT … FROM inventory.products WHERE id IN (…)` |
| 76-80 | Build the **aggregate**: `Order.create(...)` with prices snapshotted; validates lines | (pure Python, `order/domain/model.py`) | none |
| 81 | Save it as `PENDING` | own `infra/repository.py` | `INSERT INTO orders.orders …; INSERT INTO orders.order_lines …` |
| 86 | Open a **savepoint** | | `SAVEPOINT sa_savepoint_1` |
| 87-91 | Take stock | `inventory.reserve` → `infra/stock.py` | `UPDATE inventory.products SET stock_qty = stock_qty - 1 WHERE id=… AND stock_qty >= 1 RETURNING id` |
| 92-94 | Charge the wallet | `payment.charge` | `SELECT` the wallet (exists? same currency?), then `UPDATE payment.wallets SET balance_minor = balance_minor - 8999 WHERE … AND balance_minor >= 8999`; `INSERT INTO payment.payments …` |
| (end of 86) | Savepoint OK | | `RELEASE SAVEPOINT sa_savepoint_1` |
| 108 | `order.approve()`: PENDING → APPROVED (state machine check) | domain | none |
| 109 | "Email" APPROVED | `notification.notify_order_status`, which itself calls `customer.get_customer` | `INSERT INTO notification.notification_log …` |
| 110 | Book shipment | `shipping.create_shipment` | `INSERT INTO shipping.shipments …` |
| 111-112 | `order.ship()`: APPROVED → SHIPPED; save | own repository | `SELECT` the order row (and lines), then `UPDATE orders.orders SET status='SHIPPED', updated_at=now() …` |
| 113 | "Email" SHIPPED | `notification.notify_order_status` | `INSERT INTO notification.notification_log …` |
| 115 | Return the `Order` object | | |

### 8e½. The real SQL, captured

This is what SQLAlchemy actually sent for one successful order (Alice) and one rejected order (Zoe),
recorded against the running stack with SQLAlchemy event listeners and shortened to fit:

```
--- Alice: SHIPPED                              --- Zoe: REJECTED (wallet 0)
BEGIN                                           BEGIN
SELECT … FROM customer.customers                SELECT … FROM customer.customers
SELECT … FROM inventory.products                SELECT … FROM inventory.products
INSERT INTO orders.orders …                     INSERT INTO orders.orders …
INSERT INTO orders.order_lines …                INSERT INTO orders.order_lines …
SAVEPOINT sa_savepoint_1                        SAVEPOINT sa_savepoint_1
UPDATE inventory.products SET stock_qty=…       UPDATE inventory.products SET stock_qty=…   ← stock taken
SELECT … FROM payment.wallets                   SELECT … FROM payment.wallets
UPDATE payment.wallets SET balance_minor=…      UPDATE payment.wallets SET balance_minor=…  ← 0 rows: no money
INSERT INTO payment.payments …                  ROLLBACK TO SAVEPOINT sa_savepoint_1        ← stock given back
RELEASE SAVEPOINT sa_savepoint_1                SELECT … FROM orders.orders (+ lines)
SELECT … FROM customer.customers                UPDATE orders.orders SET status='REJECTED', rejection_reason=…
INSERT INTO notification.notification_log …     SELECT … FROM customer.customers
INSERT INTO shipping.shipments …                INSERT INTO notification.notification_log …
SELECT … FROM orders.orders (+ lines)           COMMIT
UPDATE orders.orders SET status='SHIPPED' …
SELECT … FROM customer.customers
INSERT INTO notification.notification_log …
COMMIT
```

Read the right-hand column slowly: the stock `UPDATE` really ran, and `ROLLBACK TO SAVEPOINT` undid it,
while the order row written *before* the savepoint survived and was committed as `REJECTED`. That is
the whole Phase 0 guarantee in six lines of SQL.

### 8f. Commit and respond (`routes.py:66 → 80`)
Leaving the `async with` block sends **`COMMIT`**. Only now are all those rows visible to anyone else.
If the commit failed, an exception would propagate and **no 201 is sent**. That's why the transaction is
opened in the route, before the response is built. Then:
- line 80: `OrderOut.from_domain(order)` → JSON body;
- FastAPI sends `201 Created`;
- `CorrelationIdMiddleware` adds `X-Correlation-ID` on the way out;
- uvicorn writes the HTTP bytes to the socket, and the connection returns to the pool.

**The request has terminated.** The process keeps running and waits for the next request.

### 8g. The other endings of the same request

| Situation | Where it branches | Result |
|---|---|---|
| Bad JSON / quantity 0 / missing field | FastAPI validation (8c), before our code | 422; no SQL at all |
| Unknown customer or product, duplicate line | `service.py:69-80` raises → `routes.py:74-79` | the transaction **rolls back** (nothing stored) → 422 |
| **Not enough money** (e.g. Zoe) | `payment.charge` raises inside the savepoint (`service.py:92`) | `ROLLBACK TO SAVEPOINT` undoes **the stock update too**; `service.py:97-98` → `order.reject(...)`; lines 100-106 save REJECTED + email; COMMIT → **201 with `"status":"REJECTED"`** |
| Not enough stock | `inventory.reserve` raises (`service.py:87`) | same as above, with reason "insufficient stock…" |
| Unexpected crash (bug, DB lost mid-request) | exception escapes everything | transaction rolled back; `ServerErrorMiddleware` → 500 |

The **"not enough money"** row is the Phase 0 acceptance criterion "a payment failure leaves stock
unchanged". It works because stock and money live in one database and one transaction. Phase 2 splits
them, and this guarantee disappears.

### 8h. The break-it switch
`settings.atomic_stock_reservation` is passed from `routes.py:72` → `service.py:90` → `inventory.reserve`,
which picks one of:
- `take_stock_atomic`: one conditional `UPDATE`; Postgres serialises concurrent buyers on the row lock
  and re-checks `stock_qty >= n` for each;
- `take_stock_naive`: `SELECT stock_qty`, compare in Python, then `UPDATE … SET stock_qty = <value
  computed in Python>`. Ten concurrent requests all read 1 and all write 0, so all ten succeed.

The value comes from the env var `ATOMIC_STOCK_RESERVATION` (`docker-compose.yml:31`), read once in
`create_app()`. Changing it needs a container restart, which is what the demo does.

**See a request in the logs:**
```bash
docker compose -f infra/compose/docker-compose.yml logs monolith | grep -E 'order_shipped|order_rejected|email_sent' | tail -5
```
Each line is JSON with the same `correlation_id` for everything that belongs to one request.

---

## Stage 9 — Termination

### `make down`: stop, keep the data
```bash
make down        # → docker compose -f infra/compose/docker-compose.yml down
```
1. Docker sends **SIGTERM** to PID 1 of each container.
2. In the monolith, PID 1 is **uvicorn** (thanks to `exec` in `Dockerfile:36`). uvicorn:
   - stops accepting new connections;
   - lets in-flight requests finish;
   - runs the **lifespan shutdown**, the code after `yield` in `main.py:30-31`:
     `await engine.dispose()` closes every pooled DB connection cleanly;
   - exits with code 0.
3. Postgres receives SIGTERM and does a clean shutdown (flushes to disk).
4. Compose removes both containers and the network. **The `pgdata` volume stays.**

Without `exec`, `sh` would be PID 1. `sh` doesn't forward SIGTERM to its child, so Docker would wait
10 s and then **SIGKILL** everything: no graceful shutdown, and connections cut mid-flight.

Next `make up`: Postgres finds existing data (no `initdb`), and `alembic upgrade head` finds everything
applied (no-op). Orders placed earlier are still there.

### `make clean`: stop and erase
```bash
make clean       # → docker compose … down -v --remove-orphans
```
Same as `down`, plus `-v` deletes the `pgdata` volume. The next `make up` starts from zero: `initdb` →
migrations 0001→0003 → fresh seed data. The demo's "clean state" means exactly this.

### Abnormal endings
| What | What you'd see |
|---|---|
| A migration fails | `&&` stops before uvicorn; the container exits, never becomes healthy; `make up` fails after `--wait`. `make logs s=monolith` shows the alembic error |
| Postgres dies while running | `/health/ready` → 503, and Docker marks the monolith **unhealthy**. It doesn't restart it: Compose has no `restart:` policy here, and healthchecks only *report*. When Postgres returns, `pool_pre_ping` swaps in fresh connections and the app recovers on its own (manual test M-11) |
| The monolith crashes | The container exits; nothing restarts it (no restart policy). Kubernetes adds automatic restarts in Phase 8 |

---

## Bonus — The same code under `make test` (no uvicorn, no Compose)

```bash
make test        # → uv run pytest
```
1. `uv run` ensures `.venv` is in sync with `uv.lock`, then runs `pytest` from it.
2. pytest reads `[tool.pytest.ini_options]` in the root `pyproject.toml`: test folders, `asyncio_mode = "auto"`.
3. Unit tests (`monolith/tests/unit/`) need no DB and run in milliseconds.
4. Component tests: `monolith/tests/component/conftest.py`:
   - `database_url` fixture: **testcontainers** starts a throwaway `postgres:16` container on a random
     port and runs Alembic against it (the same migrations as Stage 4);
   - `fresh_db` fixture (autouse): downgrade to base + upgrade to head **before every test**;
   - `client` fixture: `create_app(Settings(database_url=<test DB>))`, the **same factory as Stage 5**,
     wrapped in `httpx.ASGITransport`. Requests go straight into the ASGI app in-process, with no network
     and no uvicorn. `running_app()` (`tests/helpers.py`) runs the lifespan (Stage 6) around it.
5. At the end of the session, testcontainers removes the throwaway Postgres.

This is why `create_app` is a factory: production (uvicorn + env vars) and tests (explicit `Settings`)
build the app the same way, with different configuration.

---

## Command cheat sheet: watch each stage

```bash
C="docker compose -f infra/compose/docker-compose.yml"

make -n up                                                   # 1: what make will run
docker image inspect orderflow-monolith --format '{{json .Config.Cmd}}'   # 2: the CMD
$C ps                                                        # 3/7: running + (healthy)
$C logs monolith | grep "Running upgrade"                    # 4: migrations
$C exec monolith cat /proc/1/cmdline | tr '\0' ' '; echo     # 5: PID 1 is uvicorn
$C logs monolith | grep -E "startup complete|Uvicorn running" # 6: app started
curl -s localhost:8000/health/ready                          # 7: readiness
# browser: http://localhost:8000/docs                       # 5: every route, try them live
$C logs -f monolith                                          # 8: watch requests live (Ctrl+C to stop)
$C exec -T postgres psql -U orderflow -d orderflow -c \
  "select status, count(*) from orders.orders group by 1"   # 8: what requests left behind
make down        # 9: graceful stop, data kept
make clean       # 9: stop and erase data
```
