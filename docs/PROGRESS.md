# Progress

**Current phase:** 1 — Decomposition (plan: `docs/phases/phase-1.md`)
**Default mode:** COACH: the learner codes, Claude guides and reviews (switch per task with `MODE: BUILD` or `MODE: GUIDED`)
**Last session summary (2026-09-24):**
- Done: Phase 0 complete: six modules behind `service.py`, import-boundary test, Place Order in one transaction, break-it (naive reservation oversells 10/10) and fix (1 winner), demo, ADR-0001. 65 tests green, lint clean, `make clean && make up && make demo-0` passes.
- Next: Phase 1 (context map, gateway, extract notification, ACL). Phase 0 is tagged `phase-0-done` and pushed; docs added: how-to-test, runtime walkthrough, git push guide.
- Open questions: none.
- 2026-09-29: working mode changed to COACH; Phase 1 plan written to `docs/phases/phase-1.md`.

| Phase | Status | Demo passes | Tag | ADRs |
|---|---|---|---|---|
| 0 Modular monolith | ✅ | ✅ | phase-0-done | ADR-0001 |
| 1 Decomposition | 🟨 | ⬜ | | |
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
