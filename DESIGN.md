# Form assignment and status initialization

## Rules

The Action consumes MetadataChangeLog events. The configuration supports three independent rules:

- `tag_to_form`: newly added direct table tags assign their mapped forms.
- `minimum_metadata_form`: newly added user/group owners assign one configured form.
- `form_to_property`: newly attached forms initialize their mapped string property to
  `Awaiting population` when it is absent, has no values, or contains only blank strings.

The existing tag rule remains restricted to datasets with subtype exactly `[Table]`. Owner changes
include the initial ownership aspect created during ingestion and subsequent owner additions.
Ownership-type changes without a new owner do not trigger assignment.

Form additions are the difference between the union of incomplete/completed forms before and after
the event. Completion, verification, answer updates, and removal do not count as new attachments.
The owner and form rules confirm current entity existence and activity before acting. They also
confirm the triggering owner or form still exists on the entity.

## Entity support

GMS 1.3 declares the `forms` and `structuredProperties` aspects on these entity types:

`dataset`, `dataJob`, `dataFlow`, `chart`, `dashboard`, `corpuser`, `corpGroup`, `domain`, `container`,
`glossaryTerm`, `glossaryNode`, `mlModel`, `mlModelGroup`, `mlFeatureTable`, `mlFeature`, `mlPrimaryKey`,
`schemaField`, `dataProduct`, and `application`.

All except `corpuser` and `schemaField` support ownership. Domain has no status aspect, so its
activity check uses existence. These capability sets come from the
[GMS 1.3 entity registry](https://github.com/datahub-project/datahub/blob/v1.3.0/metadata-models/src/main/resources/entity-registry.yml).
Custom entity types require explicit support and tests.

## Components

- `events.py` validates relevant events and extracts tag, owner, and form additions.
- `entities.py` contains the supported entity capabilities.
- `service.py` applies the rules and checks current eligibility.
- `datahub.py` reads typed aspects, assigns forms, and patches one structured property.
- `action.py` validates configuration and definitions and routes events to the service.
- `demo.py` creates synthetic local definitions and tables.

No alias is provided for the old Action class. Version 0.2.0 uses `FormAssignmentAction` and requires
the updated event filter. Rule fields are optional, but at least one must be enabled.

## Writes and concurrency

Form assignment uses `batchAssignForm` followed by a forms-aspect read-back. Existing incomplete
and completed assignments are preserved. The read-back is required because GMS may return success
while skipping an entity. Form assignment itself is a server read/modify/write operation and is not
protected against independent simultaneous form writers.

Property initialization reads current values and sends a synchronous PATCH for only the selected
property. The GMS 1.3 property-URN patch template preserves unrelated properties under its database
transaction. It avoids uploading a previously read copy of the whole structured-properties aspect.
A read-back requires the property to be populated before acknowledging success.

An empty property is absent, has no values, or contains only blank strings. Any nonblank value is
preserved. The property definition must have string type, allow `Awaiting population`, and
include the current entity type. Property scope mismatches and read/write failures are errors.

GMS 1.3 supports only `add` and `remove` patch operations. A local integration probe confirmed that
`test` is rejected. The initial read and targeted patch are therefore separate operations: a write
to the same property in between them can be overwritten. This Action does not provide a strict
compare-and-set guarantee. One worker and a single initializer for the status field are the supported
operating model. The Action never advances the field to Completed or submits form answers.

## Delivery and recovery

Existing DataHub state makes replay idempotent when assignments or property values are present.
A failed property write does not undo the form assignment; the form event remains a separate unit
of work that can be retried after repair. A replayed form event can initialize a subsequently cleared
property if the form is still attached. Owner/tag removal never removes an assigned form.

The Action ignores its own structured-property events. `failure_mode: THROW` propagates malformed
relevant events, missing definitions, and external failures. Operators must monitor pipeline health,
not only whether the CLI process is alive, and protect failed-event logs.

The pipeline name identifies the consumer group. Restarts use committed offsets; a new group with
`earliest` processes retained history. Changing the configuration does not scan events already
acknowledged. Historical backfill is outside this worker's event-driven scope.

## Runtime

Python 3.11 and CLI/Actions 1.6.0.16 are used with GMS 1.3.0. No GMS extension is installed.
Company authentication, authorization, workload capacity, and multi-writer operation require target
environment validation. Local test results are recorded in [VERIFICATION.md](VERIFICATION.md).
