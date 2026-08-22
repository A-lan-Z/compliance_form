# DCL-001: Establish the Private, Versioned DCL Draft Vertical Slice

- Status: APPROVED
- Approved: 2026-08-21
- Execution ceiling: Implement and verify locally
- Architecture: [ADR-0001](../architecture/ADR-0001-sidecar-private-drafts.md)

This document is the durable approved specification for DCL-001. Material product decisions in this
document may not be changed without explicit product-owner approval recorded in a subsequent task or
decision record.

## 1. Context

At approval baseline commit `ac6a87df2e5c51acd4ab93c44bf411994a00e8c3`, the repository contained
only `AGENTS.md` and `DCL_MVP_Handoff.md`. It had no application source, dependency manifest, test
suite, database migration, CI workflow, or production DataHub configuration.

The handoff describes a broader DCL Compliance Form workflow, but it is contextual design input
rather than evidence of implementation. An unrelated local DataHub Core quickstart does not contain
the proposed DCL Form or Structured Properties, does not establish the internal target, and must not
be contacted or treated as a production substitute by this task.

DCL-001 establishes the smallest executable product slice without depending on unresolved DataHub
writes, production identity, reviewer policy, or governed proposal capabilities.

## 2. Objective

Deliver a locally runnable application in which an authorised fixture Business Contact can:

1. Open one configured DCL form for one configured fixture asset.
2. Receive draft values pre-populated from a read-only fixture metadata adapter.
3. See Disposal Action derived from Disposal Class.
4. Change Disposal Class.
5. Save the private draft to PostgreSQL.
6. Reload and retrieve the saved draft.
7. Receive an explicit conflict if another request saved a newer version.
8. Produce auditable workflow-creation and material draft-save events.

The task must prove that no DataHub mutation or DataHub HTTP request is performed.

## 3. Scope

### In scope

#### Application foundation

- A modular monorepo application.
- Java 21 backend using Spring Boot and Maven Wrapper.
- React and TypeScript frontend using Vite and npm.
- PostgreSQL persistence and Flyway migrations.
- One logical application/deployable; separate frontend and backend development processes are allowed.
- Dependency versions pinned in manifests and the npm lockfile.

#### Domain and persistence

- One immutable fixture form revision.
- One deterministic fixture asset.
- One read-only fixture metadata seed adapter.
- Workflow get-or-create and immutable baseline capture.
- Private draft persistence.
- Server-side class-to-action derivation.
- Optimistic locking.
- Creation and draft-save audit events.
- A server-side authorisation boundary.

#### API and UI

- Open/create, retrieve, and save-draft APIs.
- A minimal asset-form route.
- Save and reload behavior.
- Conflict and validation feedback.
- An explicit fixture/no-DataHub banner.

#### Verification and maintenance

- Backend unit and real-PostgreSQL integration tests.
- API tests.
- Frontend unit/component tests.
- One browser-level end-to-end test.
- One authoritative root verification command.
- README, accepted architecture record, approved task record, and future DataHub validation checklist.
- A CI workflow invoking the same root verification path. Remote CI success is outside this task's
  local execution ceiling.

### Explicitly out of scope

DCL-001 must not implement:

- production DataHub connectivity or calls to the unrelated local quickstart;
- DataHub mutations, Form provisioning, or Structured Property provisioning;
- submission or resubmission;
- a reviewer inbox, approval, rejection, or rejection reasons;
- governed Change Proposals;
- publication, an outbox processor, or a separate worker service;
- Structured Property publication or Verification Form verification;
- notifications;
- production OIDC, BCP ownership mapping, reviewer mapping, or service accounts;
- production secrets, endpoints, DCL URNs, property identifiers, ownership types, or taxonomy;
- a runtime form designer or generic workflow engine;
- recurring compliance cycles or post-publication correction;
- deployment infrastructure, backup, disaster recovery, or high availability;
- any modification of DataHub source code.

## 4. Fixed architecture and domain decisions

### Stack

