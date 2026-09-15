# Verification

Version 0.2.0 was tested on 15 September 2026 with synthetic metadata in a local DataHub stack.

## Release checks

| Check | Result |
| --- | --- |
| Complete `scripts/verify.sh` gate | 45 tests passed; Ruff lint and format passed; wheel built; dependencies valid |
| Fresh isolated wheel installation | Dependencies installed; CLI and Actions both 1.6.0.16 |
| Import outside the checkout | Action imported from the fresh environment's site-packages |
| Installed wheel unit tests | All 45 passed with no source PYTHONPATH |
| CLI and demo entry point | Package import, CLI version, and demo help passed |
| Real Kafka/GMS workflow using the installed wheel | All 38 scenarios passed |
| Source-to-wheel comparison | Every packaged Python module matches the release source |

The GitHub Verify workflow runs the unit, formatting, build, dependency, and installed-wheel checks
on Python 3.11 on both Ubuntu and Windows. Live Kafka/GMS tests run locally on Linux.

## Versions

- Python 3.11.15.
- `acryl-datahub` and `acryl-datahub-actions`: 1.6.0.16.
- GMS: official `acryldata/datahub-gms:v1.3.0`, reported commit
  `94885944cfc8067dcfb34072c90824d6100cfba7`.
- Kafka: `confluentinc/cp-kafka:8.0.0` in an isolated local test stack.
- GMS port 18083; Kafka port 19093; schema registry served by the local GMS.

[Version, image, source, and tested-wheel hashes](evidence/v0.2.0-versions.json).

## Live scenarios

The harness runs against the installed wheel without a source PYTHONPATH:

```bash
python tests/live_tag_assignment.py --gms-port 18083 --kafka-port 19093
```

The result manifest records each scenario individually:

- Existing tag workflow: native and ingestion tag changes, replay, removal/re-addition, exclusions,
  preservation of other forms and completed answers, restart, and stale events.
- Owner-triggered forms and population status across all 17 entity types with ownership support.
- Manually attached forms and population status on users and schema fields, covering all 19 entity
  types with forms and structured properties in GMS 1.3.
- Captured owner/form replay, later group-owner additions, and manual attachments.
- Preservation of populated status on reattachment and of unrelated structured properties.
- Initialization of explicit empty assignments and unrestricted blank-string values.
- Completion events, stale events after removal, and worker restart without resetting existing work.

[Live result manifest](evidence/v0.2.0-gms13-live-results.json).

The broader unit suite also covers configuration validation, unsupported property definitions,
malformed events, disabled rules, removed entities, read/write failures, missing read-back, and
property scope mismatches.

## Limits

GMS 1.3 rejects conditional JSON Patch `test` operations. The Action reads immediately before its
targeted property patch, but a simultaneous write to the same property between those operations
can be overwritten. Strict atomic initialization is not supported. See [DESIGN.md](DESIGN.md).

Live tests use actual GMS, Kafka, and the Actions worker. The local GMS has authentication disabled.
Company authentication, authorization, AWS MSK IAM, Kafka ACLs, custom GMS patches, production
workloads, outage recovery, high availability, and simultaneous independent writers were not tested.
Windows checks cover installation and unit/build behavior, not a Windows-to-Kafka integration run.
The transitive Authlib deprecation warning did not affect the completed checks.

The new rules were exercised through real API mutations and Kafka events, without a browser test.
The earlier tag-only release's results remain in
[evidence/gms13-cli16-live-results.json](evidence/gms13-cli16-live-results.json) and
[evidence/gms13-cli16-versions.json](evidence/gms13-cli16-versions.json).
