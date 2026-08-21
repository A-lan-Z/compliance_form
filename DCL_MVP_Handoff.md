# DCL Compliance Form MVP — Engineering Handoff

**Handoff status:** Implementation-ready design for an MVP  
**Prepared:** 20 August 2026  
**Primary target:** Self-hosted DataHub Core or an internal DataHub fork  
**Delivery constraint:** Do not modify or fork DataHub source code for the MVP  
**Primary asset level:** Database assets represented as DataHub `Container` entities, subject to verification in the internal deployment

---

## 1. Mission for the next agent

Implement a working MVP for the DCL Compliance Form workflow in which:

1. A Business Contact opens a DCL form for a DataHub asset.
2. Existing approved metadata is pre-populated.
3. The Business Contact edits the answers and can save a private draft.
4. Selecting **Disposal Class** automatically derives a separate, read-only **Disposal Action**.
5. Submitting the form does **not** change the DataHub asset.
6. A Business Administrator reviews the whole submission as one package.
7. The administrator can approve it or reject it with a mandatory reason.
8. Approval publishes the approved answers into DataHub Structured Properties and marks the native DataHub Verification Form as verified.
9. Rejection leaves the published DataHub metadata unchanged and permits correction and resubmission.
10. The system retains an audit trail identifying the submitter, reviewer, revision, timestamps, and publication result.

The MVP should prove the workflow end to end for **one versioned EDW database form**, one database asset, one Business Contact, and one reviewer group. It should be designed so that additional forms, platforms, and workflow automation can be added without replacing the core.

---

## 2. Executive architecture decision

### Selected approach

Build a separate **DCL Compliance Workflow extension** beside DataHub:

- React/TypeScript web interface.
- Backend service using the organisation's supported enterprise stack; Java/Spring Boot is the default recommendation when aligning with DataHub's Java ecosystem, but the API contract below is implementation-language-neutral.
- PostgreSQL for drafts, submissions, revisions, review decisions, publication state, and audit events.
- DataHub GraphQL API for reading assets/forms and publishing approved metadata.
- Configuration-as-code for DCL-specific form rules and reference data.
- A service account or publisher group as the only native DataHub form actor used to publish and verify approved responses.

### Explicitly rejected for the MVP

- Copying proprietary DataHub Cloud source code.
- Modifying the DataHub React application or GMS source.
- Rebuilding a generic Cloud-style Change Proposals platform.
- Storing pending responses directly on the DataHub asset.
- Calling native `submitFormPrompt` when a Business Contact merely saves or submits a draft.
- Building a custom DataHub metadata model before the workflow has been proven.

### Why this design

Native DataHub Compliance Forms are useful for defining questions, assigning a form, writing final Structured Properties, tracking prompt completion, and recording final verification. They are not a native whole-form draft, reviewer approval, rejection, or revision system. A sidecar extension therefore preserves DataHub as the metadata authority while adding only the missing DCL workflow.

---

## 3. Verified upstream behaviour to design around

These are upstream facts that the implementation must not contradict. Reconfirm them against the internal DataHub version before integration.

1. DataHub Core exposes form completion programmatically through GraphQL operations including `submitFormPrompt` and `verifyForm`.
2. Native form answers update the corresponding asset metadata; they are not held as unpublished form-response records.
3. Form progress is stored separately from the actual answer values.
4. A native Verification Form provides final assignee acknowledgement after required prompts are complete. It is not a separate respondent-versus-reviewer approval workflow.
5. The documented generic reviewer workflow called Change Proposals is a DataHub Cloud feature.
6. Dynamic form assignment is documented as Cloud-only; explicit batch assignment is available.
7. DataHub supports separately deployable custom metadata-model packages, but that is not required for the MVP.

### Consequence

The sidecar must stage responses outside the published DataHub asset, and only its controlled publication process should call native form mutations.

---

## 4. Business requirement interpreted for the MVP

### Actors

**Business Contact Person (BCP)**

- Responsible for documenting an eligible asset.
- May view the approved values and the active draft.
- May save, submit, and correct rejected submissions.
- May not approve or publish.

**Business Administrator (Reviewer)**

- Views pending submissions.
- Compares current approved values with proposed values.
- Approves the whole submission or rejects it with a reason.
- May retry a failed publication.

**DCL Publisher Service Account**

- Calls DataHub GraphQL after approval.
- Writes final Structured Properties.
- Marks native form prompts complete.
- Calls `verifyForm` when all required prompts have been published.

**General DataHub User**

- Sees only approved metadata on the DataHub asset.
- Does not see private drafts, rejected revisions, or reviewer comments.

### Separation of duties

Default rule for the MVP:

```text
submittedBy != reviewedBy
```

Make this configurable, but enable it unless the product owner explicitly permits self-approval.

---

## 5. MVP scope

### In scope

- One DCL form: `dcl.edw.database.v1`.
- One target entity type: DataHub `Container`, representing an EDW database.
- Native DataHub Structured Properties for every MVP question.
- Native DataHub Verification Form as the final publication/completion ledger.
- Existing-value pre-population.
- Private draft save.
- Whole-form submission.
- One-stage administrator approval.
- Whole-form rejection with mandatory reason.
- Correction and resubmission with immutable revision history.
- Disposal Class to Disposal Action dependency.
- Controlled publication to DataHub after approval.
- Publication retry after partial or temporary failure.
- Business Contact authorisation using DataHub ownership.
- Reviewer authorisation using an OIDC/SSO group or configured role.
- Audit log.
- Minimal operational health checks and structured logging.
- A linkable DCL application page for an asset.

### Deferred beyond MVP

- Generic visual form builder.
- Multiple platform forms.
- Field/column-level questions.
- Automatic tag-driven assignment reconciliation.
- Email or Teams notifications.
- Annual conformance scheduling.
- Excel export and completion analytics.
- Multiple approval stages or quorum.
- Reviewer delegation.
- Generic dependent-field rule editor.
- Native DataHub Task Center integration.
- Custom DataHub proposal entity/aspects.
- Migration of Axon inventory.
- Writing approved metadata back to EDW/ELH source systems.