- Backend: Java 21 and Spring Boot.
- Build: Maven Wrapper.
- Frontend: React, TypeScript, and Vite.
- Frontend package manager: npm with a committed lockfile.
- Persistence: PostgreSQL.
- Migration: Flyway.
- Backend tests: JUnit and Spring integration testing with real PostgreSQL through Testcontainers or
  an equivalently isolated Docker arrangement.
- Frontend tests: Vitest and React Testing Library, or equivalent Vite-compatible tools.
- Browser test: Playwright.
- H2-only integration testing is not an acceptable substitute.

Exact compatible dependency versions, Java packages, persistence access library, JSONB mapping,
UUID generation, and request-ID implementation are implementation discretion and are pinned in the
resulting manifests.

### Application shape

- A modular standalone sidecar in one repository and one logical product.
- No DataHub source modification.
- No separate microservice or worker in this task.
- Frontend and backend may run separately during development.
- Production assembly may serve compiled frontend assets from the backend or use an equivalent
  single-deployable arrangement.

### Fixture form revision

The immutable fixture definition has these semantic values:

| Property | Fixture value |
|---|---|
| Form key | `dcl.edw.database.fixture` |
| Revision | `1` |
| Display name | `DCL EDW Database Compliance — Fixture` |
| Editable field | `disposalClass` |
| Derived field | `disposalAction` |

Allowed values and mapping:

| Disposal Class | Derived Disposal Action |
|---|---|
| `TEST_CLASS_A` | `TEST_ACTION_A` |
| `TEST_CLASS_B` | `TEST_ACTION_B` |

These are non-production fixtures and must be identified as such in source configuration, UI, and
documentation.

### Fixture asset

| Property | Fixture value |
|---|---|
| URN | `urn:li:container:00000000000000000000000000000001` |
| Display name | `Fixture EDW Database` |
| Reported entity type | `CONTAINER` |
| Reported subtype | `Database` |
| Initial class | `TEST_CLASS_A` |
| Initial action | `TEST_ACTION_A` |
| Authorised BCP | `bcp.alice` |

Entity type and subtype are adapter-supplied data. The Container fixture does not authorise
hard-coding production assets as Containers, and the workflow domain treats the asset URN as opaque.

### Shared workflow, revision, and draft storage

- There is one current shared workflow for each `(assetUrn, formKey)` pair.
- All authorised BCPs share that workflow.
- The fixture definition is repository-managed and immutable.
- Its canonical representation has a deterministic SHA-256 digest.
- A workflow stores the revision and digest at creation.
- The persisted editable draft stores Disposal Class only.
- Disposal Action is derived and is not independent editable draft input.
- Conflicts are rejected through optimistic locking without automatic merge.

### Reserved future workflow model

Review and publication status are orthogonal. Review vocabulary may reserve `DRAFT`, `SUBMITTED`,
`REJECTED`, and `APPROVED`; publication vocabulary may reserve `NOT_STARTED`, `PENDING`,
`IN_PROGRESS`, `SUCCEEDED`, and `FAILED`. DCL-001 exposes only `DRAFT / NOT_STARTED`.

Future approval is reserved as an all-or-nothing decision over one immutable submission.
`RESUBMITTED` is a future audit event leading back to `SUBMITTED`, not a durable status. DCL-001
must not add any command or UI control for these future transitions.

## 5. Domain invariants

The server domain/application layer must enforce all of the following:

1. A workflow has exactly one asset URN, form key, form revision, and definition digest.
2. The asset URN is opaque to the workflow domain.
3. At most one current workflow exists for an asset URN and form key.
4. The baseline is captured once at workflow creation and is not silently replaced.
5. A workflow created by this task always has review status `DRAFT` and publication status
   `NOT_STARTED`.
6. No DCL-001 API can transition the workflow out of `DRAFT`.
7. Disposal Class may be null while the form is an incomplete draft.
8. A non-null Disposal Class must be allowed by the pinned revision.
9. Disposal Action is exactly the mapped value for the current class.
10. A null class derives a null action.
11. Client-supplied Disposal Action is invalid input.
12. A successful material draft change increments the lock version exactly once.
13. A no-op save with the current expected version returns the current workflow without increasing
    the version or creating a draft-save audit event.
