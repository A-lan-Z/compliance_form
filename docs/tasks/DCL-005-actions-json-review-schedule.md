# DCL-005: Actions JSON Review Schedule POC

- Status: IMPLEMENTED POC
- Approved: 2026-09-03
- Target: local DataHub Core and Actions Framework `v1.5.0.6`
- Scope owner: DCL compliance-form project

## Objective

Keep all three DCL notification demonstrations in one custom DataHub Actions deployment:

1. When a configured compliance Form is assigned, email the entity's current Business Contacts.
2. Fourteen days before its configured Review Date, email current Business Contacts and DSG.
3. Fourteen days after that date, if the stored date has not been advanced, email current Business
   Contacts and DSG.

Use a plain JSON schedule for the POC. Do not introduce SQLite, a standalone scheduler, atomic file
replacement, locking, multiple-replica coordination, or an external email integration.

## Repository reconciliation

The pinned DataHub `FormInfo` model has no Review Date field. The POC therefore configures a
`review_date` beside each watched Form URN in the Action YAML. A native Form-assignment event saves
that Form date against the assigned entity in JSON. Selecting the authoritative production Review
Date model remains a product decision.

## Design

- The existing Kafka Actions source detects native `forms` aspect assignment events.
- The custom Action immediately creates the assignment email and writes
  `entityUrn/formUrn/reviewDate` to one JSON array.
- A daemon timer in that same Action process checks the schedule every configured interval.
- Business Contacts are resolved from current DataHub ownership at email time.
- DSG addresses remain explicit POC configuration.
- Replacing the date for the same entity/Form pair advances that schedule and prevents the old date
  from satisfying the overdue rule.
- Delivery remains an idempotent local RFC email outbox.

## POC implementation level

The code assumes the configured YAML and DataHub event schema are correct. It uses the single
`get_untyped_aspect` ownership API supplied by the pinned Actions runtime and lets ordinary Python
errors expose bad configuration or malformed events. It deliberately has no compatibility API,
schema-validation layer, retry wrapper, atomic JSON replacement, file lock, or multi-process
coordination.

## Acceptance criteria

1. A configured Form assignment writes one JSON schedule record.
2. The same assignment path still emits one Business Contact assignment email.
3. The in-process timer emits the two-weeks-before reminder to current Business Contacts and DSG.
4. It emits the two-weeks-after reminder only while the stored date remains fourteen days behind.
5. Updating the stored date for an entity/Form replaces its previous date.
6. Replaying an event or reminder does not create duplicate email files.
7. The adapter runs against `acryl-datahub-actions==1.5.0.6`.
8. A deterministic demo produces all three notification types without an external email write.

## POC limitations

- One running Actions process and one JSON writer are assumed.
- A stopped process can miss an exact boundary-day reminder.
- Review Date creation and later updates are config/JSON operations, not yet DataHub metadata
  events.
- The local email outbox stands in for the organisation's approved email service.
- Production directory lookup, group expansion, retry, monitoring, retention, and secrets remain
  deferred.