---

## 6. Assumptions and unknowns

### Working assumptions

1. Database assets are represented as DataHub `Container` entities.
2. A Business Contact ownership type already exists or can be created.
3. The internal DataHub GraphQL API exposes forms, asset ownership, Structured Properties, `batchAssignForm`, `submitFormPrompt`, and `verifyForm`.
4. A service account token can be issued to the DCL publisher.
5. An OIDC group can identify Business Administrators.
6. The DCL metadata fields and disposal mapping will be supplied by the business owner.
7. Only one active workflow exists per `(asset URN, form URN)`.
8. Multiple Business Contacts may be associated with an asset; any authorised BCP may continue the active draft, but the audit records the individual actor.
9. Approval is all-or-nothing for the form revision.
10. Approved answers should be visible in DataHub; unapproved answers must not be visible there.

### Must be verified when internal access returns

- Exact DataHub commit, tag, and internal fork differences.
- Exact GraphQL schema and feature flags.
- Whether a Cloud-equivalent proposal implementation already exists internally.
- Exact database entity type and URN construction.
- Business Contact ownership type URN.
- Reviewer group name.
- Service account identity and permission model.
- Existing Structured Property naming convention.
- Whether native form UI is exposed and could permit bypass.
- Whether editing a verified prompt invalidates native verification in the deployed version.
- Whether a non-assigned user can call `submitFormPrompt` in the deployed version.

---

## 7. System context

```text
┌───────────────────────────────────────────────────────────┐
│                         DataHub                           │
│                                                           │
│ Assets / Containers                                       │
│ Form definitions                                          │
│ Structured Property definitions                           │
│ Approved Structured Property values                       │
│ Ownership / Business Contact                              │
│ Native form completion and verification                   │
└───────────────────────┬───────────────────────────────────┘
                        │ GraphQL, service account for writes
                        │ user-context reads where appropriate
                        ▼
┌───────────────────────────────────────────────────────────┐
│              DCL Compliance Workflow Extension            │
│                                                           │
│ React UI                                                   │
│ REST API                                                   │
│ Authorisation                                              │
│ Validation and derived-field rules                         │
│ Submission/review state machine                            │
│ DataHub integration adapter                                │
│ Publication worker                                         │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                       PostgreSQL                          │
│                                                           │
│ Workflow instance                                         │
│ Immutable revisions                                       │
│ Review decisions                                          │
│ Publication item state                                    │
│ Audit events                                               │
│ Optional transactional outbox                             │
└───────────────────────────────────────────────────────────┘
```

---

## 8. Sources of truth

| Information | Authoritative source |
|---|---|
| Asset identity, type, name, platform, environment | DataHub |
| Approved metadata values | DataHub |
| Structured Property definitions | DataHub |
| Native form prompts and required/optional status | DataHub Form entity |
| Business Contact ownership | DataHub ownership |
| DCL dependent-field behaviour | Version-controlled DCL rule configuration |
| Disposal Class to Disposal Action mapping | Version-controlled approved reference-data file, until an authoritative service is available |
| Draft answers | DCL PostgreSQL |
| Submitted revision snapshot | DCL PostgreSQL |
| Review decision and rejection reason | DCL PostgreSQL |
| Publication status and retry state | DCL PostgreSQL |
| Final native form verification | DataHub |

Do not duplicate asset master data unnecessarily in PostgreSQL. Store identifiers and immutable snapshots needed for audit, not a second asset catalogue.

---

## 9. Form and metadata configuration

### Recommended identifiers

```text
Form URN:
urn:li:form:dcl.edw.database.v1

Structured Properties:
urn:li:structuredProperty:ato.dcl.businessDescription
urn:li:structuredProperty:ato.dcl.disposalClass
urn:li:structuredProperty:ato.dcl.disposalAction
```

Prompt IDs must be stable and versioned:

```text
dcl.edw.database.v1.businessDescription
dcl.edw.database.v1.disposalClass
dcl.edw.database.v1.disposalAction
```

### Sidecar form rule configuration

```yaml
schemaVersion: 1
formUrn: urn:li:form:dcl.edw.database.v1
formVersion: 1
targetEntityTypes:
  - container

rules:
  - id: disposal-class-to-action
    type: LOOKUP
    sourcePromptId: dcl.edw.database.v1.disposalClass
    targetPromptId: dcl.edw.database.v1.disposalAction
    referenceData: disposal-class-actions-v1
    targetReadOnly: true
    clearTargetWhenSourceEmpty: true
    rejectUnknownSource: true
```

### Disposal reference data

```yaml
schemaVersion: 1
id: disposal-class-actions-v1
entries:
  "61702":
    action: "Destroy 7 years after last action"
    active: true
  "61703":
    action: "Destroy 10 years after last action"
    active: true
```

### Rules

- The client may send Disposal Class.
- The backend derives Disposal Action.
- The backend must not trust a client-supplied Disposal Action.
- On each draft save, submission, and approval, recalculate the action.
- An unknown or inactive class blocks submission.
- Existing approved values using a retired class remain displayable.
- Mapping changes do not silently rewrite verified assets.
- Every revision records the mapping version used.

---

## 10. Workflow state machine

### States

```text
AWAITING_DOCUMENTATION
DRAFT
PENDING_REVIEW
REJECTED
PUBLISHING
PUBLISH_FAILED
VERIFIED
```

Optional future state:

```text
REVIEW_DUE
```

### Allowed transitions

```text
AWAITING_DOCUMENTATION -> DRAFT
DRAFT                  -> DRAFT
DRAFT                  -> PENDING_REVIEW
PENDING_REVIEW         -> REJECTED
PENDING_REVIEW         -> PUBLISHING
REJECTED               -> DRAFT
PUBLISHING             -> VERIFIED
PUBLISHING             -> PUBLISH_FAILED
PUBLISH_FAILED         -> PUBLISHING
```

### Invariants

