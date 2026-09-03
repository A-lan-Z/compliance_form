# DCL Notification POC

This POC demonstrates three notification paths around stock DataHub Forms:

1. event-driven email when a compliance Form is newly assigned;
2. a scheduled email fourteen days before Review Date;
3. a scheduled email fourteen days after Review Date when the current date has not been advanced.

It intentionally does not decide production ownership types, DSG membership, the authoritative
Review Date metadata model, or the external email provider. Demo messages are RFC email files
written to a local outbox; nothing is sent outside the machine.

## Why the assignment detector works

DataHub's native `batchAssignForm` mutation adds the Form URN to the entity's `forms` aspect. The
Actions Framework receives the resulting `MetadataChangeLogEvent_v1` with both the new and previous
aspect values. The detector compares the union of `incompleteForms` and `completedForms` on both
sides and reports only newly appearing Form URNs.

Using the union avoids a false email when a user completes a Form and DataHub moves it from the
incomplete collection to the completed collection.

```text
DataHub batchAssignForm
        -> forms aspect MCL
        -> custom Actions adapter
        -> assignment email using current ownership
        -> entity/Form/Review Date saved in JSON

Same Actions process
        -> lightweight date timer
        -> JSON review schedule
        -> current ownership lookup
        -> +/- 14 day email to BCP + DSG
```

DataHub Core v1.5.0.6 does not have a Review Date field in its native Form definition. For this POC,
the Action YAML configures one Review Date for each watched Form. When an entity receives that Form,
the Action saves an entity/Form/date record. A future implementation can replace that input with
the agreed Structured Property or other authoritative metadata source.

The timer is deliberately part of the custom Action process. There is no separate cron job,
database, or service. The JSON file is deliberately simple: the POC assumes one Actions instance
and does not provide concurrent-writer or high-availability guarantees.

## Run the deterministic demo

From `/home/alanz/compliance_form`:

```bash
DCL_DEMO_DIR=$(mktemp -d)
PYTHONPATH=notifications/src \
  python3 -m dcl_notifications.demo \
  --work-directory "$DCL_DEMO_DIR"
```

The command creates a `review-schedule.json` file and exactly three `.eml` files: assignment,
pre-review, and overdue-review. Running it again with the same work directory creates no duplicate
emails.

Inspect the messages with:

```bash
find "$DCL_DEMO_DIR" -type f -print
sed -n '1,80p' "$DCL_DEMO_DIR"/outbox/*.eml
```

## Run focused tests

```bash
PYTHONPATH=notifications/src \
  python3 -m unittest discover -s notifications/tests -v
```

The repository's `scripts/verify.sh` also runs these tests.

## Run the real DataHub Action adapter

Use a dedicated environment and the patch release matching the local DataHub checkout:

```bash
python3.11 -m venv /tmp/dcl-notification-actions
source /tmp/dcl-notification-actions/bin/activate
python -m pip install -e './notifications[actions]'
```

Set the local connection and synthetic recipient values in the shell. Keep the authorization value
out of files and command history:

```bash
export KAFKA_BOOTSTRAP_SERVER=127.0.0.1:9092
export SCHEMA_REGISTRY_URL=http://127.0.0.1:18080/schema-registry/api/
export DATAHUB_GMS_URL=http://127.0.0.1:18080
export DATAHUB_GMS_AUTHORIZATION='replace-with-local-authorization-header'
export DCL_COMPLIANCE_FORM_URN='urn:li:form:dcl.notification.poc.v1'
export DCL_COMPLIANCE_FORM_REVIEW_DATE='2026-09-17'
export DCL_BUSINESS_CONTACT_OWNERSHIP_TYPE_URN='urn:li:ownershipType:replace-me'
export DCL_DEMO_BCP_MAKER_EMAIL='dcl-maker@example.test'
export DCL_DEMO_BCP_DATAHUB_EMAIL='datahub-owner@example.test'
export DCL_DEMO_DSG_EMAIL='dsg@example.test'
export DCL_NOTIFICATION_OUTBOX=/tmp/dcl-action-emails
export DCL_REVIEW_SCHEDULE_PATH=/tmp/dcl-review-schedule.json

datahub actions -c notifications/config/form-assignment-action.yaml
```

The outbox key makes a replayed event safe. Keep the Actions process running: its background timer
performs the Review Date checks. `DCL_REVIEW_POLL_SECONDS` defaults to 60 seconds for a quick POC
demonstration.

## Production gaps

This is not a production notification service. It can miss a boundary date while the single Action
process is stopped, and its JSON file is not suitable for multiple replicas. Production work must
supply current owner/group email resolution, authoritative Review Date creation and update events,
durable scheduler ownership, an approved mail provider, secrets, retry and monitoring policy,
templates, privacy controls, and deployment configuration.
