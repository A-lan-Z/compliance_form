# Local DataHub Notification POC Evidence

- Captured: 2026-08-25; DCL-005 extension verified 2026-09-03
- Repository: `/home/alanz/compliance_form`
- DataHub checkout: `/home/alanz/datahub-core`
- DataHub commit: `d0fce948555c06b3083479d40e8fa270d156c71f`
- DataHub release: `v1.5.0.6`
- Actions package: `acryl-datahub-actions==1.5.0.6`

## Source evidence

The pinned DataHub implementation of `batchAssignForm` reads the target entity's current `forms`
aspect, adds a new `FormAssociation` to `incompleteForms`, and ingests the updated aspect.

The pinned Actions Framework consumes `MetadataChangeLogEvent_v1` from
`MetadataChangeLog_Versioned_v1`. Its event contract exposes both the new `aspect` and the
`previousAspectValue`, and its Kafka source documents at-least-once processing.

The verified detector boundary is therefore:

```text
event type     = MetadataChangeLogEvent_v1
changeType     = UPSERT
aspectName     = forms
assignment     = union(new incomplete/completed Form URNs)
                 minus
                 union(previous incomplete/completed Form URNs)
```

A Form moving from incomplete to completed remains in both unions and produces no assignment
notification.

## Live local event path

The local DataHub containers were healthy and exposed Kafka on `127.0.0.1:9092`, GMS on
`127.0.0.1:18080`, and the versioned MCL topic through the configured schema-registry endpoint.

The target synthetic asset was:

```text
urn:li:container:328308bacafdd7dac732214f6e3eaf8b0618d00f
```

Its current configured Business Contact owners were:

```text
urn:li:corpuser:dcl.maker
urn:li:corpuser:datahub
ownership type: urn:li:ownershipType:dcl.businessContact
```

A temporary Actions 1.5.0.6 environment started the custom action using
`notifications/config/form-assignment-action.yaml`. A disposable local Form was then created and
assigned:

```text
urn:li:form:dcl.notification.poc.v1
```

Observed result:

```text
To: datahub-owner@example.test, dcl-maker@example.test
Subject: Compliance form assigned
X-DCL-Notification-Kind: form-assigned
```

This proves the real path from native `batchAssignForm`, through the local MCL Kafka stream and
custom Actions adapter, through a live current-ownership read, to one captured email.

After capture, `batchRemoveForm` returned true, `deleteForm` returned true, and a direct read
confirmed that the disposable Form was no longer assigned. The existing completed tour Forms were
not removed or reassigned.

## Scheduled reminder path

The DCL-005 deterministic demo persisted its schedule to a plain JSON file and evaluated it at
`as-of=2026-08-25`:

- `2026-09-08`: pre-review reminder produced;
- `2026-08-11`: overdue reminder produced;

The same entity/Form record was updated from the first date to the second, proving that a new date
replaces the previous date. A separate evaluator test advanced the date to `2027-08-11` and
confirmed that the old overdue cycle no longer matched.

Both reminders included the current Business Contact and the configured synthetic DSG address. The
complete assignment-plus-schedule demo produced three email files on its first run:

```text
due=3 created=3 duplicates=0
```

Replaying the identical assignment event and scheduled snapshot produced no additional files:

```text
due=3 created=0 duplicates=3
```

## DCL-005 live combined Action path

The custom Action was run against the real local Kafka listener and GMS using
`acryl-datahub-actions==1.5.0.6`. Its configured POC Review Date was `2026-09-17`, fourteen days
after the verification date, and its timer interval was one second.

A disposable native Form was created and assigned to the existing synthetic container:

```text
urn:li:form:dcl.notification.schedule.simple2.poc.v1
```

The live assignment event produced this persisted schedule:

```json
[
  {
    "entityUrn": "urn:li:container:328308bacafdd7dac732214f6e3eaf8b0618d00f",
    "formUrn": "urn:li:form:dcl.notification.schedule.simple2.poc.v1",
    "reviewDate": "2026-09-17"
  }
]
```

The same running Action process produced both live emails:

```text
To: datahub-owner@example.test, dcl-maker@example.test
Subject: Compliance form assigned
X-DCL-Notification-Kind: form-assigned

To: datahub-owner@example.test, dcl-maker@example.test, dsg@example.test
Subject: Compliance review due in two weeks
X-DCL-Notification-Kind: review-due-soon
```

The disposable assignment was removed and `deleteForm` returned true. A container Forms query
confirmed that the disposable Form remained absent from both incomplete and completed assignments.

## Verification boundaries

Verified:

- exact DataHub 1.5.0.6 Actions API import and event-envelope compatibility;
- native form-assignment event through local Kafka;
- current owner lookup through the Actions graph's untyped ownership aspect;
- assignment allowlist;
- JSON schedule creation and same-entity/Form date replacement;
- in-process Action timer execution;
- pre-review and overdue date evaluation;
- advanced Review Date suppression;
- deterministic replay idempotency;
- RFC email rendering to a local outbox.

Not verified and deliberately deferred:

- production ownership/group directory resolution;
- an authoritative DataHub Review Date field or update event;
- multi-replica or restart-safe scheduler behavior;
- SMTP, SES, or Microsoft Graph delivery;
- production retries, monitoring, bounce handling, and retention.

No external email was sent, no credential was written to the repository, and no disposable Form
remained assigned after the live check.

## DCL-005 verification results

Verified on 2026-09-03:

- System-Python notification suite: 16 passed; the optional Actions-package test was skipped.
- Pinned `acryl-datahub-actions==1.5.0.6` suite: all 17 tests passed.
- Focused Ruff correctness and format checks: passed.
- Python byte compilation: passed.
- Deterministic demo: `due=3 created=3`, followed by `due=3 created=0` on replay.
- Live local DataHub: native assignment created one JSON schedule record, one assignment email, and
  one timer-generated due-soon email.
- Frontend lint, 13 frontend tests, frontend production build, and 22 backend unit tests: passed as
  part of the repository gate.

The complete `./scripts/verify.sh` gate could not pass its PostgreSQL integration stage because
Docker Desktop rejected every new Testcontainers container before process startup with
`error loading seccomp filter into kernel: errno 524`. Both PostgreSQL integration classes failed
at container creation; the later browser stage was not reached. This is an unavailable local Docker
boundary, not a notification test failure. Existing DataHub containers continued to serve the live
Kafka/GMS verification.

The final minimal-code pass was reverified through the fresh disposable Form shown above after
removing alternate graph APIs, configuration/schema validation, model validation, delivery wrapper
objects, and the standalone failure-mode override. The live Actions graph required
`get_untyped_aspect`; the typed SDK ownership path was removed rather than retained as a
compatibility branch.