- Only one active workflow per asset/form pair.
- A `PENDING_REVIEW` revision is immutable.
- Rejection never changes DataHub metadata.
- Approval cannot operate on a stale revision.
- `VERIFIED` is set only after every required publication item and native verification succeed.
- Reviewer must be authorised and, by default, different from submitter.
- Every status transition creates an audit event.

### State transition API errors

Use HTTP `409 Conflict` for:

- stale optimistic-lock version;
- illegal state transition;
- DataHub values changed after submission;
- duplicate approval in progress.

Use HTTP `403 Forbidden` for failed authorisation.

Use HTTP `422 Unprocessable Entity` for form validation failures.

---

## 11. End-to-end flows

### 11.1 Start or open a form

1. User opens `/assets/{encodedUrn}/forms/{encodedFormUrn}`.
2. Backend identifies current user from OIDC.
3. Backend retrieves asset metadata and ownership from DataHub.
4. Backend verifies the user is a BCP or reviewer.
5. Backend retrieves the native Form definition and Structured Property definitions.
6. Backend retrieves current approved property values.
7. Backend retrieves or creates the workflow row.
8. If there is no active draft, initialize draft answers from approved values.
9. Return form schema, approved values, draft values, status, and permissions.

### 11.2 Save draft

1. Client sends editable answers and expected row version.
2. Backend validates prompt IDs and value types.
3. Backend applies derived-field rules.
4. Backend saves a mutable draft revision.
5. No DataHub write occurs.
6. Return normalized answers, including derived Disposal Action.

### 11.3 Submit

1. Backend confirms user is an authorised BCP.
2. Confirm current state is `DRAFT` or `REJECTED` after a correction draft has been created.
3. Re-fetch current form schema.
4. Validate every required prompt.
5. Re-run derived rules.
6. Capture current approved values and a baseline fingerprint.
7. Freeze an immutable revision snapshot.
8. Set status to `PENDING_REVIEW`.
9. Record `submittedBy` and `submittedAt`.
10. Emit audit event.
11. No DataHub write occurs.

### 11.4 Review

Reviewer sees:

```text
Field                   Current approved value      Proposed value
Business Description    Existing description       New description
Disposal Class           61701                      61702
Disposal Action          Old action                 Destroy 7 years...
```

Display:

- changed values;
- unchanged values;
- derived fields;
- submitter;
- submission timestamp;
- form version;
- previous rejection reason, where relevant.

### 11.5 Reject

1. Reviewer enters mandatory reason.
2. Backend verifies reviewer permission and separation of duties.
3. Status becomes `REJECTED`.
4. Submitted revision remains immutable.
5. A new mutable correction draft is created from the rejected answers.
6. DataHub remains unchanged.
7. Audit event records reviewer and reason.

### 11.6 Approve and publish

1. Reviewer clicks Approve.
2. Backend checks state, revision, reviewer permission, and separation of duties.
3. Re-fetch DataHub form definition and current approved values.
4. Revalidate required prompts and derived fields.
5. Compare DataHub values with the submission baseline.
6. If values conflict, return `409` and require reviewer resolution; do not publish silently.
7. Create a stable publication ID.
8. Set state to `PUBLISHING` and create publication items/outbox event.
9. Publisher worker calls `submitFormPrompt` for each approved response.
10. After required prompts succeed, call `verifyForm`.
11. Set state to `VERIFIED` only after native verification succeeds.
12. Record reviewer, verified timestamp, and publication result.

### 11.7 Retry publication

- Retry only failed or unknown publication items.
- Use stable idempotency keys.
- Re-read the DataHub asset before retrying.
- Do not create another workflow revision.
- Do not mark verified until all items and `verifyForm` succeed.

---

## 12. PostgreSQL data model

The following schema is intentionally conventional. Adjust naming to local standards.

### 12.1 `dcl_workflow`

One row per asset/form pair.

```sql
CREATE TYPE dcl_workflow_status AS ENUM (
  'AWAITING_DOCUMENTATION',
  'DRAFT',
  'PENDING_REVIEW',
  'REJECTED',
  'PUBLISHING',
  'PUBLISH_FAILED',
  'VERIFIED'
);

CREATE TABLE dcl_workflow (
  id                    UUID PRIMARY KEY,
  entity_urn            TEXT NOT NULL,
  form_urn              TEXT NOT NULL,
  form_version          INTEGER NOT NULL,
  status                dcl_workflow_status NOT NULL,
  active_revision       INTEGER NOT NULL DEFAULT 0,
  row_version           BIGINT NOT NULL DEFAULT 0,
  assigned_bcp_urns     JSONB NOT NULL DEFAULT '[]'::jsonb,
  submitted_by          TEXT,
  submitted_at          TIMESTAMPTZ,
  reviewed_by           TEXT,
  reviewed_at           TIMESTAMPTZ,
  rejection_reason      TEXT,
  last_verified_at      TIMESTAMPTZ,
  publication_id        UUID,
  publication_error     TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (entity_urn, form_urn)
);
```

### 12.2 `dcl_revision`

Immutable once submitted. A draft revision may be updated until submission.

```sql
CREATE TABLE dcl_revision (
  workflow_id           UUID NOT NULL REFERENCES dcl_workflow(id),
  revision_number       INTEGER NOT NULL,
  revision_state        TEXT NOT NULL CHECK (
    revision_state IN ('DRAFT', 'SUBMITTED', 'REJECTED', 'APPROVED')
  ),
  answers_json          JSONB NOT NULL,
  form_snapshot_json    JSONB NOT NULL,
  approved_values_json  JSONB NOT NULL,
  baseline_fingerprint  TEXT,
  rule_versions_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by            TEXT NOT NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  submitted_at          TIMESTAMPTZ,
  PRIMARY KEY (workflow_id, revision_number)
);
```

`approved_values_json` means the DataHub values observed at the time the draft/submission snapshot was built. It supports review diffs and conflict detection.

### 12.3 `dcl_publication_item`

