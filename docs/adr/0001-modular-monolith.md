# ADR-0001: Start as a modular monolith with enforced module boundaries

- **Status:** Accepted
- **Phase:** 0
- **Date:** 2026-09-24
- **Pattern(s):** Monolithic Architecture, Modular Monolith, Aggregate

## Context
OrderFlow will be split into services over Phases 1–5. Before that, the "Place Order" flow has to work in
its simplest form, and the cut lines between the six business capabilities (customer, order, inventory,
payment, shipping, notification) have to exist in the code, not only on a diagram. Otherwise every later
extraction starts with untangling. Constraint C2 ("modules interact only through public interfaces, never
through another's tables") is enforced from Phase 0.

Phase 0 also includes a concurrency problem to observe: 10 simultaneous orders for the last unit of stock.
`test_naive_reservation_oversells_the_last_unit` and step 3 of `make demo-0` show the naive
read-check-write reservation shipping **10 lamps from a stock of 1**. The stock still reads 0 afterwards,
so the database's `CHECK (stock_qty >= 0)` never fires.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| A. Plain monolith (one package, shared models) | Fastest to write | Boundaries erode silently; later extraction is a rewrite |
| B. **Modular monolith**: one process, one DB, one schema per module, `service.py` as each module's only public surface, boundaries checked by a test | Simple deploys and ACID, plus boundaries that CI enforces | Needs discipline and tooling; some duplication (per-module DTOs and ORM bases) |
| C. Microservices from day one | "Realistic" immediately | Distribution problems before the domain is understood; nothing to compare against |

For the stock race:

| Option | Pros | Cons |
|---|---|---|
| Naive read → check in Python → write absolute value | Obvious code | Lost update: oversells under concurrency (proved by test) |
| `SELECT … FOR UPDATE`, then check and write | Explicit lock; lets you run arbitrary checks | Two round-trips; the lock is held across application code |
| **Conditional `UPDATE … SET qty = qty - :n WHERE id = :id AND qty >= :n RETURNING id`** | One statement, one round-trip; Postgres re-checks the condition after waiting on the row lock | The check is limited to what SQL can express |

## Decision
Option B. Each module lives in `monolith/src/monolith/modules/<name>/` with `api/`, `domain/` and `infra/`
layers and one public `service.py`. Other modules import only that file. `domain/` imports no framework
code. Both rules are checked by `monolith/tests/architecture.py` (AST-based, no third-party tool) and run
in `make test`. Each module owns a Postgres schema, with no foreign keys across schemas, so its data can
leave with it. The Place Order flow runs in one transaction owned by the API layer. A savepoint wraps
"reserve + charge", so a business failure rolls back the stock and money but keeps the order row as
`REJECTED`. Stock is taken with the conditional UPDATE, with lines locked in product-ID order to avoid
deadlocks. The naive version stays behind `ATOMIC_STOCK_RESERVATION=false` so the failure remains
reproducible.

## Consequences
- **Better:**
  - `test_atomic_reservation_has_exactly_one_winner` gives 1 SHIPPED and 9 REJECTED, with 1 payment and 1
    shipment (demo step 4).
  - `test_payment_failure_leaves_stock_unchanged` shows a failed charge rolling back the reservation
    (demo step 2).
  - `test_real_codebase_respects_module_boundaries` fails with file and line when a module imports another
    module's internals (checked by adding a forbidden import to `order/service.py`).
- **Worse / more complex:** each module has its own ORM `Base` and DTOs; the cross-module "join" in
  notification (customer lookup) is a function call instead of SQL. Seeds and tests reference fixed UUIDs.
- **Accepted limitation:** orders never rest in `PENDING` or `APPROVED`, because the whole flow finishes in
  one request, so `POST /orders/{id}/cancel` always returns 409 in Phase 0. `cancel_order` raises
  `NotImplementedError` for those states rather than cancelling without a refund. Compensation arrives in
  Phase 5.
- **To operate:** one container and one database. Migrations run at container start (`alembic upgrade head`).

## Guarantees we get for free from one ACID transaction (and which phase removes each)
| Guarantee | Where we rely on it | Lost in |
|---|---|---|
| Atomicity: reserve + charge + ship + notify commit together or not at all | `order/service.py::place_order` | Phase 2 (inventory and payment get their own DBs) |
| Immediate consistency: every module sees the same data right away | stock and wallet reads after an order | Phase 2 / 4 |
| Rollback as compensation: a failed charge undoes the reservation for free | the savepoint in `place_order` | Phase 2 (stock leak xfail), Phase 5 (sagas) |
| Exactly-once side effects: a notification row exists only if the order committed | `notification_log` in the same transaction | Phase 1 (notification over HTTP), Phase 4 (outbox) |
| No partial failure: one process is either up or down | the whole app | Phase 1 onwards |
| Cheap reads across modules | notification → customer lookup | Phase 1 (ACL over HTTP), Phase 5 (API composition) |

## Learnings
- The naive race reproduced on every run even with no artificial delay (10/10 shipped), because the
  window between read and commit spans several queries. A 50 ms delay stays in the naive path as a
  safety margin on slower machines.
- A lost update is invisible to a `CHECK` constraint: the final value (0) is legal. Only an order count
  against a stock count reveals it.
- In production you'd also want database-level limits on who can write which schema; here that arrives
  with per-service DB users in Phase 2.
