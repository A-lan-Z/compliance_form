# Tag-triggered form assignment

## Contract

A newly added direct table tag establishes eligibility for attaching an existing form to that same
table. The worker checks current metadata before assignment and confirms the assignment afterward.
It leaves ownership, answers, existing forms, and tag removals to DataHub's native workflows.

## Components

- `events.py` decodes native MetadataChangeLog events and compares current and previous tag sets.
- `service.py` applies the configured mapping and checks current table eligibility and assignment.
- `datahub.py` reads typed aspects and invokes the native `batchAssignForm` GraphQL mutation.
- `action.py` adapts the Actions Framework event/context and validates configuration at startup.
- `demo.py` provisions synthetic local definitions and tables for the interactive walkthrough.

The adapter uses the framework's underlying SDK graph client. It propagates GraphQL failures and
uses the configured identity without adding an administrator impersonation header. A true mutation
response is followed by a forms-aspect read: some native assignment paths can skip entities while
returning success.

## Processing decisions

The event must add a configured direct `globalTags` tag to a dataset. Its current subtype must be
exactly `[Table]`, its status must be active, and the tag must still be present. Missing subtype,
views, containers, columns, inherited tags, and unrelated aspects are skipped.

An assignment is skipped if the form is already incomplete or completed. The native form state is
the replay guard; there is no local state database. This preserves progress in the sequential
replay/restart tests. Removing a tag retains the form. If a form was manually removed, a later
qualifying addition or replay may restore it.

The pipeline name is the stable consumer identity. A new consumer starts at retained history with
`auto.offset.reset: earliest`; normal restarts use committed offsets. Retention expiry can leave
historical gaps. Adding a mapping does not rescan acknowledged events.

Missing tag/form definitions fail startup. Malformed relevant events and read/write failures are
reported through the framework with `failure_mode: THROW`; operators repair and restart. Monitor
pipeline health because process liveness alone does not establish that it is still processing.

## Boundaries

The runtime is pinned to CLI/Actions 1.6.0.16. GMS 1.3.0 and its matching frontend passed the local
compatibility checks in VERIFICATION.md. There is no custom GMS or frontend extension in this repo.

Run one worker. Native form assignment reads and rewrites an aspect, and the current-tag check is a
separate operation. This does not provide compare-and-swap or transactional guarantees against
independent concurrent writers. Local tests do not establish company authentication, authorization,
throughput, outage recovery, or high availability.

Form definitions, Structured Properties, and assignees must be configured separately. Completion is
DataHub's native form flow. This Action has no email sender, notification state, or review scheduler.