```sql
CREATE TABLE dcl_publication_item (
  publication_id        UUID NOT NULL,
  workflow_id           UUID NOT NULL REFERENCES dcl_workflow(id),
  revision_number       INTEGER NOT NULL,
  prompt_id             TEXT NOT NULL,
  property_urn          TEXT NOT NULL,
  status                TEXT NOT NULL CHECK (
    status IN ('PENDING', 'SUCCEEDED', 'FAILED')
  ),
  attempt_count         INTEGER NOT NULL DEFAULT 0,
  last_attempt_at       TIMESTAMPTZ,
  last_error            TEXT,
  PRIMARY KEY (publication_id, prompt_id)
);
```

Treat `verifyForm` as a separate publication item named `__VERIFY_FORM__` or track it in a dedicated column.

### 12.4 `dcl_audit_event`

```sql
CREATE TABLE dcl_audit_event (
  id                    UUID PRIMARY KEY,
  workflow_id           UUID NOT NULL REFERENCES dcl_workflow(id),
  revision_number       INTEGER,
  event_type            TEXT NOT NULL,
  actor_urn              TEXT NOT NULL,
  event_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  details_json           JSONB NOT NULL DEFAULT '{}'::jsonb
);
```

Recommended events:

```text
WORKFLOW_CREATED
DRAFT_SAVED
SUBMITTED
REJECTED
CORRECTION_DRAFT_CREATED
APPROVED
PUBLICATION_STARTED
PROMPT_PUBLISHED
PUBLICATION_FAILED
FORM_VERIFIED
WORKFLOW_VERIFIED
```

### 12.5 Optional `dcl_outbox`

Use a transactional outbox when publication is asynchronous:

```sql
CREATE TABLE dcl_outbox (
  id                    UUID PRIMARY KEY,
  event_type            TEXT NOT NULL,
  aggregate_id          UUID NOT NULL,
  payload_json          JSONB NOT NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at          TIMESTAMPTZ,
  attempt_count         INTEGER NOT NULL DEFAULT 0,
  last_error            TEXT
);
```

The approval transaction should atomically set `PUBLISHING`, create publication items, and create the outbox event.

---

## 13. Sidecar API contract

Use REST for the MVP. Keep DataHub GraphQL behind a backend adapter.

### 13.1 Get compliance form for an asset

```http
GET /api/v1/assets/{encodedEntityUrn}/forms/{encodedFormUrn}
```

Response:

```json
{
  "asset": {
    "urn": "urn:li:container:...",
    "name": "EDW_DB_A",
    "type": "CONTAINER",
    "platform": "teradata",
    "businessContacts": [
      {"urn": "urn:li:corpuser:alan", "displayName": "Alan Zhou"}
    ]
  },
  "form": {
    "urn": "urn:li:form:dcl.edw.database.v1",
    "version": 1,
    "name": "DCL EDW Database Compliance",
    "prompts": [
      {
        "id": "dcl.edw.database.v1.disposalClass",
        "title": "Disposal Class",
        "required": true,
        "readOnly": false,
        "propertyUrn": "urn:li:structuredProperty:ato.dcl.disposalClass",
        "valueType": "STRING",
        "allowedValues": ["61702", "61703"]
      },
      {
        "id": "dcl.edw.database.v1.disposalAction",
        "title": "Disposal Action",
        "required": true,
        "readOnly": true,
        "derived": true,
        "propertyUrn": "urn:li:structuredProperty:ato.dcl.disposalAction",
        "valueType": "STRING"
      }
    ]
  },
  "approvedValues": {
    "dcl.edw.database.v1.disposalClass": ["61701"],
    "dcl.edw.database.v1.disposalAction": ["Existing action"]
  },
  "workflow": {
    "id": "uuid",
    "status": "DRAFT",
    "revision": 1,
    "rowVersion": 4,
    "answers": {
      "dcl.edw.database.v1.disposalClass": ["61702"],
      "dcl.edw.database.v1.disposalAction": ["Destroy 7 years after last action"]
    },
    "permissions": {
      "canEdit": true,
      "canSubmit": true,
      "canReview": false
    }
  }
}
```

### 13.2 Save draft

```http
PUT /api/v1/workflows/{workflowId}/draft
If-Match: "4"
Content-Type: application/json
```

```json
{
  "answers": {
    "dcl.edw.database.v1.businessDescription": ["Approved business purpose"],
    "dcl.edw.database.v1.disposalClass": ["61702"]
  }
}
```

Response must contain normalized answers including the server-derived action and a new row version.

### 13.3 Submit

```http
POST /api/v1/workflows/{workflowId}/submit
If-Match: "5"
```

No arbitrary answer payload should be accepted here. Submit the persisted draft after server-side revalidation.

### 13.4 Review queue

```http
GET /api/v1/reviews?status=PENDING_REVIEW&page=0&pageSize=25
```

Filters for future extension:

```text
platform
formUrn
submittedBy
submittedFrom
submittedTo
```

### 13.5 Review detail

```http
GET /api/v1/reviews/{workflowId}
```

Return approved-versus-proposed diff and immutable submitted revision.

### 13.6 Approve

```http
POST /api/v1/reviews/{workflowId}/approve
If-Match: "7"
```

```json
{
  "expectedRevision": 2,
  "comment": "Optional reviewer note"
}
```

Return `202 Accepted` with status `PUBLISHING` when using a worker.

### 13.7 Reject

```http
POST /api/v1/reviews/{workflowId}/reject
If-Match: "7"
```

```json
{
  "expectedRevision": 2,
  "reason": "The business description needs to identify the authoritative source."
}
```

### 13.8 Retry publication

```http
POST /api/v1/reviews/{workflowId}/retry-publication
If-Match: "8"
```

Only authorised reviewers or support administrators may call this.

---

## 14. DataHub integration adapter

Create an interface so the application can be developed and tested before internal DataHub access is restored.

