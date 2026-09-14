# DataHub tag-to-form Action

Automatically attach an existing DataHub form when a configured tag is added directly to a table.
This repository contains the standalone Python Action, configuration, tests, and a local demo.

```text
Table tag added -> Kafka metadata event -> Action checks current metadata -> GMS assigns form
```

The runtime is pinned to **CLI/Actions 1.6.0.16**, with **GMS 1.3.0** verified locally. Use Python
3.11. See [verification evidence](VERIFICATION.md) for the checks and their limits.

## Install and run

Clone this repository, then run these commands from its root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m pip check
datahub version
```

Configure the connections below and edit [config/tag-form-action.yaml](config/tag-form-action.yaml),
then start the worker:

```bash
datahub actions -c config/tag-form-action.yaml
```

This command stays running and consumes events. Deploy one worker under your normal service or
container supervisor. Keep the pipeline `name` stable across restarts so it resumes its Kafka offsets.
The worker needs network access to GMS, Kafka brokers, and the schema registry.

### Run directly from source

Installing this repository as a package is optional. Keep `src/dcl_form_assignment/` and the YAML
configuration together, install the framework into your Python 3.11 environment, and run:

```bash
python -m pip install 'acryl-datahub-actions==1.6.0.16'
PYTHONPATH="$PWD/src" datahub actions -c config/tag-form-action.yaml
```

`PYTHONPATH` makes the Action's modules importable for that command. No wheel or PyPI publication
is required. For a packaged deployment, install the wheel produced by the verification script and
copy the YAML separately.

## Configure company deployment

The example YAML maps synthetic local identifiers. Replace them with exact tag and form URNs:

```yaml
action:
  type: "dcl_form_assignment.action:TagFormAssignmentAction"
  config:
    tag_to_form:
      "urn:li:tag:YOUR_TAG": "urn:li:form:YOUR_FORM"
```

Both definitions must already exist. The Action validates them at startup. If the form uses
Structured Properties, provision those as part of the form definition. Set the form's assignees;
for owner-assigned forms, users must be owners of the table to access completion controls.

Supply these settings through the worker's environment:

| Variable | Purpose |
| --- | --- |
| `DATAHUB_GMS_URL` | GMS base URL, not the frontend URL or `/api/graphql` path |
| `DATAHUB_GMS_AUTHORIZATION` | Full authorization header, normally `Bearer <token>` |
| `KAFKA_BOOTSTRAP_SERVER` | Kafka bootstrap brokers |
| `SCHEMA_REGISTRY_URL` | Schema registry endpoint |
| `METADATA_CHANGE_LOG_VERSIONED_TOPIC_NAME` | Optional override for `MetadataChangeLog_Versioned_v1` |
| `PLATFORM_EVENT_TOPIC_NAME` | Optional override for `PlatformEvent_v1` |

Inject credentials from your approved secret store. The YAML defaults are for local development.
Configure Kafka and schema-registry TLS/SASL using the pinned framework's connection settings for
your infrastructure. The GMS identity needs reads of tags, subtype/status, forms, and form
definitions, plus form-assignment privileges. Company authentication and policies require a target
environment test; the local version test used a no-auth GMS.

The initial consumer policy is `auto.offset.reset: earliest`. With no saved offset, retained tag
additions can trigger assignments on existing tables. Review that first-start behavior before
production rollout. Normal restarts use committed offsets. This is not a complete historical scan.

## Behavior

- Qualifying entities are active `dataset` URNs with subtype exactly `[Table]`.
- Only newly added direct entity tags trigger processing. Views, containers, columns, inherited
  tags, missing/ambiguous subtypes, and changes to ownership or answers are excluded.
- The tag must still be present when the worker checks current GMS metadata.
- The Action attaches an existing form only when absent from both incomplete and completed forms.
- Replay, retagging, and restart preserve existing form progress in the verified sequential cases.
- Removing a tag leaves its form attached. A later qualifying addition/replay can restore a
  manually removed form; there is no continuous reconciliation or backfill scan.
- The Action does not create form definitions, assign owners, submit answers, or send notifications.

Processing errors propagate with `failure_mode: THROW`. Monitor pipeline processing and failed
records; a stopped pipeline can leave the CLI process alive. Investigate and restart using the
same pipeline identity after correcting the fault. Protect failed-event logs and avoid debug
logging of company metadata. Normal outcomes include entity/tag URNs.

Run one worker. Native assignment is a read/modify/write operation and the tag check is separate
from the assignment. Simultaneous independent writers, atomicity across these operations, throughput,
and high availability are not established by the local tests. See [DESIGN.md](DESIGN.md).

## Local walkthrough

Start a local DataHub stack with matching GMS/frontend versions, Kafka, and the schema registry.
The defaults are GMS `127.0.0.1:8080` and Kafka `127.0.0.1:9092`.

1. Run `dcl-tag-form-demo setup` and copy the generated table URN. This creates synthetic metadata,
   with no tag or assigned form, and does not connect to a database source.
2. Start `datahub actions -c config/tag-form-action.yaml` in another activated terminal and wait for
   its Kafka partition assignment.
3. Open the synthetic table in DataHub and add `dcl.poc.requires-compliance` to the table's Tags.
4. Refresh and find **Awaiting Documentation**. Add the signed-in user as an owner, expand the
   card, and choose **Complete Documentation**.
5. Select an answer and save. The card changes to **Documented**; the answer is a Structured
   Property on the table.

The demo CLI also supports `tag --entity '<URN>'` and `status --entity '<URN>'`. Add
`--server http://127.0.0.1:<port>` for another local GMS port and configure the worker's endpoints
accordingly. The demo refuses non-local GMS hosts and non-synthetic table names. Ctrl+C stops the
worker; synthetic metadata remains available for inspection.

## Development and verification

```bash
python -m pip install '.[dev]'
DCL_ACTION_PYTHON=.venv/bin/python bash scripts/verify.sh
```

The same gate runs in GitHub Actions: unit tests, Ruff lint/format checks, wheel build, and dependency
validation. CI also verifies that the installed wheel's plugin and CLI entry point work outside the
checkout. The wheel is `dist/dcl_form_assignment_poc-0.1.0-py3-none-any.whl`.

For opt-in integration testing against local services:

```bash
python tests/live_tag_assignment.py --gms-port 8080 --kafka-port 9092
```

The harness uses the installed package and the Actions CLI beside its Python interpreter. It runs
10 scenarios through real Kafka/GMS, starts and stops its own worker, creates unique synthetic
fixtures, and prints its evidence directory under `/tmp`. Schema registry is served under GMS at
`/schema-registry/api/`. Alternate ports support a separate local stack; company endpoints are
not accepted by this test command.

## Files

- `src/dcl_form_assignment/`: Action, event decoding, assignment service, GMS adapter, local demo.
- `config/tag-form-action.yaml`: pipeline and tag-to-form mapping.
- `pyproject.toml`: optional package installation and pinned framework dependency.
- `tests/` and `scripts/verify.sh`: unit and live verification.
- `DESIGN.md` and `VERIFICATION.md`: contract, limits, and tested version evidence.
