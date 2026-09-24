# Progress

**Current phase:** 0 — Modular monolith
**Default mode:** BUILD (switch per task with `MODE: GUIDED`)
**Last session summary (2026-09-24):**
- Done: Phase 0 complete: six modules behind `service.py`, import-boundary test, Place Order in one transaction, break-it (naive reservation oversells 10/10) and fix (1 winner), demo, ADR-0001. 65 tests green, lint clean, `make clean && make up && make demo-0` passes.
- Next: commit and tag `phase-0-done`; then Phase 1 (context map, gateway, extract notification, ACL).
- Open questions: none.

| Phase | Status | Demo passes | Tag | ADRs |
|---|---|---|---|---|
| 0 Modular monolith | ✅ | ✅ | phase-0-done (suggested) | ADR-0001 |
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
- Phase 1: the monolith needs a legacy `GET /customers/{id}` (`cust_nm`, `cust_eml`) for the notification ACL to call.
- Phase 5: cancel of PENDING/APPROVED with compensation (refund + release); `cancel_order` raises NotImplementedError until then.
- Phase 7: uvicorn's own access/startup logs are plain text; route them through structlog as JSON.