14. A stale expected version causes no workflow or audit mutation.
15. Workflow state mutation and its audit event commit atomically.
16. An unauthorised request causes no workflow, audit, or adapter mutation.
17. An existing workflow is reopened without another seed read.
18. No DataHub mutation capability exists in the DCL-001 application boundary.
19. Timestamps are stored as `timestamptz` and serialized as UTC ISO-8601 values.
20. Canonical form and baseline digests are deterministic across repeated runs.

## 6. Implemented workflow rules

### Create/open: `None -> DRAFT / NOT_STARTED`

Preconditions:

- the server principal is authenticated and authorised for the asset/form;
- the fixture form definition exists and is valid;
- the asset exists in the fixture seed adapter.

Effects:

- read the fixture asset and managed values once;
- capture the immutable baseline;
- initialize editable draft values;
- derive Disposal Action;
- store the form revision and definition digest;
- insert `WORKFLOW_CREATED`;
- return lock version `1`.

The workflow and audit inserts occur in one transaction.

### Reopen: `DRAFT / NOT_STARTED -> DRAFT / NOT_STARTED`

When a matching workflow exists, do not reseed, call the fixture adapter, or create another event.
Return the persisted draft and current derived action.

### Material draft save: `DRAFT / NOT_STARTED -> DRAFT / NOT_STARTED`

The actor must be authorised, expected version must match, the request must contain only editable
fields, and the class must be null or allowed. Replace the editable values, derive the action,
increment the workflow version once, update actor/timestamp, and insert `DRAFT_SAVED` in one
transaction.

### No-op save

When the complete submitted editable values are semantically identical and the expected version is
current, return `200`, retain the version, and create no audit event.

### Stale save

When expected version differs from the persisted version, return `409` with the current version,
perform no mutation, and create no audit event.

## 7. Persistence model

Flyway-managed PostgreSQL migrations create at least the following tables.

### `dcl_workflow`

| Column | Required semantics |
|---|---|
| `id` | UUID primary key |
| `asset_urn` | Non-null text |
| `asset_snapshot` | Non-null JSONB with display name, entity type, subtype, and fixture platform context |
| `form_key` | Non-null text |
| `form_revision` | Positive integer |
| `form_definition_sha256` | Non-null 64-character lowercase hexadecimal digest |
| `review_status` | Controlled non-null value, initially `DRAFT` |
| `publication_status` | Controlled non-null value, initially `NOT_STARTED` |
| `baseline_values` | Non-null JSONB with raw managed values, including existing action |
| `baseline_captured_at` | Non-null timestamp with time zone |
| `baseline_sha256` | Non-null canonical digest |
| `draft_values` | Non-null JSONB containing editable fields only |
| `lock_version` | Positive bigint, initially `1` |
| `created_by` | Non-null authenticated principal identifier |
| `updated_by` | Non-null authenticated principal identifier |
| `created_at` | Non-null timestamp with time zone |
| `updated_at` | Non-null timestamp with time zone |

Required constraints:

- unique `(asset_urn, form_key)`;
- positive form revision and lock version;
- controlled review and publication values;
- publication status is `NOT_STARTED` while review status is not `APPROVED`;
- JSON columns are not SQL null;
- `draft_values` does not store `disposalAction`.

### `dcl_audit_event`

| Column | Required semantics |
|---|---|
| `id` | UUID primary key |
| `workflow_id` | Non-null workflow foreign key |
| `sequence` | Positive monotonic sequence within the workflow |
| `event_type` | Non-null controlled value |
| `actor_id` | Non-null authenticated principal identifier |
| `actor_type` | Controlled value, initially `USER` or `SYSTEM` |
| `occurred_at` | Non-null timestamp with time zone |
| `request_id` | Non-null request/correlation identifier |
| `workflow_version` | Non-null version after the event |
| `details` | Non-null JSONB |

Required constraints and behavior:

- unique `(workflow_id, sequence)`;
- creation event sequence begins at `1`;
- sequence assignment is concurrency-safe;
- application code exposes no audit update or delete operation;
- details contain no token, password, connection string, stack trace, or unrelated adapter response.

### Canonical JSON and digests

Use one documented canonicalization implementation for definition and baseline values: object keys
are deterministically sorted, array order is preserved, bytes are UTF-8, insignificant formatting
does not affect the result, and SHA-256 is rendered as lowercase hexadecimal. Unit tests must contain
fixed digest vectors.

## 8. API contract

All endpoints use `/api/v1` and JSON. Errors use `application/problem+json` with HTTP status, stable
application error code, human-readable title/detail, request ID, field errors when relevant, and the
current version for version conflicts. Responses do not expose exception text, SQL details, stack
traces, or credentials.

### Open or retrieve

`POST /api/v1/workflows/open`

```json
{
  "assetUrn": "urn:li:container:00000000000000000000000000000001",
  "formKey": "dcl.edw.database.fixture"
}
```

The server authenticates and authorises before exposing data, resolves the active fixture revision,
returns `201 Created` plus `Location` for creation, and returns `200 OK` for an existing workflow.
Concurrent creation must result in one workflow and one creation event, with the same workflow ID
returned to both successful callers. Existing workflows are not reseeded.

### Retrieve

`GET /api/v1/workflows/{workflowId}`

Return the current representation to an authorised actor. A missing or inaccessible workflow returns
non-enumerating `404`. Retrieval performs no adapter read or mutation.

### Save draft

`PUT /api/v1/workflows/{workflowId}/draft`

```json
{
  "expectedVersion": 1,
  "values": {
    "disposalClass": "TEST_CLASS_B"
  }
}
```

Rules:

- `disposalClass` is required in `values` and may be null;
- `values` is a complete replacement of editable draft values;
- unknown fields are rejected;
- any `disposalAction` is rejected with `422 READ_ONLY_FIELD`;
- unsupported classes are rejected with `422 INVALID_FIELD_VALUE`;
- stale versions return `409`;
- material and no-op success return `200`;
- save does not call the seed adapter.

### Workflow representation

The response contains at least:

- workflow ID;
- asset URN, display name, entity type, and subtype list;
- form key, revision, and definition digest;
- review and publication statuses;
- workflow version;
- Disposal Class value, editability, and allowed values;
- Disposal Action value, `editable: false`, and `derivedFrom: disposalClass`;
- baseline capture time and digest;
- warnings;
- `permissions.canEdit`.

### Stable error codes

Implement at least:

- `ASSET_NOT_FOUND`;
- `FORM_NOT_FOUND`;
- `WORKFLOW_NOT_FOUND`;
- `ACCESS_DENIED`;
- `WORKFLOW_VERSION_CONFLICT`;
- `UNKNOWN_FIELD`;
- `READ_ONLY_FIELD`;
- `INVALID_FIELD_VALUE`;
- `DEPENDENCY_UNAVAILABLE`;
- `INVALID_BASELINE_VALUE`;
- `INTERNAL_ERROR`.

## 9. User interface contract

Provide a route such as:

```text
/compliance-form?assetUrn=<encoded-urn>&formKey=dcl.edw.database.fixture
```

The route must:

1. Call the open endpoint on load.
2. Display asset name and URN, form title and revision, review status, and current version.
3. Display Disposal Class as a labelled select.
4. Display Disposal Action as a labelled non-editable field.
5. Preview the mapping immediately when selection changes, while replacing state with the complete
   authoritative server response after save.
6. Provide an explicit **Save draft** button.
7. Not autosave.
8. Send only Disposal Class and expected version.
9. Replace local state with the complete successful response.
10. On conflict, display “This draft changed elsewhere. Reload before saving.” and a reload action;
    do not merge automatically.
11. Preserve the unsaved selection and display clear validation/dependency failures.
12. Show the persisted draft after refresh.
13. Persistently display “Local fixture data — no DataHub changes are made.”
14. Display no Submit, Approve, Reject, Publish, Verify, Delete, or Reset control.
15. Use connected labels, keyboard-operable controls, and visible validation feedback.
16. Make no authorisation decision in the browser.

