# ADR-0002: Split by business capability, extract notification first, behind a switch

- **Status:** Proposed
- **Phase:** 1
- **Date:** 2026-09-29
- **Pattern(s):** Decompose by Business Capability, Decompose by Subdomain, Strangler Fig, Anti-Corruption Layer

## Context

At the end of Phase 0, OrderFlow is one program with one database. Six modules (order, inventory, payment,
shipping, notification, customer) live inside it, each with its own tables. A test stops them from reaching
into each other's code (ADR-0001).

**What hurts today? Honestly, nothing.** One developer, low traffic, and one program is the simplest thing that
works. We split it to learn how, before it hurts. It *would* start to hurt in a real company:

- **Teams get in each other's way.** With five teams in one program, a change to email wording and a change to
  payments ship in the same deployment, and one team's bug can block everyone's release.
- **Everything scales together.** If order traffic grows 100×, we'd have to run 100× of the whole program,
  including parts that are barely used.
- **Everything fails together.** A crash anywhere (say, a memory leak in notification) takes down order-taking too.

Two decisions are needed now:
1. **Where to draw the lines** between future services.
2. **Which module to move out first, and how**, without clients noticing and with a way back if it goes wrong.

The analysis behind this ADR is in `docs/context-map.md`: who depends on whom, which tables each module owns, and
capability versus subdomain.

## Options considered

### Decision 1: where to draw the lines

| Option | Pros | Cons |
|---|---|---|
| **A. By business capability: six parts** (one per thing the business does) | Each part already owns its own tables; each changes for its own reasons; matches the brief's service list | More network calls between services once they're separate |
| B. By subdomain, with larger groups (e.g. "checkout" = order + stock, "after the sale" = shipping + notification) | Order and stock stay in one database, so a failed payment still puts the stock back automatically | Bundles things that change for different reasons (e.g. admin stock corrections vs orders); fewer, larger services |
| C. Don't split | Simplest; everything stays in one all-or-nothing database step | No learning goal met; the "would hurt" list above stays unsolved |

### Decision 2: which module to move out first

Each candidate is judged on four questions:
1. How many other modules depend on it?
2. Does it need data it doesn't own?
3. Is it part of the step where stock is set aside and money is taken (the all-or-nothing part of placing an
   order, in `order/service.py`)?
4. How bad is a bug in the move?

| Candidate | 1. Depended on by | 2. Needs others' data? | 3. In the stock-and-money step? | 4. Worst case if the move has a bug | Pros | Cons |
|---|---|---|---|---|---|---|
| **Notification** | 1 (order) | Yes: the customer's name and email | **No** (it runs after that step) | A missing or duplicated "email" | Lowest risk; a generic job with no business rules; teaches the translator (ACL) because of the customer data it needs | Needs a call back to the monolith for customer data (a round trip) |
| Shipping | 1 (order) | No (just the order ID) | No, but it comes right after the charge | An order is paid but never shipped: a refund is needed, and the refund logic (compensation) doesn't exist until Phase 5 | Simple; needs no one else's data | A failure touches money, and we can't undo it yet |
| Inventory | 1 (order) | No | **Yes** | Overselling, or stock set aside for an order that failed (a "stock leak") | Exercises the hardest problem early | Breaks the all-or-nothing step on the very first move; the roadmap plans this for Phase 2, with its failure shown on purpose |
| Payment | 1 (order) | No | **Yes** | Charging twice, or charging without an order | Same as inventory | Money is the worst place to learn; protection against double charges only arrives in Phase 4 |
| Customer | **2** (order, notification) | No | No, but every order checks it | No order can be placed at all | Would get rid of the old-style column names early | The most depended-on module; a mistake stops everything |

### Decision 3: how to switch over

| Option | Pros | Cons |
|---|---|---|
| **A. A switch (Strangler Fig):** both the old in-program notification and the new service exist; the environment variable `NOTIFICATION_ROUTE=monolith\|service` picks one | Switch back instantly if the new service misbehaves; compare both side by side with identical requests (the Phase 1 demo does this) | Two implementations to keep for a while |
| B. Big-bang: delete the old code and point everything at the new service in one release | Less code | No quick way back; any bug hits every order at once |

### Decision 4: how the new service gets customer details

| Option | Pros | Cons |
|---|---|---|
| **A. The notification service asks the monolith for them, through one translator (Anti-Corruption Layer)** that turns `cust_nm` / `cust_eml` into a clean `Recipient(name, email)` | The old-style names stay out of the new service; when customer moves out in Phase 5, only the translator changes; it's what the roadmap asks us to practise | A round trip: monolith → notification → monolith for every notification |
| B. The monolith sends the name and email along with the request | No round trip | Nothing to translate, so no ACL practice; the monolith has to know what the email needs |
| C. Notification reads the customer table directly from the database | Fastest to write | Breaks the "own your data" rule (C2); impossible once customer has its own database |

## Decision

**In one line (why notification first):** minimal impact, especially no financial loss.

- **Draw the lines by business capability, into six parts** (1A). Each part already owns its data and changes for
  its own reasons, and this matches the plan for the remaining phases.
- **Move notification out first** (2). It's the only candidate that is outside the stock-and-money step, needs no
  undo logic when it fails, and where a bug costs at most an email, not stock or money.
- **Switch over with an on/off switch, not all at once** (3A). `NOTIFICATION_ROUTE` lets us move traffic to the new
  service, compare the results, and switch back instantly if something is wrong.
- **Get customer details through one translator (ACL)** (4A). The monolith's old-style names stay out of the new
  service. We accept the round trip for now; it disappears when customer becomes its own service in Phase 5.

**Known trade-off, accepted on purpose:** the call to the notification service happens exactly where today's
function call is, inside the order's database step. So if the notification service is down, placing an order
fails, even though an email has nothing to do with whether the order is valid. Step 6 of this phase records
exactly what happens; Phase 3 fixes it.

## Consequences
_To be written in step 6, from what actually happens (test names, `make demo-1` output)._

## Learnings
_To be written in step 6._
