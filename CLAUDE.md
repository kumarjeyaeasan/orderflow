# CLAUDE.md — Microservices Patterns Lab (Python)

Claude Code reads this file at the start of every session. It holds durable rules only; details live in `docs/`.

## Mission
Learn microservice design patterns by building ONE evolving, **working** order-processing system ("OrderFlow") in
Python. It starts as a modular monolith and is decomposed phase by phase. Each pattern is introduced when the
previous phase creates the problem it solves.

**Two equal goals, neither optional:**
1. **Working code.** Every pattern is implemented, runs in Docker Compose, and is proven by automated tests and a
   runnable demo script. A pattern that isn't demonstrably working does not count as learned.
2. **Understanding.** The learner can explain why the pattern exists, what breaks without it, and what it costs.

## Current state
@docs/PROGRESS.md

## Reference docs (read on demand)
- `docs/PROJECT_BRIEF.md`: domain, services, events, API, constraints (with the phase each constraint starts)
- `docs/ROADMAP.md`: phases 0–9 with tasks, break-it experiments, demo scripts, and acceptance criteria
- `docs/PATTERN_CATALOG.md`: pattern → phase → problem → trade-off → code location
- `docs/SESSION_PLAYBOOK.md`: session prompts and habits
- `docs/adr/`: one ADR per decision (template: `docs/adr/0000-template.md`)

## Definition of Done: a step
A step is done only when **all** of these are true:
- The code runs: the affected services start and pass `/health/ready` under `make up`.
- Tests exist for the new behaviour, **including at least one failure path**, and `make test` passes.
- `make lint` is clean.
- Claude has **actually run** these commands in this session and shown the relevant output.
  Never claim something passes without running it. If a command can't be run, say so explicitly.
- No `LEARNER-WRITES` stub is left unimplemented (see Modes).

## Definition of Done: a phase
All steps are done, plus:
- Every acceptance criterion in `docs/ROADMAP.md` is met, with evidence (test name, command, or output).
- `scripts/demo/phase-N.sh` runs from a clean state (`make clean && make up && make demo-N`) and visibly shows
  the failure *without* the pattern (the break-it toggle) and the success *with* it.
- The ADR is written, `docs/PROGRESS.md` is updated, and a git tag `phase-N-done` is suggested.

## Working rules (MANDATORY)
1. **One phase at a time.** Don't implement later-phase work. If a later pattern would help, add it to the
   parking lot in `docs/PROGRESS.md` in one line and continue.
2. **Plan, then code.** Before implementing a pattern:
   - state the problem it solves in *this* codebase (≤10 lines);
   - list the files to touch and the tests to add;
   - wait for approval.
3. **Small, verified increments.** After each increment, run the tests. Keep the build green between steps.
4. **Break it first.** Implement the phase's break-it experiment as a failing test (or an env toggle such as
   `OUTBOX_ENABLED=false`) *before* the fix, so the failure is observed and stays reproducible.
5. **Explain what was built.** After implementing, walk through the key lines and the failure paths they handle.
6. **Honesty.**
   - Never invent library functions, parameters, CLI flags, or config keys. When unsure, check the installed
     package (read the source under `.venv`, `uv pip show <pkg>`) or the official docs, and say which you used.
   - Flag version-sensitive advice.
   - If a requirement is ambiguous, ask one clarifying question instead of assuming.
7. **No silent scope creep.** Don't add services, frameworks, or abstractions beyond the brief without asking.

## Modes (the learner picks per task; the default is in `docs/PROGRESS.md`)
- `MODE: BUILD` (default): Claude implements fully and tests it, then explains.
- `MODE: GUIDED`: Claude writes the scaffolding and tests first. The core pattern logic is left as
  `# LEARNER-WRITES:` stubs with hints, and the tests fail until the stubs are done. Claude reviews the attempt.
  If the learner says "show solution", Claude completes the stub. The step is not done until the tests pass.

## Tech stack (defaults; change only via an ADR)
- Python 3.12, **uv** workspace (root `pyproject.toml` + one member per service + `libs/common`)
- FastAPI + Uvicorn, Pydantic v2, pydantic-settings
- SQLAlchemy 2.x async + asyncpg + Alembic; PostgreSQL 16 (one database and DB user per service)
- httpx for HTTP between services; grpcio + grpcio-tools from Phase 2
- RabbitMQ via aio-pika (Phase 4+); Redis (Phase 3+); Kafka optional (Phase 6)
- pytest + pytest-asyncio + testcontainers; ruff; mypy (strict for `libs/common`)
- Docker Compose through Phase 7; kind (Kubernetes) in Phase 8
- structlog; OpenTelemetry → Jaeger, Prometheus, Grafana, Loki (Phase 7)
- A `Makefile` is the single entry point for commands (it works on macOS, Linux, and WSL)

## Repository layout
```
pyproject.toml  uv.lock  Makefile  .env.example
services/<name>/          # customer, order, inventory, payment, shipping, notification, order-query
  src/<name>/{api,domain,infra,messaging}/   # domain/ imports no framework code
  migrations/  tests/{unit,component}/  pyproject.toml  Dockerfile
gateway/                  # hand-written FastAPI gateway first; Traefik/Kong compared later
monolith/                 # Phase 0 app; shrinks until deleted in Phase 5
libs/common/              # logging, tracing, outbox, idempotency, resilience, event envelope
contracts/                # openapi/, proto/, events/ (JSON Schema)
infra/compose/            # docker-compose.yml (+ profiles: messaging, observability, kafka, debezium)
infra/k8s/                # Phase 8
scripts/demo/             # phase-N.sh demo scripts
tests/e2e/                # cross-service end-to-end tests
docs/
```
**Docker build rule:** the build context is the repo root, so each service image can install `libs/common` from
the workspace. Follow uv's Docker integration guide and verify the flags against the installed uv version.

## Coding conventions
- **Money:** integer minor units (e.g. cents) plus an ISO 4217 code; one configured currency (`CURRENCY`). No floats.
- **IDs and time:** UUIDv4 strings; timestamps in UTC ISO-8601.
- **Health:** every service exposes `GET /health/live` (process up) and `GET /health/ready` (dependencies reachable).
- **Correlation:** every request reads or creates `X-Correlation-ID`, then logs and propagates it (HTTP headers and
  message headers).
- **Events:** use the envelope in `docs/PROJECT_BRIEF.md`, versioned (`OrderCreated` v1), with a JSON Schema in
  `contracts/events/`.
- **Config:** env vars only (pydantic-settings). Commit `.env.example`; never commit `.env` or secrets.
- **Code quality:** type hints everywhere. No bare `except:`. Every outbound call has an explicit timeout
  (from Phase 3; Phase 2 deliberately omits them to demonstrate the problem).

## Make targets (create in Phase 0; keep this list in sync)
```
make up        # docker compose up -d --build (core services)
make down      # stop
make clean     # stop and delete volumes (fresh state)
make logs s=<service>
make test      # unit + component tests for all services
make e2e       # end-to-end tests against the running stack
make lint      # ruff check + ruff format --check + mypy on libs/common
make fmt       # ruff format + ruff check --fix
make migrate   # alembic upgrade head for all services
make demo-N    # run scripts/demo/phase-N.sh
```