## 10. Read-only integration boundary

Define a narrow application port equivalent to:

```text
loadDraftSeed(principal, assetUrn, formDefinitionRevision)
  -> asset identity snapshot
     managed current values
     authorisation/assignment evidence
     source retrieval timestamp
```

Mandatory boundary properties:

- it has no write or mutation method;
- workflow domain code does not depend on GraphQL types;
- the fixture adapter is DCL-001's only runtime implementation;
- the adapter returns the approved fixture data;
- tests can observe its invocation count;
- the first successful creation performs one seed read;
- reopen, get, and save perform no seed read;
- the repository introduces no GraphQL mutation, DataHub token, write client, or publisher adapter;
- no HTTP request is sent to `localhost:18080`, `localhost:9002`, or another DataHub endpoint;
- fixture `CONTAINER` remains adapter data, not a workflow-domain requirement.

## 11. Authorisation

Use Spring Security or an equivalent trusted server boundary.

### Local and test identity

- The explicit local profile may install fixed principal `bcp.alice`.
- Tests may inject explicit authorised and unauthorised principals.
- No request header, body field, query parameter, or browser-local value selects the principal.
- Fixed-principal behavior exists only in local/test configuration.
- There is no fixed-user fallback outside those profiles.
- Unauthenticated API requests return `401`.

### Fixture rules

- `bcp.alice` may open, retrieve, and save the fixture workflow.
- Any other authenticated actor is unassigned and may not open or mutate it.
- Direct retrieval or update of an inaccessible workflow returns `404`.
- Authorisation is checked before returning an existing workflow.
- Denial creates no workflow or audit mutation.
- Persisted and audited actor IDs come only from the authenticated server principal.

Reviewer and publisher privileges are not implemented. Edit authority must remain conceptually
separate from those future roles.

## 12. Audit events

### `WORKFLOW_CREATED`

Record workflow ID, authenticated actor, request ID, version `1`, asset URN and identity snapshot,
form key/revision/digest, baseline capture time/digest, initial editable values, derived action, and
baseline warnings. Exactly one creation event exists per workflow.

### `DRAFT_SAVED`

Record actor, request ID, prior/new versions, changed field names, canonical previous/new editable
values, previous/new derived action, form revision, and definition digest. Create it only for a
material change.

### General audit rules

- Workflow mutation and audit insertion use one transaction.
- Sequence is monotonic per workflow.
- Audit events are not updated or deleted by application code.
- Failed, denied, stale, and no-op saves create no `DRAFT_SAVED`.
- Integration tests query the audit table and verify exact counts and content.
- Credentials, authorization headers, exceptions, and unrelated response bodies never enter audit
  details or application logs.

## 13. Failure behavior

### Invalid fixture definition

Fail startup with a specific configuration error for duplicate/missing field keys, an allowed class
without one mapping, malformed revision, failed/non-deterministic digest, or production-looking
values substituted for fixtures.

### Database unavailable

Readiness reports unavailable; workflow requests do not claim a successful save; no in-memory
persistence fallback exists.

### Fixture adapter unavailable

A new open returns `503 DEPENDENCY_UNAVAILABLE` with no workflow or audit insert. Existing workflows
remain retrievable without the adapter.

### Concurrent creation

Two simultaneous opens may begin resolution, but PostgreSQL ends with one workflow and one creation
event, and both successful callers receive the same workflow ID.

### Unsupported baseline class

Preserve the raw baseline, initialize editable class and derived action as null, add
`UNSUPPORTED_BASELINE_DISPOSAL_CLASS`, and allow draft creation without coercion.

### Baseline action mismatch

Preserve both raw baseline values, initialize from the valid baseline class, expose the canonical
derived action, and add `BASELINE_DISPOSAL_ACTION_MISMATCH`.

### Stale save

Return `409 WORKFLOW_VERSION_CONFLICT` including current version, change no workflow, and create no
event.

### Transaction failure

