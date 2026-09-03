# DCL-004: DataHub Compliance Notification POC

- Status: IMPLEMENTED POC
- Approved: 2026-08-25
- Target: local DataHub Core `v1.5.0.6`
- Scope owner: DCL compliance-form project

> Scheduling note: DCL-005 supersedes this task's separate daily-command boundary with a
> minimal JSON schedule and timer inside the custom DataHub Action process. The notification rules
> and assignment detector defined here are unchanged.

## Context

The current product direction uses stock DataHub Forms and no longer requires the private
maker-reviewer workflow described by the original MVP handoff. The separately delivered frontend
restriction for the final verification Form is not part of this task.

This task promotes two capabilities that the handoff had deferred: compliance-form assignment
notifications and annual review reminders. It does not remove or reinterpret the existing DCL-001,
DCL-002, or experimental DCL-003 files.

## Objective

Prove three notification paths without fixing production recipient, ownership, review-date, or
email-provider rules:

1. When a configured compliance Form is newly assigned to an entity, notify its current configured
   Business Contact owners.
2. Fourteen days before the entity's current Review Date, notify its Business Contacts and DSG.
3. Fourteen days after the current Review Date, notify its Business Contacts and DSG. If the Review
   Date has already been advanced, the old date is no longer selected and no overdue reminder is
   produced.

## Repository and DataHub evidence

The pinned DataHub source implements `batchAssignForm` by adding a `FormAssociation` to the target
entity's `forms.incompleteForms` collection and ingesting the resulting `forms` aspect.

The DataHub Actions Framework consumes `MetadataChangeLogEvent_v1` events from the versioned MCL
Kafka topic. Each event includes the new `aspect` and optional `previousAspectValue`. The POC
therefore detects assignment by comparing the set of Form URNs in both `incompleteForms` and
`completedForms` before and after an `UPSERT` of the `forms` aspect.

The union comparison is required because completing a Form moves it from incomplete to completed;
that transition is not a new assignment and must not send another assignment email.

DataHub Actions is event driven and does not provide the calendar scheduler required by the two
Review Date rules. Those rules are implemented as a separate, deterministic command intended to be
invoked daily by cron, a Kubernetes CronJob, or the organisation's scheduler.

## POC boundaries

- The Actions adapter resolves the ownership aspect at event-processing time.
- A configured ownership-type URN selects Business Contacts.
- A configured principal-to-email map resolves synthetic owner URNs to demo addresses.
- Scheduled input is a JSON snapshot rather than a production DataHub search implementation.
- DSG recipients are explicit command/config inputs.
- Delivery creates idempotent RFC email (`.eml`) files in a local outbox.
- No SMTP, SES, Microsoft Graph, production directory, or external email write is performed.
- No DataHub metadata is changed by this POC.
- The at-least-once MCL delivery model is handled using a deterministic notification key. A replay
  of the same event does not create a duplicate email, while a later unassign/reassign event has a
  different event timestamp and can notify again.

## Implementation

The POC lives under `notifications/` and contains:

- a pure MCL `forms` aspect delta detector;
- a custom DataHub Actions `Action` adapter;
- current-ownership and static recipient adapters;
- a daily Review Date evaluator and command-line job;
- an idempotent local email outbox;
- deterministic demo fixtures and unit tests.

The Python core has no third-party runtime dependency. Running the real Actions adapter requires
the optional `acryl-datahub-actions==1.5.0.6` extra, matching the pinned local DataHub patch release.

## Acceptance criteria

1. An MCL `forms` aspect event that adds an allowed Form yields one assignment notification.
2. An unrelated aspect, an unallowed Form, removal, replay, or incomplete-to-completed transition
   yields no new assignment email.
3. Business Contact recipients are read from current ownership through a configurable ownership
   type and principal-email mapping.
4. A record whose Review Date is fourteen days ahead yields a pre-review reminder to Business
   Contacts and DSG.
5. A record whose current Review Date is fourteen days behind yields an overdue reminder to
   Business Contacts and DSG.
6. A Review Date that has been advanced no longer matches the old overdue date.
7. Reprocessing the same notification key is idempotent.
8. A local command demonstrates all three email types without DataHub or external email access.
9. The custom Action configuration targets the versioned MCL topic and filters to `UPSERT` events
   for the `forms` aspect.

## Deferred production decisions

- authoritative Business Contact ownership-type URN;
- group-owner expansion and user/group email lookup;
- DSG membership source;
- authoritative Review Date Structured Property URN and value format;
- query and pagination strategy for scheduled candidate discovery;
- timezone and daily scheduler ownership;
- SMTP, SES, or Microsoft Graph delivery;
- bounce, retry, escalation, and operational retention policy;
- message wording, branding, links, and recipient privacy requirements.
