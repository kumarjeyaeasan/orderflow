# Progress

**Current phase:** 0 — Modular monolith
**Default mode:** BUILD (switch per task with `MODE: GUIDED`)
**Last session summary (2026-09-24):**
- Done: Phase 0 step 1: uv workspace, Makefile, ruff/mypy/pytest, libs/common (logging, correlation ID), monolith skeleton (6 modules, health), Compose, Alembic schemas + seed. 17 tests green, lint clean, stack healthy.
- Next: step 2: domain + ORM per module, `service.py` interfaces, Place Order in one transaction, import-boundary test.
- Open questions: none.

| Phase | Status | Demo passes | Tag | ADRs |
|---|---|---|---|---|
| 0 Modular monolith | 🟨 | ⬜ | | |
| 1 Decomposition | ⬜ | ⬜ | | |
| 2 Sync comms and edge | ⬜ | ⬜ | | |
| 3 Resilience | ⬜ | ⬜ | | |
| 4 Async messaging | ⬜ | ⬜ | | |
| 5 Data and Sagas | ⬜ | ⬜ | | |
| 6 CQRS and Event Sourcing | ⬜ | ⬜ | | |
| 7 Observability | ⬜ | ⬜ | | |
| 8 Deployment and mesh | ⬜ | ⬜ | | |
| 9 Testing and hardening | ⬜ | ⬜ | | |

Legend: ⬜ not started · 🟨 in progress · ✅ done

## Known xfail tests (deliberate, fixed in a later phase)
| Test | Created in | Fixed in |
|---|---|---|

## Parking lot (ideas for later phases)
-
