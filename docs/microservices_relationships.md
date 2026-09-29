# Microservices Context Mapping Relationships

A summary of Domain-Driven Design (DDD) context mapping relationships between microservices.

## Summary table

| Relationship Pattern | Dependency Direction | Primary Focus | Best Used For... |
| :--- | :--- | :--- | :--- |
| **Conformist** | Upstream → Downstream | Adopting as-is | Large, stable third-party SaaS APIs |
| **Anti-Corruption Layer** | Upstream → Downstream | Local isolation | Legacy systems or unstable models |
| **Customer-Supplier** | Upstream → Downstream | Collaboration | Core internal features spanning two teams |
| **Open Host Service** | Upstream → Downstream | Public API contract | Shared utilities used by many microservices |
| **Partnership** | Bidirectional / Mutual | Joint delivery | Closely coupled subdomains |
| **Shared Kernel** | Bidirectional / Mutual | Shared code/data | Shared infrastructure constants/types |
| **Separate Ways** | None (Independent) | Zero integration | Maximizing team speed over integration |

## 1. Upstream / Downstream Relationships (Asymmetric Power)

In these relationships, the **upstream** service delivers data or capabilities, and its decisions directly
impact the **downstream** service. The downstream service is the one that must adapt.

- **Anti-Corruption Layer (ACL):** The downstream service refuses to let the upstream service's model pollute
  its own. It builds a translation layer (adapters/facades) to convert incoming data into its own clean
  internal language.
  - *Choose this* to protect your service from breaking changes in unstable upstream dependencies.
- **Customer-Supplier:** The upstream (Supplier) and downstream (Customer) teams work closely together. The
  downstream team's needs are formally factored into the upstream team's planning and release schedules.
  - *Choose this* when both teams are within the same company and need to coordinate features.
- **Open Host Service (OHS) / Published Language:** The upstream service acts as a public provider, offering a
  stable, well-documented API protocol (the Open Host) using a standard data format like JSON or XML (the
  Published Language).
  - *Choose this* when a single service (like an Identity Provider) needs to serve many different downstream
    consumers.

## 2. Mutually Dependent Relationships (Equal Power)

These relationships require deep cooperation because neither service can succeed or deploy independently
without the other.

- **Partnership:** Two service teams must coordinate their integration, design choices, and release schedules
  together. If one fails, both fail.
  - *Choose this* for microservices that are tightly aligned around a shared business feature.
- **Shared Kernel:** Two microservices physically share a small subset of the domain model, such as a shared
  library, database schema, or code module. Any change requires consensus from both teams.
  - > **Warning:** This is generally discouraged in microservices because it introduces tight coupling.

## 3. Independent / Free Relationships

These patterns describe a lack of technical dependency or standard organization.

- **Separate Ways:** The teams realize that integrating their microservices is too complex, expensive, or
  politically difficult. Instead, they choose to completely sever ties and accept any duplicated logic or data.
  - *Choose this* when total team autonomy outweighs the value of shared data.
- **Big Ball of Mud:** A chaotic state where boundaries are completely blurred, data leaks everywhere, and it is
  impossible to tell who is upstream or downstream.
  - > **Warning:** This is an architectural anti-pattern to avoid.
