# ADR-0001: Standalone Sidecar with Application-Owned Private Drafts

- Status: Accepted
- Date: 2026-08-21
- Decision owners: DCL product owner and implementation team
- Applies from: DCL-001

## Context

The repository began without an executable application or a verified production DataHub contract.
The broader handoff requires private editing, server-enforced derived values, shared-draft
concurrency control, auditable decisions, and eventual publication of approved metadata. DataHub
source modification is prohibited, and the exact internal DataHub fork, schema, entity model,
identity rules, and write semantics remain unverified.

A private draft cannot be represented safely by changing the public DataHub asset. The documented
DataHub Core plugin contract is also not a general independently deployable workflow and user-
interface extension point. Coupling the product to DataHub frontend internals would make releases
and security boundaries depend on an unverified implementation.

## Decision

Build the DCL Compliance Form as one standalone, modular sidecar product.

The initial product contains:

- a React and TypeScript presentation layer;
- a Spring Boot API and application boundary;
- focused workflow domain logic;
- application-owned PostgreSQL persistence managed by Flyway;
- server-side authentication and authorisation;
- a narrow, read-only metadata seed port;
- a fixture implementation of that port for DCL-001.

The frontend and backend may run separately during development, but they remain one logical product,
not independently evolving microservices.

### Private state ownership

PostgreSQL owns private baselines, editable drafts, lock versions, form revision pins, and DCL audit
events. No draft save or DCL-001 API operation writes to DataHub. DataHub can become the public
metadata system of record only after a later, explicitly approved publication slice.

### Integration ports

Read and publication capabilities are separate boundaries. DCL-001 contains only the read-only seed
port and a local fixture adapter; that port exposes no mutation method and no GraphQL type to the
workflow domain. A future publication port may be introduced only after the exact target contract
and least-privilege publisher identity have been proven. Draft code must not acquire publication
credentials or write capability.

### Immutable form revisions

Each workflow pins an immutable repository-managed form revision and its canonical SHA-256 digest at
creation. A used revision is never edited in place. Semantic field, allowed-value, requiredness, or
mapping changes require a new revision. Existing workflows do not silently migrate.

### Server-derived Disposal Action

Disposal Class is editable. Disposal Action is a read-only consequence of the pinned class-to-action
mapping. The server derives it on every load and save boundary. Clients cannot supply or override it,
and the editable draft does not persist it as an independent field.

### Shared draft and concurrency

The MVP supports one current shared workflow for each `(assetUrn, formKey)` pair. Authorised Business
Contacts share that draft. Every material save requires the current expected version and increments
it exactly once. Stale writes fail with a conflict; the system does not automatically merge and does
not use last-write-wins behavior.

### Future workflow vocabulary

Review and publication progress are orthogonal concepts. The reserved review vocabulary is `DRAFT`,
`SUBMITTED`, `REJECTED`, and `APPROVED`; the reserved publication vocabulary is `NOT_STARTED`,
`PENDING`, `IN_PROGRESS`, `SUCCEEDED`, and `FAILED`. `RESUBMITTED` is a future audit event, not a
durable review state. DCL-001 implements no transition beyond `DRAFT / NOT_STARTED`.

### Exact-target integration gate

No production entity type, URN, form, property, ownership type, reviewer group, publisher identity,
or write behavior will be inferred from the fixture or an unrelated local DataHub quickstart. Before
live integration, the evidence in
[datahub-target-validation.md](../integration/datahub-target-validation.md) must be captured against
the exact internal target. After that proof, the product owner must select either a native governed
Change Proposal review path or a custom DCL review path. The product will not build both.

## Alternatives considered

### Modify DataHub or build a frontend plugin

Rejected. It violates the no-fork constraint, relies on an unsuitable or undocumented extension
surface, couples releases to DataHub internals, and does not provide an application-owned boundary
for private drafts.

### Store pending answers on DataHub assets

Rejected. Native form answers change published asset metadata and therefore cannot provide private
draft isolation or reconstruct the DCL workflow audit.

### Build DataHub Change Proposals into DCL-001

Rejected for this slice. The exact internal target has not been shown to expose suitable governed
proposal APIs or whole-form atomic decision behavior.

### Separate UI, API, workflow, and publication microservices

Rejected. It adds deployment and consistency costs without evidence that the first vertical slice
needs independently scaled services. The chosen modular boundaries can be preserved inside one
product.

### Browser-only or in-memory drafts

Rejected. They do not meet persistence, shared access, concurrency, atomic audit, or restart
requirements.

## Consequences

- The private workflow has a clear trusted boundary independent of DataHub implementation details.
- Real PostgreSQL is required for integration and concurrency verification; an H2-only test suite is
  insufficient.
- The application must operate and verify locally without a DataHub endpoint or credential.
- Fixture asset type information remains adapter data and cannot become a production domain rule.
- A later integration slice must perform evidence gathering before adding any live adapter.
- PostgreSQL lifecycle, backup, retention, production OIDC, deployment, monitoring, review, and
  publication remain later work.