```text
DataHubClient
  getAsset(entityUrn)
  getAssetOwnership(entityUrn)
  getForm(formUrn)
  getStructuredPropertyDefinition(propertyUrn)
  getCurrentStructuredPropertyValues(entityUrn, propertyUrns)
  isFormAssigned(entityUrn, formUrn)
  assignForm(entityUrn, formUrn)
  submitFormPrompt(entityUrn, formUrn, prompt, values)
  verifyForm(entityUrn, formUrn)
  getNativeFormState(entityUrn, formUrn)
```

Implement:

```text
GraphQlDataHubClient
FakeDataHubClient
```

The fake client should support deterministic integration tests and local UI development.

### Publication mapping

Each answer must map to a native Form prompt and its Structured Property URN. Never accept a caller-supplied arbitrary property URN at publication time. Resolve the mapping from the frozen form snapshot or trusted server configuration.

### Native publication sequence

```text
for each required/answered prompt in deterministic form order:
    if publication item already SUCCEEDED:
        skip
    call submitFormPrompt
    mark item SUCCEEDED

call verifyForm
mark __VERIFY_FORM__ SUCCEEDED
mark workflow VERIFIED
```

### Do not assume atomicity

Native prompt submission writes one field at a time. The sidecar must tolerate:

- first property succeeds;
- second property fails;
- retry resumes from the failed item;
- repeated submission of the same approved value is harmless.

### DataHub schema introspection

When connecting to the internal instance, inspect the actual schema rather than assuming public-document field names:

```graphql
query CheckMutationCapabilities {
  __type(name: "Mutation") {
    fields { name }
  }
}
```

Confirm at minimum:

```text
batchAssignForm
submitFormPrompt
verifyForm
```

Search for internal proposal/approval mutations before proceeding, and document any internal capability that can replace part of the sidecar.

---

## 15. Bootstrap and seed process

Create an idempotent bootstrap tool, preferably Python using the organisation's approved DataHub SDK or GraphQL client.

Responsibilities:

1. Upsert required Structured Property definitions.
2. Create or validate `dcl.edw.database.v1`.
3. Confirm prompt IDs and property URNs.
4. Configure the native form actor as the publisher service account/group.
5. Assign the form to configured DevTest asset URNs.
6. Validate that the form is retrievable on each asset.
7. Print a machine-readable summary.

Suggested command:

```bash
python scripts/bootstrap_dcl.py \
  --config config/forms/edw-database-v1.yaml \
  --assets config/devtest-assets.yaml \
  --dry-run
```

Then:

```bash
python scripts/bootstrap_dcl.py \
  --config config/forms/edw-database-v1.yaml \
  --assets config/devtest-assets.yaml \
  --apply
```

The tool must be safe to rerun.

---

## 16. Frontend MVP

### Routes

```text
/assets/:encodedEntityUrn/forms/:encodedFormUrn
/reviews
/reviews/:workflowId
```

### Asset form page

Display:

- asset name, platform, and URN;
- workflow status;
- Business Contacts;
- approved values where useful;
- editable prompts;
- read-only derived prompts;
- last saved time;
- rejection reason;
- Save Draft and Submit buttons.

Behaviour:

- Disposal Action updates immediately when Disposal Class changes.
- The UI may calculate the preview, but the server remains authoritative.
- Disable editing in `PENDING_REVIEW`, `PUBLISHING`, and `VERIFIED`.
- A rejected submission creates an editable correction draft.
- Warn on navigation with unsaved changes.
- Display validation errors against the relevant prompt.

### Review queue

Columns:

```text
Asset
Form
Submitted By
Submitted At
Status
Platform
```

### Review detail

Display:

- current approved value;
- proposed value;
- changed/unchanged indicator;
- derived indicator;
- form version;
- submitter;
- revision;
- prior rejection reason;
- Approve and Reject controls.

Reject opens a dialog with a required reason.

### Accessibility and usability

- Keyboard-accessible controls.
- Labels connected to inputs.
- Clear status text in addition to colour.
- Long text values remain readable.
- URNs are copyable but not the primary display label.

---

## 17. Authentication and authorisation

### Authentication

Preferred:

- OIDC/SSO at the application or reverse-proxy layer.
- Backend receives a verified subject, username/email, and groups.
- Map the identity to a DataHub `corpuser` URN using a configured rule.

Do not place the DataHub publisher token in the browser.

### BCP authorisation

For each write operation:

1. Read current asset ownership from DataHub.
2. Select owners with the configured Business Contact ownership type.
3. Confirm current user maps to one of those owner URNs.
4. Store the observed BCP URNs on the workflow for audit, but recheck live ownership before submit.

### Reviewer authorisation

Use an OIDC group or application role such as:

```text
DCL_BUSINESS_ADMIN
```

Do not infer reviewer permission from UI access alone.

### Publisher authorisation

The publisher identity requires only the DataHub privileges needed to:

- read forms and assets;
- write the relevant Structured Properties through form submission;
- verify the assigned form.

Do not use an unrestricted administrator token where a narrower service identity is available.

### Native workflow bypass

For the MVP, do not make Business Contacts native form actors. Configure only the DCL publisher service account/group as the native form actor. Otherwise, a BCP may be able to call native submission directly and bypass DCL review.

Test this explicitly with an unauthorised account.

---

## 18. Validation rules

### Draft save

Permit incomplete values, but validate:

- known prompt ID;
- correct basic type;
- maximum length;
- value cardinality;
- no arbitrary property URN;
- derived fields are server-controlled.

### Submit

Require:

- every required prompt has a valid value;
- every value satisfies the Structured Property definition;
- Disposal Class is active and mapped;
- Disposal Action equals the server-derived value;
- form version still exists;
- asset still exists and is eligible;
- submitter is a current BCP.

### Approve

Repeat all submission validation and additionally require:

- status is `PENDING_REVIEW`;
- revision matches;
- reviewer is authorised;
- reviewer differs from submitter, unless explicitly configured otherwise;
- current DataHub values match the submission baseline or a documented conflict-resolution action is taken.

### Rejection

- Reason is mandatory.
- Trim whitespace.
- Enforce a sensible maximum length.
- Do not expose the reason to general DataHub users.

