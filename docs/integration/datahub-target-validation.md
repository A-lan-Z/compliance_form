# Exact DataHub Target Validation Gate

Status: Required before any live DataHub read, submission, review, publication, or verification
implementation.

DCL-001 deliberately uses local fixture data and makes no DataHub request. The unrelated local
quickstart is not a substitute for the internal target. Complete this checklist against the exact
authorised environment and retain sanitized evidence with the task that introduces the live
integration.

Do not place credentials, access tokens, full sensitive metadata values, internal secrets, or
unredacted production responses in this repository.

## 1. Target identity

- [ ] Record environment name and evidence-capture date.
- [ ] Record DataHub distribution, exact version/tag, commit SHA, and internal fork identifier.
- [ ] Record enabled feature flags relevant to Forms, Structured Properties, proposals, ownership,
      and audit/events.
- [ ] Identify the accountable environment and DataHub owners.
- [ ] Confirm which public documentation, if any, matches the deployed fork.

Evidence:

```text
Environment:
Captured at:
Distribution/version:
Commit/fork:
Relevant feature flags:
Owners:
Evidence location:
```

## 2. API and schema

- [ ] Retain a sanitized GraphQL schema/introspection digest for the exact deployment.
- [ ] Confirm authenticated read endpoints, transport, timeouts, and error shape.
- [ ] Confirm the available Form, Structured Property, ownership, assignment, proposal, and audit
      queries and mutations by exact name and input/output type.
- [ ] Confirm whether schema introspection is permitted in production; if not, obtain an approved
      schema artifact through the target owner.
- [ ] Record rate limits and supported retry guidance.

## 3. Asset identity and eligibility

- [ ] Identify one authorised DevTest EDW database asset by exact URN.
- [ ] Confirm whether it is a Container, Dataset, platform instance, custom entity, or another type.
- [ ] Confirm its subtype and evidence that it represents a database rather than a schema or table.
- [ ] Confirm the supported lookup mechanism and URN construction rule; do not infer either from the
      fixture.
- [ ] Confirm asset visibility rules for BCPs and reviewers.
- [ ] Confirm the entity supports required Structured Properties and native Form assignment.

## 4. Form and Structured Property definitions

- [ ] Obtain approved, versioned Form URN(s).
- [ ] Obtain exact prompt IDs, order, labels, descriptions, requiredness, types, and cardinality.
- [ ] Obtain exact Structured Property URNs and definitions.
- [ ] Confirm allowed values and the authoritative Disposal Class to Disposal Action taxonomy.
- [ ] Confirm how immutable business revisions map to DataHub Form versions or URNs.
- [ ] Confirm read behavior for missing, cleared, retired, multi-valued, and malformed values.
- [ ] Confirm whether assignment is required and whether `batchAssignForm` or an equivalent operation
      is available and idempotent.

## 5. Governed Change Proposals

- [ ] Determine whether governed Change Proposals exist in this exact target; do not confuse them
      with low-level `MetadataChangeProposal` ingestion events.
- [ ] Confirm create, retrieve, list/pending-inbox, accept, and reject APIs.
- [ ] Confirm support for the actual target entity type.
- [ ] Confirm that updates to existing Structured Properties are supported, not only additions.
- [ ] Determine whether one proposal can contain the complete DCL property set.
- [ ] Determine whether the complete decision and application are atomic.
- [ ] Determine whether fields can be accepted or rejected independently.
- [ ] Confirm reviewer routing, visibility, privileges, and self-approval prevention.
- [ ] Confirm idempotent creation, duplicate-request behavior, rejection, and resubmission semantics.
- [ ] Confirm decision actor attribution, timestamps, comments/reasons, audit retrieval, and events or
      polling support.

Decision required after this section:

```text
[ ] Native proposal path selected
[ ] Custom DCL review path selected
```

Select exactly one. Do not implement both reviewer workflows.

## 6. Prompt submission and verification

- [ ] Prove the exact semantics of `submitFormPrompt` or its target equivalent.
- [ ] Confirm whether it applies or replaces a single bound Structured Property value.
- [ ] Confirm its behavior for clearing values and for repeated identical requests.
- [ ] Confirm required form assignment, prompt identity, entity type, and actor privileges.
- [ ] Confirm read-after-write consistency and the authoritative read-back query.
- [ ] Prove the exact semantics and preconditions of `verifyForm` or its equivalent.
- [ ] Confirm repeated verification behavior and how subsequent edits invalidate verification.
- [ ] Confirm how native completion and verification state can be read back.
- [ ] Confirm whether a Boolean mutation response can mask partial or asynchronous failure.

## 7. Identity and authorisation

- [ ] Confirm production OIDC issuer, client, audience, and server-verified principal claims.
- [ ] Confirm mapping from an authenticated principal to the DataHub actor identity.
- [ ] Confirm the Business Contact ownership type and multiple-owner policy.
- [ ] Confirm reviewer group/role source and exact membership rule.
- [ ] Confirm separation-of-duties and self-approval policy.
- [ ] Provision or identify the publisher service identity and token issuance mechanism.
- [ ] Prove least-privilege publisher reads, property writes, prompt submission, and verification.
- [ ] Prove the publisher cannot approve DCL work or write arbitrary unrelated metadata.
- [ ] Confirm that browser clients never receive publisher credentials.

## 8. Idempotency, conflicts, and partial effects

- [ ] Define deterministic operation and step keys supported by the target.
- [ ] Confirm duplicate prompt submission and verification behavior.
- [ ] Confirm how to distinguish success, unknown outcome, validation failure, and temporary failure.
- [ ] Confirm whether any bulk Structured Property operation replaces unrelated properties.
- [ ] Approve the external-drift comparison and conflict policy.
- [ ] Prove safe read-before-write and read-after-write behavior.
- [ ] Define forward-recovery behavior when some properties apply but verification fails.
- [ ] Confirm safe retry timing and limits.

## 9. Actor attribution and audit/event retrieval

- [ ] Confirm which actor DataHub records for property changes, prompt completion, proposal decisions,
      and verification.
- [ ] Decide whether automated publisher attribution is acceptable when DCL separately records the
      human approver.
- [ ] If human attribution is mandatory, identify a supported secure delegation mechanism; never
      forge an actor.
- [ ] Identify audit, timeline, event, or change-log APIs and their retention.
- [ ] Confirm correlation identifiers that can link DCL publication attempts to DataHub effects.
- [ ] Confirm what sanitized evidence operations staff can retrieve after a partial failure.

## 10. Exit evidence

Before implementation begins, attach or link:

- [ ] target version and fork report;
- [ ] sanitized schema/API report;
- [ ] approved entity and form/property definitions;
- [ ] identity and privilege test matrix;
- [ ] proposal-path decision record;
- [ ] prompt/verification behavioral test results;
- [ ] idempotency and partial-failure results;
- [ ] actor/audit attribution results;
- [ ] approved conflict and retry policy;
- [ ] explicit confirmation that all tests used an authorised non-production target.

Unresolved items are blockers for the boundary they affect. They are not permission to invent
production identifiers or implement a fallback write path.

