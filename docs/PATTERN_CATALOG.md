# Pattern Catalog

57 patterns. Fill in **Where in code** and **Demo** as you complete each one. This becomes your personal index.

| # | Pattern | Category | Phase | Problem it solves here | Main trade-off | Where in code | Demo | Reference |
|---|---|---|---|---|---|---|---|---|
| 1 | Monolithic Architecture | Architecture | 0 | Baseline: simple deploys, ACID everywhere | Scaling and team coupling | `monolith/` | `make demo-0` steps 1–2 | https://microservices.io/patterns/monolithic.html |
| 2 | Modular Monolith | Architecture | 0 | Enforced module boundaries before splitting | Needs discipline and tooling | `monolith/src/monolith/modules/*/service.py`, `monolith/tests/architecture.py` | `test_real_codebase_respects_module_boundaries` | No verified single source; see ADR-0001 |
| 3 | Aggregate | Data / DDD | 0 | Consistency boundary for an order | Choosing boundaries is hard | `modules/order/domain/model.py` | `test_order_aggregate.py` | https://microservices.io/patterns/data/aggregate.html |
| 4 | Decompose by Business Capability | Decomposition | 1 | Where to cut services | Capabilities can be vague | | | https://microservices.io/patterns/decomposition/decompose-by-business-capability.html |
| 5 | Decompose by Subdomain | Decomposition | 1 | DDD-based cut | Needs domain insight | | | https://microservices.io/patterns/decomposition/decompose-by-subdomain.html |
| 6 | Strangler Fig | Refactoring | 1–5 | Migrate without a big-bang rewrite | Temporary dual running | | | https://microservices.io/patterns/refactoring/strangler-application.html |
| 7 | Anti-Corruption Layer | Refactoring | 1 | Keep the legacy customer model out of new services | Translation code | | | https://microservices.io/patterns/refactoring/anti-corruption-layer.html |
| 8 | Remote Procedure Invocation | Communication | 2 | Request/response (REST, gRPC) | Temporal coupling | | | https://microservices.io/patterns/communication-style/rpi.html |
| 9 | Database per Service | Data | 2 | Loose data coupling | No cross-service joins or transactions | | | https://microservices.io/patterns/data/database-per-service.html |
| 10 | API Gateway | External API | 1–2 | Single entry point; auth and rate limits | Bottleneck or god-service risk | | | https://microservices.io/patterns/apigateway.html |
| 11 | Backends for Frontends | External API | 2 | Client-specific responses | More components | | | https://samnewman.io/patterns/architectural/bff/ |
| 12 | Service Registry | Discovery | 2 | Locate instances | Critical infrastructure | | | https://microservices.io/patterns/service-registry.html |
| 13 | Client-side Discovery | Discovery | 2 | Client picks an instance | Logic in every client | | | https://microservices.io/patterns/client-side-discovery.html |
| 14 | Server-side Discovery | Discovery | 2 | Platform or router picks an instance | Platform dependency | | | https://microservices.io/patterns/server-side-discovery.html |
| 15 | Self-registration | Discovery | 2 | Service registers itself | Registry coupling in code | | | https://microservices.io/patterns/self-registration.html |
| 16 | Access Token | Security | 2 | Propagate identity (JWT) | Revocation is hard | | | https://microservices.io/patterns/security/access-token.html |
| 17 | Externalized Configuration | Cross-cutting | 0–8 | Same image, any environment | Config sprawl | | | https://microservices.io/patterns/externalized-configuration.html |
| 18 | Timeout | Reliability | 3 | Bounded waits | Choosing values | | | https://learn.microsoft.com/en-us/azure/architecture/patterns/retry |
| 19 | Retry with Backoff and Jitter | Reliability | 3 | Survive transient faults | Retry storms; duplicates | | | https://learn.microsoft.com/en-us/azure/architecture/patterns/retry |
| 20 | Circuit Breaker | Reliability | 3 | Stop calling a failing dependency | Threshold tuning | | | https://microservices.io/patterns/reliability/circuit-breaker.html |
| 21 | Bulkhead | Reliability | 3 | Isolate resource pools | Lower utilisation | | | https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead |
| 22 | Rate Limiting | Reliability | 3 | Protect from bursts | Rejects legitimate traffic | | | https://learn.microsoft.com/en-us/azure/architecture/patterns/rate-limiting-pattern |
| 23 | Fallback | Reliability | 3 | Degrade gracefully (notification) | Stale or partial behaviour | | | No verified single source; see ADR-0006 |
| 24 | Health Check API | Observability | 3 | Liveness and readiness | Shallow checks lie | | | https://microservices.io/patterns/observability/health-check-api.html |
| 25 | Messaging | Communication | 4 | Temporal decoupling | Broker ops; eventual consistency | | | https://microservices.io/patterns/communication-style/messaging.html |
| 26 | Domain Event | Data | 4 | Announce state changes | Event design and versioning | | | https://microservices.io/patterns/data/domain-event.html |
| 27 | Transactional Outbox | Data | 4 | Atomic DB write + publish | Extra table and relay | | | https://microservices.io/patterns/data/transactional-outbox.html |
| 28 | Polling Publisher | Data | 4 | Relay outbox rows | Latency and DB load | | | https://microservices.io/patterns/data/polling-publisher.html |
| 29 | Transaction Log Tailing | Data | 4 | Relay via CDC (Debezium) | Operational complexity | | | https://microservices.io/patterns/data/transaction-log-tailing.html |
| 30 | Idempotent Consumer | Communication | 4 | Handle duplicate deliveries | Dedup storage | | | https://microservices.io/patterns/communication-style/idempotent-consumer.html |
| 31 | Idempotency Key (API) | Communication | 4 | Safe client retries of POST /orders | Key storage and expiry | | | https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/ |
| 32 | Dead-Letter Queue | Messaging | 4 | Isolate poison messages | Needs monitoring and replay | | | https://www.enterpriseintegrationpatterns.com/patterns/messaging/DeadLetterChannel.html |
| 33 | Saga | Data | 5 | Cross-service business transactions | No isolation; compensation logic | | | https://microservices.io/patterns/data/saga.html |
| 34 | Compensating Transaction | Data | 5 | Undo completed steps | Not all actions are reversible | | | https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction |
| 35 | Semantic Lock | Data | 5 | PENDING state guards in-flight orders | Lock handling and timeouts | | | Saga countermeasures in Richardson, Microservices Patterns (book) |
| 36 | API Composition | Data | 5 | Cross-service queries | In-memory joins; partial failure | | | https://microservices.io/patterns/data/api-composition.html |
| 37 | Shared Database (anti-pattern demo) | Data | 5 | Shows the coupling problem | Tight coupling | | | https://microservices.io/patterns/data/shared-database.html |
| 38 | CQRS | Data | 6 | Efficient cross-service reads | Eventual consistency; duplication | | | https://microservices.io/patterns/data/cqrs.html |
| 39 | Event Sourcing | Data | 6 | Audit trail; reliable events | Learning curve; versioning | | | https://microservices.io/patterns/data/event-sourcing.html |
| 40 | Snapshot | Data | 6 | Faster aggregate rebuild | Snapshot consistency | | | No verified single source; see ADR-0010 |
| 41 | Event Upcasting | Data | 6 | Load old event versions | Upcaster maintenance | | | No verified single source; see ADR-0010 |
| 42 | Correlation ID | Observability | 0–7 | Tie logs and messages to one request | Must propagate everywhere | | | https://www.enterpriseintegrationpatterns.com/patterns/messaging/CorrelationIdentifier.html |
| 43 | Log Aggregation | Observability | 7 | Search logs across services | Cost and volume | | | https://microservices.io/patterns/observability/application-logging.html |
| 44 | Distributed Tracing | Observability | 7 | Follow a request across services | Instrumentation; sampling | | | https://microservices.io/patterns/observability/distributed-tracing.html |
| 45 | Application Metrics | Observability | 7 | RED metrics | Cardinality | | | https://microservices.io/patterns/observability/application-metrics.html |
| 46 | Exception Tracking | Observability | 7 | Group and deduplicate errors | Another tool | | | https://microservices.io/patterns/observability/exception-tracking.html |
| 47 | Audit Logging | Observability | 7 | Who did what | Storage and privacy | | | https://microservices.io/patterns/observability/audit-logging.html |
| 48 | Service per Container | Deployment | 2–8 | Isolation and portability | Needs orchestration | | | https://microservices.io/patterns/deployment/service-per-container.html |
| 49 | Microservice Chassis | Cross-cutting | 8 | Shared cross-cutting library | Framework lock-in | | | https://microservices.io/patterns/microservice-chassis.html |
| 50 | Service Template | Cross-cutting | 8 | Consistent new services | Template drift | | | https://microservices.io/patterns/service-template.html |
| 51 | Sidecar | Deployment | 8 | Offload cross-cutting concerns | Resource overhead | | | https://microservices.io/patterns/deployment/sidecar.html |
| 52 | Service Mesh | Deployment | 8 | Uniform mTLS, retries, traffic control | Complexity; latency | | | https://microservices.io/patterns/deployment/service-mesh.html |
| 53 | Blue-Green Deployment | Deployment | 8 | Instant switch and rollback | Double capacity | | | https://martinfowler.com/bliki/BlueGreenDeployment.html |
| 54 | Canary Release | Deployment | 8 | Limit the blast radius of new versions | Needs good metrics | | | https://martinfowler.com/bliki/CanaryRelease.html |
| 55 | Consumer-Driven Contract Test | Testing | 9 | Independent deploys | Pact workflow | | | https://microservices.io/patterns/testing/service-integration-contract-test.html |
| 56 | Service Component Test | Testing | 0–9 | Test a service in isolation | Stub maintenance | | | https://microservices.io/patterns/testing/service-component-test.html |
| 57 | Test Pyramid | Testing | 0–9 | Balance speed and confidence | Discipline | | | https://martinfowler.com/articles/practical-test-pyramid.html |

Rows marked **No verified single source** are well-known techniques without one canonical reference page. Your ADR is the reference for them.

## Further reading
- Chris Richardson, *Microservices Patterns* (Manning, 2018): https://microservices.io/book
- Sam Newman, *Building Microservices*, 2nd edition (O'Reilly, 2021): https://samnewman.io/books/building_microservices_2nd_edition/
- Microsoft Azure Architecture Center, *Cloud design patterns*: https://learn.microsoft.com/en-us/azure/architecture/patterns/
- Hohpe and Woolf, *Enterprise Integration Patterns* (messaging): https://www.enterpriseintegrationpatterns.com/
- uv workspaces: https://docs.astral.sh/uv/concepts/projects/workspaces/ · uv in Docker: https://docs.astral.sh/uv/guides/integration/docker/