Failure after preparing a workflow or audit change rolls back both. No change is saved unless the
whole transaction commits.

### Unauthorised access

Return `401`, `403`, or non-enumerating `404` as applicable; disclose no workflow content and perform
no mutation.

### UI/backend disagreement

The UI replaces its state with the successful server response and does not assume locally derived
values or versions were committed.

## 14. Protected decisions

Implementation must not:

1. Modify DataHub source.
2. Treat the unrelated local quickstart as the production target.
3. Connect to or mutate any DataHub instance.
4. Add future DataHub write methods.
5. Replace PostgreSQL integration tests with H2-only tests.
6. Store drafts only in browser state, files, or memory.
7. Trust a client-supplied actor.
8. Trust a client-supplied Disposal Action.
9. Make Disposal Action editable.
10. Put the class-to-action rule only in the frontend.
11. Persist Disposal Action as an independently editable draft field.
12. Silently refresh an existing draft from the seed adapter.
13. Use last-write-wins without expected-version checking.
14. Automatically merge conflicting drafts.
15. Create an audit event outside the state-change transaction.
16. Implement submit, approve, reject, publish, or verify behavior.
17. Invent production URNs, taxonomy, ownership types, groups, endpoints, or credentials.
18. Build a generic dynamic-form engine.
19. Create a separate publication microservice.
20. Change this approved task's material decisions without recorded product-owner approval.

## 15. Observable acceptance criteria

DCL-001 is complete only when all 42 criteria are observable.

### Repository and build

1. A clean checkout has documented prerequisites and one root verification command.
2. Maven Wrapper files, `backend/pom.xml`, `frontend/package.json`, and the npm lockfile are committed.
3. The frontend production build succeeds.
4. Backend packaging and tests succeed.
5. Flyway applies every migration to an empty PostgreSQL database.
6. No secret, token, internal endpoint, or production identifier is committed.

### Workflow creation

7. Opening the configured fixture as `bcp.alice` returns `201`.
8. The response contains the fixture asset, revision `1`, deterministic definition digest, `DRAFT`,
   `NOT_STARTED`, version `1`, `TEST_CLASS_A`, and derived `TEST_ACTION_A`.
9. PostgreSQL contains one workflow and one `WORKFLOW_CREATED` event.
10. Reopening returns `200`, the same workflow ID and version, and creates no event.
11. The seed adapter is invoked once for initial creation and not for reopen.

### Draft save and derivation

12. Saving `TEST_CLASS_B` with expected version `1` returns version `2`, class `TEST_CLASS_B`, and
    action `TEST_ACTION_B`.
13. PostgreSQL stores the new editable class but no independently editable action.
14. Reloading returns the saved class and derived action.
15. One `DRAFT_SAVED` records actor, versions, and before/after values.
16. Saving identical values with expected version `2` retains version `2` and creates no event.
17. Saving null class is allowed and returns null action.
18. Sending `disposalAction` is rejected with `422 READ_ONLY_FIELD`.
19. Sending an unknown class is rejected with `422 INVALID_FIELD_VALUE`.
20. Rejected requests leave database and audit rows unchanged.

### Concurrency

21. Two concurrent material saves with the same expected version produce exactly one success, one
    `409 WORKFLOW_VERSION_CONFLICT`, one version increment, and one draft-save event.
22. Concurrent first opens result in one workflow and one creation event.

### Authorisation

23. An unauthenticated request returns `401`.
24. An unauthorised authenticated actor cannot retrieve or mutate the workflow.
25. Denied requests create no workflow or audit mutation.
26. No request field or header can select `bcp.alice`.

### User interface

27. The fixture route loads the workflow.
28. Disposal Class is editable.
29. Disposal Action is visibly read-only.
30. The UI save payload omits Disposal Action.
31. Saving and refreshing preserves the saved class.
32. A simulated conflict displays the required reload message.
33. The fixture/no-DataHub banner is visible.
34. No submit, review, approval, rejection, publication, or verification control is present.

### Integration boundary