---

## 19. Concurrency and conflict handling

### Optimistic locking

Use `row_version` and `If-Match` for all mutations.

Example:

```text
Client loaded rowVersion 4
Another user saves and rowVersion becomes 5
First client saves with If-Match 4
Server returns 409 Conflict
```

### DataHub baseline conflict

At submit time, compute a canonical fingerprint over the relevant approved DataHub values:

```text
SHA-256(canonical JSON of property URN -> sorted values)
```

At approval time, recompute it.

If the fingerprint changed:

- do not publish automatically;
- return conflict details;
- allow reviewer to reload the current values;
- require a new submission or an explicitly authorised override in a later increment.

The MVP can simply require resubmission.

### One active submission

Use the unique `(entity_urn, form_urn)` constraint and row locking to prevent parallel active workflows for the same form and asset.

---

## 20. Failure handling

| Failure | Required behaviour |
|---|---|
| DataHub unavailable while viewing | Return service-unavailable response; do not invent asset/form data |
| DataHub unavailable on draft save | Draft may save only if trusted form snapshot is already present; otherwise fail safely |
| DataHub unavailable on submit | Do not submit because current ownership/schema cannot be revalidated |
| Partial publication | Set `PUBLISH_FAILED`; preserve successful item states; permit idempotent retry |
| Native verification fails after all fields publish | Keep `PUBLISH_FAILED`; retry verification only |
| Asset deleted after submission | Block approval and surface clear error |
| Form version changed | Block approval; require migration or resubmission |
| Business Contact removed before submit | Block submit |
| Reviewer group removed during review | Block review action |
| Disposal mapping missing | Block draft normalization/submission with configuration error |
| Duplicate approve request | Return current `PUBLISHING`/`VERIFIED` state; do not duplicate publication |
| Service restarts during publication | Worker resumes from publication items/outbox |

---

## 21. Repository layout

Recommended separate repository:

```text
dcl-compliance-mvp/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── datahub-discovery.md
│   └── operations.md
├── backend/
│   ├── src/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── domain/
│   │   ├── persistence/
│   │   ├── datahub/
│   │   ├── publication/
│   │   └── validation/
│   └── test/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── forms/
│   │   └── reviews/
│   └── test/
├── db/
│   └── migrations/
├── config/
│   ├── forms/
│   │   └── edw-database-v1.yaml
│   ├── reference-data/
│   │   └── disposal-class-actions-v1.yaml
│   └── application.yaml
├── scripts/
│   ├── bootstrap_dcl.py
│   ├── inspect_datahub_schema.py
│   └── seed_local_demo.py
├── deploy/
│   ├── docker/
│   └── helm/
└── tests/
    ├── contract/
    └── e2e/
```

---

## 22. Suggested domain classes

```text
Workflow
WorkflowStatus
Revision
RevisionState
FormSnapshot
PromptDefinition
AnswerSet
ApprovedValueSnapshot
ReviewDecision
Publication
PublicationItem
AuditEvent
UserIdentity
AssetOwnership
DerivedFieldRule
LookupReferenceData
```

Key services:

```text
WorkflowService
FormAssemblyService
FormValidationService
DerivedFieldService
ReviewService
PublicationService
AuthorisationService
DataHubClient
AuditService
```

Keep DataHub GraphQL DTOs out of the domain layer. Translate them inside `datahub/`.

---

## 23. Prioritised implementation backlog

### P0 — Repository and contracts

**MVP-001: Establish application skeleton**

- Backend, frontend, DB migration framework, CI.
- Health endpoint.
- Configuration loading.

**MVP-002: Define DataHub adapter and fake client**

- Interface listed above.
- Fake form, asset, ownership, and values.
- Contract tests for adapter behaviour.

**MVP-003: Implement PostgreSQL schema**

- Workflow, revision, publication item, audit event, optional outbox.
- Repository tests.

### P0 — Form completion

**MVP-004: Read/assemble an asset form**

- Fetch asset, ownership, form, property definitions, approved values.
- Create workflow/draft.
- Return normalized form view model.

**MVP-005: Save draft**

- Optimistic locking.
- Partial validation.
- Audit event.
- No DataHub writes.

**MVP-006: Disposal dependency**

- Versioned mapping loader.
- Client preview.
- Backend derivation and enforcement.
- Unit tests.

**MVP-007: Submit workflow**

- Required-field validation.
- Immutable revision.
- Baseline fingerprint.
- `PENDING_REVIEW` state.

### P0 — Review and publication

**MVP-008: Review queue and detail**

- Reviewer authorisation.
- Current-versus-proposed diff.

**MVP-009: Reject and resubmit**

- Mandatory reason.
- Immutable rejected revision.
- Correction draft.

**MVP-010: Approve and publish**

- Publication ID/items.
- DataHub prompt submission.
- Native verification.
- Retry support.

### P0 — Security and integration

**MVP-011: OIDC identity and role mapping**

- BCP ownership checks.
- Reviewer group checks.
- Separation of duties.

**MVP-012: Internal DataHub discovery and real adapter**

- Schema introspection.
- Version report.
- GraphQL integration.
- Bootstrap script.

### P1 — Operational completeness

**MVP-013: Structured logs and metrics**

**MVP-014: Helm/deployment configuration**

**MVP-015: End-to-end test and demo dataset**

---

## 24. Acceptance criteria

### AC1 — Form retrieval

Given an eligible EDW database asset and an authorised Business Contact, opening the DCL URL displays the configured form and current approved DataHub values.

### AC2 — Draft isolation

Saving a draft updates PostgreSQL but does not alter any DataHub Structured Property or native form prompt state.

### AC3 — Derived disposal action

When Disposal Class `61702` is selected, Disposal Action is populated with the configured corresponding action, displayed as read-only, and recalculated by the backend.

### AC4 — Invalid disposal combinations

A caller cannot submit a Disposal Action that conflicts with the selected class. The server derives or rejects it regardless of browser behaviour.

### AC5 — Submission isolation

