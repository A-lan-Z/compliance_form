# DataHub form assignment Action

Assign existing DataHub forms from table tags or ownership changes, and initialize a structured
property when a configured form is attached.

| Event | Result |
| --- | --- |
| A configured tag is added directly to a table | Attach its mapped form if absent |
| An owner is supplied at creation or added later | Attach the Minimum Metadata form if absent |
| A configured form is newly attached | Set its mapped structured property to `Awaiting population` if empty |

The runtime is pinned to CLI/Actions **1.6.0.16**. Use **Python 3.11**. Local integration tests target
**GMS 1.3.0**. See [VERIFICATION.md](VERIFICATION.md) for results and limits.

## Install and run

Download the wheel and example YAML from [GitHub Releases](https://github.com/A-lan-Z/compliance_form/releases).
From an activated Python 3.11 environment:

```shell
python -m pip install dcl_form_assignment_poc-0.2.0-py3-none-any.whl
datahub actions -c tag-form-action.yaml
```

Edit the YAML before starting the worker. Installation fetches the pinned framework dependency.
The same commands work in PowerShell and a Linux shell. The worker must be able to reach GMS,
Kafka, and the schema registry, and have the required credentials in its runtime environment.
For AWS MSK IAM, log in using your company's AWS profile or use the workload's assigned AWS role.
The DataHub token authenticates GMS requests; Kafka authentication is configured separately.

To install a checkout instead, run `python -m pip install .` from the repository root, then
`datahub actions -c config/tag-form-action.yaml`.

### Run directly from source

Install `acryl-datahub-actions==1.6.0.16`, keep the source directory and YAML together, and run from
the repository root:

```bash
PYTHONPATH="$PWD/src" datahub actions -c config/tag-form-action.yaml
```

In PowerShell:

```powershell
$env:PYTHONPATH = "$PWD/src"
datahub actions -c config/tag-form-action.yaml
```

## Configure the rules

The release YAML enables all three rules using synthetic local URNs. Replace them with your own:

```yaml
action:
  type: "dcl_form_assignment.action:FormAssignmentAction"
  config:
    tag_to_form:
      "urn:li:tag:YOUR_TAG": "urn:li:form:YOUR_TAG_FORM"
    minimum_metadata_form: "urn:li:form:YOUR_MINIMUM_METADATA_FORM"
    form_to_property:
      "urn:li:form:YOUR_WATCHED_FORM": "urn:li:structuredProperty:YOUR_STATUS_PROPERTY"
```

| Field | Meaning |
| --- | --- |
| `tag_to_form` | Tag URN to form URN mapping for direct table tags |
| `minimum_metadata_form` | Form attached when a user or group owner is added |
| `form_to_property` | Form URN to structured property URN mapping |

The watched form may be the Minimum Metadata form or a different form. Each rule is optional;
omit its field to disable it. At least one rule must be configured.

Forms, tags, and structured property definitions must already exist. The Action does not create
company definitions. Configure the Minimum Metadata form's assignees as entity owners if they
should complete it. Its questions must apply to the intended entity types.

Status properties must have the string value type, permit `Awaiting population` if allowed values
are restricted, and be enabled for each entity type on which the rule runs. An incompatible entity
scope fails visibly. Empty means no property assignment, no values, or only blank strings. Any
nonblank value is preserved.

### Connections

The example uses these environment variables:

| Variable | Purpose |
| --- | --- |
| `DATAHUB_GMS_URL` | GMS base URL |
| `DATAHUB_GMS_AUTHORIZATION` | Full authorization header, normally `Bearer <token>` |
| `KAFKA_BOOTSTRAP_SERVER` | Kafka bootstrap brokers |
| `SCHEMA_REGISTRY_URL` | Schema registry endpoint |
| `METADATA_CHANGE_LOG_VERSIONED_TOPIC_NAME` | Override for `MetadataChangeLog_Versioned_v1` |
| `PLATFORM_EVENT_TOPIC_NAME` | Override for `PlatformEvent_v1` |

Keep credentials in the environment or your approved secret store. Configure Kafka and schema
registry TLS/SASL in the connection section for your infrastructure. The DataHub identity needs
metadata reads, form-assignment permission, and permission to patch structured properties on the
target entities. The existing Kafka metadata topic carries ownership and form changes as well as tags.

## Processing behavior

The tag rule is restricted to active datasets with subtype exactly `[Table]`. The owner and form
rules cover the GMS 1.3 entity types that support their required aspects; see [DESIGN.md](DESIGN.md).
Owner types are unrestricted, and user and group owners qualify. The triggering owner must still
be present when the Action checks current metadata.

A form already present in either incomplete or completed forms is preserved, including its answers.
Owner removal and tag removal leave the assigned form in place. A later qualifying addition can
restore a manually removed form. Existing entities are not periodically scanned.

The property rule handles assignments from the UI, ingestion, or another process. Moving a form
between incomplete and completed states is not a new attachment. Removed forms and removed
entities are skipped. Property updates do not trigger another rule. Clearing a property alone does
not reinitialize it; a new form attachment is required, although a replayed attachment can also
initialize an empty property.

The worker uses a targeted server-side patch to preserve unrelated properties. It reads the status
property immediately before writing and preserves values already present at that read. GMS 1.3
does not support an atomic conditional property update: a concurrent write to the same property
between the read and patch can be overwritten. Run one Action worker and avoid another writer
initializing that status property concurrently. Form assignment also has read/modify/write
concurrency limits.

The sample keeps the existing pipeline name so upgrades resume committed Kafka offsets. Its
`auto.offset.reset: earliest` setting processes retained history when there are no saved offsets,
which can assign forms to older entities. Adding rules does not revisit already committed events.
A complete historical backfill is a separate operation.

Failures propagate with `failure_mode: THROW`. Monitor pipeline processing and failed-event logs;
a failed pipeline may leave the CLI process alive. Repair the fault and restart with the same
pipeline name. Protect failed-event logs because they may contain entity metadata.

## Fixed-version compatibility with legacy startup events

If an Actions 1.3 worker fails before `act()` with
`com.linkedin.common.AuditStamp` versus `com.linkedin.pegasus2avro.common.AuditStamp`,
the example YAML selects the source in `src/dcl_form_assignment/kafka_compat.py`. It translates only
that known named-union label before the installed SDK parses the MCL. It preserves the
record data, upstream consumer configuration, filtering and offset acknowledgments.
Errors raised by the installed SDK still propagate. The adapter adds no field validation;
some malformed field values are rejected later during event serialization.

The published 0.2.0 wheel does not contain this adapter. Use the Docker-copy option
below with that wheel, or build and install the package from this checkout.

The package source type is configured in `config/tag-form-action.yaml`:

```yaml
source:
  type: "dcl_form_assignment.kafka_compat:LegacyAuditStampKafkaEventSource"
  config:
    connection:
      # Keep your existing Kafka, registry and authentication settings.
      consumer_config:
        auto.offset.reset: earliest
```

To keep the existing 0.2.0 wheel and every dependency version, copy the same standalone
module into your existing Actions image instead:

```dockerfile
COPY src/dcl_form_assignment/kafka_compat.py /datahub-actions/src/legacy_mcl_source.py
```

The official Actions 1.3 image already imports from `/datahub-actions/src`.
For this deployment, use `source.type: "legacy_mcl_source:LegacyAuditStampKafkaEventSource"`.
Keep the remaining YAML unchanged, including `failure_mode: THROW` and `earliest`.

Deploy a fresh worker once to load the source; a crashed worker thread cannot adopt a
code change. Keep the pipeline name to resume saved offsets. `earliest` starts at the
oldest retained record only when the group has no valid committed offset; it does not
rewind saved offsets. No Kafka history deletion or GMS change is needed.

Startup logs `Legacy AuditStamp compatibility source enabled` with the pipeline name.
Conversion failures log their topic, partition, offset and error type and still propagate.
Successful translations log `Normalized legacy AuditStamp namespace` with topic,
partition and offset, excluding metadata payloads. The adapter was tested with Actions
1.3.0 and the pinned 1.6.0.16 SDK; see [VERIFICATION.md](VERIFICATION.md) for scope.

## Upgrade from 0.1.0

Stop the old worker, install the new wheel, and use the new release YAML with your connection
settings and URNs. The Action type is now `dcl_form_assignment.action:FormAssignmentAction`.
The old `aspectName: globalTags` filter must be removed so ownership and form events reach the Action.
Keep the pipeline name unchanged when preserving the existing consumer offsets.

## Local demo

Start local DataHub with GMS/frontend 1.3, Kafka, and the schema registry. The default endpoints
are GMS `127.0.0.1:8080` and Kafka `127.0.0.1:9092`.

1. Run `dcl-tag-form-demo setup` and copy the synthetic table URN. This creates the tag form,
   Minimum Metadata form, and their property definitions.
2. Start `datahub actions -c config/tag-form-action.yaml` and wait for Kafka partition assignment.
3. Add the configured tag to the table to attach the tag form.
4. Add a user or group owner to attach Minimum Metadata and initialize Population status.
5. Complete the forms through DataHub's native documentation controls. The Action does not change
   Population status on completion; an existing value remains as it is.

The CLI also supports `tag --entity '<URN>'` and `status --entity '<URN>'`. Use
`--server http://127.0.0.1:<port>` for another local GMS port. The demo accepts only local servers
and synthetic table names. It does not ingest a real database.

## Development

```bash
python -m pip install '.[dev]'
DCL_ACTION_PYTHON=.venv/bin/python bash scripts/verify.sh
```

The gate runs unit tests, Ruff lint/format checks, a wheel build, and dependency checks. GitHub CI
also tests installation outside the checkout. See [CONTRIBUTING.md](CONTRIBUTING.md).

Install the wheel before running the integration harness:

```bash
python tests/live_tag_assignment.py --gms-port 18083 --kafka-port 19093
```

The harness uses real local Kafka/GMS, starts and stops its own worker, and retains synthetic
metadata and a result manifest. It accepts only loopback endpoints.