35. Runtime contains only a read-only fixture adapter.
36. Opening a new workflow performs one fixture read.
37. Reopen, get, and save perform no adapter read.
38. Tests and the running slice execute no DataHub HTTP request or mutation.
39. Running and verifying the application requires no production DataHub configuration.

### Failure atomicity

40. Simulated adapter failure creates neither workflow nor audit event.
41. Simulated audit-insert failure rolls back the workflow mutation.
42. Simulated workflow-update failure creates no audit event.

## 16. Required verification

### Backend unit tests

Cover allowed and null mapping; unknown-class and action-override rejection; deterministic definition
and baseline digests; baseline mismatch warning; unsupported baseline class; no-op comparison; state
invariants; and authorisation decisions.

### PostgreSQL integration tests

Use real PostgreSQL and cover empty-database Flyway migration, unique asset/form constraint, atomic
workflow/audit creation, idempotent reopen, material and no-op save, stale and concurrent save,
concurrent create, audit sequence, transaction rollback, persistence across a fresh application
context using the same database, and inaccessible workflow behavior.

### API tests

Cover request/response contracts; open `201` versus `200`; `401`, `404`, `409`, `422`, and `503`;
problem response shape; request-ID propagation; unknown fields; action override; and current conflict
version.

### Frontend tests

Cover initial loading, field rendering, allowed options, read-only action, null class, save payload,
authoritative response replacement, conflict message, validation failure, fixture banner, and absence
of out-of-scope controls.

### Browser end-to-end test

With the local profile and isolated PostgreSQL:

1. Navigate to the fixture route.
2. Confirm class A and action A.
3. Select class B and save.
4. Refresh.
5. Confirm class B and action B.
6. Confirm the fixture banner.
7. Confirm no submit, review, or publication controls.

### Required commands

The repository supports documented equivalents of:

```text
./backend/mvnw -f backend/pom.xml verify
npm --prefix frontend ci
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
./scripts/verify.sh
```

`./scripts/verify.sh` is the authoritative local gate and includes static checks. GitHub Actions calls
that script instead of maintaining a materially different test sequence.

## 17. Required maintained documentation

- `README.md`: purpose, implemented scope, architecture, prerequisites, local profile/run behavior,
  one-command verification, database lifecycle, fixture route, no-DataHub warning, troubleshooting,
  and authority hierarchy.
- `docs/architecture/ADR-0001-sidecar-private-drafts.md`: accepted sidecar/private-draft decisions
  and exact-target gate.
- This approved task document.
- `docs/integration/datahub-target-validation.md`: evidence required before a live integration slice.
- `DCL_MVP_Handoff.md` remains contextual and must not be rewritten as implemented behavior.

## 18. Known limitations at completion

- Metadata and identity integration are fixture-backed.
- No live DataHub read or write has been proven or implemented.
- The Container fixture does not establish production asset type.
- Actual DCL taxonomy, URNs, prompts, and requiredness remain unknown.
- Only draft status is reachable.
- Only one current workflow per asset/form is supported.
- Recurring cycles and corrections after approval are unsupported or undefined.
- Concurrent edits are conflict-detected but never automatically merged.
- Production OIDC, reviewer, and publisher roles are absent.
- Governed Change Proposals remain undecided.
- Native Form verification is untested.
- Notifications, retention, backup, deployment, monitoring, and high availability remain future work.
- Remote CI success is not required by the local execution ceiling, though CI configuration is
  present.

## 19. Deferred decisions before later workflow or integration work

Before submission, review, publication, or verification work begins:

1. Obtain authorised access to the exact internal DataHub target.
2. Prove its version, schema, entity, form, property, ownership, prompt, verification, actor, audit,
   and idempotency behavior using the target-validation checklist.
3. Select either native governed Change Proposals or custom DCL review after that proof, never both.
4. Approve the production asset lookup/type, prompts, property URNs, requiredness, and disposal mapping.
5. Confirm BCP ownership and multiple-owner policy.
6. Confirm reviewer group and final self-approval policy.
7. Confirm publisher identity, least privileges, and verification attribution.
8. Approve external-drift and publication-retry policy.