Submitting a valid form creates an immutable `PENDING_REVIEW` revision and still does not alter DataHub metadata.

### AC6 — Review

An authorised Business Administrator can see the current approved values and the proposed values for every prompt.

### AC7 — Rejection

Rejecting requires a reason, leaves DataHub unchanged, retains the submitted revision, and creates an editable correction draft.

### AC8 — Approval and publication

Approving a valid, non-conflicting revision causes the publisher to write all approved prompt values to DataHub and call native `verifyForm`.

### AC9 — Verified final state

The DCL workflow becomes `VERIFIED` only after all prompt publications and native form verification succeed.

### AC10 — Partial failure

If one publication item fails, the workflow becomes `PUBLISH_FAILED`, successful items are retained, and retry resumes without duplicate workflow revisions.

### AC11 — Authorisation

A non-BCP cannot edit or submit. A non-reviewer cannot approve or reject. The submitter cannot approve their own revision under the default policy.

### AC12 — Audit

The audit trail identifies every save, submit, rejection, approval, publication attempt, failure, retry, and verification with actor and timestamp.

### AC13 — Bypass resistance

A Business Contact cannot publish directly through the DCL browser client, and the publisher token is never exposed to the browser.

---

## 25. Test plan

### Unit tests

- Every state transition and illegal transition.
- Optimistic locking.
- Required prompt validation.
- Type and cardinality validation.
- Disposal mapping success, inactive code, unknown code, and cleared code.
- Read-only derived field enforcement.
- Separation of duties.
- Baseline fingerprint stability.
- Diff calculation.
- Publication item idempotency.

### Persistence integration tests

- One workflow per asset/form.
- Submitted revision cannot be updated.
- Rejection creates a new correction draft.
- Concurrent draft save returns conflict.
- Approval creates publication items and outbox atomically.

### DataHub adapter contract tests

Against the fake client and later DevTest:

- Fetch form and prompts.
- Fetch Container and ownership.
- Fetch current Structured Properties.
- Submit a prompt.
- Verify a form.
- Read native form state.
- Handle GraphQL errors and timeouts.

### End-to-end scenarios

1. New workflow, draft, submit, approve, publish, verify.
2. New workflow, draft, submit, reject, edit, resubmit, approve.
3. Attempt client-supplied conflicting Disposal Action.
4. DataHub approved value changes after submission; approval is blocked.
5. First prompt publishes, second fails, retry succeeds.
6. Verification fails after prompts succeed, retry verifies only.
7. Non-BCP tries to edit.
8. Non-reviewer tries to approve.
9. Submitter tries to self-approve.
10. Service restarts with an unprocessed outbox event.

### Native DataHub behavioural spike

Capture before and after for:

```text
structuredProperties aspect
forms aspect
form definition
logged-in actor
GraphQL request/response
native verification audit
```

Test native behaviour for an assigned publisher, an unauthorised user, editing after verification, clearing a value, and assigning the same form twice.

---

## 26. Deployment and configuration

### Runtime components

```text
dcl-web
dcl-api
dcl-worker        # may be same deployment as API for MVP
dcl-postgres      # preferably managed/shared enterprise PostgreSQL
datahub           # existing
```

### Required configuration

```text
DCL_DATAHUB_GRAPHQL_URL
DCL_DATAHUB_PUBLISHER_TOKEN
DCL_FORM_URN
DCL_BUSINESS_CONTACT_OWNERSHIP_TYPE_URN
DCL_REVIEWER_GROUP
DCL_OIDC_ISSUER
DCL_OIDC_CLIENT_ID
DCL_DATABASE_URL
DCL_REFERENCE_DATA_PATH
DCL_SELF_APPROVAL_ALLOWED=false
```

### Secrets

Store publisher token, database password, and OIDC client secret in the approved secret manager/Kubernetes Secret. Never commit them.

### Health endpoints

```text
/health/live
/health/ready
```

Readiness checks:

- database connectivity;
- configuration loaded;
- reference data valid;
- DataHub reachability, unless local development mode uses the fake adapter.

---

## 27. Observability

### Structured log fields

```text
request_id
workflow_id
entity_urn
form_urn
revision_number
publication_id
prompt_id
actor_urn
status_from
status_to
```

Never log access tokens or full sensitive free-text values.

### Metrics

```text
dcl_workflows_total{status}
dcl_submissions_total
dcl_reviews_total{decision}
dcl_publication_attempts_total{result}
dcl_publication_failures_total{operation}
dcl_pending_review_age_seconds
dcl_datahub_request_duration_seconds{operation}
```

### Alerts

- Repeated publication failures.
- Outbox item unprocessed beyond threshold.
- DataHub connectivity unavailable.
- Invalid reference-data configuration.
- `PUBLISHING` workflow stuck beyond threshold.

---

## 28. Security checklist

- [ ] Publisher token remains backend-only.
- [ ] All write endpoints enforce server-side authorisation.
- [ ] BCP ownership is rechecked on submit.
- [ ] Reviewer group is rechecked on approve/reject.
- [ ] Self-approval is disabled by default.
- [ ] Prompt IDs and property URNs come from trusted schema, not arbitrary client input.
- [ ] Derived fields are recomputed by the server.
- [ ] SQL access uses parameterized queries/ORM.
- [ ] CSRF protection is enabled when cookie-based sessions are used.
- [ ] Content Security Policy is configured.
- [ ] Rejection reasons and drafts are not returned to general users.
- [ ] Audit revisions are immutable after submission.
- [ ] Secrets are loaded from the approved secret store.
- [ ] Dependency and container scanning are enabled in CI.

---

## 29. First working sequence for the next agent

Start without waiting for internal DataHub access:

1. Create the repository skeleton.
2. Add this handoff under `docs/architecture.md`.
3. Define domain enums and transition rules.
4. Add database migrations.
5. Implement `DataHubClient` and `FakeDataHubClient`.
6. Seed a fake EDW Container, native form, Structured Properties, and Business Contact.
7. Implement form assembly and `GET` endpoint.
8. Implement draft save and derived disposal rule.
9. Implement submit and immutable revision.
10. Implement review queue, approve, and reject against the fake client.
11. Implement publication items and retry logic.
12. Build the three frontend routes.
13. Add end-to-end tests against the fake adapter.

When internal access becomes available:

14. Record DataHub version/commit and GraphQL introspection output.
15. Implement the real GraphQL adapter.
16. Run the native behavioural spike.
17. Create DevTest properties/form with the bootstrap tool.
18. Replace fake URNs with approved DevTest URNs.
19. Run the end-to-end approval flow against DataHub.
20. Document any fork-specific differences and update the adapter only—not the domain workflow.

---

## 30. Internal DataHub discovery checklist

Run and retain outputs:

```bash
git rev-parse HEAD
git describe --tags --always --dirty
git remote -v
```

Search internal source if available:

```bash
git grep -nE 'submitFormPrompt|verifyForm|batchAssignForm'
git grep -nEi 'proposeStructuredProperties|change proposal|accept.*proposal|reject.*proposal'
git grep -nE 'VerifyFormResolver|SubmitFormPromptResolver|FormService'
```

GraphQL introspection:

```graphql
query CheckMutationCapabilities {
  __type(name: "Mutation") {
    fields { name }
  }
}
```

Confirm:

```text
createForm
updateForm
batchAssignForm
submitFormPrompt
verifyForm
```

Also search for:

```text
proposeStructuredProperties
acceptProposal
rejectProposal
pendingProposals
```

If an internal whole-form proposal workflow already exists, stop and compare it against this MVP before duplicating functionality.

---

## 31. Open product decisions

These do not block development against the stated assumptions, but must be resolved before production:

1. Is publication-before-administrator-approval definitely prohibited?
2. Is approval always all-or-nothing?
3. May a reviewer edit proposed values, or only approve/reject?
4. Is self-approval ever allowed?
5. Are multiple BCPs allowed to edit the same draft?
6. What is the authoritative disposal mapping source and update process?
7. What should happen to verified assets when a disposal description changes?
8. Which exact DCL prompts belong in EDW database v1?
9. Which prompts are required?
10. Is the database object definitely a Container in the internal model?
11. What constitutes an Enterprise Data Asset for future assignment?
12. Does the reviewer group vary by platform/domain?
13. Should approved values be published under the service identity only, or must human submitter/reviewer identities also be written into DataHub?
14. What is the annual conformance interval and reminder policy?
15. What export shape is required later?

Record decisions as Architecture Decision Records rather than leaving them only in tickets or email.

---

## 32. MVP demo script

Use one DevTest asset and two accounts.

### Setup

- Asset: one EDW database Container.
- BCP: test business contact.
- Reviewer: test Business Administrator.
- Form: `dcl.edw.database.v1`.
- Fields: Business Description, Disposal Class, Disposal Action.

### Demo

1. Open DataHub and show the current approved values.
2. Open the DCL sidecar form from its URL.
3. Select Disposal Class `61702`.
4. Show Disposal Action automatically becoming `Destroy 7 years after last action` and remaining read-only.
5. Save draft.
6. Return to DataHub and prove values have not changed.
7. Submit.
8. Open the reviewer queue.
9. Show current-versus-proposed diff.
10. Reject with a reason.
11. Show the BCP correction draft and unchanged DataHub asset.
12. Correct and resubmit.
13. Approve.
14. Show `PUBLISHING`, then `VERIFIED`.
15. Return to DataHub and show both Structured Properties separately.
16. Show native form verification.
17. Show the DCL audit history with submitter, reviewer, revisions, rejection, and publication events.

---

## 33. Definition of done for the MVP

The MVP is complete only when all of the following are demonstrable in DevTest:

- One real DataHub database asset can be loaded into the sidecar.
- One real native DataHub form definition drives the displayed prompts.
- Current approved values are pre-populated.
- A BCP can save a private draft.
- Disposal Action is server-derived from Disposal Class.
- Draft and submitted values do not appear in DataHub before approval.
- A reviewer can reject with a reason and the BCP can resubmit.
- A reviewer can approve the entire revision.
- Approved values publish to separate DataHub Structured Properties.
- Native form verification succeeds.
- Partial publication can be retried safely.
- Authorisation and separation-of-duties tests pass.
- Audit events identify all relevant actors and timestamps.
- Setup is reproducible using migrations, configuration, and the bootstrap script.
- No DataHub Core source modification is required.

---

## 34. Guardrails for the implementing agent

1. Do not call native `submitFormPrompt` during draft or submit.
2. Do not trust the browser to calculate Disposal Action.
3. Do not store only the latest submission; preserve immutable revisions.
4. Do not mark a workflow verified before native publication and verification finish.
5. Do not treat multiple DataHub writes as a transaction.
6. Do not expose the publisher token to the browser.
7. Do not make Business Contacts native form actors unless bypass is explicitly accepted.
8. Do not hard-code internal GraphQL fields before introspecting the deployed schema.
9. Do not edit a published form version in place; create a new version for changed questions.
10. Do not expand the MVP into a generic Cloud Change Proposals clone.
11. Do not copy proprietary DataHub Cloud implementation code.
12. Keep the workflow domain independent from the DataHub adapter so internal fork differences remain isolated.

---

## 35. One-paragraph implementation brief

Build a no-fork DCL Compliance Workflow sidecar that reads a versioned native DataHub Verification Form and its Structured Property definitions, authorises respondents using Business Contact ownership, stages drafts and immutable submissions in PostgreSQL, derives Disposal Action from Disposal Class on the server, provides a one-stage Business Administrator approve/reject workflow, and publishes approved answers through native DataHub `submitFormPrompt` calls followed by `verifyForm`. Use optimistic locking, immutable revisions, baseline conflict detection, per-prompt idempotent publication state, a backend-only publisher token, and a clear audit trail. Prove the design first for one EDW database Container and one form; defer generic form building, automated assignment, notifications, annual review, export, and custom DataHub metadata models.
